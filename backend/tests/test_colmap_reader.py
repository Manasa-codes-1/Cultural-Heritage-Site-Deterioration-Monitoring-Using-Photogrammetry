"""
Unit tests for COLMAP binary and text model parsing.
Tests parsing of cameras.txt, images.txt, points3D.txt and geometric transforms.
"""
import pytest
import numpy as np
from pathlib import Path
from app.photogrammetry.colmap_reader import (
    qvec2rotmat,
    rotmat2qvec,
    read_cameras_text,
    read_images_text,
    read_points3d_text,
    parse_colmap_model,
)

def test_quaternion_rotmat_roundtrip():
    # Test identity quaternion [1, 0, 0, 0]
    q_id = np.array([1.0, 0.0, 0.0, 0.0])
    R_id = qvec2rotmat(q_id)
    assert np.allclose(R_id, np.eye(3))
    q_rec = rotmat2qvec(R_id)
    assert np.allclose(q_rec, q_id)

    # Test 90-degree rotation around Z
    # q = [cos(45), 0, 0, sin(45)] = [0.7071068, 0, 0, 0.7071068]
    val = np.sqrt(0.5)
    q_z = np.array([val, 0.0, 0.0, val])
    R_z = qvec2rotmat(q_z)
    expected_R = np.array([
        [0.0, -1.0, 0.0],
        [1.0,  0.0, 0.0],
        [0.0,  0.0, 1.0],
    ])
    assert np.allclose(R_z, expected_R, atol=1e-5)

def test_parse_colmap_text_model(tmp_path):
    # Create mock sparse model text files
    cameras_txt = tmp_path / "cameras.txt"
    images_txt = tmp_path / "images.txt"
    points3d_txt = tmp_path / "points3D.txt"

    cameras_txt.write_text(
        "# Camera list with one line of data per camera:\n"
        "#   CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n"
        "1 PINHOLE 1920 1080 1500.0 1500.0 960.0 540.0\n"
    )

    images_txt.write_text(
        "# Image list with two lines of data per image:\n"
        "#   IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n"
        "#   POINTS2D[] as (X, Y, POINT3D_ID)\n"
        "1 1.0 0.0 0.0 0.0 0.0 0.0 -5.0 1 image_01.jpg\n"
        "100.0 200.0 1\n"
        "2 1.0 0.0 0.0 0.0 1.0 0.0 -5.0 1 image_02.jpg\n"
        "120.0 210.0 1\n"
    )

    points3d_txt.write_text(
        "# 3D point list with one line of data per point:\n"
        "#   POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]\n"
        "1 0.0 0.0 0.0 255 0 0 0.42 1 0 2 0\n"
        "2 2.0 4.0 6.0 0 255 0 0.58 1 1 2 1\n"
    )

    parsed = parse_colmap_model(tmp_path)
    assert parsed["registered_image_count"] == 2
    assert parsed["sparse_point_count"] == 2
    assert parsed["mean_reprojection_error"] == 0.50

    poses = parsed["camera_poses"]
    assert len(poses) == 2
    # image_01: C = -R^T * t = -I * [0, 0, -5] = [0, 0, 5]
    assert poses[0]["image_name"] == "image_01.jpg"
    assert poses[0]["position"] == [0.0, 0.0, 5.0]
    # image_02: C = -I * [1, 0, -5] = [-1, 0, 5]
    assert poses[1]["image_name"] == "image_02.jpg"
    assert poses[1]["position"] == [-1.0, 0.0, 5.0]

    bbox = parsed["bounding_box"]
    assert bbox is not None
    assert bbox["min"] == [0.0, 0.0, 0.0]
    assert bbox["max"] == [2.0, 4.0, 6.0]
    assert bbox["dimensions"] == [2.0, 4.0, 6.0]
