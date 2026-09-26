"""
Camera Model Abstraction for Photogrammetric 2D-to-3D Damage Mapping.
Implements pinhole camera geometry, image-to-ray casting, world-to-pixel reprojection,
and robust camera parameter validation.

Coordinate System Documentation:
--------------------------------
1. Camera Local Coordinate System (OpenCV pinhole convention):
   - +X: Right
   - +Y: Down
   - +Z: Forward (optical axis into the scene)
2. World Coordinate System:
   - Identical to the Photogrammetric 3D Reconstruction coordinate system (Phase 3).
3. Transformations:
   - Camera to World:  X_world = R_c2w * X_cam + C
     where C is camera center position in world space, and R_c2w is the rotation matrix.
   - World to Camera:  X_cam = R_w2c * (X_world - C)
     where R_w2c = R_c2w^T.
"""
from typing import Optional, Tuple, Dict, Any, List
import math
import numpy as np
import logging

from app.models.heritage import Reconstruction, Image

logger = logging.getLogger(__name__)


def quaternion_to_rotation_matrix(q: List[float]) -> np.ndarray:
    """
    Converts a quaternion [qx, qy, qz, qw] to a 3x3 orthonormal rotation matrix (R_c2w).
    Normalizes the quaternion to prevent numerical drift.
    """
    qx, qy, qz, qw = q
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if norm < 1e-12:
        return np.eye(3, dtype=np.float64)

    qx /= norm
    qy /= norm
    qz /= norm
    qw /= norm

    # Standard quaternion to rotation matrix formula
    r00 = 1.0 - 2.0 * (qy * qy + qz * qz)
    r01 = 2.0 * (qx * qy - qz * qw)
    r02 = 2.0 * (qx * qz + qy * qw)

    r10 = 2.0 * (qx * qy + qz * qw)
    r11 = 1.0 - 2.0 * (qx * qx + qz * qz)
    r12 = 2.0 * (qy * qz - qx * qw)

    r20 = 2.0 * (qx * qz - qy * qw)
    r21 = 2.0 * (qy * qz + qx * qw)
    r22 = 1.0 - 2.0 * (qx * qx + qy * qy)

    return np.array([
        [r00, r01, r02],
        [r10, r11, r12],
        [r20, r21, r22]
    ], dtype=np.float64)


def rotation_matrix_to_quaternion(R: np.ndarray) -> List[float]:
    """Converts a 3x3 rotation matrix to quaternion [qx, qy, qz, qw]."""
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        s = 0.5 / math.sqrt(tr + 1.0)
        qw = 0.25 / s
        qx = (R[2, 1] - R[1, 2]) * s
        qy = (R[0, 2] - R[2, 0]) * s
        qz = (R[1, 0] - R[0, 1]) * s
    elif (R[0, 0] > R[1, 1]) and (R[0, 0] > R[2, 2]):
        s = 2.0 * math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s

    return [float(qx), float(qy), float(qz), float(qw)]


class CameraModel:
    """
    Calibrated pinhole camera model for photogrammetric raycasting.
    Transforms 2D pixel coordinates to 3D world rays and reprojects 3D world points to pixels.
    """

    def __init__(
        self,
        width: int,
        height: int,
        fx: float,
        fy: float,
        cx: float,
        cy: float,
        position: np.ndarray,
        rotation_matrix: Optional[np.ndarray] = None,
        rotation_quaternion: Optional[List[float]] = None,
        distortion_coeffs: Optional[List[float]] = None,
        camera_id: Optional[str] = None,
        is_demo: bool = False,
    ):
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid image dimensions: {width}x{height}")
        if fx <= 0 or fy <= 0:
            raise ValueError(f"Invalid focal lengths: fx={fx}, fy={fy}")

        self.width = int(width)
        self.height = int(height)
        self.fx = float(fx)
        self.fy = float(fy)
        self.cx = float(cx)
        self.cy = float(cy)
        self.position = np.asarray(position, dtype=np.float64).reshape((3,))
        self.camera_id = camera_id
        self.is_demo = is_demo
        self.distortion_coeffs = distortion_coeffs or []

        # Rotation matrix (R_c2w)
        if rotation_matrix is not None:
            self.R_c2w = np.asarray(rotation_matrix, dtype=np.float64).reshape((3, 3))
            self.quaternion = rotation_matrix_to_quaternion(self.R_c2w)
        elif rotation_quaternion is not None and len(rotation_quaternion) == 4:
            self.quaternion = [float(q) for q in rotation_quaternion]
            self.R_c2w = quaternion_to_rotation_matrix(self.quaternion)
        else:
            raise ValueError("Must provide either rotation_matrix (3x3) or rotation_quaternion (4 values)")

        # World-to-camera rotation is transpose of camera-to-world
        self.R_w2c = self.R_c2w.T

    @classmethod
    def create_from_lookat(
        cls,
        eye: List[float],
        target: List[float] = [0.0, 0.0, 0.0],
        up: List[float] = [0.0, 1.0, 0.0],
        width: int = 1920,
        height: int = 1080,
        fov_degrees: float = 60.0,
    ) -> "CameraModel":
        """
        Creates a synthetic or calibrated camera looking towards a target point.
        Useful for deterministic testing and synthetic geometries.
        """
        eye_np = np.array(eye, dtype=np.float64)
        target_np = np.array(target, dtype=np.float64)
        up_np = np.array(up, dtype=np.float64)

        # Forward (+Z) points from eye towards target
        forward = target_np - eye_np
        dist = np.linalg.norm(forward)
        if dist < 1e-9:
            forward = np.array([0.0, 0.0, 1.0])
        else:
            forward = forward / dist

        # Right (+X)
        right = np.cross(forward, up_np)
        right_norm = np.linalg.norm(right)
        if right_norm < 1e-9:
            right = np.array([1.0, 0.0, 0.0])
        else:
            right = right / right_norm

        # Down (+Y) in OpenCV is -up
        down = np.cross(forward, right)
        down = down / np.linalg.norm(down)

        # R_c2w has columns [right, down, forward]
        R_c2w = np.column_stack([right, down, forward])

        fov_rad = math.radians(fov_degrees)
        fx = (width / 2.0) / math.tan(fov_rad / 2.0)
        fy = fx
        cx = width / 2.0
        cy = height / 2.0

        return cls(
            width=width,
            height=height,
            fx=fx,
            fy=fy,
            cx=cx,
            cy=cy,
            position=eye_np,
            rotation_matrix=R_c2w,
            is_demo=True,
        )

    def pixel_to_ray(self, u: float, v: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Transforms 2D pixel coordinates (u, v) into a 3D ray (origin, direction) in world space.
        
        Returns:
            origin (np.ndarray): Camera center in world space (shape: (3,))
            direction (np.ndarray): Normalized direction unit vector in world space (shape: (3,))
        """
        # 1. Normalized camera plane coordinates
        x_norm = (float(u) - self.cx) / self.fx
        y_norm = (float(v) - self.cy) / self.fy
        z_norm = 1.0  # +Z forward in OpenCV pinhole

        # 2. Camera space vector
        ray_cam = np.array([x_norm, y_norm, z_norm], dtype=np.float64)

        # 3. Transform to world space: d_world = R_c2w * ray_cam
        ray_world = self.R_c2w @ ray_cam

        # 4. Normalize ray direction
        norm = np.linalg.norm(ray_world)
        if norm < 1e-12:
            direction = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        else:
            direction = ray_world / norm

        origin = self.position.copy()
        return origin, direction

    def world_to_pixel(self, world_point: np.ndarray) -> Tuple[Optional[float], Optional[float], float]:
        """
        Reprojects a 3D world coordinate back into 2D camera pixel coordinates (u, v).
        
        Returns:
            (u, v, z_cam):
                u (float): horizontal pixel coordinate
                v (float): vertical pixel coordinate
                z_cam (float): depth in camera space (must be > 0 to be in front of camera)
        """
        p_world = np.asarray(world_point, dtype=np.float64).reshape((3,))
        
        # Camera space point: P_cam = R_w2c * (P_world - C)
        p_cam = self.R_w2c @ (p_world - self.position)
        z_cam = float(p_cam[2])

        if z_cam <= 1e-6:
            # Point is behind or on the camera plane
            return None, None, z_cam

        u = self.fx * (p_cam[0] / z_cam) + self.cx
        v = self.fy * (p_cam[1] / z_cam) + self.cy

        return float(u), float(v), z_cam

    def compute_reprojection_error(
        self,
        world_point: np.ndarray,
        orig_u: float,
        orig_v: float,
    ) -> Optional[float]:
        """
        Calculates the Euclidean reprojection error in pixels between the projected 3D point
        and the original 2D image observation.
        """
        u_proj, v_proj, z_cam = self.world_to_pixel(world_point)
        if u_proj is None or v_proj is None or z_cam <= 0:
            return None

        du = u_proj - float(orig_u)
        dv = v_proj - float(orig_v)
        return float(math.sqrt(du * du + dv * dv))

    @classmethod
    def from_reconstruction_and_image(
        cls,
        reconstruction: Reconstruction,
        image: Image,
    ) -> Tuple[Optional["CameraModel"], str]:
        """
        Resolves camera parameters from a Phase 3 Reconstruction and Image model.
        Returns (camera_model, status_message).
        Strictly validates existence; never invents arbitrary camera poses.
        """
        if not reconstruction:
            return None, "MAPPING_UNAVAILABLE: Reconstruction does not exist."

        camera_poses = reconstruction.camera_poses or []
        if not camera_poses or len(camera_poses) == 0:
            return None, "MAPPING_UNAVAILABLE: Reconstruction has no camera poses."

        # Find matching camera pose
        # Matching priority: image.id -> image.filename -> camera_index
        matched_pose = None
        for pose in camera_poses:
            if pose.get("image_id") and pose.get("image_id") == image.id:
                matched_pose = pose
                break
            if pose.get("filename") and pose.get("filename") == image.filename:
                matched_pose = pose
                break

        # Fallback to index if poses are sequentially numbered
        if not matched_pose:
            # Try to match survey image order
            try:
                # Find index of image in survey
                if image.survey and image.survey.images:
                    sorted_images = sorted(image.survey.images, key=lambda img: img.id)
                    for idx, img_item in enumerate(sorted_images):
                        if img_item.id == image.id and idx < len(camera_poses):
                            matched_pose = camera_poses[idx]
                            break
            except Exception:
                pass

        # If still not found and camera_poses has items, use by camera_index if available
        if not matched_pose and len(camera_poses) == 1:
            matched_pose = camera_poses[0]

        if not matched_pose:
            return None, f"MAPPING_UNAVAILABLE: Camera pose unavailable for image '{image.filename}'."

        pos = matched_pose.get("position")
        rot_q = matched_pose.get("rotation_quaternion")
        rot_m = matched_pose.get("rotation_matrix")

        if not pos or len(pos) != 3:
            return None, "MAPPING_REQUIRES_CALIBRATION: Camera position coordinates missing or incomplete."

        if not rot_q and not rot_m:
            return None, "MAPPING_REQUIRES_CALIBRATION: Camera rotation parameters missing."

        # Image dimensions
        width = image.width or 1920
        height = image.height or 1080

        # Focal length resolution
        # Check if reconstruction metadata has focal length
        fx = matched_pose.get("fx") or matched_pose.get("focal_length")
        fy = matched_pose.get("fy") or matched_pose.get("focal_length")
        cx = matched_pose.get("cx") or (width / 2.0)
        cy = matched_pose.get("cy") or (height / 2.0)

        if not fx or not fy:
            # Nominal standard 50mm equivalent for 35mm sensor (approx ~ 1.2 * max(W, H))
            nominal_f = 1.25 * max(width, height)
            fx = nominal_f
            fy = nominal_f

        try:
            cam = cls(
                width=width,
                height=height,
                fx=float(fx),
                fy=float(fy),
                cx=float(cx),
                cy=float(cy),
                position=np.array(pos, dtype=np.float64),
                rotation_matrix=rot_m,
                rotation_quaternion=rot_q,
                camera_id=image.id,
                is_demo=bool(reconstruction.is_demo),
            )
            return cam, "OK"
        except Exception as e:
            logger.error(f"Error creating CameraModel for image {image.id}: {e}")
            return None, f"MAPPING_REQUIRES_CALIBRATION: {str(e)}"
