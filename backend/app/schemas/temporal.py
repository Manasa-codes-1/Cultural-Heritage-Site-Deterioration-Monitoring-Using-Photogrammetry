"""
Pydantic v2 Schemas for Phase 7: Multi-Temporal Monitoring & Change Detection.
Provides strict validation for survey pairing, registration, geometric distance metrics,
deterioration evolution classification, and research provenance.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class Point3D(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    x: float
    y: float
    z: float


class TemporalComparisonCreateRequest(BaseModel):
    """Initializes a temporal comparison between baseline T1 and target T2."""
    site_id: str = Field(..., description="ID of the heritage site containing both surveys")
    baseline_survey_id: str = Field(..., description="ID of reference survey T1")
    comparison_survey_id: str = Field(..., description="ID of comparison survey T2")
    alignment_method: Optional[str] = Field(
        default="ICP_POINT_TO_POINT",
        description="Registration method: IDENTITY, CENTROID_INIT, ICP_POINT_TO_POINT, ICP_POINT_TO_PLANE"
    )
    change_threshold: Optional[float] = Field(
        default=0.02,
        ge=0.0001,
        le=10.0,
        description="Distance threshold in local/metric units above which points are considered geometric change candidates"
    )
    damage_matching_distance_threshold: Optional[float] = Field(
        default=0.15,
        ge=0.001,
        le=5.0,
        description="Max 3D Euclidean distance for matching damage instances across surveys"
    )


class TemporalAlignmentRequest(BaseModel):
    """Request parameters for point cloud / reconstruction alignment."""
    alignment_method: Optional[str] = Field(
        default="ICP_POINT_TO_POINT",
        description="IDENTITY, CENTROID_INIT, ICP_POINT_TO_POINT, ICP_POINT_TO_PLANE"
    )
    max_correspondence_distance: Optional[float] = Field(
        default=0.08,
        ge=0.001,
        le=5.0,
        description="Max correspondence distance for ICP inlier pairs"
    )
    max_iterations: Optional[int] = Field(default=50, ge=5, le=500)
    voxel_size: Optional[float] = Field(
        default=0.02,
        ge=0.001,
        le=1.0,
        description="Voxel size for downsampling during registration"
    )


class TemporalChangeDetectRequest(BaseModel):
    """Request parameters for geometric surface change detection."""
    change_threshold: Optional[float] = Field(default=0.02, ge=0.0001, le=10.0)
    voxel_size: Optional[float] = Field(default=0.02, ge=0.001, le=1.0)


class TemporalDamageTrackRequest(BaseModel):
    """Request parameters for matching Phase 6 damage instances across surveys."""
    damage_matching_distance_threshold: Optional[float] = Field(default=0.15, ge=0.001, le=5.0)


class TemporalChangeRecordItem(BaseModel):
    """Detailed observation record for a localized temporal change candidate."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    comparison_id: str
    site_id: str
    baseline_survey_id: str
    comparison_survey_id: str
    change_status: str  # NEW_DETERIORATION, PERSISTING_DETERIORATION, POSSIBLY_RESOLVED_OR_UNDETECTED, GEOMETRIC_CHANGE_WITHOUT_DETERIORATION_LABEL, NO_SIGNIFICANT_CHANGE, ALIGNMENT_UNCERTAIN
    deterioration_type: str
    material_class: str
    material_status: str  # CONSISTENT, MATERIAL_LABEL_CHANGED, UNKNOWN
    baseline_mapping_id: Optional[str] = None
    comparison_mapping_id: Optional[str] = None
    baseline_x: Optional[float] = None
    baseline_y: Optional[float] = None
    baseline_z: Optional[float] = None
    comparison_x: Optional[float] = None
    comparison_y: Optional[float] = None
    comparison_z: Optional[float] = None
    spatial_distance: Optional[float] = None
    geometry_distance: Optional[float] = None
    baseline_image_id: Optional[str] = None
    comparison_image_id: Optional[str] = None
    baseline_confidence: Optional[float] = None
    comparison_confidence: Optional[float] = None
    baseline_material_class: Optional[str] = None
    comparison_material_class: Optional[str] = None
    scale_status: str = "LOCAL"
    is_demo: bool = True
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class TemporalComparisonSummary(BaseModel):
    """Full summary of a multi-temporal comparison between surveys."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    site_name: Optional[str] = None
    baseline_survey_id: str
    baseline_survey_code: Optional[str] = None
    baseline_survey_date: Optional[datetime] = None
    comparison_survey_id: str
    comparison_survey_code: Optional[str] = None
    comparison_survey_date: Optional[datetime] = None
    elapsed_days: Optional[int] = None
    elapsed_time_formatted: str = "UNKNOWN"
    baseline_reconstruction_id: Optional[str] = None
    comparison_reconstruction_id: Optional[str] = None
    alignment_status: str
    alignment_method: str
    transformation_matrix: Optional[List[List[float]]] = None
    fitness: Optional[float] = None
    rmse: Optional[float] = None
    correspondence_count: int = 0
    scale_status: str = "LOCAL"
    change_detection_method: str
    change_threshold: float
    damage_matching_distance_threshold: float
    status: str
    summary_metrics: Dict[str, Any] = Field(default_factory=dict)
    is_demo: bool = True
    inference_mode: str = "demo"
    notes: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TemporalTimelineItem(BaseModel):
    """Represents a survey along the temporal timeline of a site."""
    survey_id: str
    survey_code: str
    survey_date: Optional[datetime] = None
    operator: Optional[str] = None
    status: str
    reconstruction_id: Optional[str] = None
    reconstruction_status: Optional[str] = None
    image_count: int = 0
    deterioration_count: int = 0
    mapped_3d_count: int = 0
