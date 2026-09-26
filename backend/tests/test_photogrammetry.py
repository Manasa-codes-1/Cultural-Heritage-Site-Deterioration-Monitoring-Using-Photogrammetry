"""
Phase 3 Photogrammetry & 3D Reconstruction Tests.
Tests engine abstraction, mock/demo engine generation, Open3D geometry processing,
and FastAPI photogrammetry endpoints.
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import numpy as np
import cv2

from app.main import app
from app.photogrammetry.mock_engine import MockPhotogrammetryEngine
from app.photogrammetry.colmap_engine import ColmapEngine
from app.photogrammetry import check_photogrammetry_system, get_photogrammetry_engine
from app.processing.pointcloud_processor import PointCloudProcessor


def test_photogrammetry_system_availability():

    """Verify system diagnostics returns structured, non-null hardware/binary info."""
    diag = check_photogrammetry_system()
    assert "colmap_available" in diag
    assert "cuda_available" in diag
    assert "open3d_available" in diag
    assert "recommended_engine" in diag
    assert isinstance(diag["system_notes"], list)
    assert len(diag["system_notes"]) > 0


def test_colmap_engine_missing_graceful():
    """Verify ColmapEngine handles non-existent executable without raising unhandled exception."""
    engine = ColmapEngine(binary_path="non_existent_colmap_bin_xyz")
    avail = engine.check_availability()
    assert avail["available"] is False
    assert avail["binary_path"] is None


def test_mock_photogrammetry_engine_generation(tmp_path: Path):
    """Verify MockPhotogrammetryEngine generates valid PLY and OBJ files with demo tags."""
    engine = MockPhotogrammetryEngine()
    avail = engine.check_availability()
    assert avail["available"] is True

    # Create dummy images
    dummy_img = tmp_path / "img1.jpg"
    img_data = np.full((100, 100, 3), 128, dtype=np.uint8)
    cv2.imwrite(str(dummy_img), img_data)

    workspace = tmp_path / "recon_workspace"
    result = engine.run_reconstruction(
        survey_id="test-survey-123",
        image_paths=[dummy_img],
        workspace_dir=workspace,
        dense=True,
        generate_mesh=True,
    )

    assert result["is_demo"] is True
    assert result["sparse_point_count"] > 0
    assert result["dense_point_count"] > 0
    assert result["mesh_vertex_count"] > 0
    assert result["mesh_triangle_count"] > 0
    assert Path(result["sparse_point_cloud_path"]).exists()
    assert Path(result["dense_point_cloud_path"]).exists()
    assert Path(result["mesh_path"]).exists()

    # Check bounding box
    bbox = result["bounding_box"]
    assert "centroid" in bbox
    assert "dimensions" in bbox
    assert len(bbox["centroid"]) == 3

    # Check camera poses
    assert len(result["camera_poses"]) == 1
    assert "position" in result["camera_poses"][0]


def test_open3d_pointcloud_processor(tmp_path: Path):
    """Verify PointCloudProcessor accurately inspects geometry and downsamples."""
    engine = MockPhotogrammetryEngine()
    dummy_img = tmp_path / "img.jpg"
    cv2.imwrite(str(dummy_img), np.zeros((50, 50, 3), dtype=np.uint8))
    workspace = tmp_path / "proc_workspace"

    recon = engine.run_reconstruction(
        survey_id="test-survey-proc",
        image_paths=[dummy_img],
        workspace_dir=workspace,
        dense=True,
        generate_mesh=True,
    )

    dense_ply = Path(recon["dense_point_cloud_path"])
    mesh_ply = Path(recon["mesh_path"])

    pcd_info = PointCloudProcessor.inspect_point_cloud(dense_ply)
    assert pcd_info["point_count"] > 1000
    assert len(pcd_info["centroid"]) == 3

    mesh_info = PointCloudProcessor.inspect_mesh(mesh_ply)
    assert mesh_info["vertex_count"] > 100
    assert mesh_info["triangle_count"] > 100

    # Downsampling test
    down_ply = workspace / "downsampled.ply"
    PointCloudProcessor.downsample_point_cloud(dense_ply, down_ply, voxel_size=0.1)
    assert down_ply.exists()


def test_photogrammetry_api_lifecycle(client, db_session):
    """Test the complete API lifecycle: availability -> trigger -> status -> stream model."""
    # 1. Check availability
    res_avail = client.get("/api/photogrammetry/availability")
    assert res_avail.status_code == 200
    avail_data = res_avail.json()
    assert "recommended_engine" in avail_data

    # 2. Create Site and Survey
    site_res = client.post(
        "/api/sites",
        json={
            "name": "Phase 3 Test Site",
            "location": "Sector 3",
            "primary_material": "Sandstone",
        },
    )
    assert site_res.status_code == 201
    site_id = site_res.json()["id"]

    survey_res = client.post(
        "/api/surveys",
        json={
            "site_id": site_id,
            "survey_code": "SRV-P3-001",
            "description": "Photogrammetry testing survey",
        },
    )
    assert survey_res.status_code == 201
    survey_id = survey_res.json()["id"]

    # 3. Upload a sample image to survey
    img_bytes = cv2.imencode(".jpg", np.full((120, 120, 3), 150, dtype=np.uint8))[1].tobytes()
    upload_res = client.post(
        f"/api/surveys/{survey_id}/images/upload",
        files=[("files", ("test_p3_1.jpg", img_bytes, "image/jpeg"))],
    )
    assert upload_res.status_code == 201

    # 4. Trigger reconstruction (using mock engine)
    recon_res = client.post(
        f"/api/photogrammetry/surveys/{survey_id}/reconstruct",
        json={"engine": "mock", "dense": True, "generate_mesh": True, "force": True},
    )
    assert recon_res.status_code == 202
    recon_data = recon_res.json()
    recon_id = recon_data["id"]
    assert recon_data["survey_id"] == survey_id

    # 5. Execute synchronously for test verification
    from app.services.photogrammetry_service import photogrammetry_service
    photogrammetry_service._execute_reconstruction_pipeline(
        reconstruction_id=recon_id,
        survey_id=survey_id,
        engine_name="mock",
        dense=True,
        generate_mesh=True,
        db_session=db_session,
    )


    # 6. Fetch status
    status_res = client.get(f"/api/photogrammetry/reconstructions/{recon_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "completed"
    assert status_res.json()["is_demo"] is True

    # 7. Fetch full survey reconstruction
    survey_recon_res = client.get(f"/api/photogrammetry/surveys/{survey_id}/reconstruction")
    assert survey_recon_res.status_code == 200
    survey_recon = survey_recon_res.json()
    assert survey_recon["point_count"] > 0
    assert survey_recon["mesh_vertex_count"] > 0
    assert survey_recon["is_demo"] is True

    # 8. Download 3D model file
    model_res = client.get(f"/api/photogrammetry/reconstructions/{recon_id}/model?model_type=mesh")
    assert model_res.status_code == 200
    assert len(model_res.content) > 0

    # 9. Download logs
    logs_res = client.get(f"/api/photogrammetry/reconstructions/{recon_id}/logs")
    assert logs_res.status_code == 200
    assert "DEMO" in logs_res.text or "RESEARCH SAFETY" in logs_res.text
