"""
Pydantic Schemas for Phase 6: 2D-to-3D Damage Mapping.
Strictly preserves confidence scores, material associations, demo provenance,
and geometric parameters without fabricating certainty or scale.
"""
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class Point2D(BaseModel):
    """2D Image pixel coordinates."""
    x: float = Field(..., description="Horizontal pixel coordinate (u)")
    y: float = Field(..., description="Vertical pixel coordinate (v)")


class Point3D(BaseModel):
    """3D coordinates in the reconstruction coordinate system."""
    x: float = Field(..., description="X coordinate (reconstruction local or metric)")
    y: float = Field(..., description="Y coordinate (reconstruction local or metric)")
    z: float = Field(..., description="Z coordinate (reconstruction local or metric)")


class Deterioration3DMappingPointItem(BaseModel):
    """Individual sample point mapped from image to 3D surface."""
    id: str
    mapping_id: str
    point_type: str = Field("center", description="center, box_corner, polygon_vertex, grid_point, mask_sample")
    image_point: Point2D
    world_point: Optional[Point3D] = None
    intersection_distance: Optional[float] = None
    reprojection_error_px: Optional[float] = None
    mapping_status: str = Field("MAPPED", description="MAPPED, PARTIALLY_MAPPED, NO_SURFACE_INTERSECTION")
    created_at: Optional[datetime] = None


class Deterioration3DMappingItem(BaseModel):
    """
    Core Research Representation of 3D Deterioration Mapping:
    Material + Deterioration + 3D Location + Survey + Image + Model Confidence
    """
    id: str
    mapping_id: Optional[str] = None
    detection_id: str
    image_id: str
    image_filename: Optional[str] = None
    survey_id: str
    reconstruction_id: str

    # Material classification
    material_class: str = Field("UNKNOWN", description="Substrate class from Phase 4")
    material: Optional[str] = None  # Alias for material_class
    material_confidence: Optional[float] = Field(None, description="Substrate model confidence (0.0 - 1.0)")
    material_association_status: str = Field("MATERIAL_ASSOCIATION_UNAVAILABLE")

    # Deterioration classification
    deterioration_type: str = Field(..., description="Defect type from Phase 5")
    deterioration_confidence: float = Field(..., description="Defect model confidence (0.0 - 1.0)")
    severity_hint: Optional[str] = "moderate"

    # Spatial Coordinates
    image_point: Point2D
    world_point: Optional[Point3D] = None
    ray_origin: Optional[List[float]] = None
    ray_direction: Optional[List[float]] = None
    intersection_distance: Optional[float] = None

    # Mapping diagnostics & provenance
    mapping_method: str = Field("MESH_RAYCAST", description="MESH_RAYCAST, POINT_CLOUD_APPROXIMATION")
    surface_source: str = Field("DENSE_MESH", description="DENSE_MESH, SPARSE_MESH, DENSE_POINT_CLOUD, SPARSE_POINT_CLOUD, NONE")
    mapping_status: str = Field("MAPPED", description="MAPPED, PARTIALLY_MAPPED, NO_SURFACE_INTERSECTION, MAPPING_UNAVAILABLE, MAPPING_REQUIRES_CALIBRATION, MAPPING_REQUIRES_REVIEW")
    reprojection_error_px: Optional[float] = Field(None, description="Euclidean error in pixels when reprojected to camera")
    scale_status: str = Field("LOCAL", description="LOCAL, METRIC, UNKNOWN")
    sampling_strategy: str = Field("CENTER_ONLY", description="CENTER_ONLY, BOX_GRID, POLYGON_VERTICES, MASK_SAMPLES")
    sample_point_count: int = 1
    mapped_point_count: int = 1

    # Research Provenance & Transparency
    is_demo: bool = True
    inference_mode: str = "demo"
    notes: Optional[str] = None

    # Associated sample points and 2D bbox
    points: List[Deterioration3DMappingPointItem] = []
    bounding_box: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class Deterioration3DMappingRequest(BaseModel):
    """Configuration for triggering 2D-to-3D damage mapping."""
    sampling_strategy: Optional[str] = Field("CENTER_ONLY", description="CENTER_ONLY, BOX_GRID, POLYGON_VERTICES, MASK_SAMPLES")
    reprojection_threshold_px: Optional[float] = Field(5.0, description="Max acceptable reprojection error in pixels")
    force: bool = Field(False, description="Re-compute existing mappings")


class Survey3DMappingSummary(BaseModel):
    """
    Survey-level mapping aggregation and statistics.
    Note: These reflect mapping success/coverage, NOT model detection accuracy.
    """
    survey_id: str
    reconstruction_id: Optional[str] = None
    total_eligible_detections: int = 0
    mapped_detections: int = 0
    partially_mapped_detections: int = 0
    no_intersection_detections: int = 0
    unavailable_mappings: int = 0
    mapping_success_rate: float = Field(0.0, description="Percentage of detections successfully mapped to 3D surface (NOT accuracy)")

    detections_by_type: Dict[str, int] = {}
    detections_by_material: Dict[str, int] = {}
    material_deterioration_cross_tabulation: Dict[str, Dict[str, int]] = {}

    mean_reprojection_error_px: Optional[float] = None
    surface_source_breakdown: Dict[str, int] = {}
    scale_status: str = "LOCAL"

    is_demo: bool = True
    inference_mode: str = "demo"
    mappings: List[Deterioration3DMappingItem] = []
    research_disclaimer: str = (
        "2D-to-3D mapping quality depends on the accuracy and completeness of photogrammetric "
        "camera calibration, camera poses, reconstruction geometry, and source deterioration localization. "
        "Mapped coordinates should therefore be interpreted within the documented reconstruction coordinate system and scale."
    )


class MappingValidationResponse(BaseModel):
    """Response from reprojecting a 3D mapped damage point back into image space."""
    mapping_id: str
    status: str
    reprojection_error_px: Optional[float] = None
    is_valid: bool = False
    original_point: Point2D
    reprojected_point: Optional[Point2D] = None
    world_point: Optional[Point3D] = None
    tolerance_px: float = 5.0
    notes: str
