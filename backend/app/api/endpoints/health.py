import sys
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db
from app.schemas.health import HealthCheckResponse, SystemInfo

router = APIRouter(tags=["Health & System"])


def check_colmap() -> tuple[bool, str | None]:
    cmd = shutil.which(settings.COLMAP_PATH) or shutil.which("colmap")
    return (cmd is not None, cmd)


def check_gpu() -> tuple[bool, str | None]:
    try:
        import torch
        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0)
    except Exception:
        pass
    return False, "Integrated GPU / CPU Mode (No NVIDIA CUDA)"


@router.get("/health", response_model=HealthCheckResponse)
def health_check(db: Session = Depends(get_db)):
    """Comprehensive system inspection and health check endpoint."""
    # Check DB
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    colmap_found, colmap_bin = check_colmap()
    cuda_found, gpu_name = check_gpu()

    sys_info = SystemInfo(
        python_version=sys.version.split()[0],
        colmap_available=colmap_found,
        colmap_path=colmap_bin,
        cuda_available=cuda_found,
        gpu_name=gpu_name,
        mock_photogrammetry_enabled=settings.USE_MOCK_PHOTOGRAMMETRY,
        mock_ml_enabled=settings.USE_MOCK_ML,
        environment=settings.ENVIRONMENT,
    )

    return HealthCheckResponse(
        status="healthy" if db_connected else "degraded",
        app_name=settings.PROJECT_NAME,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        system_info=sys_info,
        database_connected=db_connected,
    )
