from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.heritage import Survey, Image
from app.schemas.matching import (
    PairMatchRequest,
    PairMatchResponse,
    SurveyReadinessResponse,
)
from app.services.matching_service import MatchingService

router = APIRouter(tags=["Image Quality & Matching"])


# ==========================================
# PHASE 1 PRESERVED ENDPOINTS
# ==========================================

@router.get("/surveys/{survey_id}/quality-summary", response_model=Dict[str, Any])
def get_survey_quality_summary(survey_id: str, db: Session = Depends(get_db)):
    """
    Get aggregate individual quality assessment statistics, pass/fail breakdowns, 
    and preliminary optical readiness for a survey. (Phase 1 Preserved)
    """
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found.")

    images = db.query(Image).filter(Image.survey_id == survey_id).all()
    total = len(images)
    if total == 0:
        return {
            "survey_id": survey_id,
            "total_images": 0,
            "status": "empty",
            "message": "No images uploaded yet.",
            "average_quality_score": 0.0,
            "pass_count": 0,
            "warning_count": 0,
            "fail_count": 0,
            "blur_failures": 0,
            "brightness_failures": 0,
            "resolution_failures": 0,
            "recommendation": "Upload images to proceed with quality inspection.",
            "ready_for_photogrammetry": False,
        }

    scores = [img.quality_score for img in images if img.quality_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    pass_count = sum(1 for img in images if img.quality_status == "pass")
    warn_count = sum(1 for img in images if img.quality_status == "warning")
    fail_count = sum(1 for img in images if img.quality_status == "fail")

    blur_fails = sum(1 for img in images if img.blur_status == "fail")
    bright_fails = sum(1 for img in images if img.brightness_status == "fail")
    res_fails = sum(1 for img in images if img.resolution_status == "fail")

    ready = total >= 3 and (fail_count / total) <= 0.30 and avg_score >= 60.0

    if total < 3:
        rec = "A minimum of 3-5 overlapping images is required for multi-view photogrammetry."
    elif fail_count > 0:
        rec = f"{fail_count} of {total} image(s) flagged with quality issues (blur/lighting). Consider recapturing flagged images for optimal point cloud density."
    else:
        rec = f"All {total} images passed optical quality checks. Dataset meets basic individual quality criteria."

    return {
        "survey_id": survey_id,
        "total_images": total,
        "average_quality_score": avg_score,
        "pass_count": pass_count,
        "warning_count": warn_count,
        "fail_count": fail_count,
        "pass_percentage": round((pass_count / total) * 100, 1),
        "blur_failures": blur_fails,
        "brightness_failures": bright_fails,
        "resolution_failures": res_fails,
        "recommendation": rec,
        "ready_for_photogrammetry": ready,
    }


# ==========================================
# PHASE 2 ADVANCED MATCHING & READINESS
# ==========================================

@router.post("/image-quality/match", response_model=PairMatchResponse)
def match_image_pair(req: PairMatchRequest, db: Session = Depends(get_db)):
    """
    Perform pairwise feature extraction and descriptor matching between two survey images.
    Returns keypoint counts, candidate matches, Lowe's ratio test filtered good matches,
    and a heuristic overlap classification.
    """
    try:
        return MatchingService.match_two_images(
            db, image_a_id=req.image_a_id, image_b_id=req.image_b_id, save_to_db=True
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Feature matching processing failure: {str(e)}"
        )


@router.post("/image-quality/surveys/{survey_id}/analyze", response_model=SurveyReadinessResponse)
def analyze_survey_readiness(survey_id: str, db: Session = Depends(get_db)):
    """
    Trigger full photogrammetric collection analysis for a survey:
    - Extracts ORB descriptors for all images
    - Performs pairwise matching across selected image combinations
    - Constructs image connectivity graph (identifying isolated and weakly connected views)
    - Computes overall collection readiness status and actionable recapture recommendations.
    """
    try:
        return MatchingService.analyze_survey_collection(db, survey_id=survey_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Survey collection analysis failed: {str(e)}"
        )


@router.get("/image-quality/surveys/{survey_id}/readiness", response_model=SurveyReadinessResponse)
def get_survey_readiness(survey_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the latest cached photogrammetric readiness assessment, connectivity graph,
    and recommendations for a survey.
    """
    readiness = MatchingService.get_survey_readiness(db, survey_id=survey_id)
    if not readiness:
        raise HTTPException(
            status_code=404,
            detail="No readiness analysis found for this survey. Upload at least 2 images and trigger analysis.",
        )
    return readiness


@router.get("/image-quality/surveys/{survey_id}/pairs", response_model=List[PairMatchResponse])
def get_survey_pairs(
    survey_id: str,
    status: Optional[str] = Query(None, description="Filter pairs by status: GOOD, WARNING, POOR"),
    db: Session = Depends(get_db),
):
    """
    Retrieve all analyzed image pairs for a survey, optionally filtered by status.
    """
    return MatchingService.get_survey_pair_matches(db, survey_id=survey_id, status_filter=status)
