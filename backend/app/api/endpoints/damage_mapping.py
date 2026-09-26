"""
REST API Endpoints for Phase 6: 2D-to-3D Damage Mapping.
Provides 3D spatial localization of deterioration detections onto photogrammetric reconstructions.
"""
from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.heritage import Deterioration3DMapping, Reconstruction
from app.schemas.damage_mapping import (
    Deterioration3DMappingItem,
    Deterioration3DMappingRequest,
    Survey3DMappingSummary,
    MappingValidationResponse,
)
from app.services.damage_mapping_service import DamageMappingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/damage-mapping", tags=["Phase 6: 2D-to-3D Damage Mapping"])
damage_mapping_service = DamageMappingService()


@router.post("/detections/{detection_id}/map", response_model=Deterioration3DMappingItem)
def map_single_detection(
    detection_id: str,
    sampling_strategy: str = Query("CENTER_ONLY", description="CENTER_ONLY, BOX_GRID, POLYGON_VERTICES, MASK_SAMPLES"),
    reprojection_threshold_px: float = Query(5.0, description="Max acceptable reprojection error in pixels"),
    db: Session = Depends(get_db),
):
    """
    Projects a single 2D deterioration detection onto the survey's 3D reconstruction.
    Intersects camera rays with the dense mesh or point cloud, computes reprojection residuals,
    and returns the spatial 3D mapping record.
    """
    mapping = damage_mapping_service.map_detection(
        detection_id=detection_id,
        db=db,
        sampling_strategy=sampling_strategy,
        reprojection_threshold_px=reprojection_threshold_px,
    )
    return DamageMappingService._convert_mapping_to_item(mapping)


@router.post("/surveys/{survey_id}/map", response_model=Survey3DMappingSummary)
def map_survey_detections(
    survey_id: str,
    request: Deterioration3DMappingRequest = Deterioration3DMappingRequest(),
    db: Session = Depends(get_db),
):
    """
    Batch maps all deterioration detections in a survey to its photogrammetric 3D model.
    Computes survey-wide mapping statistics, defect cross-tabulations, and mean reprojection error.
    """
    return damage_mapping_service.map_survey_detections(
        survey_id=survey_id,
        db=db,
        request=request,
    )


@router.get("/detections/{detection_id}", response_model=Deterioration3DMappingItem)
def get_detection_mapping(
    detection_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves the 3D mapping associated with a specific deterioration detection.
    """
    mapping = db.query(Deterioration3DMapping).filter(Deterioration3DMapping.detection_id == detection_id).first()
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"3D Mapping for detection '{detection_id}' not found.",
        )
    return DamageMappingService._convert_mapping_to_item(mapping)


@router.get("/surveys/{survey_id}", response_model=Survey3DMappingSummary)
def get_survey_mapping_summary(
    survey_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves stored 3D damage mappings and summary statistics for a survey.
    """
    return damage_mapping_service.get_survey_mapping_summary(
        survey_id=survey_id,
        db=db,
    )


@router.get("/reconstructions/{reconstruction_id}", response_model=List[Deterioration3DMappingItem])
def get_reconstruction_mappings(
    reconstruction_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves all 3D mapped deterioration detections associated with a reconstruction,
    ready for direct interactive rendering in the 3D WebGL viewer.
    """
    recon = db.query(Reconstruction).filter(Reconstruction.id == reconstruction_id).first()
    if not recon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconstruction '{reconstruction_id}' not found.",
        )

    mappings = db.query(Deterioration3DMapping).filter(
        Deterioration3DMapping.reconstruction_id == reconstruction_id
    ).all()
    return [DamageMappingService._convert_mapping_to_item(m) for m in mappings]


@router.post("/validate/{mapping_id}", response_model=MappingValidationResponse)
def validate_mapping(
    mapping_id: str,
    tolerance_px: float = Query(5.0, description="Reprojection error threshold in pixels"),
    db: Session = Depends(get_db),
):
    """
    Validates a 3D mapping by projecting its world coordinate back to the camera
    and measuring the geometric residual error in pixels.
    """
    return damage_mapping_service.validate_mapping(
        mapping_id=mapping_id,
        db=db,
        tolerance_px=tolerance_px,
    )
