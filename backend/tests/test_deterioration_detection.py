"""
Unit and Integration Tests for Phase 5: Deterioration Detection / Segmentation ML Pipeline.
Tests:
- Configurable defect taxonomy CRUD
- Defect dataset validator and bounding box geometry checks
- Demo detector behavior and low-confidence thresholding
- Material-damage association logic (spatial overlap & missing material handling)
- Genuine detection metric calculations (mAP@0.50, Precision, Recall)
- API endpoints for defect detection, survey batch analysis, and cross-tabulation
"""
import io
import json
from pathlib import Path
from PIL import Image
import pytest

from app.core.deterioration_config import (
    load_deterioration_classes,
    add_deterioration_class,
    update_deterioration_class,
    reset_deterioration_classes,
)
from app.ml.demo_detector import DemoDeteriorationDetector
from app.ml.deterioration_validator import DeteriorationDatasetValidator
from app.ml.deterioration_trainer import calculate_detection_metrics, compute_box_iou
from app.services.material_association import (
    associate_deterioration_with_materials,
    compute_intersection_over_min,
)
from app.models.heritage import Site, Survey, Image as DBImage, MaterialDetection


def create_test_image_bytes(color=(140, 120, 100), size=(200, 200)) -> bytes:
    """Creates synthetic RGB image for testing."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# -------------------------------------------------------------
# 1. Defect Taxonomy CRUD
# -------------------------------------------------------------
def test_deterioration_classes_crud():
    classes = reset_deterioration_classes()
    assert len(classes) >= 5
    ids = [c["id"] for c in classes]
    assert "crack" in ids
    assert "erosion" in ids
    assert "spalling" in ids

    # Add class
    new_c = add_deterioration_class({
        "id": "delamination",
        "name": "Subsurface Delamination",
        "description": "Separation of stone along cleavage planes",
        "color": "#f43f5e",
        "severity_weight": 0.85,
    })
    assert new_c["id"] == "delamination"
    assert new_c["severity_weight"] == 0.85

    # Update class
    updated = update_deterioration_class("delamination", {"enabled": False, "severity_weight": 0.90})
    assert updated is not None
    assert updated["enabled"] is False
    assert updated["severity_weight"] == 0.90

    reset_deterioration_classes()


# -------------------------------------------------------------
# 2. Dataset Validator & Box Geometry
# -------------------------------------------------------------
def test_deterioration_dataset_validator(tmp_path):
    validator = DeteriorationDatasetValidator()

    # Non-existent path
    rep_invalid = validator.validate(tmp_path / "non_existent")
    assert rep_invalid["status"] == "INVALID"

    # Create dummy images and valid annotations
    img_dir = tmp_path / "images"
    img_dir.mkdir(parents=True)
    img_file = img_dir / "test_wall.jpg"
    img_file.write_bytes(create_test_image_bytes())

    annot_file = tmp_path / "annotations.json"
    annot_data = [
        {
            "image": "test_wall.jpg",
            "boxes": [
                {"class": "crack", "x": 10, "y": 20, "w": 50, "h": 60},
                {"class": "erosion", "x": 30, "y": 40, "w": 40, "h": 50},
            ]
        }
    ]
    with open(annot_file, "w", encoding="utf-8") as f:
        json.dump(annot_data, f)

    rep_valid = validator.validate(tmp_path)
    assert rep_valid["status"] in ["VALID", "WARNING"]
    assert rep_valid["total_images"] == 1
    assert rep_valid["total_annotations"] == 2
    assert "crack" in rep_valid["classes_found"]

    # Test invalid box detection
    annot_invalid = [
        {
            "image": "test_wall.jpg",
            "boxes": [
                {"class": "crack", "x": -5, "y": 10, "w": -20, "h": 0}  # Invalid coordinates
            ]
        }
    ]
    with open(annot_file, "w", encoding="utf-8") as f:
        json.dump(annot_invalid, f)

    rep_err = validator.validate(tmp_path)
    assert rep_err["status"] == "INVALID"
    assert rep_err["invalid_boxes_count"] > 0


# -------------------------------------------------------------
# 3. Demo Detector Inference & Confidence Thresholding
# -------------------------------------------------------------
def test_demo_detector_inference():
    detector = DemoDeteriorationDetector(confidence_threshold=0.60)
    assert detector.is_demo is True
    assert "Demo" in detector.name

    img_bytes = create_test_image_bytes()
    dets = detector.predict(img_bytes)

    assert isinstance(dets, list)
    assert len(dets) > 0
    d = dets[0]
    assert "damage_type" in d
    assert "confidence" in d
    assert "status" in d
    assert "bounding_box" in d
    assert 0.0 <= d["confidence"] <= 1.0

    # Low-confidence thresholding
    detector_strict = DemoDeteriorationDetector(confidence_threshold=0.99)
    strict_dets = detector_strict.predict(img_bytes)
    assert all(sd["status"] == "LOW_CONFIDENCE" for sd in strict_dets)
    assert any("verification" in sd["notes"].lower() for sd in strict_dets)


# -------------------------------------------------------------
# 4. Material-Damage Association Logic
# -------------------------------------------------------------
def test_material_damage_association():
    # 1. Spatial overlap match
    class DummyMat:
        def __init__(self, id, mat_class, conf, bbox):
            self.id = id
            self.material_class = mat_class
            self.confidence = conf
            self.bounding_box = bbox

    mat1 = DummyMat("mat_1", "brick", 0.90, {"x": 0, "y": 0, "w": 100, "h": 100})
    mat2 = DummyMat("mat_2", "sandstone", 0.85, {"x": 150, "y": 150, "w": 50, "h": 50})

    # Deterioration fully inside mat1
    det_box = {"x": 20, "y": 20, "w": 30, "h": 30}
    assoc = associate_deterioration_with_materials(det_box, [mat1, mat2])
    assert assoc["material_class"] == "brick"
    assert assoc["material_confidence"] == 0.90
    assert assoc["material_association_status"] == "ASSOCIATED"
    assert assoc["material_id"] == "mat_1"

    # 2. Missing material handling (honestly marked UNKNOWN)
    assoc_none = associate_deterioration_with_materials(det_box, [])
    assert assoc_none["material_class"] == "UNKNOWN"
    assert assoc_none["material_confidence"] is None
    assert assoc_none["material_association_status"] == "MATERIAL_ASSOCIATION_UNAVAILABLE"


# -------------------------------------------------------------
# 5. Genuine Detection Metric Calculations
# -------------------------------------------------------------
def test_calculate_detection_metrics():
    gt = [{"boxes": [[10, 10, 50, 50]], "labels": [0]}]
    pred_good = [{"boxes": [[11, 10, 50, 50]], "labels": [0], "scores": [0.92]}]
    classes = ["crack"]

    metrics = calculate_detection_metrics(gt, pred_good, classes, iou_threshold=0.50)
    assert metrics["total_evaluated_images"] == 1
    assert metrics["per_class"]["crack"]["true_positives"] == 1
    assert metrics["per_class"]["crack"]["precision"] == 1.0
    assert metrics["per_class"]["crack"]["recall"] == 1.0


# -------------------------------------------------------------
# 6. API Endpoints Integration Tests
# -------------------------------------------------------------
def test_api_deterioration_classes(client):
    # GET classes
    resp = client.get("/api/deterioration/classes")
    assert resp.status_code == 200
    classes = resp.json()
    assert len(classes) >= 5

    # POST new class
    resp_create = client.post("/api/deterioration/classes", json={
        "id": "efflorescence",
        "name": "Salt Efflorescence",
        "description": "White crystalline salt deposit",
        "color": "#e2e8f0",
        "severity_weight": 0.45,
    })
    assert resp_create.status_code == 201
    assert resp_create.json()["id"] == "efflorescence"

    # PUT update
    resp_update = client.put("/api/deterioration/classes/efflorescence", json={
        "severity_weight": 0.55
    })
    assert resp_update.status_code == 200
    assert resp_update.json()["severity_weight"] == 0.55

    # Reset
    resp_reset = client.post("/api/deterioration/classes/reset")
    assert resp_reset.status_code == 200


def test_api_deterioration_models(client):
    resp = client.get("/api/deterioration/models")
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) >= 1
    assert any(m["is_demo"] is True for m in models)


def test_api_deterioration_predict(client):
    img_bytes = create_test_image_bytes()
    files = {"file": ("masonry_crack.jpg", img_bytes, "image/jpeg")}
    resp = client.post("/api/deterioration/predict", files=files)
    assert resp.status_code == 200
    res_data = resp.json()
    assert "detections" in res_data
    assert "detections_count" in res_data
    assert res_data["is_demo"] is True
    assert "disclaimer" in res_data


def test_api_survey_deterioration_analysis(client, db_session, tmp_path):
    # 1. Setup Site & Survey
    site = Site(name="Citadel Tower", location="North Bastion")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    survey = Survey(site_id=site.id, survey_code="SRV-DET-01", description="Defect Survey")
    db_session.add(survey)
    db_session.commit()
    db_session.refresh(survey)

    # 2. Add an image file and record
    img_file = tmp_path / "tower_face.jpg"
    img_file.write_bytes(create_test_image_bytes())

    img_rec = DBImage(
        survey_id=survey.id,
        filename="tower_face.jpg",
        relative_path=str(img_file),
        file_size_bytes=len(img_file.read_bytes()),
    )
    db_session.add(img_rec)
    db_session.commit()
    db_session.refresh(img_rec)

    # 3. Add a Phase 4 Material Detection to test material-damage association
    mat_rec = MaterialDetection(
        survey_id=survey.id,
        image_id=img_rec.id,
        material_class="brick",
        confidence=0.88,
        bounding_box={"x": 0, "y": 0, "w": 200, "h": 200},  # Covers entire image
    )
    db_session.add(mat_rec)
    db_session.commit()

    # 4. Trigger survey deterioration analysis
    resp_analyze = client.post(f"/api/deterioration/surveys/{survey.id}/analyze")
    assert resp_analyze.status_code == 200
    analysis = resp_analyze.json()
    assert analysis["survey_id"] == survey.id
    assert analysis["total_images"] == 1
    assert analysis["total_detections"] > 0
    assert "material_damage_crosstab" in analysis
    # Verify material was associated with brick
    assert any(d["material_class"] == "brick" for d in analysis["detections"])

    # 5. Fetch survey deterioration results
    resp_results = client.get(f"/api/deterioration/surveys/{survey.id}/results")
    assert resp_results.status_code == 200
    results = resp_results.json()
    assert results["survey_id"] == survey.id
    assert results["total_detections"] > 0
