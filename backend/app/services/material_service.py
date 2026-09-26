"""
Material Classification Service.
Coordinates ML inference, configurable class registry, survey-level analysis,
database persistence, and dataset validation.

STRICT RESEARCH INTEGRITY:
- Model confidence is strictly presented as probabilistic inference, not ground-truth certainty.
- Low-confidence detections are explicitly tagged with recommendations for manual verification.
- Real trained inference and demo modes are visibly tracked and stored.
"""
import io
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.material_config import (
    load_material_classes,
    add_material_class,
    update_material_class,
    reset_material_classes,
    get_material_class_by_id,
    get_enabled_classes,
)
from app.models.heritage import Survey, Image, MaterialDetection
from app.ml import get_material_classifier, list_available_models
from app.ml.dataset_validator import DatasetValidator
from app.schemas.material import (
    MaterialClassItem,
    MaterialClassCreate,
    MaterialClassUpdate,
    MaterialPredictionResponse,
    SurveyMaterialAnalysisSummary,
    MaterialDetectionRecord,
    DatasetValidationReport,
)

logger = logging.getLogger(__name__)


class MaterialService:
    """Core domain service for heritage substrate classification."""

    def __init__(self):
        self.validator = DatasetValidator()

    # ---------------------------------------------------------
    # 1. Configurable Material Classes Management
    # ---------------------------------------------------------
    def get_classes(self) -> List[MaterialClassItem]:
        """Returns all configured material classes."""
        classes = load_material_classes()
        return [MaterialClassItem(**c) for c in classes]

    def add_class(self, data: MaterialClassCreate) -> MaterialClassItem:
        """Adds a new material class to the registry."""
        new_item = add_material_class(data.model_dump())
        return MaterialClassItem(**new_item)

    def update_class(self, class_id: str, data: MaterialClassUpdate) -> Optional[MaterialClassItem]:
        """Updates an existing material class."""
        updated = update_material_class(class_id, data.model_dump(exclude_unset=True))
        if updated:
            return MaterialClassItem(**updated)
        return None

    def reset_classes(self) -> List[MaterialClassItem]:
        """Resets registry to default baseline heritage classes."""
        classes = reset_material_classes()
        return [MaterialClassItem(**c) for c in classes]

    # ---------------------------------------------------------
    # 2. Model Registry & Provenance
    # ---------------------------------------------------------
    def get_models(self) -> List[Dict[str, Any]]:
        """Returns all available material classifiers (trained and demo)."""
        return list_available_models()

    # ---------------------------------------------------------
    # 3. Direct Image / Crop Prediction
    # ---------------------------------------------------------
    def predict_image(
        self,
        image_input: Union[bytes, Path, str, PILImage.Image],
        region: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> MaterialPredictionResponse:
        """
        Runs material classification on an image or cropped region.
        """
        classifier = get_material_classifier(model_id)
        if confidence_threshold is not None:
            classifier.confidence_threshold = confidence_threshold

        # Parse bytes to PIL Image if necessary
        if isinstance(image_input, bytes):
            image = PILImage.open(io.BytesIO(image_input)).convert("RGB")
        else:
            image = image_input

        res = classifier.predict(image=image, region=region)
        return MaterialPredictionResponse(**res)

    @staticmethod
    def _resolve_image_path(db_image: Image) -> Optional[Path]:
        """Resolves absolute path on disk for an Image database record."""
        if hasattr(db_image, "relative_path") and db_image.relative_path:
            p = Path(db_image.relative_path)
            if p.is_absolute() and p.exists():
                return p
            data_p = settings.DATA_DIR / db_image.relative_path
            if data_p.exists():
                return data_p
        if hasattr(db_image, "file_path") and getattr(db_image, "file_path", None):
            p = Path(db_image.file_path)
            if p.exists():
                return p
        return None

    # ---------------------------------------------------------
    # 4. Database Image Prediction & Recording
    # ---------------------------------------------------------
    def predict_image_by_id(
        self,
        db: Session,
        image_id: str,
        region: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> Optional[MaterialDetectionRecord]:
        """
        Classifies an existing database image (full or crop) and persists the detection record.
        """
        db_image = db.query(Image).filter(Image.id == image_id).first()
        if not db_image:
            logger.error(f"Image not found with id: {image_id}")
            return None

        image_path = self._resolve_image_path(db_image)
        if not image_path or not image_path.exists():
            logger.error(f"Image file does not exist on disk for image ID: {image_id}")
            return None

        # Predict
        pred = self.predict_image(
            image_input=image_path,
            region=region,
            model_id=model_id,
            confidence_threshold=confidence_threshold,
        )

        # Create or update MaterialDetection record
        detection = MaterialDetection(
            survey_id=db_image.survey_id,
            image_id=db_image.id,
            material_class=pred.material,
            material_type=pred.material,
            confidence=pred.confidence,
            status=pred.status,
            top_k_predictions=[p.model_dump() for p in pred.top_k],
            bounding_box=pred.region,
            model_name=pred.model_name,
            model_version=pred.model_version,
            inference_mode=pred.inference_mode,
            is_demo=pred.is_demo,
            is_mock=pred.is_demo,
            notes=pred.recommendation,
        )
        db.add(detection)
        db.commit()
        db.refresh(detection)

        return MaterialDetectionRecord(
            id=detection.id,
            survey_id=detection.survey_id,
            image_id=detection.image_id,
            material_class=detection.material_class,
            confidence=detection.confidence,
            status=detection.status,
            top_k_predictions=detection.top_k_predictions,
            bounding_box=detection.bounding_box,
            model_name=detection.model_name,
            model_version=detection.model_version,
            inference_mode=detection.inference_mode,
            is_demo=detection.is_demo,
            notes=detection.notes,
            created_at=detection.created_at,
        )

    # ---------------------------------------------------------
    # 5. Survey-Level Material Analysis
    # ---------------------------------------------------------
    def analyze_survey(
        self,
        db: Session,
        survey_id: str,
        model_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> SurveyMaterialAnalysisSummary:
        """
        Executes material classification across all images in a survey,
        records each detection in the database, and computes an aggregated summary.
        """
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise ValueError(f"Survey not found: {survey_id}")

        images = db.query(Image).filter(Image.survey_id == survey_id).all()
        if not images:
            raise ValueError(f"No images found for survey: {survey_id}")

        # Clear existing survey-level full-image detections to avoid duplicate bloating
        db.query(MaterialDetection).filter(
            MaterialDetection.survey_id == survey_id,
            MaterialDetection.bounding_box == None
        ).delete(synchronize_session=False)

        classifier = get_material_classifier(model_id)
        if confidence_threshold is not None:
            classifier.confidence_threshold = confidence_threshold

        detections = []
        class_counts: Dict[str, int] = {}
        confidences = []
        confident_count = 0
        low_confidence_count = 0

        for img in images:
            img_path = self._resolve_image_path(img)
            if not img_path or not img_path.exists():
                logger.warning(f"File missing on disk for image {img.id}: {img.relative_path if hasattr(img, 'relative_path') else 'unknown'}")
                continue

            try:
                pred = classifier.predict(image=img_path)
                mat_class = pred["material"]
                conf = pred["confidence"]
                stat = pred["status"]

                det = MaterialDetection(
                    survey_id=survey_id,
                    image_id=img.id,
                    material_class=mat_class,
                    material_type=mat_class,
                    confidence=conf,
                    status=stat,
                    top_k_predictions=pred["top_k"],
                    model_name=pred["model_name"],
                    model_version=pred["model_version"],
                    inference_mode=pred["inference_mode"],
                    is_demo=pred["is_demo"],
                    is_mock=pred["is_demo"],
                    notes=pred.get("recommendation"),
                )
                db.add(det)
                detections.append(det)

                class_counts[mat_class] = class_counts.get(mat_class, 0) + 1
                confidences.append(conf)

                if stat == "CONFIDENT":
                    confident_count += 1
                else:
                    low_confidence_count += 1

            except Exception as e:
                logger.error(f"Error predicting image {img.id}: {e}")

        db.commit()

        # Build distribution summary
        total_analyzed = len(detections)
        distribution_counts = {c_id: count for c_id, count in class_counts.items()}
        distribution_percentages = {
            c_id: round((count / total_analyzed) * 100, 1) if total_analyzed > 0 else 0.0
            for c_id, count in class_counts.items()
        }
        avg_confs_per_class = {}
        for c_id in class_counts:
            c_confs = [d.confidence for d in detections if d.material_class == c_id]
            avg_confs_per_class[c_id] = round(float(np.mean(c_confs)), 3) if c_confs else 0.0

        dominant_mat = None
        max_count = -1
        for c_id, count in class_counts.items():
            if count > max_count:
                max_count = count
                dominant_mat = c_id

        # Update survey dominant material if applicable
        if dominant_mat and hasattr(survey, "dominant_material"):
            survey.dominant_material = dominant_mat
            db.commit()

        avg_conf = round(float(np.mean(confidences)), 3) if confidences else 0.0

        return SurveyMaterialAnalysisSummary(
            survey_id=survey_id,
            total_images=len(images),
            analyzed_images=total_analyzed,
            detections_count=total_analyzed,
            dominant_material=dominant_mat,
            distribution=distribution_counts,
            distribution_percentage=distribution_percentages,
            average_confidences=avg_confs_per_class,
            overall_average_confidence=avg_conf,
            low_confidence_count=low_confidence_count,
            is_demo=classifier.is_demo,
            model_used=classifier.name,
            detections=[
                MaterialDetectionRecord(
                    id=d.id,
                    survey_id=d.survey_id,
                    image_id=d.image_id,
                    material_class=d.material_class,
                    confidence=d.confidence,
                    status=d.status,
                    top_k_predictions=d.top_k_predictions,
                    bounding_box=d.bounding_box,
                    model_name=d.model_name,
                    model_version=d.model_version,
                    inference_mode=d.inference_mode,
                    is_demo=d.is_demo,
                    notes=d.notes,
                    created_at=d.created_at,
                )
                for d in detections
            ],
            disclaimer=(
                "DEMO MATERIAL CLASSIFICATION — Synthetic/heuristic prediction only."
                if classifier.is_demo
                else "Model confidence reflects probabilistic similarity to training substrates. Field verification required."
            )
        )

    def get_survey_results(self, db: Session, survey_id: str) -> Optional[SurveyMaterialAnalysisSummary]:
        """
        Retrieves existing material detections for a survey and reconstructs the summary.
        """
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            return None

        total_images = db.query(Image).filter(Image.survey_id == survey_id).count()

        detections = db.query(MaterialDetection).filter(
            MaterialDetection.survey_id == survey_id
        ).all()

        if not detections:
            return None

        total_analyzed = len(detections)
        confident_count = sum(1 for d in detections if d.status == "CONFIDENT")
        low_confidence_count = sum(1 for d in detections if d.status == "LOW_CONFIDENCE")
        confidences = [d.confidence for d in detections]
        avg_conf = round(float(np.mean(confidences)), 3) if confidences else 0.0

        class_counts = {}
        for d in detections:
            c_id = d.material_class
            class_counts[c_id] = class_counts.get(c_id, 0) + 1

        distribution_counts = {c_id: count for c_id, count in class_counts.items()}
        distribution_percentages = {
            c_id: round((count / total_analyzed) * 100, 1) if total_analyzed > 0 else 0.0
            for c_id, count in class_counts.items()
        }
        avg_confs_per_class = {}
        for c_id in class_counts:
            c_confs = [d.confidence for d in detections if d.material_class == c_id]
            avg_confs_per_class[c_id] = round(float(np.mean(c_confs)), 3) if c_confs else 0.0

        dominant_mat = None
        max_count = -1
        for c_id, count in class_counts.items():
            if count > max_count:
                max_count = count
                dominant_mat = c_id

        sample = detections[0]

        return SurveyMaterialAnalysisSummary(
            survey_id=survey_id,
            total_images=total_images,
            analyzed_images=total_analyzed,
            detections_count=total_analyzed,
            dominant_material=dominant_mat,
            distribution=distribution_counts,
            distribution_percentage=distribution_percentages,
            average_confidences=avg_confs_per_class,
            overall_average_confidence=avg_conf,
            low_confidence_count=low_confidence_count,
            is_demo=sample.is_demo if sample.is_demo is not None else True,
            model_used=sample.model_name or "DemoMaterialClassifier",
            detections=[
                MaterialDetectionRecord(
                    id=d.id,
                    survey_id=d.survey_id,
                    image_id=d.image_id,
                    material_class=d.material_class,
                    confidence=d.confidence,
                    status=d.status,
                    top_k_predictions=d.top_k_predictions,
                    bounding_box=d.bounding_box,
                    model_name=d.model_name,
                    model_version=d.model_version,
                    inference_mode=d.inference_mode,
                    is_demo=d.is_demo,
                    notes=d.notes,
                    created_at=d.created_at,
                )
                for d in detections
            ],
            disclaimer=(
                "DEMO MATERIAL CLASSIFICATION — Synthetic/heuristic prediction only."
                if sample.is_demo
                else "Model confidence reflects probabilistic similarity to training substrates. Field verification required."
            )
        )

    # ---------------------------------------------------------
    # 6. Dataset Validation
    # ---------------------------------------------------------
    def validate_dataset(self, dataset_dir: str) -> DatasetValidationReport:
        """Validates dataset folder structure, balance, and image file integrity."""
        report_data = self.validator.validate(Path(dataset_dir))
        return DatasetValidationReport(**report_data)


# Global singleton instance
material_service = MaterialService()
