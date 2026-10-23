"""
COLMAP Reconstruction Model Parser.
Parses sparse/dense SfM reconstruction models in both binary (.bin) and text (.txt) formats:
  - cameras.bin / cameras.txt
  - images.bin / images.txt
  - points3D.bin / points3D.txt

Extracts real camera poses (quaternion & world position), intrinsics, reprojection errors,
and 3D point cloud bounds without fabrication.
"""
import os
import struct
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

# COLMAP Camera Model IDs
CAMERA_MODEL_NAMES = {
    0: "SIMPLE_PINHOLE",
    1: "PINHOLE",
    2: "SIMPLE_RADIAL",
    3: "RADIAL",
    4: "OPENCV",
    5: "OPENCV_FISHEYE",
    6: "FULL_OPENCV",
    7: "FOV",
    8: "SIMPLE_RADIAL_FISHEYE",
    9: "RADIAL_FISHEYE",
    10: "THIN_PRISM_FISHEYE",
}

CAMERA_MODEL_NUM_PARAMS = {
    0: 3,   # f, cx, cy
    1: 4,   # fx, fy, cx, cy
    2: 4,   # f, cx, cy, k
    3: 5,   # f, cx, cy, k1, k2
    4: 8,   # fx, fy, cx, cy, k1, k2, p1, p2
    5: 8,
    6: 12,
    7: 5,
    8: 4,
    9: 5,
    10: 12,
}


def qvec2rotmat(qvec: np.ndarray) -> np.ndarray:
    """Converts COLMAP quaternion [qw, qx, qy, qz] to 3x3 rotation matrix."""
    qw, qx, qy, qz = qvec
    return np.array([
        [1 - 2 * qy**2 - 2 * qz**2, 2 * qx * qy - 2 * qz * qw, 2 * qx * qz + 2 * qy * qw],
        [2 * qx * qy + 2 * qz * qw, 1 - 2 * qx**2 - 2 * qz**2, 2 * qy * qz - 2 * qx * qw],
        [2 * qx * qz - 2 * qy * qw, 2 * qy * qz + 2 * qx * qw, 1 - 2 * qx**2 - 2 * qy**2],
    ], dtype=np.float64)


def rotmat2qvec(R: np.ndarray) -> np.ndarray:
    """Converts 3x3 rotation matrix to quaternion [qw, qx, qy, qz]."""
    Rxx, Ryx, Rzx = R[0, 0], R[1, 0], R[2, 0]
    Rxy, Ryy, Rzy = R[0, 1], R[1, 1], R[2, 1]
    Rxz, Ryz, Rzz = R[0, 2], R[1, 2], R[2, 2]
    K = np.array([
        [Rxx - Ryy - Rzz, 0, 0, 0],
        [Ryx + Rxy, Ryy - Rxx - Rzz, 0, 0],
        [Rzx + Rxz, Rzy + Ryz, Rzz - Rxx - Ryy, 0],
        [Ryz - Rzy, Rzx - Rxz, Rxy - Ryx, Rxx + Ryy + Rzz],
    ]) / 3.0
    vals, vecs = np.linalg.eigh(K)
    qvec = vecs[[3, 0, 1, 2], np.argmax(vals)]
    if qvec[0] < 0:
        qvec *= -1
    return qvec


def read_cameras_text(path: Path) -> Dict[int, Dict[str, Any]]:
    """Reads cameras.txt into a dictionary keyed by camera_id."""
    cameras = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            cam_id = int(parts[0])
            model = parts[1]
            width = int(parts[2])
            height = int(parts[3])
            params = [float(p) for p in parts[4:]]
            cameras[cam_id] = {
                "id": cam_id,
                "model": model,
                "width": width,
                "height": height,
                "params": params,
                "focal_length": params[0] if params else None,
            }
    return cameras


def read_cameras_binary(path: Path) -> Dict[int, Dict[str, Any]]:
    """Reads cameras.bin into a dictionary keyed by camera_id."""
    cameras = {}
    with open(path, "rb") as f:
        num_cameras = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_cameras):
            cam_id, model_id, width, height = struct.unpack("<iiQQ", f.read(24))
            model_name = CAMERA_MODEL_NAMES.get(model_id, f"MODEL_{model_id}")
            num_params = CAMERA_MODEL_NUM_PARAMS.get(model_id, 4)
            params = struct.unpack(f"<{num_params}d", f.read(8 * num_params))
            cameras[cam_id] = {
                "id": cam_id,
                "model": model_name,
                "width": width,
                "height": height,
                "params": list(params),
                "focal_length": params[0] if params else None,
            }
    return cameras


def read_images_text(path: Path) -> Dict[int, Dict[str, Any]]:
    """Reads images.txt into a dictionary keyed by image_id."""
    images = {}
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        i = 0
        while i < len(lines):
            parts = lines[i].split()
            img_id = int(parts[0])
            qw, qx, qy, qz = [float(p) for p in parts[1:5]]
            tx, ty, tz = [float(p) for p in parts[5:8]]
            cam_id = int(parts[8])
            name = parts[9]

            qvec = np.array([qw, qx, qy, qz], dtype=np.float64)
            tvec = np.array([tx, ty, tz], dtype=np.float64)
            R = qvec2rotmat(qvec)
            # Camera center in world coordinates: C = -R^T * t
            pos = -R.T @ tvec

            images[img_id] = {
                "id": img_id,
                "qvec": [qw, qx, qy, qz],
                "tvec": [tx, ty, tz],
                "camera_id": cam_id,
                "name": name,
                "position": [round(float(p), 6) for p in pos],
                "rotation": [round(float(qx), 6), round(float(qy), 6), round(float(qz), 6), round(float(qw), 6)],
                "rotmat": R.tolist(),
            }
            i += 2  # skip the 2D points line
    return images


def read_images_binary(path: Path) -> Dict[int, Dict[str, Any]]:
    """Reads images.bin into a dictionary keyed by image_id."""
    images = {}
    with open(path, "rb") as f:
        num_images = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_images):
            img_id = struct.unpack("<I", f.read(4))[0]
            qvec = struct.unpack("<4d", f.read(32))
            tvec = struct.unpack("<3d", f.read(24))
            cam_id = struct.unpack("<I", f.read(4))[0]

            # Null-terminated name
            name_chars = bytearray()
            while True:
                c = f.read(1)
                if c == b"\x00":
                    break
                name_chars.extend(c)
            name = name_chars.decode("utf-8", errors="replace")

            # Points2D
            num_points2d = struct.unpack("<Q", f.read(8))[0]
            f.seek(num_points2d * 24, os.SEEK_CUR)

            q_arr = np.array(qvec, dtype=np.float64)
            t_arr = np.array(tvec, dtype=np.float64)
            R = qvec2rotmat(q_arr)
            pos = -R.T @ t_arr

            images[img_id] = {
                "id": img_id,
                "qvec": list(qvec),
                "tvec": list(tvec),
                "camera_id": cam_id,
                "name": name,
                "position": [round(float(p), 6) for p in pos],
                "rotation": [round(float(q_arr[1]), 6), round(float(q_arr[2]), 6), round(float(q_arr[3]), 6), round(float(q_arr[0]), 6)],
                "rotmat": R.tolist(),
            }
    return images


def read_points3d_text(path: Path) -> Dict[int, Dict[str, Any]]:
    """Reads points3D.txt into points dictionary."""
    points = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            p_id = int(parts[0])
            x, y, z = [float(p) for p in parts[1:4]]
            r, g, b = [int(p) for p in parts[4:7]]
            error = float(parts[7])
            points[p_id] = {
                "xyz": [x, y, z],
                "rgb": [r, g, b],
                "error": error,
            }
    return points


def read_points3d_binary(path: Path) -> Dict[int, Dict[str, Any]]:
    """Reads points3D.bin into points dictionary."""
    points = {}
    with open(path, "rb") as f:
        num_points = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_points):
            p_id = struct.unpack("<Q", f.read(8))[0]
            xyz = struct.unpack("<3d", f.read(24))
            rgb = struct.unpack("<3B", f.read(3))
            error = struct.unpack("<d", f.read(8))[0]
            track_len = struct.unpack("<Q", f.read(8))[0]
            f.seek(track_len * 8, os.SEEK_CUR)

            points[p_id] = {
                "xyz": list(xyz),
                "rgb": list(rgb),
                "error": error,
            }
    return points


def parse_colmap_model(model_dir: Path) -> Dict[str, Any]:
    """
    Parses a COLMAP sparse model directory containing cameras, images, and points3D
    (in either binary or text format) and extracts camera poses and geometric bounds.
    """
    model_dir = Path(model_dir)
    if not model_dir.exists():
        return {}

    cameras = {}
    images = {}
    points = {}

    # 1. Cameras
    if (model_dir / "cameras.bin").exists():
        cameras = read_cameras_binary(model_dir / "cameras.bin")
    elif (model_dir / "cameras.txt").exists():
        cameras = read_cameras_text(model_dir / "cameras.txt")

    # 2. Images
    if (model_dir / "images.bin").exists():
        images = read_images_binary(model_dir / "images.bin")
    elif (model_dir / "images.txt").exists():
        images = read_images_text(model_dir / "images.txt")

    # 3. Points3D
    if (model_dir / "points3D.bin").exists():
        points = read_points3d_binary(model_dir / "points3D.bin")
    elif (model_dir / "points3D.txt").exists():
        points = read_points3d_text(model_dir / "points3D.txt")

    # Format camera poses
    camera_poses = []
    for img_id, img_data in images.items():
        cam_info = cameras.get(img_data.get("camera_id"), {})
        camera_poses.append({
            "image_id": str(img_id),
            "image_name": img_data["name"],
            "position": img_data["position"],
            "rotation": img_data["rotation"],
            "quaternion": img_data["qvec"],
            "translation": img_data["tvec"],
            "focal_length": cam_info.get("focal_length"),
            "width": cam_info.get("width"),
            "height": cam_info.get("height"),
        })

    # Reprojection error & bounding box
    errors = [p["error"] for p in points.values() if "error" in p]
    mean_error = round(float(np.mean(errors)), 4) if errors else None

    bbox = None
    if points:
        coords = np.array([p["xyz"] for p in points.values()])
        min_pt = coords.min(axis=0).tolist()
        max_pt = coords.max(axis=0).tolist()
        centroid = coords.mean(axis=0).tolist()
        dims = (coords.max(axis=0) - coords.min(axis=0)).tolist()
        bbox = {
            "min": [round(v, 4) for v in min_pt],
            "max": [round(v, 4) for v in max_pt],
            "centroid": [round(v, 4) for v in centroid],
            "dimensions": [round(v, 4) for v in dims],
        }

    return {
        "cameras": cameras,
        "images": images,
        "camera_poses": camera_poses,
        "registered_image_count": len(images),
        "sparse_point_count": len(points),
        "mean_reprojection_error": mean_error,
        "bounding_box": bbox,
    }
