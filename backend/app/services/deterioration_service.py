"""
Deterioration Detection Service.
Coordinates ML defect detection, material-aware association, database persistence,
survey-level cross-tabulation, and dataset validation.

STRICT RESEARCH INTEGRITY:
- Model confidence is strictly presented as probabilistic inference, not structural certainty.
- If material data is unavailable, defect is marked UNKNOWN and MATERIAL_ASSOCIATION_UNAVAILABLE.
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
from app.core.deterioration_config import (
    load_deterioration_classes,
    add_deterioration_class,
    update_deterioration_class,
    reset_deterioration_classes,
    get_deterioration_class_by_id,
)
from app.models.heritage import Survey, Image, MaterialDetection, DeteriorationDetection
from app.ml import (
    get_deterioration_detector,
    list_deterioration_models,
    DeteriorationDatasetValidator,
)
from app.services.material_association import associate_deterioration_with_materials
from app.schemas.deterioration import (
    DeteriorationClassItem,
    DeteriorationClassCreate,
    DeteriorationClassUpdate,
    DeteriorationItem,
    DeteriorationPredictionResponse,
    SurveyDeteriorationAnalysisSummary,
    DeteriorationDatasetValidationReport,
)

logger = logging.getLogger(__name__)


class DeteriorationService:
    """Core domain service for physical heritage defect detection and material-aware association."""

    def __init__(self):
        self.validator = DeteriorationDatasetValidator()

    # ---------------------------------------------------------
    # 1. Configurable Deterioration Classes Management
    # ---------------------------------------------------------
    def get_classes(self) -> List[DeteriorationClassItem]:
        classes = load_deterioration_classes(include_disabled=True)
        return [DeteriorationClassItem(**c) for c in classes]

    def add_class(self, data: DeteriorationClassCreate) -> DeteriorationClassItem:
        new_item = add_deterioration_class(data.model_dump())
        return DeteriorationClassItem(**new_item)

    def update_class(self, class_id: str, data: DeteriorationClassUpdate) -> Optional[DeteriorationClassItem]:
        updated = update_deterioration_class(class_id, data.model_dump(exclude_unset=True))
        if updated:
            return DeteriorationClassItem(**updated)
        return None

    def reset_classes(self) -> List[DeteriorationClassItem]:
        classes = reset_deterioration_classes()
        return [DeteriorationClassItem(**c) for c in classes]

    # ---------------------------------------------------------
    # 2. Model Registry & Introspection
    # ---------------------------------------------------------
    def get_models(self) -> List[Dict[str, Any]]:
        return list_deterioration_models()

    # ---------------------------------------------------------
    # 3. Path Resolution Helper
    # ---------------------------------------------------------
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
    # 4. Direct Image Detection
    # ---------------------------------------------------------
    def predict_image(
        self,
        image_input: Union[bytes, Path, str, PILImage.Image],
        image_id: Optional[str] = None,
        db: Optional[Session] = None,
        model_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> DeteriorationPredictionResponse:
        """
        Runs defect detection on an image, associates defects with substrate materials
        if existing material detections are found, and formats response.
        """
        detector = get_deterioration_detector(model_id)
        if confidence_threshold is not None:
            detector.confidence_threshold = confidence_threshold

        # Parse bytes to PIL if necessary
        if isinstance(image_input, bytes):
            image = PILImage.open(io.BytesIO(image_input)).convert("RGB")
        else:
            image = image_input

        raw_detections = detector.predict(image=image, confidence_threshold=confidence_threshold)

        # Retrieve material detections if image_id and db are provided
        material_detections = []
        survey_id = None
        if image_id and db:
            db_img = db.query(Image).filter(Image.id == image_id).first()
            if db_img:
                survey_id = db_img.survey_id
            material_detections = db.query(MaterialDetection).filter(
                MaterialDetection.image_id == image_id
            ).all()

        items: List[DeteriorationItem] = []
        for idx, det in enumerate(raw_detections):
            det_box = det.get("bounding_box")

            # Perform material-damage association
            mat_assoc = associate_deterioration_with_materials(det_box, material_detections)

            item_id = f"det_{idx+1}"
            det_record = None

            # Persist if image_id and db session are present
            if image_id and db and survey_id:
                det_record = DeteriorationDetection(
                    survey_id=survey_id,
                    image_id=image_id,
                    material_id=mat_assoc.get("material_id"),
                    material_class=mat_assoc.get("material_class", "UNKNOWN"),
                    material_type=mat_assoc.get("material_class", "UNKNOWN"),
                    material_confidence=mat_assoc.get("material_confidence"),
                    material_association_status=mat_assoc.get("material_association_status", "MATERIAL_ASSOCIATION_UNAVAILABLE"),
                    candidate_materials=mat_assoc.get("candidate_materials"),
                    damage_type=det["damage_type"],
                    confidence=det["confidence"],
                    status=det["status"],
                    severity_hint=det.get("severity_hint", "moderate"),
                    bounding_box=det_box,
                    polygon=det.get("polygon"),
                    model_name=detector.name,
                    model_version=detector.version,
                    inference_mode="demo" if detector.is_demo else "real_trained",
                    is_demo=detector.is_demo,
                    is_mock=detector.is_demo,
                    notes=det.get("notes") or mat_assoc.get("notes"),
                )
                db.add(det_record)
                db.commit()
                db.refresh(det_record)
                item_id = det_record.id

            items.append(
                DeteriorationItem(
                    id=item_id,
                    image_id=image_id,
                    survey_id=survey_id,
                    damage_type=det["damage_type"],
                    confidence=det["confidence"],
                    status=det["status"],
                    severity_hint=det.get("severity_hint", "moderate"),
                    bounding_box=det_box,
                    polygon=det.get("polygon"),
                    material_class=mat_assoc.get("material_class", "UNKNOWN"),
                    material_confidence=mat_assoc.get("material_confidence"),
                    material_association_status=mat_assoc.get("material_association_status", "MATERIAL_ASSOCIATION_UNAVAILABLE"),
                    candidate_materials=mat_assoc.get("candidate_materials", []),
                    notes=det.get("notes") or mat_assoc.get("notes"),
                    model_name=detector.name,
                    model_version=detector.version,
                    inference_mode="demo" if detector.is_demo else "real_trained",
                    is_demo=detector.is_demo,
                    created_at=getattr(det_record, "created_at", None),
                )
            )

        return DeteriorationPredictionResponse(
            image_id=image_id,
            detections=items,
            detections_count=len(items),
            model_name=detector.name,
            model_version=detector.version,
            inference_mode="demo" if detector.is_demo else "real_trained",
            is_demo=detector.is_demo,
        )

    # ---------------------------------------------------------
    # 5. Survey-Level Batch Deterioration Analysis
    # ---------------------------------------------------------
    def analyze_survey(
        self,
        db: Session,
        survey_id: str,
        model_id: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> SurveyDeteriorationAnalysisSummary:
        """
        Executes deterioration detection across all images in a survey,
        associates each defect with existing material classifications,
        persists records, and generates cross-tabulated material x damage statistics.
        """
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise ValueError(f"Survey not found: {survey_id}")

        images = db.query(Image).filter(Image.survey_id == survey_id).all()
        if not images:
            raise ValueError(f"No images found for survey: {survey_id}")

        # Delete existing detections for this survey to prevent duplicate accumulation
        db.query(DeteriorationDetection).filter(
            DeteriorationDetection.survey_id == survey_id
        ).delete(synchronize_session=False)

        # Pre-load all material detections for this survey
        survey_materials = db.query(MaterialDetection).filter(
            MaterialDetection.survey_id == survey_id
        ).all()
        mat_by_image: Dict[str, List[MaterialDetection]] = {}
        for m in survey_materials:
            if m.image_id:
                mat_by_image.setdefault(m.image_id, []).append(m)

        detector = get_deterioration_detector(model_id)
        if confidence_threshold is not None:
            detector.confidence_threshold = confidence_threshold

        persisted_items: List[DeteriorationItem] = []
        damage_counts: Dict[str, int] = {}
        crosstab: Dict[str, Dict[str, int]] = {}
        confidences: List[float] = []
        low_confidence_count = 0

        for img in images:
            img_path = self._resolve_image_path(img)
            if not img_path or not img_path.exists():
                logger.warning(f"File missing for image {img.id}: {img.relative_path if hasattr(img, 'relative_path') else 'unknown'}")
                continue

            try:
                raw_dets = detector.predict(image=img_path, confidence_threshold=confidence_threshold)
                img_mats = mat_by_image.get(img.id, [])

                for det in raw_dets:
                    det_box = det.get("bounding_box")
                    mat_assoc = associate_deterioration_with_materials(det_box, img_mats)

                    rec = DeteriorationDetection(
                        survey_id=survey_id,
                        image_id=img.id,
                        material_id=mat_assoc.get("material_id"),
                        material_class=mat_assoc.get("material_class", "UNKNOWN"),
                        material_type=mat_assoc.get("material_class", "UNKNOWN"),
                        material_confidence=mat_assoc.get("material_confidence"),
                        material_association_status=mat_assoc.get("material_association_status", "MATERIAL_ASSOCIATION_UNAVAILABLE"),
                        candidate_materials=mat_assoc.get("candidate_materials"),
                        damage_type=det["damage_type"],
                        confidence=det["confidence"],
                        status=det["status"],
                        severity_hint=det.get("severity_hint", "moderate"),
                        bounding_box=det_box,
                        polygon=det.get("polygon"),
                        model_name=detector.name,
                        model_version=detector.version,
                        inference_mode="demo" if detector.is_demo else "real_trained",
                        is_demo=detector.is_demo,
                        is_mock=detector.is_demo,
                        notes=det.get("notes") or mat_assoc.get("notes"),
                    )
                    db.add(rec)
                    db.flush()  # assign ID

                    conf = det["confidence"]
                    dmg = det["damage_type"]
                    mat = mat_assoc.get("material_class", "UNKNOWN")

                    damage_counts[dmg] = damage_counts.get(dmg, 0) + 1
                    confidences.append(conf)
                    if det["status"] == "LOW_CONFIDENCE":
                        low_confidence_count += 1

                    # Crosstab
                    crosstab.setdefault(mat, {})
                    crosstab[mat][dmg] = crosstab[mat].get(dmg, 0) + 1

                    persisted_items.append(
                        DeteriorationItem(
                            id=rec.id,
                            image_id=rec.image_id,
                            survey_id=rec.survey_id,
                            damage_type=rec.damage_type,
                            confidence=rec.confidence,
                            status=rec.status,
                            severity_hint=rec.severity_hint,
                            bounding_box=rec.bounding_box,
                            polygon=rec.polygon,
                            material_class=rec.material_class,
                            material_confidence=rec.material_confidence,
                            material_association_status=rec.material_association_status,
                            candidate_materials=rec.candidate_materials or [],
                            notes=rec.notes,
                            model_name=rec.model_name,
                            model_version=rec.model_version,
                            inference_mode=rec.inference_mode,
                            is_demo=rec.is_demo,
                            created_at=rec.created_at,
                        )
                    )

            except Exception as e:
                logger.error(f"Error processing image {img.id} for deterioration: {e}")

        db.commit()

        total_dets = len(persisted_items)
        distribution_pct = {
            k: round((v / total_dets) * 100, 1) if total_dets > 0 else 0.0
            for k, v in damage_counts.items()
        }
        avg_conf = round(float(np.mean(confidences)), 3) if confidences else 0.0

        return SurveyDeteriorationAnalysisSummary(
            survey_id=survey_id,
            total_images=len(images),
            analyzed_images=len(images),
            total_detections=total_dets,
            class_distribution=damage_counts,
            class_distribution_percentage=distribution_pct,
            material_damage_crosstab=crosstab,
            average_confidence=avg_conf,
            low_confidence_count=low_confidence_count,
            is_demo=detector.is_demo,
            model_used=detector.name,
            detections=persisted_items,
        )

    # ---------------------------------------------------------
    # 6. Retrieve Stored Survey Results
    # ---------------------------------------------------------
    def get_survey_results(self, db: Session, survey_id: str) -> Optional[SurveyDeteriorationAnalysisSummary]:
        """Reconstructs survey deterioration analysis summary from database."""
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            return None

        total_images = db.query(Image).filter(Image.survey_id == survey_id).count()
        records = db.query(DeteriorationDetection).filter(
            DeteriorationDetection.survey_id == survey_id
        ).all()

        if not records:
            return None

        damage_counts: Dict[str, int] = {}
        crosstab: Dict[str, Dict[str, int]] = {}
        confidences = [r.confidence for r in records]
        low_confidence_count = sum(1 for r in records if r.status == "LOW_CONFIDENCE")

        items = []
        for r in records:
            dmg = r.damage_type
            mat = r.material_class or "UNKNOWN"
            damage_counts[dmg] = damage_counts.get(dmg, 0) + 1
            crosstab.setdefault(mat, {})
            crosstab[mat][dmg] = crosstab[mat].get(dmg, 0) + 1

            items.append(
                DeteriorationItem(
                    id=r.id,
                    image_id=r.image_id,
                    survey_id=r.survey_id,
                    damage_type=r.damage_type,
                    confidence=r.confidence,
                    status=r.status or "CONFIDENT",
                    severity_hint=r.severity_hint or "moderate",
                    bounding_box=r.bounding_box,
                    polygon=r.polygon,
                    material_class=r.material_class or "UNKNOWN",
                    material_confidence=r.material_confidence,
                    material_association_status=r.material_association_status or "MATERIAL_ASSOCIATION_UNAVAILABLE",
                    candidate_materials=r.candidate_materials or [],
                    notes=r.notes,
                    model_name=r.model_name or "DemoDeteriorationDetector",
                    model_version=r.model_version or "v1.0",
                    inference_mode=r.inference_mode or "demo",
                    is_demo=r.is_demo if r.is_demo is not None else True,
                    created_at=r.created_at,
                )
            )

        total_dets = len(records)
        distribution_pct = {
            k: round((v / total_dets) * 100, 1) if total_dets > 0 else 0.0
            for k, v in damage_counts.items()
        }
        avg_conf = round(float(np.mean(confidences)), 3) if confidences else 0.0
        sample = records[0]

        return SurveyDeteriorationAnalysisSummary(
            survey_id=survey_id,
            total_images=total_images,
            analyzed_images=total_images,
            total_detections=total_dets,
            class_distribution=damage_counts,
            class_distribution_percentage=distribution_pct,
            material_damage_crosstab=crosstab,
            average_confidence=avg_conf,
            low_confidence_count=low_confidence_count,
            is_demo=sample.is_demo if sample.is_demo is not None else True,
            model_used=sample.model_name or "DemoDeteriorationDetector",
            detections=items,
        )

    # ---------------------------------------------------------
    # 7. Dataset Validation
    # ---------------------------------------------------------
    def validate_dataset(self, dataset_path: str) -> DeteriorationDatasetValidationReport:
        report_data = self.validator.validate(Path(dataset_path))
        return DeteriorationDatasetValidationReport(**report_data)


# Global singleton instance
deterioration_service = DeteriorationService()
