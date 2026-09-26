"""
Demo Material Classifier for Testing, UI Demonstration, and Development.
Simulates material identification using deterministic image chromatic properties
when no trained PyTorch model weights are available.

RESEARCH SAFETY:
Explicitly tags all outputs with is_demo = True, inference_mode = 'demo',
and includes prominent academic disclaimers.
Does NOT fabricate model accuracy or claim scientific validation.
"""
import io
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image
import cv2


from app.core.config import settings
from app.core.material_config import load_material_classes, get_material_class_by_id
from app.ml.base import MaterialClassifier


class DemoMaterialClassifier(MaterialClassifier):
    """
    Rule-based mock classifier that maps image color statistics to heritage materials
    with explicit demo labeling and low-confidence handling.
    """

    def __init__(self, confidence_threshold: Optional[float] = None):
        self._confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(settings, "CONFIDENCE_THRESHOLD", 0.60)
        )

    @property
    def name(self) -> str:
        return "DemoMaterialClassifier"

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
        return load_material_classes(include_disabled=False)

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": "demo-v1",
            "name": self.name,
            "architecture": "Heuristic Chromatic Demo Engine",
            "version": self.version,
            "is_demo": True,
            "is_active": True,
            "dataset_identifier": "None (Synthetic Demo)",
            "training_date": None,
            "classes": [c["id"] for c in self.get_classes()],
            "metrics": None,  # Strictly None - no fake accuracy metrics
            "notes": "Demonstration classifier intended for UI and API validation without trained weights.",
        }

    def _extract_crop(
        self,
        img: np.ndarray,
        region: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """Crops image if a valid bounding box region is specified."""
        if not region:
            return img

        h, w = img.shape[:2]
        rx = max(0, min(w - 1, int(region.get("x", 0))))
        ry = max(0, min(h - 1, int(region.get("y", 0))))
        rw = max(1, min(w - rx, int(region.get("w", w))))
        rh = max(1, min(h - ry, int(region.get("h", h))))

        crop = img[ry : ry + rh, rx : rx + rw]
        if crop.size == 0:
            return img
        return crop

    def predict(
        self,
        image: Union[np.ndarray, Image.Image, Path, str],
        region: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Infers probable substrate class based on chromatic distribution
        and texture variance with calibrated demo confidence.
        """
        # Load image into RGB NumPy array
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image file does not exist: {path}")
            bgr = cv2.imread(str(path))
            if bgr is None:
                raise ValueError(f"Could not decode image at {path}")
            img_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        elif isinstance(image, Image.Image):
            img_rgb = np.array(image.convert("RGB"))
        elif isinstance(image, (bytes, bytearray)):
            img_pil = Image.open(io.BytesIO(image)).convert("RGB")
            img_rgb = np.array(img_pil)
        elif isinstance(image, np.ndarray):
            if image.ndim == 2:
                img_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                img_rgb = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            else:
                img_rgb = image
        else:
            raise TypeError(f"Unsupported image input type: {type(image)}")

        # Apply region crop
        target = self._extract_crop(img_rgb, region)

        # Compute mean RGB and standard deviation
        mean_r = float(np.mean(target[:, :, 0]))
        mean_g = float(np.mean(target[:, :, 1]))
        mean_b = float(np.mean(target[:, :, 2]))
        gray = cv2.cvtColor(target, cv2.COLOR_RGB2GRAY)
        std_dev = float(np.std(gray))

        # Chromatic heuristic scores for default classes
        raw_scores: Dict[str, float] = {
            "sandstone": 0.20,
            "granite": 0.20,
            "brick": 0.20,
            "lime_mortar": 0.20,
            "other": 0.20,
        }

        # Warm yellowish/ochre: R > G > B
        if mean_r > 130 and mean_g > 100 and (mean_r - mean_b) > 25:
            raw_scores["sandstone"] += 0.45
            raw_scores["brick"] += 0.15

        # Strong terracotta / red tone: R significantly higher than G and B
        if mean_r > 140 and (mean_r - mean_g) > 30 and (mean_r - mean_b) > 35:
            raw_scores["brick"] += 0.55
            raw_scores["sandstone"] += 0.10

        # Pale gray / off-white: low saturation, high brightness
        if abs(mean_r - mean_g) < 15 and abs(mean_g - mean_b) < 15 and mean_r > 165:
            raw_scores["lime_mortar"] += 0.50

        # Speckled / granular texture with balanced color: granite
        if std_dev > 35 and abs(mean_r - mean_b) < 30:
            raw_scores["granite"] += 0.40

        # Check configured active classes
        configured_classes = [c["id"] for c in self.get_classes()]
        filtered_scores = {k: v for k, v in raw_scores.items() if k in configured_classes}
        if not filtered_scores:
            filtered_scores = {"other": 1.0}

        # Normalize to probabilities
        total = sum(filtered_scores.values())
        probs = {k: round(v / total, 4) for k, v in filtered_scores.items()}

        # Sort top-k
        sorted_preds = sorted(probs.items(), key=lambda item: item[1], reverse=True)
        best_material, best_conf = sorted_preds[0]

        # Determine confidence status
        if best_conf < self._confidence_threshold:
            status = "LOW_CONFIDENCE"
            recommendation = "Material classification requires verification or additional imagery."
        else:
            status = "CONFIDENT"
            recommendation = f"Probable {best_material} substrate identified in demo mode."

        top_k = [{"material": m, "confidence": c} for m, c in sorted_preds[:3]]

        return {
            "material": best_material,
            "confidence": best_conf,
            "status": status,
            "recommendation": recommendation,
            "top_k": top_k,
            "model_name": self.name,
            "model_version": self.version,
            "inference_mode": "demo",
            "is_demo": True,
            "region": region,
            "disclaimer": (
                "DEMO MATERIAL CLASSIFICATION — NOT A VALIDATED RESEARCH PREDICTION. "
                "Operates using deterministic chromatic analysis in demo mode without trained ML weights."
            ),
        }

    def predict_batch(
        self,
        images: List[Union[np.ndarray, Image.Image, Path, str]],
        regions: Optional[List[Optional[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for i, img in enumerate(images):
            reg = regions[i] if regions and i < len(regions) else None
            results.append(self.predict(img, reg))
        return results
