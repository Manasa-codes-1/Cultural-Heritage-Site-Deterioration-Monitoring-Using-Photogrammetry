"""
Material Classification API Endpoints.
Provides endpoints for:
- Configurable material classes registry (CRUD)
- Model registry and provenance introspection
- Direct image and cropped region inference
- Survey-level batch material analysis
- Dataset structure and distribution validation
- Transfer-learning model training with genuine evaluation metrics
"""
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Body,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.material_service import material_service
from app.schemas.material import (
    MaterialClassItem,
    MaterialClassCreate,
    MaterialClassUpdate,
    MaterialPredictionResponse,
    MaterialPredictRequest,
    SurveyMaterialAnalysisSummary,
    DatasetValidationReport,
    MaterialDetectionRecord,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["Material Classification"])


# -------------------------------------------------------------
# 1. Configurable Material Classes Registry
# -------------------------------------------------------------
@router.get("/classes", response_model=List[MaterialClassItem])
def get_material_classes():
    """Returns the list of all configured material classes."""
    return material_service.get_classes()


@router.post("/classes", response_model=MaterialClassItem, status_code=status.HTTP_201_CREATED)
def create_material_class(class_data: MaterialClassCreate):
    """Registers a new material class in the configurable registry."""
    try:
        return material_service.add_class(class_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/classes/{class_id}", response_model=MaterialClassItem)
def update_material_class(class_id: str, class_data: MaterialClassUpdate):
    """Updates properties (name, description, color, enabled) of an existing material class."""
    updated = material_service.update_class(class_id, class_data)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Material class '{class_id}' not found.")
    return updated


@router.post("/classes/reset", response_model=List[MaterialClassItem])
def reset_material_classes():
    """Resets the material class registry to default baseline heritage classes."""
    return material_service.reset_classes()


# -------------------------------------------------------------
# 2. Model Registry & Provenance
# -------------------------------------------------------------
@router.get("/models")
def list_material_models():
    """
    Returns available material classification models (trained transfer learning + demo).
    Includes provenance, training architectures, and genuine evaluation metrics.
    """
    return material_service.get_models()


# -------------------------------------------------------------
# 3. Direct Image & Crop Prediction
# -------------------------------------------------------------
@router.post("/predict", response_model=MaterialPredictionResponse)
async def predict_material(
    file: Optional[UploadFile] = File(None),
    image_id: Optional[str] = Form(None),
    region_json: Optional[str] = Form(None),
    model_id: Optional[str] = Form("auto"),
    confidence_threshold: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Classifies heritage material from either an uploaded image or an existing database image.
    Supports optional bounding-box crop region: {"x": 10, "y": 20, "w": 100, "h": 100}.
    """
    region = None
    if region_json:
        try:
            region = json.loads(region_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid region JSON: {e}")

    # Case A: Direct file upload
    if file:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        return material_service.predict_image(
            image_input=content,
            region=region,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )

    # Case B: Existing Image by ID
    elif image_id:
        record = material_service.predict_image_by_id(
            db=db,
            image_id=image_id,
            region=region,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found or cannot be loaded.")

        # Map record to response format
        return MaterialPredictionResponse(
            material=record.material_class,
            confidence=record.confidence,
            status=record.status,
            recommendation=record.notes,
            top_k=[],
            model_name=record.model_name or "DemoMaterialClassifier",
            model_version=record.model_version or "v1.0",
            inference_mode=record.inference_mode,
            is_demo=record.is_demo,
            region=record.bounding_box,
            image_id=record.image_id,
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either an uploaded 'file' or a valid 'image_id'."
        )


# -------------------------------------------------------------
# 4. Survey-Level Batch Material Analysis
# -------------------------------------------------------------
@router.post("/surveys/{survey_id}/analyze", response_model=SurveyMaterialAnalysisSummary)
def analyze_survey_materials(
    survey_id: str,
    model_id: Optional[str] = Query(None, description="Model identifier or None for default/active"),
    confidence_threshold: Optional[float] = Query(None, description="Optional override for confidence threshold"),
    db: Session = Depends(get_db),
):
    """
    Executes material classification across all images in a survey.
    Persists detections in the database and returns class distribution summary.
    """
    try:
        summary = material_service.analyze_survey(
            db=db,
            survey_id=survey_id,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Survey material analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/surveys/{survey_id}/results", response_model=SurveyMaterialAnalysisSummary)
def get_survey_material_results(
    survey_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves the latest material classification summary and detections for a survey.
    """
    summary = material_service.get_survey_results(db=db, survey_id=survey_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"No material analysis results found for survey '{survey_id}'. Run analysis first."
        )
    return summary


# -------------------------------------------------------------
# 5. Dataset Validation & Model Training
# -------------------------------------------------------------
@router.post("/dataset/validate", response_model=DatasetValidationReport)
def validate_dataset_path(
    dataset_path: str = Body(..., embed=True, description="Filesystem directory path to dataset"),
):
    """
    Validates dataset directory for train/val splits, class presence, corrupt files, and class balance.
    """
    return material_service.validate_dataset(dataset_path)


@router.post("/models/train")
def train_material_model(
    dataset_dir: str = Body(..., embed=True),
    output_dir: str = Body("models/material/active", embed=True),
    architecture: str = Body("mobilenet_v3_small", embed=True),
    epochs: int = Body(5, embed=True),
    batch_size: int = Body(8, embed=True),
    lr: float = Body(1e-4, embed=True),
    device: str = Body("cpu", embed=True),
):
    """
    Trains a transfer learning model on a structured dataset directory.
    Strict research safety: Evaluates and records real metrics (no fabrication).
    """
    from app.ml.trainer import MaterialModelTrainer, HAS_TORCH

    if not HAS_TORCH:
        raise HTTPException(
            status_code=503,
            detail="PyTorch is not available in the environment to perform training."
        )

    dataset_p = Path(dataset_dir)
    if not dataset_p.exists():
        raise HTTPException(status_code=400, detail=f"Dataset directory not found: {dataset_dir}")

    try:
        trainer = MaterialModelTrainer(base_architecture=architecture, device=device)
        result = trainer.train(
            dataset_dir=dataset_p,
            output_dir=Path(output_dir),
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=lr,
        )
        return result
    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
