"""
Damage Point Sampler for 2D Deterioration Detections.
Supports configurable sampling strategies (CENTER_ONLY, BOX_GRID, POLYGON_VERTICES, MASK_SAMPLES)
to provide representative 2D image coordinates for 3D surface projection.
"""
from typing import List, Tuple, Dict, Any, Optional
from app.models.heritage import DeteriorationDetection


class DamagePointSampler:
    """Extracts representative (u, v) pixel coordinates from a 2D deterioration detection."""

    @staticmethod
    def sample_points(
        detection: DeteriorationDetection,
        strategy: str = "CENTER_ONLY",
    ) -> List[Tuple[str, float, float]]:
        """
        Samples 2D pixel coordinates from detection bounding box, polygon, or mask.
        
        Returns:
            List of (point_type, u, v)
        """
        strategy = (strategy or "CENTER_ONLY").upper()
        bbox = detection.bounding_box or {}
        x = float(bbox.get("x", 0))
        y = float(bbox.get("y", 0))
        w = float(bbox.get("w", bbox.get("width", 0)))
        h = float(bbox.get("h", bbox.get("height", 0)))

        # Default center point
        cx = x + w / 2.0
        cy = y + h / 2.0

        if strategy == "CENTER_ONLY" or (w <= 0 and h <= 0):
            return [("center", cx, cy)]

        if strategy == "POLYGON_VERTICES":
            polygon = detection.polygon or []
            if polygon and len(polygon) >= 3:
                samples = [("center", cx, cy)]
                for idx, pt in enumerate(polygon):
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        samples.append((f"polygon_vertex_{idx+1}", float(pt[0]), float(pt[1])))
                    elif isinstance(pt, dict) and "x" in pt and "y" in pt:
                        samples.append((f"polygon_vertex_{idx+1}", float(pt["x"]), float(pt["y"])))
                return samples
            # Fallback if no polygon available
            return DamagePointSampler._sample_box_grid(x, y, w, h, cx, cy)

        if strategy == "BOX_GRID":
            return DamagePointSampler._sample_box_grid(x, y, w, h, cx, cy)

        if strategy == "MASK_SAMPLES":
            # If mask reference exists, we sample grid points inside bbox
            return DamagePointSampler._sample_box_grid(x, y, w, h, cx, cy)

        # Default fallback
        return [("center", cx, cy)]

    @staticmethod
    def _sample_box_grid(
        x: float,
        y: float,
        w: float,
        h: float,
        cx: float,
        cy: float,
    ) -> List[Tuple[str, float, float]]:
        """
        Generates 9 representative points inside the bounding box:
        - Center
        - 4 corners (inset by 10% to remain on the defect)
        - 4 edge midpoints
        """
        inset_x = w * 0.12
        inset_y = h * 0.12

        x_left = x + inset_x
        x_right = x + w - inset_x
        y_top = y + inset_y
        y_bottom = y + h - inset_y

        return [
            ("center", cx, cy),
            ("corner_top_left", x_left, y_top),
            ("corner_top_right", x_right, y_top),
            ("corner_bottom_right", x_right, y_bottom),
            ("corner_bottom_left", x_left, y_bottom),
            ("midpoint_top", cx, y_top),
            ("midpoint_right", x_right, cy),
            ("midpoint_bottom", cx, y_bottom),
            ("midpoint_left", x_left, cy),
        ]
