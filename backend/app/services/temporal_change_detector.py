"""
Temporal Change Detector.
Quantifies geometric distance fields between co-registered 3D reconstructions.
Segments points into NO_SIGNIFICANT_CHANGE and GEOMETRIC_CHANGE_CANDIDATE
based on configurable spatial deviation thresholds.
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import numpy as np

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeometricChangeCandidate:
    """Represents a localized cluster or region of detected geometric deviation."""
    def __init__(
        self,
        centroid: Tuple[float, float, float],
        mean_distance: float,
        max_distance: float,
        point_count: int,
        bounding_box: Dict[str, Any],
        status: str = "GEOMETRIC_CHANGE_CANDIDATE",
    ):
        self.centroid = centroid
        self.mean_distance = float(mean_distance)
        self.max_distance = float(max_distance)
        self.point_count = int(point_count)
        self.bounding_box = bounding_box
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "centroid": {
                "x": round(self.centroid[0], 4),
                "y": round(self.centroid[1], 4),
                "z": round(self.centroid[2], 4),
            },
            "mean_distance": round(self.mean_distance, 4),
            "max_distance": round(self.max_distance, 4),
            "point_count": self.point_count,
            "bounding_box": self.bounding_box,
            "status": self.status,
        }


class GeometricChangeReport:
    """Detailed summary of geometric distance analysis between two point clouds."""
    def __init__(
        self,
        total_points_evaluated: int,
        mean_distance: float,
        median_distance: float,
        max_distance: float,
        std_distance: float,
        unchanged_point_count: int,
        changed_point_count: int,
        change_ratio: float,
        change_threshold: float,
        scale_status: str,
        clusters: List[GeometricChangeCandidate],
    ):
        self.total_points_evaluated = total_points_evaluated
        self.mean_distance = float(mean_distance)
        self.median_distance = float(median_distance)
        self.max_distance = float(max_distance)
        self.std_distance = float(std_distance)
        self.unchanged_point_count = unchanged_point_count
        self.changed_point_count = changed_point_count
        self.change_ratio = float(change_ratio)
        self.change_threshold = float(change_threshold)
        self.scale_status = scale_status
        self.clusters = clusters

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_points_evaluated": self.total_points_evaluated,
            "mean_distance": round(self.mean_distance, 5),
            "median_distance": round(self.median_distance, 5),
            "max_distance": round(self.max_distance, 5),
            "std_distance": round(self.std_distance, 5),
            "unchanged_point_count": self.unchanged_point_count,
            "changed_point_count": self.changed_point_count,
            "change_ratio": round(self.change_ratio, 4),
            "change_threshold": self.change_threshold,
            "scale_status": self.scale_status,
            "candidate_regions_count": len(self.clusters),
            "clusters": [c.to_dict() for c in self.clusters],
        }


class TemporalChangeDetector:
    """Computes point-to-point distance residuals and identifies candidate change clusters."""

    @classmethod
    def detect_changes(
        cls,
        target_pcd: "o3d.geometry.PointCloud",  # Reference T1
        aligned_source_pcd: "o3d.geometry.PointCloud",  # Aligned T2
        change_threshold: Optional[float] = None,
        scale_status: str = "LOCAL",
        max_sample_points: int = 10000,
    ) -> GeometricChangeReport:
        """
        Computes nearest-neighbor distance from each point in aligned source (T2)
        to the reference target (T1).
        Flags points exceeding change_threshold as GEOMETRIC_CHANGE_CANDIDATE.
        """
        threshold = change_threshold if change_threshold is not None else settings.TEMPORAL_CHANGE_THRESHOLD

        if not HAS_OPEN3D or len(target_pcd.points) == 0 or len(aligned_source_pcd.points) == 0:
            return GeometricChangeReport(
                total_points_evaluated=0,
                mean_distance=0.0,
                median_distance=0.0,
                max_distance=0.0,
                std_distance=0.0,
                unchanged_point_count=0,
                changed_point_count=0,
                change_ratio=0.0,
                change_threshold=threshold,
                scale_status=scale_status,
                clusters=[],
            )

        # Work on a representative sample to avoid CPU exhaustion
        source_eval = aligned_source_pcd
        if len(aligned_source_pcd.points) > max_sample_points:
            step = len(aligned_source_pcd.points) // max_sample_points
            sub_pts = np.asarray(aligned_source_pcd.points)[::step]
            source_eval = o3d.geometry.PointCloud()
            source_eval.points = o3d.utility.Vector3dVector(sub_pts)

        # Compute point-to-point distances from source to target
        dists = np.asarray(source_eval.compute_point_cloud_distance(target_pcd))
        total_pts = len(dists)

        if total_pts == 0:
            return GeometricChangeReport(
                total_points_evaluated=0,
                mean_distance=0.0,
                median_distance=0.0,
                max_distance=0.0,
                std_distance=0.0,
                unchanged_point_count=0,
                changed_point_count=0,
                change_ratio=0.0,
                change_threshold=threshold,
                scale_status=scale_status,
                clusters=[],
            )

        mean_d = float(np.mean(dists))
        median_d = float(np.median(dists))
        max_d = float(np.max(dists))
        std_d = float(np.std(dists))

        is_changed = dists >= threshold
        changed_count = int(np.sum(is_changed))
        unchanged_count = total_pts - changed_count
        change_ratio = float(changed_count / total_pts)

        # Cluster changed points to identify candidate regions
        clusters: List[GeometricChangeCandidate] = []
        if changed_count > 0:
            changed_pts = np.asarray(source_eval.points)[is_changed]
            changed_dists = dists[is_changed]
            clusters = cls._cluster_changed_points(changed_pts, changed_dists)

        return GeometricChangeReport(
            total_points_evaluated=total_pts,
            mean_distance=mean_d,
            median_distance=median_d,
            max_distance=max_d,
            std_distance=std_d,
            unchanged_point_count=unchanged_count,
            changed_point_count=changed_count,
            change_ratio=change_ratio,
            change_threshold=threshold,
            scale_status=scale_status,
            clusters=clusters,
        )

    @classmethod
    def _cluster_changed_points(
        cls,
        points: np.ndarray,
        distances: np.ndarray,
        eps: float = 0.15,
        min_points: int = 5,
        max_clusters: int = 20,
    ) -> List[GeometricChangeCandidate]:
        """
        Groups changed points into spatial clusters using DBSCAN where available,
        or bounding-box grid partitioning.
        """
        if len(points) == 0:
            return []

        clusters: List[GeometricChangeCandidate] = []

        if HAS_OPEN3D and len(points) >= min_points:
            try:
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(points)
                labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_points, print_progress=False))
                unique_labels = set(labels)
                for label in unique_labels:
                    if label == -1:
                        continue  # Skip noise points
                    mask = (labels == label)
                    c_pts = points[mask]
                    c_dists = distances[mask]
                    centroid = tuple(np.mean(c_pts, axis=0))
                    min_b = np.min(c_pts, axis=0).tolist()
                    max_b = np.max(c_pts, axis=0).tolist()
                    clusters.append(
                        GeometricChangeCandidate(
                            centroid=centroid,
                            mean_distance=float(np.mean(c_dists)),
                            max_distance=float(np.max(c_dists)),
                            point_count=len(c_pts),
                            bounding_box={"min": min_b, "max": max_b},
                            status="GEOMETRIC_CHANGE_CANDIDATE",
                        )
                    )
                    if len(clusters) >= max_clusters:
                        break
            except Exception as ex:
                logger.warning(f"DBSCAN clustering fallback: {ex}")

        # Fallback if no DBSCAN clusters found but points exist
        if len(clusters) == 0 and len(points) > 0:
            centroid = tuple(np.mean(points, axis=0))
            min_b = np.min(points, axis=0).tolist()
            max_b = np.max(points, axis=0).tolist()
            clusters.append(
                GeometricChangeCandidate(
                    centroid=centroid,
                    mean_distance=float(np.mean(distances)),
                    max_distance=float(np.max(distances)),
                    point_count=len(points),
                    bounding_box={"min": min_b, "max": max_b},
                    status="GEOMETRIC_CHANGE_CANDIDATE",
                )
            )

        return clusters
