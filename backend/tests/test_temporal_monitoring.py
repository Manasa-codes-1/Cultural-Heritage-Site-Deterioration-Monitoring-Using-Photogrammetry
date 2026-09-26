"""
Unit and Integration Tests for Phase 7: Multi-Temporal Monitoring & Change Detection.
Tests survey pair validation, Open3D ICP alignment, synthetic displacement quantification,
damage evolution categorization across surveys, and REST API lifecycles.
"""
import pytest
import numpy as np
import open3d as o3d
from datetime import datetime, timezone, timedelta

from app.models.heritage import (
    Site,
    Survey,
    Image,
    Reconstruction,
    DeteriorationDetection,
    Deterioration3DMapping,
    TemporalComparison,
    TemporalChangeRecord,
)
from app.services.temporal_alignment import TemporalAlignmentService
from app.services.temporal_change_detector import TemporalChangeDetector
from app.services.temporal_service import temporal_service
from app.schemas.temporal import (
    TemporalComparisonCreateRequest,
    TemporalAlignmentRequest,
    TemporalChangeDetectRequest,
    TemporalDamageTrackRequest,
)


# -------------------------------------------------------------
# 1. Alignment Tests (Mathematical Validation)
# -------------------------------------------------------------

def test_identity_alignment():
    """Validates that registering identical point clouds produces identity transform and 100% fitness."""
    pcd1 = TemporalAlignmentService.create_synthetic_plane(z=5.0, num_points_per_axis=10)
    pcd2 = TemporalAlignmentService.create_synthetic_plane(z=5.0, num_points_per_axis=10)

    result = TemporalAlignmentService.align_point_clouds(
        target_pcd=pcd1,
        source_pcd=pcd2,
        method="IDENTITY",
        max_correspondence_distance=0.05,
    )

    assert result.alignment_status == "ALIGNED"
    assert result.fitness == 1.0
    assert result.rmse == pytest.approx(0.0, abs=1e-5)
    np.testing.assert_allclose(result.transformation_matrix, np.eye(4), atol=1e-5)


def test_icp_known_translation_recovery():
    """Validates that ICP registration successfully recovers a known translation shift."""
    pcd_target = TemporalAlignmentService.create_synthetic_plane(z=5.0, num_points_per_axis=12)
    pcd_source = o3d.geometry.PointCloud(pcd_target)

    # Apply known shift of +0.02 along X and -0.01 along Y
    known_shift = np.array([0.02, -0.01, 0.0])
    pcd_source.points = o3d.utility.Vector3dVector(np.asarray(pcd_source.points) + known_shift)

    result = TemporalAlignmentService.align_point_clouds(
        target_pcd=pcd_target,
        source_pcd=pcd_source,
        method="ICP_POINT_TO_POINT",
        max_correspondence_distance=0.08,
        max_iterations=50,
    )

    assert result.alignment_status == "ALIGNED"
    assert result.fitness > 0.90
    assert result.rmse < 0.005

    # Transformed source should align back to target
    recovered_t = np.array(result.transformation_matrix)
    aligned_source = o3d.geometry.PointCloud(pcd_source)
    aligned_source.transform(recovered_t)

    # Inlier distances after transform should be very small
    dists = np.asarray(aligned_source.compute_point_cloud_distance(pcd_target))
    assert dists.mean() < 0.005


def test_icp_insufficient_overlap():
    """Tests that orthogonal or non-overlapping geometries assign ALIGNMENT_REQUIRES_REVIEW or FAILED."""
    pcd_target = TemporalAlignmentService.create_synthetic_plane(z=5.0, num_points_per_axis=10)

    # Orthogonal plane along Y-Z (X = 0)
    ys = np.linspace(-1, 1, 100)
    zs = np.linspace(4, 6, 100)
    xs = np.zeros(100)
    pts = np.vstack([xs, ys, zs]).T
    pcd_source = o3d.geometry.PointCloud()
    pcd_source.points = o3d.utility.Vector3dVector(pts)

    result = TemporalAlignmentService.align_point_clouds(
        target_pcd=pcd_target,
        source_pcd=pcd_source,
        method="ICP_POINT_TO_POINT",
        max_correspondence_distance=0.05,
    )

    # With orthogonal points, fitness will not meet the 0.60 threshold
    assert result.alignment_status in ["ALIGNMENT_REQUIRES_REVIEW", "FAILED"]


# -------------------------------------------------------------
# 2. Geometric Change Detection Tests
# -------------------------------------------------------------

def test_geometric_change_zero_displacement():
    """Validates that identical geometries report zero change and no candidates."""
    pcd1 = TemporalAlignmentService.create_synthetic_plane(z=5.0, num_points_per_axis=10)
    pcd2 = TemporalAlignmentService.create_synthetic_plane(z=5.0, num_points_per_axis=10)

    report = TemporalChangeDetector.detect_changes(
        target_pcd=pcd1,
        aligned_source_pcd=pcd2,
        change_threshold=0.02,
        scale_status="LOCAL",
    )

    assert report.total_points_evaluated == 100
    assert report.changed_point_count == 0
    assert report.unchanged_point_count == 100
    assert report.change_ratio == 0.0
    assert report.mean_distance == pytest.approx(0.0, abs=1e-5)
    assert len(report.clusters) == 0


def test_geometric_change_known_displacement():
    """Validates that points shifted beyond threshold are flagged as GEOMETRIC_CHANGE_CANDIDATE."""
    pcd1 = TemporalAlignmentService.create_synthetic_plane(z=5.0, num_points_per_axis=10)
    pcd2 = o3d.geometry.PointCloud(pcd1)

    # Shift all points along Z by 0.04 (threshold is 0.02)
    pts = np.asarray(pcd2.points).copy()
    pts[:, 2] += 0.04
    pcd2.points = o3d.utility.Vector3dVector(pts)

    report = TemporalChangeDetector.detect_changes(
        target_pcd=pcd1,
        aligned_source_pcd=pcd2,
        change_threshold=0.02,
        scale_status="LOCAL",
    )

    assert report.total_points_evaluated == 100
    assert report.changed_point_count == 100
    assert report.change_ratio == 1.0
    assert report.mean_distance == pytest.approx(0.04, abs=1e-4)
    assert len(report.clusters) > 0


# -------------------------------------------------------------
# 3. Deterioration Evolution Tracking Tests
# -------------------------------------------------------------

def test_deterioration_evolution_states(db_session):
    """
    Tests deterioration tracking categorization:
    - Same location + defect -> PERSISTING_DETERIORATION
    - Same location + different material -> MATERIAL_LABEL_CHANGED
    - Only in T2 -> NEW_DETERIORATION
    - Only in T1 -> POSSIBLY_RESOLVED_OR_UNDETECTED
    """
    db = db_session
    # Create test site
    site = Site(name="Temporal Test Temple", location="Survey Quad A")
    db.add(site)
    db.commit()

    # Create Survey T1 (Baseline) and Survey T2 (Comparison)
    date_t1 = datetime(2025, 1, 15, tzinfo=timezone.utc)
    date_t2 = datetime(2025, 7, 15, tzinfo=timezone.utc)

    srv1 = Survey(site_id=site.id, survey_code="TEST-T1", survey_date=date_t1)
    srv2 = Survey(site_id=site.id, survey_code="TEST-T2", survey_date=date_t2)
    db.add_all([srv1, srv2])
    db.commit()

    # Add mock reconstructions
    r1 = Reconstruction(survey_id=srv1.id, status="completed", is_demo=True)
    r2 = Reconstruction(survey_id=srv2.id, status="completed", is_demo=True)
    db.add_all([r1, r2])
    db.commit()

    # Add images
    img1 = Image(survey_id=srv1.id, filename="t1.jpg", relative_path="t1.jpg", file_size_bytes=1000)
    img2 = Image(survey_id=srv2.id, filename="t2.jpg", relative_path="t2.jpg", file_size_bytes=1000)
    db.add_all([img1, img2])
    db.commit()

    # Add Deterioration detections & 3D mappings for T1
    det_t1_1 = DeteriorationDetection(
        survey_id=srv1.id, image_id=img1.id, damage_type="crack", confidence=0.85
    )
    det_t1_2 = DeteriorationDetection(
        survey_id=srv1.id, image_id=img1.id, damage_type="erosion", confidence=0.80
    )
    db.add_all([det_t1_1, det_t1_2])
    db.commit()

    map_t1_1 = Deterioration3DMapping(
        detection_id=det_t1_1.id,
        survey_id=srv1.id,
        reconstruction_id=r1.id,
        image_id=img1.id,
        world_x=0.0,
        world_y=0.0,
        world_z=5.0,
        deterioration_type="crack",
        deterioration_confidence=0.85,
        material_class="sandstone",
    )
    map_t1_2 = Deterioration3DMapping(
        detection_id=det_t1_2.id,
        survey_id=srv1.id,
        reconstruction_id=r1.id,
        image_id=img1.id,
        world_x=1.0,
        world_y=1.0,
        world_z=5.0,
        deterioration_type="erosion",
        deterioration_confidence=0.80,
        material_class="sandstone",
    )
    db.add_all([map_t1_1, map_t1_2])
    db.commit()

    # Add Detections & 3D mappings for T2
    det_t2_1 = DeteriorationDetection(
        survey_id=srv2.id, image_id=img2.id, damage_type="crack", confidence=0.88
    )
    det_t2_2 = DeteriorationDetection(
        survey_id=srv2.id, image_id=img2.id, damage_type="spalling", confidence=0.90
    )
    db.add_all([det_t2_1, det_t2_2])
    db.commit()

    map_t2_1 = Deterioration3DMapping(
        detection_id=det_t2_1.id,
        survey_id=srv2.id,
        reconstruction_id=r2.id,
        image_id=img2.id,
        world_x=0.01,
        world_y=0.01,
        world_z=5.0,
        deterioration_type="crack",
        deterioration_confidence=0.88,
        material_class="sandstone",
    )
    map_t2_2 = Deterioration3DMapping(
        detection_id=det_t2_2.id,
        survey_id=srv2.id,
        reconstruction_id=r2.id,
        image_id=img2.id,
        world_x=-1.0,
        world_y=-1.0,
        world_z=5.0,
        deterioration_type="spalling",
        deterioration_confidence=0.90,
        material_class="sandstone",
    )
    db.add_all([map_t2_1, map_t2_2])
    db.commit()

    # Create Temporal Comparison
    comp_req = TemporalComparisonCreateRequest(
        site_id=site.id,
        baseline_survey_id=srv1.id,
        comparison_survey_id=srv2.id,
        alignment_method="IDENTITY",
        change_threshold=0.02,
        damage_matching_distance_threshold=0.15,
    )
    comp = temporal_service.create_or_get_comparison(comp_req, db)
    assert comp.elapsed_days == 181

    # Run deterioration tracking
    track_req = TemporalDamageTrackRequest(damage_matching_distance_threshold=0.15)
    records = temporal_service.run_deterioration_tracking(comp.id, track_req, db)

    statuses = {r.change_status: r for r in records}
    assert "PERSISTING_DETERIORATION" in statuses
    assert "POSSIBLY_RESOLVED_OR_UNDETECTED" in statuses
    assert "NEW_DETERIORATION" in statuses

    persisting = statuses["PERSISTING_DETERIORATION"]
    assert persisting.deterioration_type == "crack"
    assert persisting.material_status == "CONSISTENT"
    assert persisting.spatial_distance is not None
    assert persisting.spatial_distance < 0.05

    unresolved = statuses["POSSIBLY_RESOLVED_OR_UNDETECTED"]
    assert unresolved.deterioration_type == "erosion"
    assert "Candidate absence may stem from" in unresolved.notes

    new_defect = statuses["NEW_DETERIORATION"]
    assert new_defect.deterioration_type == "spalling"


def test_invalid_survey_pair_validation(db_session):
    """Validates rejection of mismatched sites or identical surveys."""
    db = db_session
    site_a = Site(name="Site Alpha", location="Loc A")
    site_b = Site(name="Site Beta", location="Loc B")
    db.add_all([site_a, site_b])
    db.commit()

    srv_a = Survey(site_id=site_a.id, survey_code="SRV-A")
    srv_b = Survey(site_id=site_b.id, survey_code="SRV-B")
    db.add_all([srv_a, srv_b])
    db.commit()

    # Cross-site comparison request
    req = TemporalComparisonCreateRequest(
        site_id=site_a.id,
        baseline_survey_id=srv_a.id,
        comparison_survey_id=srv_b.id,
    )

    with pytest.raises(Exception) as excinfo:
        temporal_service.create_or_get_comparison(req, db)
    assert "INVALID_SURVEY_PAIR" in str(excinfo.value)

    # Same survey comparison request
    req_same = TemporalComparisonCreateRequest(
        site_id=site_a.id,
        baseline_survey_id=srv_a.id,
        comparison_survey_id=srv_a.id,
    )
    with pytest.raises(Exception) as excinfo_same:
        temporal_service.create_or_get_comparison(req_same, db)
    assert "INVALID_SURVEY_PAIR" in str(excinfo_same.value)


# -------------------------------------------------------------
# 4. API Endpoints Lifecycle Test
# -------------------------------------------------------------

def test_api_temporal_monitoring_lifecycle(client, db_session):
    """Tests full REST API lifecycle: create comparison, align, detect change, track damage, fetch timeline."""
    site = Site(name="API Test Site", location="Sector 4")
    db_session.add(site)
    db_session.commit()

    srv1 = Survey(
        site_id=site.id,
        survey_code="API-SRV-1",
        survey_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    srv2 = Survey(
        site_id=site.id,
        survey_code="API-SRV-2",
        survey_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    db_session.add_all([srv1, srv2])
    db_session.commit()

    r1 = Reconstruction(survey_id=srv1.id, status="completed", is_demo=True)
    r2 = Reconstruction(survey_id=srv2.id, status="completed", is_demo=True)
    db_session.add_all([r1, r2])
    db_session.commit()

    # 1. POST /api/temporal/compare
    comp_payload = {
        "site_id": site.id,
        "baseline_survey_id": srv1.id,
        "comparison_survey_id": srv2.id,
        "alignment_method": "ICP_POINT_TO_POINT",
        "change_threshold": 0.02,
        "damage_matching_distance_threshold": 0.15,
    }
    res_comp = client.post("/api/temporal/compare", json=comp_payload)
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert comp_data["elapsed_days"] == 151
    comparison_id = comp_data["id"]

    # 2. POST /api/temporal/{id}/align
    res_align = client.post(
        f"/api/temporal/{comparison_id}/align",
        json={"alignment_method": "IDENTITY", "max_correspondence_distance": 0.08},
    )
    assert res_align.status_code == 200
    align_data = res_align.json()
    assert align_data["alignment_result"]["alignment_status"] in ["ALIGNED", "ALIGNMENT_REQUIRES_REVIEW"]

    # 3. POST /api/temporal/{id}/detect-change
    res_change = client.post(
        f"/api/temporal/{comparison_id}/detect-change",
        json={"change_threshold": 0.02},
    )
    assert res_change.status_code == 200
    change_data = res_change.json()
    assert "total_points_evaluated" in change_data["geometric_change_report"]

    # 4. POST /api/temporal/{id}/track-deterioration
    res_track = client.post(
        f"/api/temporal/{comparison_id}/track-deterioration",
        json={"damage_matching_distance_threshold": 0.15},
    )
    assert res_track.status_code == 200

    # 5. GET /api/temporal/{id}/changes
    res_records = client.get(f"/api/temporal/{comparison_id}/changes")
    assert res_records.status_code == 200
    assert isinstance(res_records.json(), list)

    # 6. GET /api/temporal/site/{site_id}/timeline
    res_timeline = client.get(f"/api/temporal/site/{site.id}/timeline")
    assert res_timeline.status_code == 200
    timeline_items = res_timeline.json()
    assert len(timeline_items) == 2
    assert timeline_items[0]["survey_code"] == "API-SRV-1"
    assert timeline_items[1]["survey_code"] == "API-SRV-2"

    # 7. GET /api/temporal/site/{site_id}/comparisons
    res_list = client.get(f"/api/temporal/site/{site.id}/comparisons")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
