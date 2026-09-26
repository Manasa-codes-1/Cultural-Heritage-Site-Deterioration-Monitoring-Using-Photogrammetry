"""
3D Surface Raycasting and Intersection Engine.
Uses Open3D RaycastingScene for precise ray-triangle mesh intersection,
with transparent fallback to point-cloud proximity approximation.

Supports CPU execution, geometry caching, and deterministic synthetic geometries for testing.
"""
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import math
import numpy as np
import logging

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

from app.models.heritage import Reconstruction
from app.core.config import settings

logger = logging.getLogger(__name__)


class SurfaceRaycaster:
    """
    Manages 3D geometric structures and performs raycasting into 3D reconstructions.
    """

    def __init__(
        self,
        mesh_path: Optional[Path] = None,
        dense_pcd_path: Optional[Path] = None,
        sparse_pcd_path: Optional[Path] = None,
        synthetic_mesh: Optional[Any] = None,
        synthetic_pcd: Optional[Any] = None,
        proximity_tolerance: float = 0.05,
    ):
        self.mesh_path = mesh_path
        self.dense_pcd_path = dense_pcd_path
        self.sparse_pcd_path = sparse_pcd_path
        self.proximity_tolerance = proximity_tolerance

        # Cached Open3D objects
        self._scene: Optional[Any] = None
        self._dense_points: Optional[np.ndarray] = None
        self._sparse_points: Optional[np.ndarray] = None
        self._has_mesh: bool = False
        self._has_dense_pcd: bool = False
        self._has_sparse_pcd: bool = False

        if synthetic_mesh is not None:
            self._init_with_open3d_mesh(synthetic_mesh)
        elif synthetic_pcd is not None:
            self._init_with_open3d_pcd(synthetic_pcd)
        else:
            self._load_geometry()

    def _init_with_open3d_mesh(self, mesh: Any):
        if not HAS_OPEN3D:
            return
        try:
            t_mesh = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
            self._scene = o3d.t.geometry.RaycastingScene()
            _ = self._scene.add_triangles(t_mesh)
            self._has_mesh = True
        except Exception as e:
            logger.error(f"Failed to initialize synthetic mesh: {e}")

    def _init_with_open3d_pcd(self, pcd: Any):
        try:
            self._dense_points = np.asarray(pcd.points, dtype=np.float64)
            self._has_dense_pcd = len(self._dense_points) > 0
        except Exception as e:
            logger.error(f"Failed to initialize synthetic PCD: {e}")

    def _load_geometry(self):
        """Loads and prepares Open3D geometry from filesystem."""
        if not HAS_OPEN3D:
            logger.warning("Open3D is not installed; surface raycasting disabled.")
            return

        # 1. Try loading mesh
        if self.mesh_path and self.mesh_path.exists():
            try:
                mesh = o3d.io.read_triangle_mesh(str(self.mesh_path))
                if len(mesh.vertices) > 0 and len(mesh.triangles) > 0:
                    t_mesh = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
                    self._scene = o3d.t.geometry.RaycastingScene()
                    _ = self._scene.add_triangles(t_mesh)
                    self._has_mesh = True
                    logger.info(f"Loaded mesh for raycasting: {len(mesh.triangles)} triangles.")
            except Exception as e:
                logger.warning(f"Could not load mesh from {self.mesh_path}: {e}")

        # 2. Try loading dense point cloud
        if self.dense_pcd_path and self.dense_pcd_path.exists():
            try:
                dense_pcd = o3d.io.read_point_cloud(str(self.dense_pcd_path))
                if len(dense_pcd.points) > 0:
                    self._dense_points = np.asarray(dense_pcd.points, dtype=np.float64)
                    self._has_dense_pcd = True
                    logger.info(f"Loaded dense point cloud: {len(self._dense_points)} points.")
            except Exception as e:
                logger.warning(f"Could not load dense point cloud from {self.dense_pcd_path}: {e}")

        # 3. Try loading sparse point cloud
        if self.sparse_pcd_path and self.sparse_pcd_path.exists():
            try:
                sparse_pcd = o3d.io.read_point_cloud(str(self.sparse_pcd_path))
                if len(sparse_pcd.points) > 0:
                    self._sparse_points = np.asarray(sparse_pcd.points, dtype=np.float64)
                    self._has_sparse_pcd = True
            except Exception as e:
                logger.warning(f"Could not load sparse point cloud from {self.sparse_pcd_path}: {e}")

    @classmethod
    def from_reconstruction(
        cls,
        reconstruction: Reconstruction,
        proximity_tolerance: float = 0.05,
    ) -> "SurfaceRaycaster":
        """Factory method resolving geometric file paths from a Reconstruction database record."""
        mesh_p = None
        dense_p = None
        sparse_p = None

        if reconstruction.mesh_path:
            p = Path(reconstruction.mesh_path)
            if not p.is_absolute():
                p = settings.BASE_DIR / p
            if p.exists():
                mesh_p = p

        if reconstruction.dense_point_cloud_path:
            p = Path(reconstruction.dense_point_cloud_path)
            if not p.is_absolute():
                p = settings.BASE_DIR / p
            if p.exists():
                dense_p = p

        if reconstruction.sparse_point_cloud_path:
            p = Path(reconstruction.sparse_point_cloud_path)
            if not p.is_absolute():
                p = settings.BASE_DIR / p
            if p.exists():
                sparse_p = p

        return cls(
            mesh_path=mesh_p,
            dense_pcd_path=dense_p,
            sparse_pcd_path=sparse_p,
            proximity_tolerance=proximity_tolerance,
        )

    @classmethod
    def create_synthetic_plane(
        cls,
        z: float = 0.0,
        x_min: float = -2.0,
        x_max: float = 2.0,
        y_min: float = -2.0,
        y_max: float = 2.0,
    ) -> "SurfaceRaycaster":
        """
        Creates a deterministic synthetic plane at Z = z for geometric verification tests.
        """
        if not HAS_OPEN3D:
            return cls()

        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector([
            [x_min, y_min, z],
            [x_max, y_min, z],
            [x_max, y_max, z],
            [x_min, y_max, z],
        ])
        mesh.triangles = o3d.utility.Vector3iVector([
            [0, 1, 2],
            [0, 2, 3],
        ])
        return cls(synthetic_mesh=mesh)

    @classmethod
    def create_synthetic_point_cloud(
        cls,
        points: List[List[float]],
        proximity_tolerance: float = 0.1,
    ) -> "SurfaceRaycaster":
        """Creates a deterministic point cloud raycaster for testing."""
        if not HAS_OPEN3D:
            return cls()

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        return cls(synthetic_pcd=pcd, proximity_tolerance=proximity_tolerance)

    def cast_ray(
        self,
        origin: np.ndarray,
        direction: np.ndarray,
    ) -> Tuple[Optional[np.ndarray], Optional[float], str, str]:
        """
        Intersects ray with 3D reconstruction geometry.
        
        Args:
            origin (np.ndarray): Ray origin [ox, oy, oz] (3,)
            direction (np.ndarray): Normalized direction [dx, dy, dz] (3,)
            
        Returns:
            (hit_point, hit_distance, surface_source, mapping_method)
            If no intersection is found: (None, None, "NONE", "NO_SURFACE_INTERSECTION")
        """
        origin = np.asarray(origin, dtype=np.float64).reshape((3,))
        direction = np.asarray(direction, dtype=np.float64).reshape((3,))

        # Normalize direction
        norm = np.linalg.norm(direction)
        if norm < 1e-9:
            return None, None, "NONE", "NO_SURFACE_INTERSECTION"
        direction = direction / norm

        # 1. Primary: Triangle Mesh Raycasting via Open3D
        if self._has_mesh and self._scene is not None:
            hit_pos, dist = self._raycast_mesh(origin, direction)
            if hit_pos is not None:
                return hit_pos, dist, "DENSE_MESH", "MESH_RAYCAST"

        # 2. Secondary: Dense Point Cloud Proximity Approximation
        if self._has_dense_pcd and self._dense_points is not None:
            hit_pos, dist = self._ray_pointcloud_proximity(origin, direction, self._dense_points)
            if hit_pos is not None:
                return hit_pos, dist, "DENSE_POINT_CLOUD", "POINT_CLOUD_APPROXIMATION"

        # 3. Tertiary: Sparse Point Cloud Proximity Approximation
        if self._has_sparse_pcd and self._sparse_points is not None:
            hit_pos, dist = self._ray_pointcloud_proximity(origin, direction, self._sparse_points)
            if hit_pos is not None:
                return hit_pos, dist, "SPARSE_POINT_CLOUD", "POINT_CLOUD_APPROXIMATION"

        return None, None, "NONE", "NO_SURFACE_INTERSECTION"

    def _raycast_mesh(
        self,
        origin: np.ndarray,
        direction: np.ndarray,
    ) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """Executes Open3D RaycastingScene query."""
        try:
            ray_tensor = o3d.core.Tensor(
                [[origin[0], origin[1], origin[2], direction[0], direction[1], direction[2]]],
                dtype=o3d.core.Dtype.Float32,
            )
            ans = self._scene.cast_rays(ray_tensor)
            t_hit = float(ans["t_hit"].numpy()[0])

            # Open3D returns inf if no intersection
            if not math.isinf(t_hit) and not math.isnan(t_hit) and t_hit > 1e-6:
                hit_point = origin + t_hit * direction
                return hit_point, t_hit
        except Exception as e:
            logger.debug(f"Raycast mesh exception: {e}")

        return None, None

    def _ray_pointcloud_proximity(
        self,
        origin: np.ndarray,
        direction: np.ndarray,
        points: np.ndarray,
    ) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """
        Approximates surface intersection on a point cloud by finding the closest
        point to the ray within proximity_tolerance.
        
        Geometric method:
        For point P:
          v = P - origin
          t = dot(v, direction)
          If t > 0:
            perp_dist = ||v - t * direction||
        """
        if len(points) == 0:
            return None, None

        # Vectors from origin to all points
        v = points - origin  # (N, 3)

        # Projection distance along ray
        t = v @ direction  # (N,)

        # Mask points in front of the ray origin
        forward_mask = t > 0.05
        if not np.any(forward_mask):
            return None, None

        forward_indices = np.where(forward_mask)[0]
        v_fwd = v[forward_indices]
        t_fwd = t[forward_indices]

        # Perpendicular vector: v - t * d
        proj = np.outer(t_fwd, direction)
        perp = v_fwd - proj
        perp_dists = np.linalg.norm(perp, axis=1)

        # Filter within proximity tolerance
        within_tolerance = perp_dists <= self.proximity_tolerance
        if not np.any(within_tolerance):
            return None, None

        valid_indices = np.where(within_tolerance)[0]
        
        # Pick the point closest to the ray
        best_local_idx = valid_indices[np.argmin(perp_dists[valid_indices])]
        best_global_idx = forward_indices[best_local_idx]

        hit_point = points[best_global_idx].copy()
        hit_dist = float(t_fwd[best_local_idx])

        return hit_point, hit_dist
