"""
Tests for Integrated Demo Mode (Phases 1–7).
Validates DeepCrack dataset resolution, full end-to-end pipeline execution,
mask endpoint streaming, and research provenance banners.
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.demo_service import DemoService


def test_deepcrack_dataset_available():
    """Verify that the DeepCrack dataset is located and accessible."""
    img_dir, mask_dir = DemoService.get_deepcrack_paths()
    assert img_dir.exists(), f"DeepCrack images directory not found: {img_dir}"
    assert mask_dir.exists(), f"DeepCrack masks directory not found: {mask_dir}"

    images = list(img_dir.glob("*.jpg"))
    masks = list(mask_dir.glob("*.png"))
    assert len(images) > 0, "No JPEG images found in DeepCrack dataset."
    assert len(masks) > 0, "No PNG masks found in DeepCrack dataset."


def test_api_demo_status_endpoint(client: TestClient):
    """Test GET /api/demo/status endpoint."""
    resp = client.get("/api/demo/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "initialized" in data
    assert "deepcrack_available" in data
    assert data["deepcrack_available"] is True
    assert data["deepcrack_image_count"] > 0


def test_api_demo_mask_endpoint(client: TestClient):
    """Test streaming of ground-truth mask PNG via GET /api/demo/mask/{filename}."""
    resp = client.get("/api/demo/mask/11111.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0


def test_api_demo_mask_not_found(client: TestClient):
    """Test non-existent mask returns 404."""
    resp = client.get("/api/demo/mask/non_existent_mask_xyz.png")
    assert resp.status_code == 404


def test_api_run_integrated_demo_lifecycle(client: TestClient, db_session: Session):
    """
    Test full end-to-end integrated demo execution across Phases 1–7.
    """
    resp = client.post("/api/demo/run")
    assert resp.status_code == 200, f"Demo run failed: {resp.text}"
    data = resp.json()

    # Core response structure
    assert data["success"] is True
    assert data["site_name"] == "Demo Heritage Structure"
    assert data["survey_t1_name"] == "Demo Survey — Initial Inspection"
    assert data["survey_t2_name"] == "Demo Survey — Follow-up Inspection"

    # Data Provenance check
    prov = data["provenance"]
    assert "DeepCrack" in prov["image_data"]
    assert "DeepCrack" in prov["image_masks"]
    assert "synthetic" in prov["photogrammetry_3d"].lower()
    assert "HYBRID DEMONSTRATION" in prov["overall_classification"]

    # Phase 1: Image Quality
    p1 = data["phase1_quality"]
    assert p1["total_images"] >= 2
    assert p1["usable_images"] >= 1
    assert p1["average_blur"] > 0.0
    for img in p1["images"]:
        assert img["download_url"].startswith("/api/images/")
        if img["mask_filename"]:
            assert img["mask_url"].startswith("/api/demo/mask/")

    # Phase 2: Image Matching / Survey Readiness
    p2 = data["phase2_matching"]
    assert p2["pairs_analyzed"] >= 1
    assert p2["readiness_status"] in [
        "EXCELLENT_OVERLAP",
        "SUITABLE_FOR_RECONSTRUCTION",
        "READY_WITH_WARNINGS",
        "RECAPTURE_REQUIRED",
        "INSUFFICIENT_IMAGE_CONNECTIVITY",
    ]

    # Phase 3: 3D Reconstruction
    p3 = data["phase3_reconstruction"]
    assert p3["is_demo"] is True
    assert p3["point_count"] > 0
    assert p3["mesh_vertex_count"] > 0
    assert p3["scale_status"] == "LOCAL"
    assert "DEMO / SYNTHETIC GEOMETRY" in p3["disclaimer"]

    # Phase 4: Material Classification
    p4 = data["phase4_materials"]
    assert p4["is_demo"] is True
    assert len(p4["primary_material"]) > 0
    assert p4["average_confidence"] > 0.0

    # Phase 5: Deterioration Detection
    p5 = data["phase5_deterioration"]
    assert p5["is_demo"] is True
    assert p5["total_detections"] > 0
    assert "crack" in p5["damage_distribution"] or len(p5["detections"]) > 0

    # Phase 6: 2D-to-3D Damage Mapping
    p6 = data["phase6_damage_mapping"]
    assert p6["is_demo"] is True
    assert p6["total_mapped"] > 0
    assert len(p6["mappings"]) > 0
    first_map = p6["mappings"][0]
    assert first_map["mapping_status"] in ["MAPPED", "PARTIALLY_MAPPED"]

    # Phase 7: Multi-Temporal Monitoring
    p7 = data["phase7_temporal"]
    assert p7["is_demo"] is True
    assert p7["fitness"] > 0.0
    assert p7["total_changes"] > 0
    assert "SYNTHETIC DEMONSTRATION" in p7["disclaimer"]

    # Final Summary Card
    fs = data["final_summary"]
    assert fs["is_demo"] is True
    assert fs["site_name"] == "Demo Heritage Structure"
    assert "T1" in fs["survey_epochs"] and "T2" in fs["survey_epochs"]
    assert fs["scale_status"] == "LOCAL"
    assert "reliability_indicators" in fs
