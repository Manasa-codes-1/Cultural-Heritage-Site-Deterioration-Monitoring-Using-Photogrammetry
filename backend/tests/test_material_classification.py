"""
Unit and Integration Tests for Phase 4: Material Classification ML Pipeline.
Tests:
- Configurable material class registry CRUD
- Dataset structure and imbalance validator
- Heuristic/Demo classifier behavior and low-confidence thresholding
- Metric calculation accuracy (no fabrication)
- API endpoints for classes, prediction, survey analysis, and dataset validation
"""
import io
import json
import numpy as np
from PIL import Image
import pytest

from app.core.material_config import (
    load_material_classes,
    add_material_class,
    update_material_class,
    reset_material_classes,
)
from app.ml.demo_classifier import DemoMaterialClassifier
from app.ml.dataset_validator import DatasetValidator
from app.ml.trainer import calculate_classification_metrics
from app.models.heritage import Site, Survey, Image as DBImage


def create_dummy_image_bytes(color=(180, 100, 60), size=(100, 100)) -> bytes:
    """Creates synthetic RGB JPEG image in memory."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# -------------------------------------------------------------
# 1. Configurable Material Classes Tests
# -------------------------------------------------------------
def test_material_classes_crud():
    # Reset to defaults
    classes = reset_material_classes()
    assert len(classes) >= 5
    class_ids = [c["id"] for c in classes]
    assert "sandstone" in class_ids
    assert "brick" in class_ids

    # Add new class
    new_c = add_material_class({
        "id": "marble",
        "name": "White Marble",
        "description": "Metamorphic rock of recrystallized carbonate minerals",
        "color": "#e2e8f0"
    })
    assert new_c["id"] == "marble"
    assert new_c["name"] == "White Marble"

    # Verify presence
    updated_list = load_material_classes()
    assert any(c["id"] == "marble" for c in updated_list)

    # Update class
    updated = update_material_class("marble", {"description": "Updated marble description", "enabled": False})
    assert updated is not None
    assert updated["description"] == "Updated marble description"
    assert updated["enabled"] is False

    # Cleanup reset
    reset_material_classes()


# -------------------------------------------------------------
# 2. Dataset Validator Tests
# -------------------------------------------------------------
def test_dataset_validator(tmp_path):
    validator = DatasetValidator()

    # Case A: Empty non-existent dir
    report = validator.validate(tmp_path / "non_existent")
    assert report["status"] == "INVALID"
    assert len(report["errors"]) > 0

    # Case B: Valid split structure
    train_dir = tmp_path / "train"
    val_dir = tmp_path / "val"
    train_dir.mkdir(parents=True)
    val_dir.mkdir(parents=True)

    # Add 2 classes with dummy images
    for c in ["brick", "sandstone"]:
        (train_dir / c).mkdir()
        (val_dir / c).mkdir()
        for i in range(5):
            img_p = train_dir / c / f"img_{i}.jpg"
            img_p.write_bytes(create_dummy_image_bytes())
        for i in range(2):
            img_p = val_dir / c / f"val_img_{i}.jpg"
            img_p.write_bytes(create_dummy_image_bytes())

    report_valid = validator.validate(tmp_path)
    assert report_valid["status"] in ["VALID", "WARNING"]
    assert report_valid["num_classes"] == 2
    assert "brick" in report_valid["classes_found"]
    assert "sandstone" in report_valid["classes_found"]


# -------------------------------------------------------------
# 3. Demo Classifier & Low-Confidence Behavior
# -------------------------------------------------------------
def test_demo_classifier_inference():
    clf = DemoMaterialClassifier(confidence_threshold=0.60)
    assert clf.is_demo is True
    assert "Demo" in clf.name

    # Reddish / terracotta colored image should detect brick
    brick_bytes = create_dummy_image_bytes(color=(190, 80, 50))
    res = clf.predict(brick_bytes)

    assert "material" in res
    assert "confidence" in res
    assert 0.0 <= res["confidence"] <= 1.0
    assert res["is_demo"] is True
    assert res["inference_mode"] == "demo"
    assert len(res["top_k"]) > 0
    assert "disclaimer" in res

    # High threshold forcing LOW_CONFIDENCE
    clf_strict = DemoMaterialClassifier(confidence_threshold=0.99)
    res_low = clf_strict.predict(brick_bytes)
    assert res_low["status"] == "LOW_CONFIDENCE"
    assert "requires verification" in res_low["recommendation"].lower()


# -------------------------------------------------------------
# 4. Rigorous Metrics Calculation (No Fabrication)
# -------------------------------------------------------------
def test_calculate_classification_metrics():
    y_true = [0, 1, 0, 1, 0, 1]
    y_pred = [0, 1, 0, 0, 0, 1]
    classes = ["sandstone", "brick"]

    metrics = calculate_classification_metrics(y_true, y_pred, classes)
    assert metrics["total_evaluated_samples"] == 6
    assert metrics["accuracy"] == pytest.approx(5 / 6, 0.001)
    assert "confusion_matrix" in metrics
    assert len(metrics["confusion_matrix"]) == 2
    assert "macro_f1" in metrics
    assert "per_class" in metrics
    assert "sandstone" in metrics["per_class"]
    assert "brick" in metrics["per_class"]


# -------------------------------------------------------------
# 5. API Endpoints Integration Tests
# -------------------------------------------------------------
def test_api_material_classes(client):
    # GET classes
    resp = client.get("/api/materials/classes")
    assert resp.status_code == 200
    classes = resp.json()
    assert isinstance(classes, list)
    assert len(classes) >= 5

    # POST new class
    resp_create = client.post("/api/materials/classes", json={
        "id": "tuff_stone",
        "name": "Volcanic Tuff",
        "description": "Porous volcanic stone",
        "color": "#a8a29e"
    })
    assert resp_create.status_code == 201
    created = resp_create.json()
    assert created["id"] == "tuff_stone"

    # PUT update class
    resp_update = client.put("/api/materials/classes/tuff_stone", json={
        "name": "Volcanic Tuff (Altered)",
        "enabled": False
    })
    assert resp_update.status_code == 200
    assert resp_update.json()["name"] == "Volcanic Tuff (Altered)"
    assert resp_update.json()["enabled"] is False

    # POST reset
    resp_reset = client.post("/api/materials/classes/reset")
    assert resp_reset.status_code == 200


def test_api_material_models(client):
    resp = client.get("/api/materials/models")
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) >= 1
    # Check that demo model is present and labeled
    assert any(m.get("is_demo") is True for m in models)


def test_api_material_predict(client):
    img_bytes = create_dummy_image_bytes(color=(160, 140, 110))
    files = {"file": ("test_wall.jpg", img_bytes, "image/jpeg")}
    data = {"region_json": json.dumps({"x": 10, "y": 10, "w": 50, "h": 50})}

    resp = client.post("/api/materials/predict", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert "material" in res_data
    assert "confidence" in res_data
    assert res_data["is_demo"] is True
    assert res_data["region"] == {"x": 10, "y": 10, "w": 50, "h": 50}


def test_api_survey_material_analysis(client, db_session, tmp_path):
    # 1. Create a dummy site and survey
    site = Site(name="Test Citadel", location="Western Bastion")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    survey = Survey(site_id=site.id, survey_code="SRV-2026-001", description="Survey 2026-A")
    db_session.add(survey)
    db_session.commit()
    db_session.refresh(survey)

    # 2. Create dummy image files on disk and records in DB
    img_file = tmp_path / "survey_img_1.jpg"
    img_file.write_bytes(create_dummy_image_bytes(color=(190, 85, 45)))

    img_rec = DBImage(
        survey_id=survey.id,
        filename="survey_img_1.jpg",
        relative_path=str(img_file),
        file_size_bytes=len(img_file.read_bytes()),
    )
    db_session.add(img_rec)
    db_session.commit()

    # 3. Analyze survey materials
    resp_analyze = client.post(f"/api/materials/surveys/{survey.id}/analyze")
    assert resp_analyze.status_code == 200
    analysis = resp_analyze.json()
    assert analysis["survey_id"] == survey.id
    assert analysis["total_images"] == 1
    assert analysis["analyzed_images"] == 1
    assert "dominant_material" in analysis
    assert len(analysis["detections"]) == 1

    # 4. Retrieve survey material results
    resp_results = client.get(f"/api/materials/surveys/{survey.id}/results")
    assert resp_results.status_code == 200
    results = resp_results.json()
    assert results["survey_id"] == survey.id
    assert results["analyzed_images"] == 1
