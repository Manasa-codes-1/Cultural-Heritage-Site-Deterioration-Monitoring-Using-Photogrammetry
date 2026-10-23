"""
COLMAP Photogrammetry Engine.
Wraps the COLMAP CLI for Structure-from-Motion (SfM) and Multi-View Stereo (MVS).
Ensures safe subprocess execution on Windows/Linux with granular error handling,
CUDA capability detection, and fallback paths.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from app.core.config import settings
from app.photogrammetry.base import PhotogrammetryEngine
from app.photogrammetry.colmap_reader import parse_colmap_model


class ColmapEngine(PhotogrammetryEngine):
    """
    Subprocess-driven COLMAP photogrammetric reconstruction pipeline.
    Executes:
      1. Feature Extraction (SIFT)
      2. Feature Matching (Exhaustive / Sequential)
      3. Sparse Reconstruction (SfM Mapper)
      4. Undistortion (Image Undistorter)
      5. Dense Stereo (PatchMatchStereo) [Optional/CUDA-dependent]
      6. Stereo Fusion & Meshing (Poisson / Delaunay)
    """

    def __init__(self, binary_path: Optional[str] = None):
        self.binary = binary_path or getattr(settings, "COLMAP_PATH", "colmap")

    @property
    def name(self) -> str:
        return "colmap"

    def _resolve_binary_and_env(self) -> Tuple[Optional[str], Dict[str, str]]:
        env = os.environ.copy()

        # 1. System PATH or explicitly specified binary
        colmap_exe = shutil.which(self.binary)
        if not colmap_exe and os.path.exists(self.binary):
            colmap_exe = self.binary
        if colmap_exe:
            return colmap_exe, env

        default_binary = getattr(settings, "COLMAP_PATH", "colmap")
        if self.binary and self.binary not in ("colmap", default_binary):
            return None, env

        # 2. Check workspace tools/colmap installation
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        candidates = [
            project_root / "tools" / "colmap" / "COLMAP-3.9.1-windows-no-cuda",
            Path("C:/tools/colmap/COLMAP-3.9.1-windows-no-cuda"),
        ]
        for cand in candidates:
            exe = cand / "bin" / "colmap.exe"
            if exe.exists():
                env["PATH"] = str(cand / "lib") + os.pathsep + env.get("PATH", "")
                env["QT_PLUGIN_PATH"] = str(cand / "lib" / "plugins")
                return str(exe), env

        return None, env

    def check_availability(self) -> Dict[str, Any]:
        """Verify whether colmap binary is executable and detect CUDA support."""
        result = {
            "available": False,
            "version": None,
            "binary_path": None,
            "cuda_available": False,
            "details": "COLMAP executable not found in system PATH or configuration.",
        }

        colmap_exe, env = self._resolve_binary_and_env()
        if not colmap_exe:
            return result

        try:
            # Query COLMAP help/version
            proc = subprocess.run(
                [colmap_exe, "help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                check=False,
                env=env,
            )
            output = proc.stdout + proc.stderr
            result["available"] = True
            result["binary_path"] = colmap_exe

            # Parse version if present
            for line in output.splitlines():
                if "COLMAP" in line and ("version" in line.lower() or "commit" in line.lower() or "3." in line):
                    result["version"] = line.strip()
                    break
            if not result["version"]:
                result["version"] = "COLMAP 3.x"

            # Check CUDA support hint
            cuda_supported = "without CUDA" not in output.lower() and "CUDA" in output
            result["cuda_available"] = cuda_supported
            result["details"] = (
                f"COLMAP detected at {colmap_exe} (CUDA: {'Enabled' if cuda_supported else 'Disabled/CPU only'})."
            )
        except Exception as e:
            result["details"] = f"Error checking COLMAP executable: {str(e)}"

        return result

    def _run_stage(
        self,
        cmd: List[str],
        stage_name: str,
        log_file: Path,
        progress_cb: Optional[Callable[[str, int, str], None]] = None,
        progress_pct: int = 0,
    ) -> bool:
        """Helper to run a single COLMAP CLI sub-command and stream stdout/stderr."""
        if progress_cb:
            progress_cb(stage_name, progress_pct, f"Executing COLMAP {stage_name}...")

        _, env = self._resolve_binary_and_env()

        with open(log_file, "a", encoding="utf-8") as lf:
            lf.write(f"\n--- [COLMAP STAGE: {stage_name}] ---\n")
            lf.write(f"Command: {' '.join(cmd)}\n")
            lf.flush()

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env,
                )

                if proc.stdout:
                    for line in proc.stdout:
                        lf.write(line)
                        lf.flush()
                        if progress_cb and any(keyword in line for keyword in ["Processing", "Extracting", "Matching", "Registering", "Iter"]):
                            progress_cb(stage_name, progress_pct, line.strip())

                proc.wait()
                if proc.returncode != 0:
                    lf.write(f"COLMAP stage {stage_name} failed with exit code {proc.returncode}\n")
                    return False
                return True
            except Exception as e:
                lf.write(f"Exception during {stage_name}: {str(e)}\n")
                return False

    def _diagnose_mapper_failure(self, log_file: Path) -> str:
        """Inspects COLMAP log to provide actionable diagnostic feedback to the surveyor."""
        if not log_file.exists():
            return (
                "COLMAP Sparse Reconstruction failed: Unable to register camera poses. "
                "Ensure survey contains overlapping photographs with 60-80% visual overlap."
            )

        try:
            content = log_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = ""

        if "No images with matches found in the database" in content or "connected 0" in content:
            return (
                "COLMAP Reconstruction Failed: Zero matching image pairs found across survey images. "
                "Photogrammetry requires overlapping photographs (minimum 60-80% overlap between adjacent views). "
                "The uploaded images do not share sufficient visual features or were taken from unrelated viewpoints."
            )
        if "Could not register any initial image pair" in content or "No good initial image pair found" in content:
            return (
                "COLMAP Reconstruction Failed: Could not find a valid initial image pair with sufficient parallax. "
                "Photogrammetry requires camera baseline variation (photos must be taken from slightly different positions "
                "and angles around the structure, not from the exact same standing spot or zoom level)."
            )
        if "failed to create sparse model" in content or "No models created" in content:
            return (
                "COLMAP Reconstruction Failed: Structure-from-Motion could not initialize a 3D coordinate model. "
                "Ensure photos have high contrast, sharp focus (avoid motion blur), distinct surface texture, "
                "and consistent lighting across at least 5-15 overlapping views."
            )
        return (
            "COLMAP Sparse Reconstruction failed to register camera poses. "
            "Please check image overlap (minimum 60-80% overlap), lighting uniformity, and ensure photographs "
            "capture common structural features across multiple viewpoints."
        )

    def run_reconstruction(
        self,
        survey_id: str,
        image_paths: List[Path],
        workspace_dir: Path,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        dense: bool = True,
        generate_mesh: bool = True,
    ) -> Dict[str, Any]:
        """Executes full COLMAP photogrammetric pipeline."""
        start_time = time.time()
        colmap_info = self.check_availability()
        if not colmap_info["available"]:
            raise RuntimeError(f"COLMAP is not available on this system: {colmap_info['details']}")

        colmap_bin = colmap_info["binary_path"]
        use_gpu = 1 if colmap_info["cuda_available"] else 0

        # Workspace directory layout
        workspace_dir.mkdir(parents=True, exist_ok=True)
        images_dir = workspace_dir / "images"
        sparse_dir = workspace_dir / "sparse"
        dense_dir = workspace_dir / "dense"
        logs_dir = workspace_dir / "logs"

        images_dir.mkdir(parents=True, exist_ok=True)
        sparse_dir.mkdir(parents=True, exist_ok=True)
        dense_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "colmap_execution.log"
        database_path = workspace_dir / "database.db"

        # Stage 0: Link or copy images
        if progress_callback:
            progress_callback("PREPARING", 5, "Preparing image workspace...")

        for img in image_paths:
            target_link = images_dir / img.name
            if not target_link.exists():
                try:
                    os.link(str(img), str(target_link))
                except Exception:
                    shutil.copy2(str(img), str(target_link))

        # Stage 1: Feature Extraction
        cmd_extract = [
            colmap_bin,
            "feature_extractor",
            "--database_path", str(database_path),
            "--image_path", str(images_dir),
            "--ImageReader.camera_model", "SIMPLE_RADIAL",
            "--ImageReader.single_camera", "1",
            "--SiftExtraction.use_gpu", str(use_gpu),
        ]
        if not self._run_stage(cmd_extract, "FEATURE_EXTRACTION", log_file, progress_callback, 15):
            raise RuntimeError("COLMAP Feature Extraction failed. See log file.")

        # Stage 2: Feature Matching
        cmd_match = [
            colmap_bin,
            "exhaustive_matcher",
            "--database_path", str(database_path),
            "--SiftMatching.use_gpu", str(use_gpu),
        ]
        if not self._run_stage(cmd_match, "FEATURE_MATCHING", log_file, progress_callback, 35):
            raise RuntimeError("COLMAP Feature Matching failed. See log file.")

        # Stage 3: Sparse Reconstruction (SfM Mapper)
        cmd_mapper = [
            colmap_bin,
            "mapper",
            "--database_path", str(database_path),
            "--image_path", str(images_dir),
            "--output_path", str(sparse_dir),
        ]
        if not self._run_stage(cmd_mapper, "SPARSE_RECONSTRUCTION", log_file, progress_callback, 55):
            diag = self._diagnose_mapper_failure(log_file)
            raise RuntimeError(diag)

        # Sparse sub-model 0
        model_0_dir = sparse_dir / "0"
        if not model_0_dir.exists():
            # Sometimes output is directly in sparse_dir
            if (sparse_dir / "cameras.bin").exists() or (sparse_dir / "cameras.txt").exists():
                model_0_dir = sparse_dir
            else:
                diag = self._diagnose_mapper_failure(log_file)
                raise RuntimeError(diag)

        # Convert sparse model to PLY
        sparse_ply = workspace_dir / "sparse.ply"
        cmd_sparse_ply = [
            colmap_bin,
            "model_converter",
            "--input_path", str(model_0_dir),
            "--output_path", str(sparse_ply),
            "--output_type", "PLY",
        ]
        self._run_stage(cmd_sparse_ply, "CONVERT_SPARSE_PLY", log_file, progress_callback, 65)

        dense_ply_path = None
        mesh_ply_path = None

        if dense:
            # Stage 4: Undistort Images
            cmd_undistort = [
                colmap_bin,
                "image_undistorter",
                "--image_path", str(images_dir),
                "--input_path", str(model_0_dir),
                "--output_path", str(dense_dir),
                "--output_type", "COLMAP",
            ]
            undistort_ok = self._run_stage(cmd_undistort, "IMAGE_UNDISTORTION", log_file, progress_callback, 75)

            if undistort_ok and colmap_info["cuda_available"]:
                # Stage 5: PatchMatchStereo (CUDA)
                cmd_stereo = [
                    colmap_bin,
                    "patch_match_stereo",
                    "--workspace_path", str(dense_dir),
                    "--PatchMatchStereo.geom_consistency", "true",
                ]
                self._run_stage(cmd_stereo, "DENSE_STEREO", log_file, progress_callback, 85)

                # Stage 6: Stereo Fusion
                dense_fused_ply = dense_dir / "fused.ply"
                cmd_fusion = [
                    colmap_bin,
                    "stereo_fusion",
                    "--workspace_path", str(dense_dir),
                    "--output_path", str(dense_fused_ply),
                ]
                fusion_ok = self._run_stage(cmd_fusion, "STEREO_FUSION", log_file, progress_callback, 90)
                if fusion_ok and dense_fused_ply.exists():
                    dense_ply_path = str(dense_fused_ply)

                    if generate_mesh:
                        # Stage 7: Meshing (Poisson)
                        mesh_ply = dense_dir / "meshed-poisson.ply"
                        cmd_mesh = [
                            colmap_bin,
                            "poisson_mesher",
                            "--input_path", str(dense_fused_ply),
                            "--output_path", str(mesh_ply),
                        ]
                        if self._run_stage(cmd_mesh, "MESH_GENERATION", log_file, progress_callback, 95) and mesh_ply.exists():
                            mesh_ply_path = str(mesh_ply)
            elif generate_mesh and sparse_ply.exists():
                # CPU-Compatible Surface Meshing via Open3D
                if progress_callback:
                    progress_callback("MESH_GENERATION", 85, "Generating 3D surface mesh via Open3D Poisson Reconstruction (CPU Mode)...")
                try:
                    import numpy as np
                    import open3d as o3d
                    pcd = o3d.io.read_point_cloud(str(sparse_ply))
                    if len(pcd.points) >= 10:
                        pcd.estimate_normals(
                            search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30)
                        )
                        pcd.orient_normals_towards_camera_location(camera_location=np.array([0.0, 0.0, 2.0]))
                        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=7)
                        # Filter out low-density boundary noise if sufficient vertices
                        if len(mesh.vertices) > 20:
                            dens_arr = np.asarray(densities)
                            cutoff = np.quantile(dens_arr, 0.05)
                            mesh.remove_vertices_by_mask(dens_arr < cutoff)
                        mesh_ply = workspace_dir / "mesh.ply"
                        o3d.io.write_triangle_mesh(str(mesh_ply), mesh)
                        if mesh_ply.exists():
                            mesh_ply_path = str(mesh_ply)
                except Exception as ex:
                    with open(log_file, "a", encoding="utf-8") as lf:
                        lf.write(f"\n[Open3D Notice] CPU surface meshing note: {str(ex)}\n")


        # Parse metrics, camera poses, and sparse points from COLMAP model files
        total_time = round(time.time() - start_time, 2)
        log_content = ""
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()

        parsed_model = parse_colmap_model(model_0_dir)
        camera_poses = parsed_model.get("camera_poses", [])
        sparse_pts = parsed_model.get("sparse_point_count", 0)
        reproj_err = parsed_model.get("mean_reprojection_error")
        bbox = parsed_model.get("bounding_box", {})

        return {
            "engine": "colmap",
            "engine_version": colmap_info.get("version", "COLMAP"),
            "is_demo": False,
            "registered_image_count": parsed_model.get("registered_image_count", len(image_paths)),
            "sparse_point_count": sparse_pts,
            "dense_point_count": 0,
            "mesh_vertex_count": 0,
            "mesh_triangle_count": 0,
            "mean_reprojection_error": reproj_err,
            "sparse_point_cloud_path": str(sparse_ply) if sparse_ply.exists() else None,
            "dense_point_cloud_path": dense_ply_path,
            "mesh_path": mesh_ply_path,
            "workspace_path": str(workspace_dir),
            "log_path": str(log_file),
            "logs": log_content,
            "camera_poses": camera_poses,
            "bounding_box": bbox,
            "metadata": {
                "elapsed_seconds": total_time,
                "cuda_used": bool(use_gpu),
            },
        }
