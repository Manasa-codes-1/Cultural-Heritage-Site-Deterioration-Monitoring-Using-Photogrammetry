"""
Temporal Alignment Service using Open3D.
Provides multi-temporal reconstruction alignment using initial centroid alignment,
point-to-point ICP, and point-to-plane ICP refinement.
Computes registration quality metrics: fitness (inlier ratio) and inlier RMSE.
"""
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import logging
import numpy as np

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class AlignmentResult:
    """Encapsulates alignment transformation matrix and registration metrics."""
    def __init__(
        self,
        transformation_matrix: List[List[float]],
        fitness: float,
        rmse: float,
        correspondence_count: int,
        alignment_status: str,
        method: str,
        message: str = "",
    ):
        self.transformation_matrix = transformation_matrix
        self.fitness = float(fitness)
        self.rmse = float(rmse)
        self.correspondence_count = int(correspondence_count)
        self.alignment_status = alignment_status  # ALIGNED, ALIGNMENT_REQUIRES_REVIEW, FAILED
        self.method = method
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transformation_matrix": self.transformation_matrix,
            "fitness": round(self.fitness, 4),
            "rmse": round(self.rmse, 6),
            "correspondence_count": self.correspondence_count,
            "alignment_status": self.alignment_status,
            "method": self.method,
            "message": self.message,
        }


class TemporalAlignmentService:
    """Manages geometric registration between baseline and comparison reconstructions."""

    @staticmethod
    def is_available() -> bool:
        return HAS_OPEN3D

    @staticmethod
    def load_geometry_as_pointcloud(
        mesh_path: Optional[str] = None,
        point_cloud_path: Optional[str] = None,
        voxel_size: Optional[float] = None,
    ) -> Optional["o3d.geometry.PointCloud"]:
        """
        Loads a mesh or point cloud from disk into an Open3D PointCloud object.
        Applies voxel downsampling if requested.
        """
        if not HAS_OPEN3D:
            logger.warning("Open3D is not installed; geometry loading unavailable.")
            return None

        pcd: Optional[o3d.geometry.PointCloud] = None

        # Priority 1: Dense or sparse point cloud
        if point_cloud_path and Path(point_cloud_path).exists():
            try:
                pcd = o3d.io.read_point_cloud(str(point_cloud_path))
                if len(pcd.points) == 0:
                    pcd = None
            except Exception as ex:
                logger.warning(f"Failed to read point cloud at {point_cloud_path}: {ex}")

        # Priority 2: Extract vertices / sampled points from mesh if point cloud absent
        if pcd is None and mesh_path and Path(mesh_path).exists():
            try:
                mesh = o3d.io.read_triangle_mesh(str(mesh_path))
                if len(mesh.vertices) > 0:
                    pcd = o3d.geometry.PointCloud()
                    pcd.points = mesh.vertices
                    if mesh.has_vertex_normals():
                        pcd.normals = mesh.vertex_normals
                    if mesh.has_vertex_colors():
                        pcd.colors = mesh.vertex_colors
            except Exception as ex:
                logger.warning(f"Failed to read mesh at {mesh_path}: {ex}")

        if pcd is None or len(pcd.points) == 0:
            return None

        if voxel_size and voxel_size > 0.0 and len(pcd.points) > 500:
            try:
                pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
            except Exception as ex:
                logger.warning(f"Voxel downsampling error: {ex}")

        return pcd

    @classmethod
    def align_point_clouds(
        cls,
        target_pcd: "o3d.geometry.PointCloud",  # Reference baseline T1
        source_pcd: "o3d.geometry.PointCloud",  # Comparison source T2 (to be moved onto T1)
        method: str = "ICP_POINT_TO_POINT",
        max_correspondence_distance: Optional[float] = None,
        max_iterations: Optional[int] = None,
        voxel_size: Optional[float] = None,
    ) -> AlignmentResult:
        """
        Performs 3D registration aligning source (T2) to target (T1).
        Methods:
          - IDENTITY: No registration, identity transform
          - CENTROID_INIT: Center-to-center translation initialization
          - ICP_POINT_TO_POINT: Centroid init followed by point-to-point ICP refinement
          - ICP_POINT_TO_PLANE: Centroid init followed by point-to-plane ICP refinement
        """
        if not HAS_OPEN3D:
            return AlignmentResult(
                transformation_matrix=np.eye(4).tolist(),
                fitness=0.0,
                rmse=999.0,
                correspondence_count=0,
                alignment_status="FAILED",
                method=method,
                message="Open3D is not available on the runtime environment.",
            )

        if len(target_pcd.points) == 0 or len(source_pcd.points) == 0:
            return AlignmentResult(
                transformation_matrix=np.eye(4).tolist(),
                fitness=0.0,
                rmse=999.0,
                correspondence_count=0,
                alignment_status="FAILED",
                method=method,
                message="One or both point clouds contain 0 points.",
            )

        dist_threshold = max_correspondence_distance or settings.ICP_MAX_CORRESPONDENCE_DISTANCE
        max_iter = max_iterations or settings.ICP_MAX_ITERATIONS

        # Downsample for faster registration if requested
        t_pcd = target_pcd
        s_pcd = source_pcd
        if voxel_size and voxel_size > 0.0:
            t_down = target_pcd.voxel_down_sample(voxel_size)
            s_down = source_pcd.voxel_down_sample(voxel_size)
            if len(t_down.points) > 10 and len(s_down.points) > 10:
                t_pcd = t_down
                s_pcd = s_down

        # 1. Initial Transformation (Centroid-based)
        init_transform = np.eye(4)
        if method in ["CENTROID_INIT", "ICP_POINT_TO_POINT", "ICP_POINT_TO_PLANE"]:
            c_target = np.asarray(t_pcd.get_center())
            c_source = np.asarray(s_pcd.get_center())
            init_transform[:3, 3] = c_target - c_source

        if method == "IDENTITY":
            init_transform = np.eye(4)

        if method in ["IDENTITY", "CENTROID_INIT"]:
            # Evaluate fitness of initial transform
            eval_result = o3d.pipelines.registration.evaluate_registration(
                s_pcd, t_pcd, dist_threshold, init_transform
            )
            fitness = float(eval_result.fitness)
            rmse = float(eval_result.inlier_rmse)
            corr_count = len(eval_result.correspondence_set)
            status = "ALIGNED" if fitness >= settings.ICP_FITNESS_MIN_ACCEPTABLE else "ALIGNMENT_REQUIRES_REVIEW"
            return AlignmentResult(
                transformation_matrix=init_transform.tolist(),
                fitness=fitness,
                rmse=rmse,
                correspondence_count=corr_count,
                alignment_status=status,
                method=method,
                message=f"Direct evaluation with method '{method}'. Fitness={fitness:.3f}, RMSE={rmse:.5f}.",
            )

        # 2. ICP Refinement
        criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
            max_iteration=max_iter,
            relative_fitness=settings.ICP_RELATIVE_FITNESS,
            relative_rmse=settings.ICP_RELATIVE_RMSE,
        )

        try:
            if method == "ICP_POINT_TO_PLANE":
                # Ensure normals exist
                if not t_pcd.has_normals():
                    t_pcd.estimate_normals(
                        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=dist_threshold * 2, max_nn=30)
                    )
                if not s_pcd.has_normals():
                    s_pcd.estimate_normals(
                        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=dist_threshold * 2, max_nn=30)
                    )

                reg_result = o3d.pipelines.registration.registration_icp(
                    s_pcd,
                    t_pcd,
                    dist_threshold,
                    init_transform,
                    o3d.pipelines.registration.TransformationEstimationPointToPlane(),
                    criteria,
                )
            else:
                # Default: Point-to-Point ICP
                reg_result = o3d.pipelines.registration.registration_icp(
                    s_pcd,
                    t_pcd,
                    dist_threshold,
                    init_transform,
                    o3d.pipelines.registration.TransformationEstimationPointToPoint(),
                    criteria,
                )

            fitness = float(reg_result.fitness)
            rmse = float(reg_result.inlier_rmse)
            corr_count = len(reg_result.correspondence_set)
            trans = reg_result.transformation.tolist()

            if fitness >= settings.ICP_FITNESS_MIN_ACCEPTABLE:
                align_status = "ALIGNED"
                msg = f"ICP convergence succeeded. Inlier fitness={fitness:.4f}, inlier RMSE={rmse:.6f}."
            else:
                align_status = "ALIGNMENT_REQUIRES_REVIEW"
                msg = (
                    f"ICP registration quality below acceptable threshold ({fitness:.3f} < "
                    f"{settings.ICP_FITNESS_MIN_ACCEPTABLE:.2f}). Manual review or additional visual features required."
                )

            return AlignmentResult(
                transformation_matrix=trans,
                fitness=fitness,
                rmse=rmse,
                correspondence_count=corr_count,
                alignment_status=align_status,
                method=method,
                message=msg,
            )

        except Exception as e:
            logger.exception("Error executing Open3D ICP registration.")
            return AlignmentResult(
                transformation_matrix=init_transform.tolist(),
                fitness=0.0,
                rmse=999.0,
                correspondence_count=0,
                alignment_status="FAILED",
                method=method,
                message=f"ICP registration execution error: {str(e)}",
            )

    @classmethod
    def transform_point_cloud(
        cls,
        pcd: "o3d.geometry.PointCloud",
        transformation_matrix: List[List[float]],
    ) -> "o3d.geometry.PointCloud":
        """Applies a 4x4 rigid transformation to a point cloud."""
        if not HAS_OPEN3D:
            return pcd
        trans = np.array(transformation_matrix, dtype=np.float64)
        transformed = o3d.geometry.PointCloud(pcd)
        transformed.transform(trans)
        return transformed

    @classmethod
    def transform_3d_point(
        cls,
        point: Tuple[float, float, float],
        transformation_matrix: List[List[float]],
    ) -> Tuple[float, float, float]:
        """Transforms a single 3D point (x, y, z) into the baseline reference frame."""
        x, y, z = point
        vec = np.array([x, y, z, 1.0], dtype=np.float64)
        trans = np.array(transformation_matrix, dtype=np.float64)
        transformed = trans @ vec
        return (float(transformed[0]), float(transformed[1]), float(transformed[2]))

    # Synthetic Test Helpers
    @staticmethod
    def create_synthetic_plane(
        z: float = 5.0,
        num_points_per_axis: int = 15,
        bounds: Tuple[float, float] = (-1.0, 1.0),
    ) -> "o3d.geometry.PointCloud":
        """Generates a planar grid of 3D points for deterministic mathematical testing."""
        if not HAS_OPEN3D:
            raise RuntimeError("Open3D required for synthetic test geometry.")
        xs = np.linspace(bounds[0], bounds[1], num_points_per_axis)
        ys = np.linspace(bounds[0], bounds[1], num_points_per_axis)
        grid_x, grid_y = np.meshgrid(xs, ys)
        pts = np.vstack([grid_x.ravel(), grid_y.ravel(), np.full(grid_x.size, z)]).T

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pts)
        normals = np.zeros_like(pts)
        normals[:, 2] = -1.0  # Facing camera
        pcd.normals = o3d.utility.Vector3dVector(normals)
        return pcd
