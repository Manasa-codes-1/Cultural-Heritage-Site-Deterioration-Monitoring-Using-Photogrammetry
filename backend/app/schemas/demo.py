"""
Pydantic schemas for the Integrated Demo pipeline.
Supports the end-to-end demonstration across Phases 1–7.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DemoImageItem(BaseModel):
    id: str
    filename: str
    width: Optional[int] = None
    height: Optional[int] = None
    blur_score: Optional[float] = None
    blur_status: Optional[str] = None
    brightness_score: Optional[float] = None
    brightness_status: Optional[str] = None
    quality_score: Optional[float] = None
    is_usable: bool = True
    download_url: str
    mask_filename: Optional[str] = None
    mask_url: Optional[str] = None


class DemoPhase1Quality(BaseModel):
    total_images: int
    usable_images: int
    average_blur: float
    images: List[DemoImageItem]


class DemoPhase2Matching(BaseModel):
    readiness_status: str
    pairs_analyzed: int
    good_pairs: int
    warning_pairs: int
    poor_pairs: int
    average_good_matches: float
    recommendations: List[str] = []


class DemoPhase3Reconstruction(BaseModel):
    reconstruction_id: str
    point_count: int
    mesh_vertex_count: int
    mesh_face_count: int
    ply_url: Optional[str] = None
    obj_url: Optional[str] = None
    scale_status: str = "LOCAL"
    is_demo: bool = True
    disclaimer: str = "DEMO / SYNTHETIC GEOMETRY — NOT A FIELD PHOTOGRAMMETRY RECONSTRUCTION"


class DemoPhase4Materials(BaseModel):
    primary_material: str
    average_confidence: float
    material_distribution: Dict[str, int]
    is_demo: bool = True
    inference_mode: str = "demo"


class DemoDetectionItem(BaseModel):
    id: str
    image_id: str
    image_filename: str
    damage_type: str
    confidence: float
    status: str
    bounding_box: Optional[Dict[str, int]] = None
    polygon: Optional[List[Dict[str, int]]] = None
    material_class: str = "UNKNOWN"
    material_confidence: Optional[float] = None
    mask_filename: Optional[str] = None
    mask_url: Optional[str] = None
    is_demo: bool = True


class DemoPhase5Deterioration(BaseModel):
    total_detections: int
    detections: List[DemoDetectionItem]
    damage_distribution: Dict[str, int]
    is_demo: bool = True
    disclaimer: str = "DEMO DETERIORATION INFERENCE — EVALUATED ON REAL DEEPCRACK BENCHMARK IMAGES"


class DemoMappingItem(BaseModel):
    id: str
    detection_id: str
    image_filename: str
    damage_type: str
    material_class: str
    world_point: Optional[Dict[str, float]] = None
    mapping_status: str
    reprojection_error_px: Optional[float] = None
    is_demo: bool = True


class DemoPhase6DamageMapping(BaseModel):
    total_mapped: int
    mappings: List[DemoMappingItem]
    scale_status: str = "LOCAL"
    is_demo: bool = True
    disclaimer: str = "3D Damage Location: DEMO / SYNTHETIC MAPPING"


class DemoChangeItem(BaseModel):
    id: str
    change_status: str
    deterioration_type: str
    material_class: str
    material_status: str
    spatial_distance: Optional[float] = None
    baseline_point: Optional[Dict[str, float]] = None
    comparison_point: Optional[Dict[str, float]] = None
    notes: Optional[str] = None


class DemoPhase7Temporal(BaseModel):
    comparison_id: str
    elapsed_days: int
    alignment_method: str
    fitness: float
    rmse: float
    scale_status: str = "LOCAL"
    total_changes: int
    persisting_count: int
    new_count: int
    possibly_resolved_count: int
    change_records: List[DemoChangeItem]
    is_demo: bool = True
    disclaimer: str = "Temporal Comparison: SYNTHETIC DEMONSTRATION (Simulated change for workflow demonstration)"


class DemoFinalSummary(BaseModel):
    site_name: str = "Demo Heritage Structure"
    survey_epochs: str = "T1 (Initial) → T2 (Follow-up)"
    elapsed_days: int = 152
    material: str
    material_confidence: float
    deterioration: str
    deterioration_confidence: float
    deterioration_3d_location: str
    temporal_status: str
    temporal_displacement: Optional[float] = None
    scale_status: str = "LOCAL"
    reliability_indicators: Dict[str, Any]
    is_demo: bool = True


class DataProvenance(BaseModel):
    image_data: str = "DeepCrack optical benchmark dataset (real images)"
    image_masks: str = "DeepCrack training masks (ground-truth reference)"
    photogrammetry_3d: str = "Existing project MockPhotogrammetryEngine (synthetic geometry)"
    material_classification: str = "Existing project demo material inference"
    deterioration_detection: str = "Existing project demo detector on real DeepCrack imagery"
    damage_3d_mapping: str = "Existing project raycasting on synthetic geometry"
    temporal_monitoring: str = "Existing project ICP alignment and change detection on simulated T1/T2 epochs"
    overall_classification: str = "HYBRID DEMONSTRATION DATASET — NOT A REAL FIELD SURVEY"


class IntegratedDemoResponse(BaseModel):
    success: bool = True
    site_id: str
    site_name: str
    survey_t1_id: str
    survey_t1_name: str
    survey_t2_id: str
    survey_t2_name: str
    provenance: DataProvenance = Field(default_factory=DataProvenance)
    phase1_quality: DemoPhase1Quality
    phase2_matching: DemoPhase2Matching
    phase3_reconstruction: DemoPhase3Reconstruction
    phase4_materials: DemoPhase4Materials
    phase5_deterioration: DemoPhase5Deterioration
    phase6_damage_mapping: DemoPhase6DamageMapping
    phase7_temporal: DemoPhase7Temporal
    final_summary: DemoFinalSummary


class DemoStatusResponse(BaseModel):
    initialized: bool
    site_id: Optional[str] = None
    survey_t1_id: Optional[str] = None
    survey_t2_id: Optional[str] = None
    comparison_id: Optional[str] = None
    last_run_at: Optional[str] = None
    deepcrack_available: bool = False
    deepcrack_image_count: int = 0
