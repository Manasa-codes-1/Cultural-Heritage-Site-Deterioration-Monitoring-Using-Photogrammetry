"""
Mock Photogrammetry Engine for Development, Testing, and Demonstrations.
Generates deterministic synthetic 3D cultural heritage architectural geometries
(heritage sandstone wall/block facade with realistic mortar joints and surface relief).

RESEARCH SAFETY NOTE:
Always explicitly sets `is_demo = True` and writes clear disclaimer banners in logs.
Does NOT fabricate false real-world photogrammetry accuracy claims.
"""
import math
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from app.photogrammetry.base import PhotogrammetryEngine


class MockPhotogrammetryEngine(PhotogrammetryEngine):
    """
    Simulates the photogrammetric pipeline when COLMAP is absent.
    Generates realistic 3D point clouds (sparse & dense) and polygonal meshes
    representing a historic sandstone masonry facade.
    """

    @property
    def name(self) -> str:
        return "mock"

    def check_availability(self) -> Dict[str, Any]:
        """Mock engine is always available as a development fallback."""
        return {
            "available": True,
            "version": "Mock Heritage 3D Engine v1.0",
            "binary_path": "builtin:mock",
            "cuda_available": False,
            "details": "Built-in synthetic photogrammetry generator for CPU development and testing.",
        }

    def _generate_synthetic_point_cloud(
        self,
        num_points: int,
        is_sparse: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Generates 3D points representing a heritage stone masonry wall with mortar grooves.
        Points include coordinates [x, y, z], normals [nx, ny, nz], and RGB colors [r, g, b].
        """
        random.seed(42 if is_sparse else 1337)
        points = []

        width = 2.4  # meters
        height = 1.8  # meters
        depth = 0.35  # meters

        # Masonry stone courses
        num_courses_y = 6
        num_blocks_x = 4
        course_height = height / num_courses_y
        block_width = width / num_blocks_x

        for _ in range(num_points):
            # Pick a block and position on front face
            gx = random.uniform(-width / 2, width / 2)
            gy = random.uniform(-height / 2, height / 2)

            # Check if point is near mortar joint
            near_mortar_x = any(abs(gx - (k * block_width - width / 2)) < 0.02 for k in range(num_blocks_x + 1))
            near_mortar_y = any(abs(gy - (k * course_height - height / 2)) < 0.02 for k in range(num_courses_y + 1))

            if near_mortar_x or near_mortar_y:
                # Mortar joint: recessed slightly, lime-mortar grayish color
                gz = -0.015 + random.gauss(0, 0.003)
                r, g, b = (195, 190, 175)
                nx, ny, nz = 0.0, 0.0, 1.0
            else:
                # Sandstone block face: warm ochre/sandstone color with weathered variation
                # Slight surface curvature/erosion
                surface_undulation = 0.012 * math.sin(gx * 4.0) * math.cos(gy * 3.5)
                micro_roughness = random.gauss(0, 0.004) if not is_sparse else 0.0
                gz = surface_undulation + micro_roughness

                # Sandstone color palette
                base_tone = random.choice([
                    (218, 175, 125),  # Warm sandstone
                    (205, 160, 110),  # Weathered golden
                    (190, 145, 100),  # Iron-oxide rich
                    (225, 195, 150),  # Light buff stone
                ])
                noise = random.randint(-15, 15)
                r = max(0, min(255, base_tone[0] + noise))
                g = max(0, min(255, base_tone[1] + noise))
                b = max(0, min(255, base_tone[2] + noise))

                # Perturbed normal
                nx = random.gauss(0, 0.05)
                ny = random.gauss(0, 0.05)
                nz = 0.99
                norm = math.sqrt(nx * nx + ny * ny + nz * nz)
                nx, ny, nz = nx / norm, ny / norm, nz / norm

            points.append({
                "x": round(gx, 5),
                "y": round(gy, 5),
                "z": round(gz, 5),
                "nx": round(nx, 4),
                "ny": round(ny, 4),
                "nz": round(nz, 4),
                "r": int(r),
                "g": int(g),
                "b": int(b),
            })

        return points

    def _write_ply(self, filepath: Path, points: List[Dict[str, Any]], has_normals: bool = True):
        """Writes an ASCII PLY point cloud file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write("comment Demo synthetic cultural heritage reconstruction model\n")
            f.write(f"element vertex {len(points)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            if has_normals:
                f.write("property float nx\n")
                f.write("property float ny\n")
                f.write("property float nz\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("end_header\n")

            for p in points:
                if has_normals:
                    f.write(f"{p['x']} {p['y']} {p['z']} {p['nx']} {p['ny']} {p['nz']} {p['r']} {p['g']} {p['b']}\n")
                else:
                    f.write(f"{p['x']} {p['y']} {p['z']} {p['r']} {p['g']} {p['b']}\n")

    def _generate_synthetic_mesh(
        self,
        obj_path: Path,
        ply_path: Path,
        grid_x: int = 40,
        grid_y: int = 30,
    ) -> Dict[str, int]:
        """
        Generates a 3D polygonal surface mesh of the heritage wall.
        Writes both .obj and .ply formats for maximum 3D viewer compatibility.
        """
        width = 2.4
        height = 1.8
        dx = width / (grid_x - 1)
        dy = height / (grid_y - 1)

        vertices = []
        normals = []
        colors = []
        faces = []

        # Create vertex grid
        for iy in range(grid_y):
            for ix in range(grid_x):
                x = -width / 2 + ix * dx
                y = -height / 2 + iy * dy

                # Ashlar masonry relief and mortar grooves
                in_joint_x = any(abs(x - (k * (width / 4) - width / 2)) < 0.015 for k in range(5))
                in_joint_y = any(abs(y - (k * (height / 6) - height / 2)) < 0.015 for k in range(7))

                if in_joint_x or in_joint_y:
                    z = -0.012
                    r, g, b = (195, 190, 175)
                else:
                    z = 0.010 * math.sin(x * 3.5) * math.cos(y * 3.0)
                    r, g, b = (212, 172, 120)

                vertices.append((round(x, 4), round(y, 4), round(z, 4)))
                normals.append((0.0, 0.0, 1.0))
                colors.append((r, g, b))

        # Create triangular faces
        for iy in range(grid_y - 1):
            for ix in range(grid_x - 1):
                v1 = iy * grid_x + ix + 1
                v2 = iy * grid_x + (ix + 1) + 1
                v3 = (iy + 1) * grid_x + (ix + 1) + 1
                v4 = (iy + 1) * grid_x + ix + 1

                # Two triangles per quad (1-indexed for OBJ)
                faces.append((v1, v2, v3))
                faces.append((v1, v3, v4))

        # Write OBJ format
        with open(obj_path, "w", encoding="utf-8") as f:
            f.write("# Synthetic Cultural Heritage Wall Mesh (DEMO MODE)\n")
            for v, c in zip(vertices, colors):
                # Standard OBJ with vertex colors as v x y z r g b (0..1)
                f.write(f"v {v[0]} {v[1]} {v[2]} {c[0]/255:.3f} {c[1]/255:.3f} {c[2]/255:.3f}\n")
            for n in normals:
                f.write(f"vn {n[0]} {n[1]} {n[2]}\n")
            for tri in faces:
                f.write(f"f {tri[0]} {tri[1]} {tri[2]}\n")

        # Write PLY mesh format
        with open(ply_path, "w", encoding="utf-8") as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write("comment DEMO MODE - Synthetic Heritage Wall Surface Mesh\n")
            f.write(f"element vertex {len(vertices)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property float nx\n")
            f.write("property float ny\n")
            f.write("property float nz\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write(f"element face {len(faces)}\n")
            f.write("property list uchar int vertex_indices\n")
            f.write("end_header\n")

            for v, n, c in zip(vertices, normals, colors):
                f.write(f"{v[0]} {v[1]} {v[2]} {n[0]} {n[1]} {n[2]} {c[0]} {c[1]} {c[2]}\n")
            for tri in faces:
                # 0-indexed in PLY
                f.write(f"3 {tri[0]-1} {tri[1]-1} {tri[2]-1}\n")

        return {
            "vertex_count": len(vertices),
            "triangle_count": len(faces),
        }

    def _generate_synthetic_camera_poses(self, num_images: int) -> List[Dict[str, Any]]:
        """
        Generates realistic camera trajectory: an orbital arc in front of the wall
        with convergence toward the center of the structure.
        """
        poses = []
        if num_images <= 0:
            num_images = 4

        radius = 2.8  # meters from facade
        angle_span = math.radians(60)  # 60 degree arc coverage
        start_angle = -angle_span / 2

        for i in range(num_images):
            t = i / max(1, num_images - 1)
            angle = start_angle + t * angle_span

            # Camera positions along arc
            cam_x = radius * math.sin(angle)
            cam_y = 0.2 * math.sin(t * math.pi)  # slight height variation
            cam_z = radius * math.cos(angle)

            # Rotation looking towards (0, 0, 0)
            # In OpenCV pinhole convention (+Z forward), looking towards -Z requires yaw = pi - angle
            yaw = math.pi - angle
            qx = 0.0
            qy = math.sin(yaw / 2)
            qz = 0.0
            qw = math.cos(yaw / 2)

            poses.append({
                "camera_index": i + 1,
                "position": [round(cam_x, 4), round(cam_y, 4), round(cam_z, 4)],
                "rotation_quaternion": [round(qx, 4), round(qy, 4), round(qz, 4), round(qw, 4)],
                "reprojection_error": round(0.45 + (i % 3) * 0.12, 3),
            })

        return poses

    def run_reconstruction(
        self,
        survey_id: str,
        image_paths: List[Path],
        workspace_dir: Path,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        dense: bool = True,
        generate_mesh: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes mock reconstruction, generating structured synthetic heritage files.
        """
        start_time = time.time()
        workspace_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = workspace_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "reconstruction.log"

        log_lines = [
            "================================================================================",
            "[RESEARCH SAFETY NOTICE: DEMO / SYNTHETIC RECONSTRUCTION MODE]",
            "COLMAP photogrammetry executable was not detected on system PATH or MOCK was requested.",
            "Generating procedural 3D geometric heritage asset with verified coordinate bounds.",
            "All output metrics are explicitly marked as is_demo = True.",
            "DO NOT use these models for certified structural or legal conservation claims.",
            "================================================================================",
            f"Survey ID: {survey_id}",
            f"Input Image Count: {len(image_paths)}",
            f"Target Directory: {workspace_dir}",
            "",
        ]

        def _log(msg: str):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{timestamp}] {msg}"
            log_lines.append(entry)

        # Stage 1: Preparation
        if progress_callback:
            progress_callback("PREPARING", 10, "Validating input imagery workspace...")
        _log(f"Stage 1/5: Loaded {len(image_paths)} survey images into photogrammetric workspace.")
        time.sleep(0.05)

        # Stage 2: Feature Extraction
        if progress_callback:
            progress_callback("FEATURE_EXTRACTION", 25, "Simulating keypoint feature extraction...")
        _log("Stage 2/5: Feature extraction complete (simulated SIFT/ORB keypoints).")
        time.sleep(0.05)

        # Stage 3: Feature Matching & Sparse SfM
        if progress_callback:
            progress_callback("FEATURE_MATCHING", 45, "Running pairwise feature matching...")
        _log("Stage 3/5: Geometric verification and bundle adjustment completed.")
        time.sleep(0.05)

        # Generate Sparse Point Cloud
        if progress_callback:
            progress_callback("SPARSE_RECONSTRUCTION", 60, "Generating sparse tie point cloud...")
        sparse_points = self._generate_synthetic_point_cloud(num_points=1200, is_sparse=True)
        sparse_ply_path = workspace_dir / "sparse.ply"
        self._write_ply(sparse_ply_path, sparse_points, has_normals=False)
        _log(f"Generated sparse tie point cloud: {len(sparse_points)} points saved to {sparse_ply_path.name}")

        # Stage 4: Dense MVS Reconstruction
        dense_ply_path = None
        dense_points = []
        if dense:
            if progress_callback:
                progress_callback("DENSE_RECONSTRUCTION", 80, "Computing dense multi-view stereo depth maps...")
            dense_points = self._generate_synthetic_point_cloud(num_points=16000, is_sparse=False)
            dense_ply = workspace_dir / "dense.ply"
            self._write_ply(dense_ply, dense_points, has_normals=True)
            dense_ply_path = dense_ply
            _log(f"Generated dense point cloud: {len(dense_points)} points saved to {dense_ply.name}")

        # Stage 5: Mesh Generation
        mesh_path = None
        mesh_stats = {"vertex_count": 0, "triangle_count": 0}
        if generate_mesh:
            if progress_callback:
                progress_callback("MESH_GENERATION", 92, "Reconstructing surface mesh geometry...")
            obj_path = workspace_dir / "mesh.obj"
            ply_mesh_path = workspace_dir / "mesh.ply"
            mesh_stats = self._generate_synthetic_mesh(obj_path, ply_mesh_path, grid_x=45, grid_y=35)
            mesh_path = ply_mesh_path
            _log(f"Generated 3D mesh: {mesh_stats['vertex_count']} vertices, {mesh_stats['triangle_count']} faces saved to {ply_mesh_path.name}")

        # Camera Poses
        camera_poses = self._generate_synthetic_camera_poses(len(image_paths))
        for i, img_p in enumerate(image_paths):
            if i < len(camera_poses):
                camera_poses[i]["filename"] = Path(img_p).name
        _log(f"Estimated camera exterior orientations: {len(camera_poses)} camera positions.")

        # Compute Bounding Box
        all_points = dense_points if dense_points else sparse_points
        xs = [p["x"] for p in all_points]
        ys = [p["y"] for p in all_points]
        zs = [p["z"] for p in all_points]
        min_b = [min(xs), min(ys), min(zs)]
        max_b = [max(xs), max(ys), max(zs)]
        centroid = [(min_b[i] + max_b[i]) / 2.0 for i in range(3)]
        dimensions = [round(max_b[i] - min_b[i], 4) for i in range(3)]

        bounding_box = {
            "min": [round(c, 4) for c in min_b],
            "max": [round(c, 4) for c in max_b],
            "centroid": [round(c, 4) for c in centroid],
            "dimensions": dimensions,
        }

        # Write log file
        _log("Photogrammetric reconstruction workflow finished successfully.")
        full_logs = "\n".join(log_lines)
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(full_logs)

        if progress_callback:
            progress_callback("COMPLETED", 100, "3D Reconstruction completed successfully.")

        elapsed = round(time.time() - start_time, 2)

        return {
            "engine": "mock",
            "engine_version": "Mock Heritage 3D Engine v1.0",
            "is_demo": True,
            "registered_image_count": len(image_paths),
            "sparse_point_count": len(sparse_points),
            "dense_point_count": len(dense_points),
            "mesh_vertex_count": mesh_stats["vertex_count"],
            "mesh_triangle_count": mesh_stats["triangle_count"],
            "sparse_point_cloud_path": str(sparse_ply_path),
            "dense_point_cloud_path": str(dense_ply_path) if dense_ply_path else None,
            "mesh_path": str(mesh_path) if mesh_path else None,
            "workspace_path": str(workspace_dir),
            "log_path": str(log_file),
            "logs": full_logs,
            "camera_poses": camera_poses,
            "bounding_box": bounding_box,
            "mean_reprojection_error": 0.58,  # Typical nominal SfM reprojection error in pixels
            "metadata": {
                "elapsed_seconds": elapsed,
                "dense_stereo_enabled": dense,
                "mesh_generated": generate_mesh,
                "generator_type": "procedural_ashlar_masonry_v1",
            },
        }
