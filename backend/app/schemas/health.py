from typing import Optional, Dict, Any
from pydantic import BaseModel


class SystemInfo(BaseModel):
    python_version: str
    colmap_available: bool
    colmap_path: Optional[str]
    cuda_available: bool
    gpu_name: Optional[str]
    mock_photogrammetry_enabled: bool
    mock_ml_enabled: bool
    environment: str


class HealthCheckResponse(BaseModel):
    status: str
    app_name: str
    version: str
    timestamp: str
    system_info: SystemInfo
    database_connected: bool
