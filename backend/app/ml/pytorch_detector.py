"""
PyTorch Transfer-Learning Heritage Deterioration Detector.
Executes deep learning object detection (e.g. Faster R-CNN MobileNetV3 / ResNet-50)
on CPU/GPU to detect cracks, erosion, spalling, discoloration, and biological growth.
"""
import io
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.deterioration_config import get_deterioration_class_by_id
from app.ml.base_detector import DeteriorationDetector

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    from torchvision import transforms
    from torchvision.models.detection import fasterrcnn_mobilenet_v3_large_fpn, FasterRCNN_MobileNet_V3_Large_FPN_Weights
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class PyTorchDeteriorationDetector(DeteriorationDetector):
    """
    Inference engine for fine-tuned transfer-learning PyTorch object detection models.
    Detects physical deterioration defects with spatial bounding boxes and model confidences.
    """

    def __init__(
        self,
        model_dir: Optional[Path] = None,
        confidence_threshold: Optional[float] = None,
        device: str = "cpu",
    ):
        self.model_dir = model_dir
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(settings, "DETERIORATION_CONFIDENCE_THRESHOLD", 0.60)
        )
        self.device = device
        self.model = None
        self.classes: List[str] = []
        self.config: Dict[str, Any] = {}
        self.metrics: Optional[Dict[str, Any]] = None

        if self.model_dir and Path(self.model_dir).exists():
            self.load_model(self.model_dir)

    @property
    def name(self) -> str:
        return self.config.get("name", "PyTorchHeritageDeteriorationDetector")

    @property
    def version(self) -> str:
        return self.config.get("version", "v1.0")

    @property
    def is_demo(self) -> bool:
        return False

    def is_available(self) -> bool:
        return HAS_TORCH and self.model is not None

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """Loads weights, class mapping, configuration, and evaluation metrics from disk."""
        if not HAS_TORCH:
            logger.warning("PyTorch is not installed in the environment.")
            return False

        target_dir = Path(model_path) if model_path else self.model_dir
        if not target_dir or not target_dir.exists():
            return False

        weights_file = target_dir / "weights.pt"
        config_file = target_dir / "config.json"
        classes_file = target_dir / "classes.json"
        metrics_file = target_dir / "metrics.json"

        if not weights_file.exists() or not classes_file.exists():
            logger.info(f"Incomplete model package at {target_dir}")
            return False

        try:
            with open(classes_file, "r", encoding="utf-8") as f:
                self.classes = json.load(f)

            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)

            if metrics_file.exists():
                with open(metrics_file, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)

            # Build Faster R-CNN with adapted head
            num_classes = len(self.classes) + 1  # +1 for background
            self.model = fasterrcnn_mobilenet_v3_large_fpn(weights=None, num_classes=num_classes)

            state_dict = torch.load(str(weights_file), map_location=self.device)
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()

            self.model_dir = target_dir
            logger.info(f"Successfully loaded PyTorch deterioration detector from {target_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to load PyTorch deterioration model: {e}")
            self.model = None
            return False

    def get_classes(self) -> List[Dict[str, Any]]:
        result = []
        for c_id in self.classes:
            info = get_deterioration_class_by_id(c_id)
            if info:
                result.append(info)
            else:
                result.append({
                    "id": c_id,
                    "name": c_id.capitalize(),
                    "description": "",
                    "color": "#ef4444",
                    "enabled": True,
                    "is_default": False,
                    "severity_weight": 0.5,
                })
        return result

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": self.config.get("model_id", self.model_dir.name if self.model_dir else "pytorch_detector"),
            "name": self.name,
            "architecture": self.config.get("architecture", "fasterrcnn_mobilenet_v3_large_fpn"),
            "version": self.version,
            "is_demo": False,
            "is_active": self.is_available(),
            "classes": self.classes,
            "metrics": self.metrics,
            "disclaimer": "Validated on specific test dataset split. Field verification by conservator required.",
        }

    def predict(
        self,
        image: Union[np.ndarray, Image.Image, Path, str, bytes],
        confidence_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("PyTorch deterioration detector model is not loaded or available.")

        # Load image to PIL
        if isinstance(image, (str, Path)):
            pil_img = Image.open(str(image)).convert("RGB")
        elif isinstance(image, np.ndarray):
            pil_img = Image.fromarray(image.astype(np.uint8)).convert("RGB")
        elif isinstance(image, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image)).convert("RGB")
        elif isinstance(image, Image.Image):
            pil_img = image.convert("RGB")
        else:
            raise TypeError(f"Unsupported image input type: {type(image)}")

        threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        transform = transforms.ToTensor()
        tensor = transform(pil_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            predictions = self.model(tensor)[0]

        boxes = predictions["boxes"].cpu().numpy()
        scores = predictions["scores"].cpu().numpy()
        labels = predictions["labels"].cpu().numpy()

        detections = []
        for box, score, label in zip(boxes, scores, labels):
            score_val = float(score)
            if score_val < 0.20:  # Ignore extreme low background noise
                continue

            # Class index (1-based, 0 is background)
            class_idx = int(label) - 1
            if 0 <= class_idx < len(self.classes):
                damage_type = self.classes[class_idx]
            else:
                damage_type = "crack"

            stat = "CONFIDENT" if score_val >= threshold else "LOW_CONFIDENCE"
            x1, y1, x2, y2 = box.tolist()
            bx = int(max(0, x1))
            by = int(max(0, y1))
            bw = int(max(1, x2 - x1))
            bh = int(max(1, y2 - y1))

            detections.append({
                "damage_type": damage_type,
                "confidence": round(score_val, 3),
                "status": stat,
                "severity_hint": "severe" if (bw * bh) > (pil_img.width * pil_img.height * 0.15) else "moderate",
                "bounding_box": {"x": bx, "y": by, "w": bw, "h": bh},
                "polygon": None,
                "notes": "Deep learning detector bounding-box localization."
                if stat == "CONFIDENT"
                else "Detection requires verification or additional imagery.",
            })

        return detections

    def predict_batch(
        self,
        images: List[Union[np.ndarray, Image.Image, Path, str, bytes]],
        confidence_threshold: Optional[float] = None,
    ) -> List[List[Dict[str, Any]]]:
        return [self.predict(img, confidence_threshold=confidence_threshold) for img in images]
