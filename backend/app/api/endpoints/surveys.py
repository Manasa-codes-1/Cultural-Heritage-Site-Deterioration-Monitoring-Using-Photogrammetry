from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.survey import SurveyCreate, SurveyUpdate, SurveyRead, SurveyDetail
from app.services.survey_service import SurveyService
from app.services.image_service import ImageService
from app.schemas.image import ImageRead

router = APIRouter(prefix="/surveys", tags=["Surveys"])


@router.get("", response_model=List[SurveyRead])
def list_surveys(
    site_id: Optional[str] = Query(None, description="Filter surveys by site ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve surveys, optionally filtered by site ID."""
    return SurveyService.get_surveys(db, site_id=site_id, skip=skip, limit=limit)


@router.post("", response_model=SurveyRead, status_code=status.HTTP_201_CREATED)
def create_survey(survey_in: SurveyCreate, db: Session = Depends(get_db)):
    """Create a new survey record under a heritage site."""
    survey = SurveyService.create_survey(db, survey_in)
    if not survey:
        raise HTTPException(
            status_code=400,
            detail=f"Target site '{survey_in.site_id}' does not exist.",
        )
    return survey


@router.get("/{survey_id}", response_model=SurveyDetail)
def get_survey(survey_id: str, db: Session = Depends(get_db)):
    """Get complete survey record including associated images."""
    survey = SurveyService.get_survey_by_id(db, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail=f"Survey '{survey_id}' not found.")

    images = ImageService.get_survey_images(db, survey_id)
    img_models = []
    for img in images:
        img_dict = ImageRead.model_validate(img)
        img_dict.download_url = f"/api/images/{img.id}/file"
        img_models.append(img_dict)

    detail = SurveyDetail.model_validate(survey)
    detail.images = img_models
    return detail


@router.put("/{survey_id}", response_model=SurveyRead)
def update_survey(survey_id: str, survey_in: SurveyUpdate, db: Session = Depends(get_db)):
    """Update survey details or environmental conditions."""
    survey = SurveyService.update_survey(db, survey_id, survey_in)
    if not survey:
        raise HTTPException(status_code=404, detail=f"Survey '{survey_id}' not found.")
    return survey


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_survey(survey_id: str, db: Session = Depends(get_db)):
    """Delete survey and all associated images and detections."""
    success = SurveyService.delete_survey(db, survey_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Survey '{survey_id}' not found.")
    return None
