"""
Deterioration Detection API Endpoints.
Provides endpoints for:
- Configurable physical defect taxonomy registry (CRUD)
- Model registry and provenance introspection
- Direct image defect detection with material-aware association
- Survey-level batch defect analysis and cross-tabulation (material x damage)
- Dataset structure and bounding box validation
- Transfer-learning model training with genuine evaluation metrics
"""
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
from app.services.deterioration_service import deterioration_service
from app.schemas.deterioration import (
    DeteriorationClassItem,
    DeteriorationClassCreate,
    DeteriorationClassUpdate,
    DeteriorationPredictionResponse,
    SurveyDeteriorationAnalysisSummary,
    DeteriorationDatasetValidationReport,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deterioration", tags=["Deterioration Detection & Segmentation"])


# -------------------------------------------------------------
# 1. Configurable Deterioration Classes Registry
# -------------------------------------------------------------
@router.get("/classes", response_model=List[DeteriorationClassItem])
def get_deterioration_classes():
    """Returns the list of all configured physical deterioration classes."""
    return deterioration_service.get_classes()


@router.post("/classes", response_model=DeteriorationClassItem, status_code=status.HTTP_201_CREATED)
def create_deterioration_class(class_data: DeteriorationClassCreate):
    """Registers a new deterioration class in the configurable taxonomy."""
    try:
        return deterioration_service.add_class(class_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/classes/{class_id}", response_model=DeteriorationClassItem)
def update_deterioration_class(class_id: str, class_data: DeteriorationClassUpdate):
    """Updates properties (name, description, color, severity weight) of an existing defect class."""
    updated = deterioration_service.update_class(class_id, class_data)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Deterioration class '{class_id}' not found.")
    return updated


@router.post("/classes/reset", response_model=List[DeteriorationClassItem])
def reset_deterioration_classes():
    """Resets the defect taxonomy to baseline heritage categories."""
    return deterioration_service.reset_classes()


# -------------------------------------------------------------
# 2. Model Registry & Provenance
# -------------------------------------------------------------
@router.get("/models")
def list_deterioration_models():
    """
    Returns available deterioration detection models (trained transfer learning + demo).
    Includes architecture provenance, class mapping, and genuine evaluation metrics.
    """
    return deterioration_service.get_models()


# -------------------------------------------------------------
# 3. Direct Image Detection with Material Association
# -------------------------------------------------------------
@router.post("/predict", response_model=DeteriorationPredictionResponse)
async def predict_deterioration(
    file: Optional[UploadFile] = File(None),
    image_id: Optional[str] = Form(None),
    model_id: Optional[str] = Form("auto"),
    confidence_threshold: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Detects physical deterioration defects on an uploaded image or database image.
    Associates detected defect regions with substrate materials when available.
    """
    if file:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        return deterioration_service.predict_image(
            image_input=content,
            image_id=image_id,
            db=db,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )
    elif image_id:
        db_img = deterioration_service._resolve_image_path(
            db.query(Image).filter(Image.id == image_id).first()
        )
        if not db_img or not db_img.exists():
            raise HTTPException(status_code=404, detail=f"Image with id '{image_id}' not found on disk.")

        return deterioration_service.predict_image(
            image_input=db_img,
            image_id=image_id,
            db=db,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either an uploaded 'file' or a valid 'image_id'."
        )


# -------------------------------------------------------------
# 4. Survey-Level Batch Deterioration Analysis
# -------------------------------------------------------------
@router.post("/surveys/{survey_id}/analyze", response_model=SurveyDeteriorationAnalysisSummary)
def analyze_survey_deterioration(
    survey_id: str,
    model_id: Optional[str] = Query(None, description="Model identifier or None for default/active"),
    confidence_threshold: Optional[float] = Query(None, description="Confidence threshold override"),
    db: Session = Depends(get_db),
):
    """
    Executes deterioration detection across all images in a survey.
    Associates defects with substrate materials and produces cross-tabulation summary.
    """
    try:
        return deterioration_service.analyze_survey(
            db=db,
            survey_id=survey_id,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Survey deterioration analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/surveys/{survey_id}/results", response_model=SurveyDeteriorationAnalysisSummary)
def get_survey_deterioration_results(
    survey_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves the latest deterioration analysis summary and cross-tabulation for a survey.
    """
    summary = deterioration_service.get_survey_results(db=db, survey_id=survey_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"No deterioration analysis results found for survey '{survey_id}'. Run analysis first."
        )
    return summary


# -------------------------------------------------------------
# 5. Dataset Validation & Model Training
# -------------------------------------------------------------
@router.post("/dataset/validate", response_model=DeteriorationDatasetValidationReport)
def validate_deterioration_dataset(
    dataset_path: str = Body(..., embed=True, description="Filesystem directory path to dataset"),
):
    """
    Validates dataset directory for annotations, bounding-box geometry, corrupt files, and class balance.
    """
    return deterioration_service.validate_dataset(dataset_path)


@router.post("/models/train")
def train_deterioration_model(
    dataset_dir: str = Body(..., embed=True),
    output_dir: str = Body("models/deterioration/active", embed=True),
    architecture: str = Body("fasterrcnn_mobilenet_v3_large_fpn", embed=True),
    epochs: int = Body(5, embed=True),
    batch_size: int = Body(4, embed=True),
    lr: float = Body(1e-4, embed=True),
    device: str = Body("cpu", embed=True),
):
    """
    Trains a transfer-learning object detection model on physical defect annotations.
    Strict research safety: Evaluates and records real metrics (no fabrication).
    """
    from app.ml.deterioration_trainer import DeteriorationModelTrainer, HAS_TORCH

    if not HAS_TORCH:
        raise HTTPException(
            status_code=503,
            detail="PyTorch and torchvision are required in the environment to perform training."
        )

    dataset_p = Path(dataset_dir)
    if not dataset_p.exists():
        raise HTTPException(status_code=400, detail=f"Dataset directory not found: {dataset_dir}")

    try:
        trainer = DeteriorationModelTrainer(base_architecture=architecture, device=device)
        result = trainer.train(
            dataset_dir=dataset_p,
            output_dir=Path(output_dir),
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=lr,
        )
        return result
    except Exception as e:
        logger.error(f"Deterioration model training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")
