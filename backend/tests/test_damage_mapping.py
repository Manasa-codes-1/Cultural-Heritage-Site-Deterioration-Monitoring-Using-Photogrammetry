"""
Unit and Integration Tests for Phase 6: 2D-to-3D Damage Mapping.
Validates camera models, ray generation, synthetic ray-surface intersections,
point cloud proximity fallback, reprojection error calculation, database persistence,
and REST API endpoints using deterministic synthetic geometry.
"""
import pytest
import numpy as np
import math
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.heritage import (
    Site,
    Survey,
    Image,
    Reconstruction,
    DeteriorationDetection,
    Deterioration3DMapping,
    Deterioration3DMappingPoint,
)
from app.services.camera_model import (
    CameraModel,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion,
)
from app.services.surface_raycaster import SurfaceRaycaster
from app.services.damage_sampler import DamagePointSampler
from app.services.damage_mapping_service import DamageMappingService


def test_quaternion_and_rotation_conversions():
    """Validates quaternion to rotation matrix conversions and roundtrips."""
    # Identity rotation (looking down +Z)
    q_ident = [0.0, 0.0, 0.0, 1.0]
    R_ident = quaternion_to_rotation_matrix(q_ident)
    assert np.allclose(R_ident, np.eye(3), atol=1e-6)

    # 90-degree yaw rotation around Y-axis
    yaw_90 = math.radians(90)
    q_yaw = [0.0, math.sin(yaw_90 / 2), 0.0, math.cos(yaw_90 / 2)]
    R_yaw = quaternion_to_rotation_matrix(q_yaw)
    assert np.allclose(R_yaw @ R_yaw.T, np.eye(3), atol=1e-6)  # Orthonormal

    # Roundtrip conversion
    q_recovered = rotation_matrix_to_quaternion(R_yaw)
    R_recovered = quaternion_to_rotation_matrix(q_recovered)
    assert np.allclose(R_yaw, R_recovered, atol=1e-5)


def test_camera_model_creation_and_validation():
    """Validates CameraModel parameters and error handling."""
    # Invalid image dimensions
    with pytest.raises(ValueError):
        CameraModel(width=0, height=600, fx=800, fy=800, cx=400, cy=300, position=np.array([0, 0, 0]))

    # Invalid focal length
    with pytest.raises(ValueError):
        CameraModel(width=800, height=600, fx=-10, fy=800, cx=400, cy=300, position=np.array([0, 0, 0]))

    # Valid camera looking along -Z from (0, 0, 5) towards (0, 0, 0)
    cam = CameraModel.create_from_lookat(
        eye=[0.0, 0.0, 5.0],
        target=[0.0, 0.0, 0.0],
        width=1000,
        height=1000,
        fov_degrees=90.0,
    )
    assert cam.width == 1000
    assert cam.height == 1000
    assert cam.position[2] == 5.0


def test_pixel_to_ray_transformation():
    """
    Validates pixel to ray transformation using synthetic camera.
    A camera at (0, 0, 5) looking at (0, 0, 0):
    Center pixel (cx, cy) must produce a normalized ray pointing along (0, 0, -1).
    """
    cam = CameraModel.create_from_lookat(
        eye=[0.0, 0.0, 5.0],
        target=[0.0, 0.0, 0.0],
        width=800,
        height=600,
        fov_degrees=60.0,
    )

    origin, direction = cam.pixel_to_ray(u=cam.cx, v=cam.cy)

    assert np.allclose(origin, [0.0, 0.0, 5.0], atol=1e-6)
    # Forward vector from (0, 0, 5) to (0, 0, 0) is [0, 0, -1]
    assert np.allclose(direction, [0.0, 0.0, -1.0], atol=1e-5)
    # Unit length
    assert math.isclose(np.linalg.norm(direction), 1.0, rel_tol=1e-6)


def test_synthetic_ray_plane_intersection():
    """
    Deterministic geometric unit test:
    Mesh plane at Z = 0.
    Camera at (0, 0, 5) looking at (0, 0, 0).
    Center ray intersects the plane at exactly (0, 0, 0) with distance 5.0.
    """
    raycaster = SurfaceRaycaster.create_synthetic_plane(
        z=0.0,
        x_min=-2.0,
        x_max=2.0,
        y_min=-2.0,
        y_max=2.0,
    )

    cam = CameraModel.create_from_lookat(
        eye=[0.0, 0.0, 5.0],
        target=[0.0, 0.0, 0.0],
        width=800,
        height=800,
        fov_degrees=90.0,
    )

    origin, direction = cam.pixel_to_ray(u=400, v=400)
    hit_pos, dist, surf_src, method = raycaster.cast_ray(origin, direction)

    assert hit_pos is not None
    assert math.isclose(dist, 5.0, abs_tol=1e-4)
    assert np.allclose(hit_pos, [0.0, 0.0, 0.0], atol=1e-4)
    assert surf_src == "DENSE_MESH"
    assert method == "MESH_RAYCAST"


def test_no_surface_intersection_handling():
    """Validates that rays missing the surface return NO_SURFACE_INTERSECTION."""
    raycaster = SurfaceRaycaster.create_synthetic_plane(
        z=0.0,
        x_min=-1.0,
        x_max=1.0,
        y_min=-1.0,
        y_max=1.0,
    )

    # Ray pointing away in the opposite direction (+Z)
    hit_pos, dist, surf_src, method = raycaster.cast_ray(
        origin=np.array([0.0, 0.0, 5.0]),
        direction=np.array([0.0, 0.0, 1.0]),
    )
    assert hit_pos is None
    assert dist is None
    assert surf_src == "NONE"
    assert method == "NO_SURFACE_INTERSECTION"


def test_point_cloud_proximity_fallback():
    """Validates point cloud proximity approximation when mesh is absent."""
    points = [
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [2.0, 2.0, 0.0],
    ]
    raycaster = SurfaceRaycaster.create_synthetic_point_cloud(points, proximity_tolerance=0.1)

    # Ray from (0, 0, 5) pointing at (0, 0, 0)
    hit_pos, dist, surf_src, method = raycaster.cast_ray(
        origin=np.array([0.0, 0.0, 5.0]),
        direction=np.array([0.0, 0.0, -1.0]),
    )

    assert hit_pos is not None
    assert np.allclose(hit_pos, [0.0, 0.0, 0.0], atol=1e-5)
    assert math.isclose(dist, 5.0, abs_tol=1e-4)
    assert surf_src == "DENSE_POINT_CLOUD"
    assert method == "POINT_CLOUD_APPROXIMATION"


def test_reprojection_calculation_accuracy():
    """
    Projects 3D world point back into camera and confirms reprojection error is near zero.
    """
    cam = CameraModel.create_from_lookat(
        eye=[0.0, 0.0, 4.0],
        target=[0.0, 0.0, 0.0],
        width=1000,
        height=800,
        fov_degrees=70.0,
    )

    test_u, test_v = 450.0, 350.0
    origin, direction = cam.pixel_to_ray(test_u, test_v)

    # Intersection point at distance 4.0 along the ray
    test_world_point = origin + 4.0 * direction

    # Reproject back
    reproj_err = cam.compute_reprojection_error(test_world_point, test_u, test_v)
    assert reproj_err is not None
    assert reproj_err < 0.05  # Within 0.05 pixel precision


def test_damage_point_sampler_strategies():
    """Validates CENTER_ONLY, BOX_GRID, and POLYGON_VERTICES sampling."""
    det = DeteriorationDetection(
        damage_type="crack",
        confidence=0.88,
        bounding_box={"x": 100, "y": 200, "w": 50, "h": 80},
        polygon=[[100, 200], [150, 200], [150, 280], [100, 280]],
    )

    # CENTER_ONLY
    pts_center = DamagePointSampler.sample_points(det, "CENTER_ONLY")
    assert len(pts_center) == 1
    assert pts_center[0][0] == "center"
    assert pts_center[0][1] == 125.0  # 100 + 25
    assert pts_center[0][2] == 240.0  # 200 + 40

    # BOX_GRID
    pts_grid = DamagePointSampler.sample_points(det, "BOX_GRID")
    assert len(pts_grid) == 9

    # POLYGON_VERTICES
    pts_poly = DamagePointSampler.sample_points(det, "POLYGON_VERTICES")
    assert len(pts_poly) == 5  # center + 4 polygon vertices


def test_api_damage_mapping_lifecycle(client, db_session):
    """
    Full end-to-end integration test of Phase 6:
    Creates a Site, Survey, Image, Reconstruction with camera poses, DeteriorationDetection,
    maps the detection to 3D, and verifies endpoints.
    """
    # Create test survey entities
    site = Site(name="Phase 6 Test Heritage Site", location="Site Loc")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    survey = Survey(site_id=site.id, survey_code="SURV-PHASE6", operator="Lead Architect")
    db_session.add(survey)
    db_session.commit()
    db_session.refresh(survey)

    image = Image(
        survey_id=survey.id,
        filename="wall_defect_01.jpg",
        relative_path="surveys/SURV-PHASE6/wall_defect_01.jpg",
        file_size_bytes=10240,
        width=1000,
        height=1000,
    )
    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)

    # Camera at (0, 0, 3) looking at (0, 0, 0)
    camera_poses = [
        {
            "image_id": image.id,
            "filename": image.filename,
            "position": [0.0, 0.0, 3.0],
            "rotation_quaternion": [0.0, 0.0, 0.0, 1.0],
            "focal_length": 1000.0,
            "cx": 500.0,
            "cy": 500.0,
        }
    ]

    recon = Reconstruction(
        survey_id=survey.id,
        status="completed",
        engine="mock",
        is_demo=True,
        camera_poses=camera_poses,
    )
    db_session.add(recon)
    db_session.commit()
    db_session.refresh(recon)

    det = DeteriorationDetection(
        survey_id=survey.id,
        image_id=image.id,
        damage_type="erosion",
        confidence=0.82,
        status="CONFIRMED",
        material_class="sandstone",
        material_confidence=0.78,
        material_association_status="SPATIAL_OVERLAP",
        bounding_box={"x": 480, "y": 480, "w": 40, "h": 40},
        is_demo=True,
        inference_mode="demo",
    )
    db_session.add(det)
    db_session.commit()
    db_session.refresh(det)

    detection_id = det.id
    survey_id = survey.id
    recon_id = recon.id

    # 1. Map single detection
    resp = client.post(f"/api/damage-mapping/detections/{detection_id}/map?sampling_strategy=CENTER_ONLY")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["detection_id"] == detection_id
    assert data["deterioration_type"] == "erosion"
    assert data["material_class"] == "sandstone"
    assert data["material_confidence"] == 0.78
    assert data["deterioration_confidence"] == 0.82
    assert data["is_demo"] is True
    assert data["inference_mode"] == "demo"
    assert data["scale_status"] == "LOCAL"

    # 2. Get detection mapping
    resp_get = client.get(f"/api/damage-mapping/detections/{detection_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["detection_id"] == detection_id

    # 3. Survey batch mapping
    resp_survey = client.post(f"/api/damage-mapping/surveys/{survey_id}/map", json={"sampling_strategy": "CENTER_ONLY"})
    assert resp_survey.status_code == 200
    summary = resp_survey.json()
    assert summary["survey_id"] == survey_id
    assert summary["total_eligible_detections"] == 1
    assert "erosion" in summary["detections_by_type"]
    assert "sandstone" in summary["detections_by_material"]
    assert "sandstone" in summary["material_deterioration_cross_tabulation"]
    assert summary["material_deterioration_cross_tabulation"]["sandstone"]["erosion"] == 1

    # 4. Get survey mapping summary
    resp_summ = client.get(f"/api/damage-mapping/surveys/{survey_id}")
    assert resp_summ.status_code == 200
    assert resp_summ.json()["total_eligible_detections"] == 1

    # 5. Get reconstruction mappings
    resp_recon = client.get(f"/api/damage-mapping/reconstructions/{recon_id}")
    assert resp_recon.status_code == 200
    recon_mappings = resp_recon.json()
    assert len(recon_mappings) == 1
    assert recon_mappings[0]["detection_id"] == detection_id

    # 6. Validate mapping
    current_mapping_id = recon_mappings[0]["id"]
    resp_val = client.post(f"/api/damage-mapping/validate/{current_mapping_id}?tolerance_px=5.0")
    assert resp_val.status_code == 200
    val_data = resp_val.json()
    assert val_data["mapping_id"] == current_mapping_id
