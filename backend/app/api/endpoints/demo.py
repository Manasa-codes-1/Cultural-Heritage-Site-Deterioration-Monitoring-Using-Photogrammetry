"""
Demo API Endpoints.
Provides REST endpoints for one-click integrated demo execution, status inspection,
ground-truth mask streaming, and demo state reset.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.demo import (
    IntegratedDemoResponse,
    DemoStatusResponse,
)
from app.services.demo_service import DemoService

router = APIRouter(prefix="/demo", tags=["Integrated Demo"])


@router.get("/status", response_model=DemoStatusResponse)
def get_demo_status(db: Session = Depends(get_db)):
    """
    Returns current demo environment status, DeepCrack dataset availability,
    and whether the demo survey pair has been initialized.
    """
    return DemoService.get_status(db)


@router.post("/run", response_model=IntegratedDemoResponse)
def run_integrated_demo(db: Session = Depends(get_db)):
    """
    Executes the complete end-to-end demonstration across Phases 1–7.
    Uses real DeepCrack images for optical analysis and existing mock/synthetic
    engines for 3D photogrammetry and temporal registration.
    """
    try:
        return DemoService.run_integrated_demo(db)
    except FileNotFoundError as fnf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DeepCrack dataset error: {str(fnf)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrated demo pipeline failed: {str(e)}",
        )


@router.get("/mask/{filename}")
def get_ground_truth_mask(filename: str):
    """
    Streams a DeepCrack ground-truth reference mask PNG.
    """
    mask_path = DemoService.get_mask_path(filename)
    if not mask_path or not mask_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ground-truth mask '{filename}' not found.",
        )
    return FileResponse(path=str(mask_path), media_type="image/png", filename=mask_path.name)


@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)):
    """
    Resets the demo site, surveys, and reconstructions for a clean re-run.
    """
    success = DemoService.reset_demo(db)
    return {"success": success, "message": "Demo data reset successfully." if success else "No demo data found to reset."}
