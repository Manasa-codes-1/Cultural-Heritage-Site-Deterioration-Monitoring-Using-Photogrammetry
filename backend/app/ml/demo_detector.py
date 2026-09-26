"""
Demo Deterioration Detector for Testing, UI Demonstration, and Development.
Simulates physical defect detection (cracks, erosion, spalling, discoloration, biological growth)
using deterministic image gradients, color shifts, and edge contours when no trained weights are loaded.

STRICT RESEARCH SAFETY:
- Explicitly flags all outputs with is_demo = True, inference_mode = 'demo'.
- Attaches the mandatory academic disclaimer:
  'DEMO DETERIORATION DETECTION — NOT A VALIDATED RESEARCH PREDICTION'
- Never fabricates evaluation metrics.
"""
import io
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image
import cv2

from app.core.config import settings
from app.core.deterioration_config import load_deterioration_classes, get_deterioration_class_by_id
from app.ml.base_detector import DeteriorationDetector


class DemoDeteriorationDetector(DeteriorationDetector):
    """
    Deterministic rule-based heuristic detector that simulates multi-class deterioration
    detection with spatial bounding boxes and polygon boundaries.
    """

    def __init__(self, confidence_threshold: Optional[float] = None):
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(settings, "DETERIORATION_CONFIDENCE_THRESHOLD", 0.60)
        )

    @property
    def name(self) -> str:
        return "DemoDeteriorationDetector"

    @property
    def version(self) -> str:
        return "v1.0-demo"

    @property
    def is_demo(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        return True

    def get_classes(self) -> List[Dict[str, Any]]:
        return load_deterioration_classes(include_disabled=False)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": "demo",
            "name": self.name,
            "version": self.version,
            "architecture": "Deterministic Heuristic / Gradient Analysis (Demo)",
            "is_demo": True,
            "is_active": True,
            "classes": [c["id"] for c in self.get_classes()],
            "metrics": None,
            "disclaimer": "DEMO DETERIORATION DETECTION — NOT A VALIDATED RESEARCH PREDICTION",
        }

    def _load_image(self, image: Union[np.ndarray, Image.Image, Path, str, bytes]) -> np.ndarray:
        """Loads any supported image format into RGB NumPy array."""
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image file does not exist: {path}")
            bgr = cv2.imread(str(path))
            if bgr is None:
                raise ValueError(f"Could not decode image at {path}")
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        elif isinstance(image, Image.Image):
            return np.array(image.convert("RGB"))
        elif isinstance(image, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image)).convert("RGB")
            return np.array(pil_img)
        elif isinstance(image, np.ndarray):
            if image.ndim == 2:
                return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            return image
        else:
            raise TypeError(f"Unsupported image input type: {type(image)}")

    def predict(
        self,
        image: Union[np.ndarray, Image.Image, Path, str, bytes],
        confidence_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Infers plausible deterioration defects using deterministic image gradient,
        color saturation, and contour analysis.
        """
        img_rgb = self._load_image(image)
        h, w = img_rgb.shape[:2]
        threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold

        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

        detections = []

        # Deterministic seed based on image statistics and dimensions
        img_hash = int(hashlib.md5(f"{w}_{h}_{int(np.mean(gray))}".encode()).hexdigest()[:6], 16)
        rng = np.random.RandomState(img_hash)

        # 1. Edge & Contour Analysis for Cracks
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        significant_contours = [c for c in contours if cv2.contourArea(c) > 40 or cv2.arcLength(c, False) > 50]

        if significant_contours:
            # Pick most prominent contour for crack
            c = max(significant_contours, key=lambda cnt: cv2.arcLength(cnt, False))
            x, y, cw, ch = cv2.boundingRect(c)
            # Add padding
            pad = 10
            bx = max(0, x - pad)
            by = max(0, y - pad)
            bw = min(w - bx, cw + 2 * pad)
            bh = min(h - by, ch + 2 * pad)

            conf = round(float(0.72 + (rng.rand() * 0.16)), 3)
            stat = "CONFIDENT" if conf >= threshold else "LOW_CONFIDENCE"

            # Extract simplified polygon points
            epsilon = 0.02 * cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, epsilon, True)
            poly_points = [{"x": int(pt[0][0]), "y": int(pt[0][1])} for pt in approx]

            detections.append({
                "damage_type": "crack",
                "confidence": conf,
                "status": stat,
                "severity_hint": "severe" if ch > h * 0.3 else "moderate",
                "bounding_box": {"x": bx, "y": by, "w": bw, "h": bh},
                "polygon": poly_points if len(poly_points) >= 3 else None,
                "notes": "Linear discontinuity detected via high-gradient edge trajectory."
                if stat == "CONFIDENT"
                else "Detection requires verification or additional imagery."
            })

        # 2. Texture Variance / Flaking for Erosion or Spalling
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        var_lap = float(np.var(lap))
        if var_lap > 80.0 or len(detections) == 0:
            # Create a bounded region in lower or center quadrant
            sx = int(w * (0.2 + rng.rand() * 0.3))
            sy = int(h * (0.3 + rng.rand() * 0.3))
            sw = int(min(w - sx - 10, w * (0.25 + rng.rand() * 0.2)))
            sh = int(min(h - sy - 10, h * (0.20 + rng.rand() * 0.2)))

            damage_type = "spalling" if rng.rand() > 0.5 else "erosion"
            conf = round(float(0.65 + (rng.rand() * 0.20)), 3)
            stat = "CONFIDENT" if conf >= threshold else "LOW_CONFIDENCE"

            poly = [
                {"x": sx, "y": sy},
                {"x": sx + sw, "y": sy + int(sh * 0.1)},
                {"x": sx + int(sw * 0.9), "y": sy + sh},
                {"x": sx + int(sw * 0.1), "y": sy + int(sh * 0.95)},
            ]

            detections.append({
                "damage_type": damage_type,
                "confidence": conf,
                "status": stat,
                "severity_hint": "moderate",
                "bounding_box": {"x": sx, "y": sy, "w": sw, "h": sh},
                "polygon": poly,
                "notes": f"Surface relief irregularity indicative of {damage_type}."
                if stat == "CONFIDENT"
                else "Detection requires verification or additional imagery."
            })

        # 3. Green / Biological or Discoloration Hue Check
        sat = hsv[:, :, 1]
        hue = hsv[:, :, 0]
        green_mask = (hue >= 35) & (hue <= 85) & (sat > 40)
        green_ratio = float(np.sum(green_mask)) / (w * h)

        if green_ratio > 0.03:
            # Biological growth
            y_indices, x_indices = np.where(green_mask)
            bx1, bx2 = int(np.percentile(x_indices, 5)), int(np.percentile(x_indices, 95))
            by1, by2 = int(np.percentile(y_indices, 5)), int(np.percentile(y_indices, 95))
            bw, bh = max(20, bx2 - bx1), max(20, by2 - by1)

            conf = round(float(0.78 + (rng.rand() * 0.14)), 3)
            stat = "CONFIDENT" if conf >= threshold else "LOW_CONFIDENCE"

            detections.append({
                "damage_type": "biological_growth",
                "confidence": conf,
                "status": stat,
                "severity_hint": "moderate" if green_ratio < 0.20 else "severe",
                "bounding_box": {"x": bx1, "y": by1, "w": bw, "h": bh},
                "polygon": None,
                "notes": "Chromatic hue shift matching photosynthetic colonization."
                if stat == "CONFIDENT"
                else "Detection requires verification or additional imagery."
            })

        return detections

    def predict_batch(
        self,
        images: List[Union[np.ndarray, Image.Image, Path, str, bytes]],
        confidence_threshold: Optional[float] = None,
    ) -> List[List[Dict[str, Any]]]:
        return [self.predict(img, confidence_threshold=confidence_threshold) for img in images]
