import io
import cv2
import numpy as np
import pytest
from PIL import Image as PILImage
from app.processing.feature_matcher import ImageFeatureMatcher


def create_synthetic_textured_image(width=400, height=300, offset=0) -> np.ndarray:
    """Deterministic synthetic brick masonry pattern for testing."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    np.random.seed(42 + offset)
    noise = np.random.randint(120, 220, (height, width, 3), dtype=np.uint8)
    img = cv2.addWeighted(img, 0.3, noise, 0.7, 0)
    for y in range(0, height, 40):
        cv2.line(img, (0, y), (width, y), (50, 50, 50), 2)
    for x in range(offset % 60, width, 60):
        cv2.line(img, (x, 0), (x, height), (50, 50, 50), 2)
    return img


def create_synthetic_blank_image(width=400, height=300) -> np.ndarray:
    """Uniform textureless image to test insufficient feature detection."""
    return np.full((height, width, 3), 180, dtype=np.uint8)


def create_synthetic_checkerboard(width=400, height=300) -> np.ndarray:
    """Checkerboard pattern with distinctly different features from masonry."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    sq = 25
    for i in range(0, height, sq):
        for j in range(0, width, sq):
            if (i // sq + j // sq) % 2 == 0:
                img[i : i + sq, j : j + sq] = 255
    return img


# 1. Feature Extraction Test
def test_feature_extraction():
    matcher = ImageFeatureMatcher(max_features=500, min_keypoints=50)
    img = create_synthetic_textured_image()
    kps, descs, dims = matcher.extract_features(img)
    assert len(kps) > 50
    assert descs is not None
    assert dims == (400, 300)


# 2. Good Matching Pair Test
def test_good_matching_pair():
    matcher = ImageFeatureMatcher(min_good_matches=25, warn_good_matches=10)
    img_a = create_synthetic_textured_image(offset=0)
    img_b = create_synthetic_textured_image(offset=4)  # Small viewpoint shift

    kps_a, descs_a, _ = matcher.extract_features(img_a)
    kps_b, descs_b, _ = matcher.extract_features(img_b)

    result = matcher.match_descriptors(kps_a, descs_a, kps_b, descs_b)
    assert result["status"] == "GOOD"
    assert result["good_matches"] >= 25
    assert result["match_ratio"] > 0.05
    assert "High" in result["estimated_overlap"] or "Moderate" in result["estimated_overlap"]


# 3. Poor Matching Pair Test
def test_poor_matching_pair():
    matcher = ImageFeatureMatcher(min_good_matches=50, warn_good_matches=25)
    img_a = create_synthetic_textured_image()
    img_c = create_synthetic_checkerboard()

    kps_a, descs_a, _ = matcher.extract_features(img_a)
    kps_c, descs_c, _ = matcher.extract_features(img_c)

    result = matcher.match_descriptors(kps_a, descs_a, kps_c, descs_c)
    assert result["status"] in ("POOR", "WARNING")
    assert result["good_matches"] < 50


# 4. Insufficient Features Test
def test_insufficient_features():
    matcher = ImageFeatureMatcher(min_keypoints=80)
    img_a = create_synthetic_textured_image()
    img_blank = create_synthetic_blank_image()

    kps_a, descs_a, _ = matcher.extract_features(img_a)
    kps_blank, descs_blank, _ = matcher.extract_features(img_blank)

    result = matcher.match_descriptors(kps_a, descs_a, kps_blank, descs_blank)
    assert result["status"] == "INSUFFICIENT_FEATURES"
    assert result["good_matches"] == 0
    assert result["keypoints_b"] < 80


# 5. Survey-level Collection Analysis & Connectivity Graph Test
def test_survey_collection_analysis_connectivity():
    matcher = ImageFeatureMatcher(min_good_matches=20, warn_good_matches=10)
    # Create 3 matching images and 1 blank isolated image
    img1 = create_synthetic_textured_image(offset=0)
    img2 = create_synthetic_textured_image(offset=2)
    img3 = create_synthetic_textured_image(offset=4)
    img_iso = create_synthetic_blank_image()

    images_info = [
        {"id": "img-1", "filename": "masonry_01.jpg", "path": img1},
        {"id": "img-2", "filename": "masonry_02.jpg", "path": img2},
        {"id": "img-3", "filename": "masonry_03.jpg", "path": img3},
        {"id": "img-iso", "filename": "isolated_view.jpg", "path": img_iso},
    ]

    res = matcher.analyze_survey_collection(images_info)
    assert res["images_analyzed"] == 4
    assert res["pairs_analyzed"] > 0
    assert res["good_pairs"] >= 2
    # The blank image should be identified as isolated
    assert "img-iso" in res["isolated_image_ids"]
    assert res["readiness_status"] in ("READY_WITH_WARNINGS", "RECAPTURE_REQUIRED")
    assert any("isolated_view.jpg" in rec or "Isolated" in rec for rec in res["recommendations"])


# 6. Full API Endpoints Integration Test
def test_matching_api_endpoints(client):
    # Create site & survey
    site_res = client.post("/api/sites", json={"name": "Test Fort", "location": "Test Area"})
    site_id = site_res.json()["id"]

    srv_res = client.post("/api/surveys", json={"site_id": site_id, "survey_code": "MATCH-SRV-01"})
    survey_id = srv_res.json()["id"]

    # Generate 2 overlapping images and 1 blank image in memory
    def np_to_bytes(arr):
        pil_img = PILImage.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        buf.seek(0)
        return buf

    img_a_bytes = np_to_bytes(create_synthetic_textured_image(offset=0))
    img_b_bytes = np_to_bytes(create_synthetic_textured_image(offset=3))
    img_c_bytes = np_to_bytes(create_synthetic_blank_image())

    upload_res = client.post(
        f"/api/surveys/{survey_id}/images/upload",
        files=[
            ("files", ("stone_a.jpg", img_a_bytes, "image/jpeg")),
            ("files", ("stone_b.jpg", img_b_bytes, "image/jpeg")),
            ("files", ("blank_c.jpg", img_c_bytes, "image/jpeg")),
        ],
    )
    assert upload_res.status_code == 201
    uploaded = upload_res.json()["uploaded_images"]
    assert len(uploaded) == 3

    id_a = uploaded[0]["id"]
    id_b = uploaded[1]["id"]
    id_c = uploaded[2]["id"]

    # 1. Test POST /api/image-quality/match
    match_res = client.post(
        "/api/image-quality/match",
        json={"image_a_id": id_a, "image_b_id": id_b},
    )
    assert match_res.status_code == 200
    m_data = match_res.json()
    assert m_data["status"] == "GOOD"
    assert m_data["good_matches"] > 0
    assert "image_a_filename" in m_data
    assert m_data["image_a_filename"] == "stone_a.jpg"

    # 2. Test POST /api/image-quality/surveys/{survey_id}/analyze
    analyze_res = client.post(f"/api/image-quality/surveys/{survey_id}/analyze")
    assert analyze_res.status_code == 200
    ana_data = analyze_res.json()
    assert ana_data["images_analyzed"] == 3
    assert ana_data["pairs_analyzed"] == 3  # 3*(3-1)/2 = 3 pairs
    assert len(ana_data["connectivity_nodes"]) == 3
    assert len(ana_data["recommendations"]) > 0

    # 3. Test GET /api/image-quality/surveys/{survey_id}/readiness
    readiness_res = client.get(f"/api/image-quality/surveys/{survey_id}/readiness")
    assert readiness_res.status_code == 200
    r_data = readiness_res.json()
    assert r_data["survey_id"] == survey_id
    assert r_data["is_heuristic"] is True

    # 4. Test GET /api/image-quality/surveys/{survey_id}/pairs
    pairs_res = client.get(f"/api/image-quality/surveys/{survey_id}/pairs")
    assert pairs_res.status_code == 200
    pairs_list = pairs_res.json()
    assert len(pairs_list) == 3

    # Filter by GOOD status
    good_pairs_res = client.get(f"/api/image-quality/surveys/{survey_id}/pairs?status=GOOD")
    assert good_pairs_res.status_code == 200
    good_list = good_pairs_res.json()
    assert all(p["status"] == "GOOD" for p in good_list)
