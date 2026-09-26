"""
Photogrammetry API Endpoints.
Provides endpoints for COLMAP system diagnostic checks, reconstruction job triggering,
progress polling, metadata inspection, and streaming 3D point cloud & mesh files.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.photogrammetry import (
    ReconstructionTriggerRequest,
    ReconstructionResponse,
    ReconstructionStatusResponse,
    PhotogrammetryAvailabilityResponse,
)
from app.services.photogrammetry_service import photogrammetry_service

router = APIRouter(prefix="/photogrammetry", tags=["Photogrammetry & 3D Reconstruction"])


@router.get("/availability", response_model=PhotogrammetryAvailabilityResponse)
def check_photogrammetry_availability():
    """
    Returns system diagnostic status for photogrammetric reconstruction,
    including COLMAP installation, CUDA GPU availability, and Open3D capabilities.
    """
    return photogrammetry_service.get_system_diagnostics()


@router.post(
    "/surveys/{survey_id}/reconstruct",
    response_model=ReconstructionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_reconstruction(
    survey_id: str,
    request: ReconstructionTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Initiates asynchronous 3D photogrammetric reconstruction for a survey.
    Runs in the background and can be polled via status endpoints.
    """
    reconstruction = photogrammetry_service.trigger_reconstruction(
        survey_id=survey_id,
        request=request,
        db=db,
        background_tasks=background_tasks,
    )
    return reconstruction


@router.get("/surveys/{survey_id}/reconstruction", response_model=ReconstructionResponse)
def get_survey_reconstruction(
    survey_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves the latest 3D reconstruction record and geometric metrics for a survey.
    """
    reconstruction = photogrammetry_service.get_reconstruction_by_survey(survey_id, db)
    if not reconstruction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No 3D reconstruction found for survey '{survey_id}'.",
        )
    return reconstruction


@router.get("/reconstructions/{reconstruction_id}", response_model=ReconstructionResponse)
def get_reconstruction(
    reconstruction_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves a reconstruction by its ID.
    """
    recon = photogrammetry_service.get_reconstruction_by_id(reconstruction_id, db)
    if not recon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconstruction '{reconstruction_id}' not found.",
        )
    return recon


@router.get(
    "/reconstructions/{reconstruction_id}/status",
    response_model=ReconstructionStatusResponse,
)
def get_reconstruction_status(
    reconstruction_id: str,
    db: Session = Depends(get_db),
):
    """
    Lightweight status and stage polling endpoint for frontend reconstruction monitors.
    """
    recon = photogrammetry_service.get_reconstruction_by_id(reconstruction_id, db)
    if not recon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconstruction '{reconstruction_id}' not found.",
        )
    return recon


@router.get("/reconstructions/{reconstruction_id}/model")
def download_reconstruction_model(
    reconstruction_id: str,
    model_type: str = Query(
        default="mesh",
        description="Type of 3D asset: 'mesh', 'dense', 'sparse', 'obj'",
    ),
    db: Session = Depends(get_db),
):
    """
    Streams the requested 3D model asset (.ply, .obj) for Three.js WebGL visualization.
    """
    file_path, media_type, filename = photogrammetry_service.get_model_file(
        reconstruction_id=reconstruction_id,
        model_type=model_type,
        db=db,
    )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
        headers={"Access-Control-Allow-Origin": "*"},
    )


@router.get("/reconstructions/{reconstruction_id}/logs", response_class=PlainTextResponse)
def get_reconstruction_logs(
    reconstruction_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns full raw execution logs for photogrammetric auditing and transparency.
    """
    recon = photogrammetry_service.get_reconstruction_by_id(reconstruction_id, db)
    if not recon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconstruction '{reconstruction_id}' not found.",
        )
    return recon.processing_logs or "No logs available."
