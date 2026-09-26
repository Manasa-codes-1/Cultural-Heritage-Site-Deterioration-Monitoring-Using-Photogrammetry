"""
Pydantic Schemas for Deterioration Detection / Segmentation Pipeline.
Provides schemas for defect taxonomy, bounding box / polygon representations,
material-aware defect associations, dataset validation reports, and survey summaries.

STRICT RESEARCH INTEGRITY:
- Distinguishes model confidence from structural certainty.
- Explicitly captures material association status without fabrication.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DeteriorationClassItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    color: str = "#ef4444"
    enabled: bool = True
    is_default: bool = False
    severity_weight: float = 0.5


class DeteriorationClassCreate(BaseModel):
    id: str = Field(..., description="Unique alphanumeric identifier (e.g. 'crack')")
    name: str = Field(..., description="Human-readable defect title")
    description: Optional[str] = ""
    color: Optional[str] = "#ef4444"
    severity_weight: Optional[float] = Field(0.5, ge=0.0, le=1.0)


class DeteriorationClassUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    enabled: Optional[bool] = None
    severity_weight: Optional[float] = None


class CandidateMaterial(BaseModel):
    material: str
    overlap_ratio: float = 0.0
    confidence: Optional[float] = None


class DeteriorationItem(BaseModel):
    id: str
    image_id: Optional[str] = None
    survey_id: Optional[str] = None
    damage_type: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    status: str = Field(default="CONFIDENT", description="'CONFIDENT' or 'LOW_CONFIDENCE'")
    severity_hint: Optional[str] = "moderate"
    bounding_box: Optional[Dict[str, Any]] = None  # {"x": int, "y": int, "w": int, "h": int}
    polygon: Optional[List[Dict[str, Any]]] = None  # [{"x": int, "y": int}, ...]
    mask_reference: Optional[str] = None
    material_class: str = "UNKNOWN"
    material_confidence: Optional[float] = None
    material_association_status: str = Field(
        default="MATERIAL_ASSOCIATION_UNAVAILABLE",
        description="'ASSOCIATED', 'OVERLAPPING_MULTIPLE', or 'MATERIAL_ASSOCIATION_UNAVAILABLE'",
    )
    candidate_materials: List[Dict[str, Any]] = []
    notes: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    inference_mode: str = "demo"
    is_demo: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeteriorationPredictionResponse(BaseModel):
    image_id: Optional[str] = None
    detections: List[DeteriorationItem] = []
    detections_count: int = 0
    model_name: str
    model_version: Optional[str] = None
    inference_mode: str = Field(..., description="'real_trained' or 'demo'")
    is_demo: bool = True
    disclaimer: str = (
        "Deterioration predictions represent probabilistic computer vision outputs and associated model confidence values. "
        "They require architectural conservator validation and should not be interpreted as definitive physical or structural assessments."
    )


class SurveyDeteriorationAnalysisSummary(BaseModel):
    survey_id: str
    total_images: int
    analyzed_images: int
    total_detections: int
    class_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Count of detections per damage_type"
    )
    class_distribution_percentage: Dict[str, float] = Field(default_factory=dict)
    material_damage_crosstab: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Cross-tabulation: {material_class: {damage_type: count}}",
    )
    average_confidence: float = 0.0
    low_confidence_count: int = 0
    is_demo: bool = True
    model_used: str = "DemoDeteriorationDetector"
    detections: List[DeteriorationItem] = []
    disclaimer: str = (
        "Deterioration predictions represent probabilistic computer vision outputs and associated model confidence values. "
        "They require architectural conservator validation and should not be interpreted as definitive physical or structural assessments."
    )


class DeteriorationDatasetValidationReport(BaseModel):
    status: str = Field(..., description="'VALID', 'WARNING', or 'INVALID'")
    dataset_path: str
    total_images: int = 0
    total_annotations: int = 0
    num_classes: int = 0
    classes_found: List[str] = []
    missing_classes: List[str] = []
    invalid_boxes_count: int = 0
    imbalance_ratio: Optional[float] = None
    warnings: List[str] = []
    errors: List[str] = []
    recommendation: str
    research_note: str = (
        "Dataset validation verifies annotation geometry and sample counts; "
        "it does not scientifically certify domain generalization or inspection efficacy."
    )


class DeteriorationModelSummary(BaseModel):
    id: str
    name: str
    architecture: str
    version: str
    classes: List[str] = []
    is_demo: bool = False
    is_active: bool = False
    metrics: Optional[Dict[str, Any]] = None  # None if model has not been evaluated
    disclaimer: Optional[str] = None
