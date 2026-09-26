"""
Temporal Monitoring & Change Detection API Endpoints.
Routes for survey-to-survey comparison initialization, ICP alignment,
geometric change quantification, deterioration evolution tracking, and site timelines.
"""
from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.heritage import TemporalComparison
from app.schemas.temporal import (
    TemporalComparisonCreateRequest,
    TemporalAlignmentRequest,
    TemporalChangeDetectRequest,
    TemporalDamageTrackRequest,
    TemporalComparisonSummary,
    TemporalChangeRecordItem,
    TemporalTimelineItem,
)
from app.services.temporal_service import temporal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/temporal", tags=["Temporal Monitoring & Change Detection"])


@router.post(
    "/compare",
    response_model=TemporalComparisonSummary,
    summary="Create or initialize a temporal comparison between baseline T1 and target T2",
)
def create_comparison(
    request: TemporalComparisonCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Validates survey pairing (same site, different dates/IDs, valid reconstructions)
    and initializes a TemporalComparison record.
    """
    comparison = temporal_service.create_or_get_comparison(request, db)
    return temporal_service.get_comparison_summary(comparison.id, db)


@router.post(
    "/{comparison_id}/align",
    summary="Execute reconstruction alignment using Open3D ICP",
)
def align_reconstructions(
    comparison_id: str,
    request: Optional[TemporalAlignmentRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Applies initial centroid positioning and Open3D ICP refinement
    to register comparison survey geometry onto baseline coordinate frame.
    """
    req = request or TemporalAlignmentRequest()
    result = temporal_service.run_alignment(comparison_id, req, db)
    return {
        "status": "success",
        "alignment_result": result.to_dict(),
        "comparison_summary": temporal_service.get_comparison_summary(comparison_id, db),
    }


@router.post(
    "/{comparison_id}/detect-change",
    summary="Quantify geometric distance field between aligned reconstructions",
)
def detect_geometric_change(
    comparison_id: str,
    request: Optional[TemporalChangeDetectRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Computes point-to-point distance residuals and identifies candidate geometric change clusters.
    """
    req = request or TemporalChangeDetectRequest()
    report = temporal_service.run_geometric_change_detection(comparison_id, req, db)
    return {
        "status": "success",
        "geometric_change_report": report.to_dict(),
        "comparison_summary": temporal_service.get_comparison_summary(comparison_id, db),
    }


@router.post(
    "/{comparison_id}/track-deterioration",
    summary="Match Phase 6 3D mapped damage points across surveys and classify evolution",
)
def track_deterioration(
    comparison_id: str,
    request: Optional[TemporalDamageTrackRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Associates Phase 6 3D mapped defects across baseline T1 and comparison T2.
    Identifies PERSISTING_DETERIORATION, NEW_DETERIORATION, and POSSIBLY_RESOLVED_OR_UNDETECTED states.
    """
    req = request or TemporalDamageTrackRequest()
    records = temporal_service.run_deterioration_tracking(comparison_id, req, db)
    return {
        "status": "success",
        "records_created": len(records),
        "comparison_summary": temporal_service.get_comparison_summary(comparison_id, db),
    }


@router.post(
    "/{comparison_id}/run-full-pipeline",
    response_model=TemporalComparisonSummary,
    summary="Execute alignment, geometric change detection, and deterioration tracking in sequence",
)
def run_full_temporal_pipeline(
    comparison_id: str,
    alignment_req: Optional[TemporalAlignmentRequest] = None,
    change_req: Optional[TemporalChangeDetectRequest] = None,
    track_req: Optional[TemporalDamageTrackRequest] = None,
    db: Session = Depends(get_db),
):
    """Convenience endpoint executing full Phase 7 pipeline end-to-end."""
    align_r = alignment_req or TemporalAlignmentRequest()
    change_r = change_req or TemporalChangeDetectRequest()
    track_r = track_req or TemporalDamageTrackRequest()

    temporal_service.run_alignment(comparison_id, align_r, db)
    temporal_service.run_geometric_change_detection(comparison_id, change_r, db)
    temporal_service.run_deterioration_tracking(comparison_id, track_r, db)

    return temporal_service.get_comparison_summary(comparison_id, db)


@router.get(
    "/{comparison_id}",
    response_model=TemporalComparisonSummary,
    summary="Get summary metrics, registration status, and metadata for a comparison",
)
def get_comparison(
    comparison_id: str,
    db: Session = Depends(get_db),
):
    return temporal_service.get_comparison_summary(comparison_id, db)


@router.get(
    "/{comparison_id}/changes",
    response_model=List[TemporalChangeRecordItem],
    summary="Retrieve localized temporal change records with optional status or material filters",
)
def get_comparison_changes(
    comparison_id: str,
    change_status: Optional[str] = Query(None, description="Filter by change_status"),
    material_class: Optional[str] = Query(None, description="Filter by material_class"),
    deterioration_type: Optional[str] = Query(None, description="Filter by deterioration_type"),
    db: Session = Depends(get_db),
):
    return temporal_service.get_comparison_changes(
        comparison_id=comparison_id,
        db=db,
        change_status=change_status,
        material_class=material_class,
        deterioration_type=deterioration_type,
    )


@router.get(
    "/site/{site_id}/timeline",
    response_model=List[TemporalTimelineItem],
    summary="Retrieve chronological survey history and defect progression for a site",
)
def get_site_timeline(
    site_id: str,
    db: Session = Depends(get_db),
):
    return temporal_service.get_site_timeline(site_id, db)


@router.get(
    "/site/{site_id}/comparisons",
    response_model=List[TemporalComparisonSummary],
    summary="List all temporal comparisons created for a site",
)
def get_site_comparisons(
    site_id: str,
    db: Session = Depends(get_db),
):
    comparisons = (
        db.query(TemporalComparison)
        .filter(TemporalComparison.site_id == site_id)
        .order_by(TemporalComparison.created_at.desc())
        .all()
    )
    return [temporal_service.get_comparison_summary(c.id, db) for c in comparisons]
