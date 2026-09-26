"""
Pydantic Schemas for Material Classification Pipeline.
Supports material class taxonomies, prediction requests/responses,
dataset validation reports, model registry metadata, and survey-level material distributions.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MaterialClassItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    color: str = "#38bdf8"
    enabled: bool = True
    is_default: bool = False


class MaterialClassCreate(BaseModel):
    id: str = Field(..., description="Unique alphanumeric identifier (e.g. 'limestone')")
    name: str = Field(..., description="Human-readable material name")
    description: Optional[str] = ""
    color: Optional[str] = "#38bdf8"


class MaterialClassUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    enabled: Optional[bool] = None


class TopKPrediction(BaseModel):
    material: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class MaterialPredictionResponse(BaseModel):
    material: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    status: str = Field(..., description="'CONFIDENT' or 'LOW_CONFIDENCE'")
    recommendation: Optional[str] = None
    top_k: List[TopKPrediction] = []
    model_name: str
    model_version: Optional[str] = None
    inference_mode: str = Field(..., description="'real_trained' or 'demo'")
    is_demo: bool = False
    region: Optional[Dict[str, Any]] = None
    image_id: Optional[str] = None
    disclaimer: str = (
        "Material classification outputs represent model predictions and associated confidence values. "
        "They should not be interpreted as definitive material identification without appropriate validation or expert verification."
    )


class MaterialPredictRequest(BaseModel):
    image_id: Optional[str] = None
    region: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional bounding box crop region: {'x': int, 'y': int, 'w': int, 'h': int}",
    )
    model_id: Optional[str] = Field(default="auto", description="'auto', 'demo', or model identifier")


class DatasetValidationReport(BaseModel):
    status: str = Field(..., description="'VALID', 'WARNING', or 'INVALID'")
    dataset_path: str
    class_counts: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Split counts: {'train': {'brick': 50, ...}, 'val': {...}, 'test': {...}}",
    )
    total_samples: int = 0
    num_classes: int = 0
    classes_found: List[str] = []
    missing_classes: List[str] = []
    imbalance_ratio: Optional[float] = None
    warnings: List[str] = []
    errors: List[str] = []
    recommendation: str
    research_note: str = (
        "Dataset validation verifies structural integrity and sample counts; "
        "it does not scientifically certify domain generalization or dataset representativeness."
    )


class MaterialModelSummary(BaseModel):
    id: str
    name: str
    architecture: str
    version: str
    training_date: Optional[str] = None
    dataset_identifier: Optional[str] = None
    classes: List[str] = []
    is_demo: bool = False
    is_active: bool = False
    metrics: Optional[Dict[str, Any]] = None  # None if model has not been evaluated


class MaterialDetectionRecord(BaseModel):
    id: str
    survey_id: str
    image_id: Optional[str] = None
    reconstruction_id: Optional[str] = None
    material_class: str
    confidence: float
    status: str = "CONFIDENT"
    bounding_box: Optional[Dict[str, Any]] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    inference_mode: str = "demo"
    is_demo: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class SurveyMaterialAnalysisSummary(BaseModel):
    survey_id: str
    total_images: int
    analyzed_images: int
    detections_count: int
    dominant_material: Optional[str] = None
    distribution: Dict[str, int]
    distribution_percentage: Dict[str, float]
    average_confidences: Dict[str, float]
    overall_average_confidence: float = 0.0
    low_confidence_count: int
    is_demo: bool
    model_used: str
    detections: List[MaterialDetectionRecord] = []
    disclaimer: str = (
        "Material classification outputs represent model predictions and associated confidence values. "
        "They should not be interpreted as definitive material identification without appropriate validation or expert verification."
    )

