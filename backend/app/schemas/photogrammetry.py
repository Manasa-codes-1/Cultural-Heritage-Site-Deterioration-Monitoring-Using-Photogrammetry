from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ReconstructionTriggerRequest(BaseModel):
    engine: str = Field(
        default="auto",
        description="Reconstruction engine: 'auto' (detects COLMAP or falls back to mock), 'colmap', or 'mock'"
    )
    dense: bool = Field(default=True, description="Run dense multi-view stereo reconstruction")
    generate_mesh: bool = Field(default=True, description="Generate surface mesh from point cloud")
    force: bool = Field(default=False, description="Force re-run even if existing reconstruction completed")


class ReconstructionStatusResponse(BaseModel):
    id: str
    survey_id: str
    engine: str
    status: str
    current_stage: str
    progress_percent: int
    is_demo: bool
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CameraPoseModel(BaseModel):
    image_id: Optional[str] = None
    image_name: Optional[str] = None
    position: List[float]  # [x, y, z]
    rotation: Optional[List[float]] = None  # quaternion [x, y, z, w] or euler


class BoundingBoxModel(BaseModel):
    min: List[float]
    max: List[float]
    centroid: List[float]
    dimensions: List[float]


class ReconstructionResponse(BaseModel):
    id: str
    survey_id: str
    engine: str
    engine_version: Optional[str] = None
    status: str
    current_stage: str
    progress_percent: int

    sparse_point_cloud_path: Optional[str] = None
    dense_point_cloud_path: Optional[str] = None
    mesh_path: Optional[str] = None
    texture_path: Optional[str] = None
    workspace_path: Optional[str] = None
    log_path: Optional[str] = None

    camera_count: int = 0
    registered_image_count: int = 0
    point_count: int = 0
    sparse_point_count: int = 0
    dense_point_count: int = 0
    mesh_vertex_count: int = 0
    mesh_triangle_count: int = 0
    mean_reprojection_error: Optional[float] = None

    camera_poses: Optional[List[Dict[str, Any]]] = None
    bounding_box: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None

    is_demo: bool = False
    error_message: Optional[str] = None
    processing_logs: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PhotogrammetryAvailabilityResponse(BaseModel):
    colmap_available: bool
    colmap_path: Optional[str] = None
    colmap_version: Optional[str] = None
    cuda_available: bool
    gpu_info: Optional[str] = None
    open3d_available: bool
    open3d_version: Optional[str] = None
    recommended_engine: str
    system_notes: List[str]
