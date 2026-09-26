"""
PyTorch Transfer-Learning Heritage Material Classifier.
Executes deep learning inference on CPU/GPU using architectures like
MobileNetV3 or ResNet-18 fine-tuned on cultural heritage substrates.
"""
import io
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image


from app.core.config import settings
from app.core.material_config import get_material_class_by_id
from app.ml.base import MaterialClassifier

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    from torchvision import transforms, models
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class PyTorchMaterialClassifier(MaterialClassifier):
    """
    Inference engine for fine-tuned transfer-learning PyTorch models.
    Supports full image classification and cropped bounding box evaluation.
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
            else getattr(settings, "CONFIDENCE_THRESHOLD", 0.60)
        )
        self.device = device
        self.model = None
        self.classes: List[str] = []
        self.config: Dict[str, Any] = {}
        self.metrics: Optional[Dict[str, Any]] = None
        self.transform = None

        if self.model_dir and Path(self.model_dir).exists():
            self.load_model(self.model_dir)

    @property
    def name(self) -> str:
        return self.config.get("name", "PyTorchHeritageMaterialClassifier")

    @property
    def version(self) -> str:
        return self.config.get("version", "v1.0")

    @property
    def is_demo(self) -> bool:
        return False

    def is_available(self) -> bool:
        return HAS_TORCH and self.model is not None

    def _build_transform(self, image_size: int = 224):
        if not HAS_TORCH:
            return None
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """
        Loads weights, class mapping, configuration, and evaluation metrics from disk.
        """
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
            logger.warning(f"Incomplete model directory at {target_dir}")
            return False

        try:
            # 1. Classes
            with open(classes_file, "r", encoding="utf-8") as f:
                self.classes = json.load(f)

            # 2. Config
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "architecture": "mobilenet_v3_small",
                    "image_size": 224,
                }

            # 3. Metrics (if evaluated on real validation data)
            if metrics_file.exists():
                with open(metrics_file, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
            else:
                self.metrics = None

            # 4. Instantiate Architecture
            arch = self.config.get("architecture", "mobilenet_v3_small").lower()
            num_classes = len(self.classes)

            if arch == "mobilenet_v3_small":
                net = models.mobilenet_v3_small(weights=None)
                in_feat = net.classifier[3].in_features
                net.classifier[3] = nn.Linear(in_feat, num_classes)
            elif arch == "resnet18":
                net = models.resnet18(weights=None)
                in_feat = net.fc.in_features
                net.fc = nn.Linear(in_feat, num_classes)
            else:
                net = models.mobilenet_v3_small(weights=None)
                in_feat = net.classifier[3].in_features
                net.classifier[3] = nn.Linear(in_feat, num_classes)

            # 5. Load State Dict
            state = torch.load(str(weights_file), map_location=self.device)
            net.load_state_dict(state)
            net.to(self.device)
            net.eval()

            self.model = net
            self.model_dir = target_dir
            self.transform = self._build_transform(self.config.get("image_size", 224))
            return True
        except Exception as e:
            logger.exception(f"Failed to load PyTorch model from {target_dir}: {e}")
            return False

    def get_classes(self) -> List[Dict[str, Any]]:
        result = []
        for c in self.classes:
            info = get_material_class_by_id(c)
            if info:
                result.append(info)
            else:
                result.append({
                    "id": c,
                    "name": c.replace("_", " ").title(),
                    "description": "Substrate category",
                    "color": "#38bdf8",
                    "enabled": True,
                    "is_default": False,
                })
        return result

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": self.config.get("model_id", self.model_dir.name if self.model_dir else "pytorch_model"),
            "name": self.name,
            "architecture": self.config.get("architecture", "mobilenet_v3_small"),
            "version": self.version,
            "is_demo": False,
            "is_active": self.is_available(),
            "dataset_identifier": self.config.get("dataset_identifier"),
            "training_date": self.config.get("training_date"),
            "classes": self.classes,
            "metrics": self.metrics,
            "notes": self.config.get("notes", "Fine-tuned transfer learning heritage material classifier."),
        }

    def _extract_crop(
        self,
        pil_img: Image.Image,
        region: Optional[Dict[str, Any]] = None,
    ) -> Image.Image:
        if not region:
            return pil_img

        w, h = pil_img.size
        rx = max(0, min(w - 1, int(region.get("x", 0))))
        ry = max(0, min(h - 1, int(region.get("y", 0))))
        rw = max(1, min(w - rx, int(region.get("w", w))))
        rh = max(1, min(h - ry, int(region.get("h", h))))

        return pil_img.crop((rx, ry, rx + rw, ry + rh))

    def predict(
        self,
        image: Union[np.ndarray, Image.Image, Path, str],
        region: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Runs PyTorch inference on the provided image or cropped bounding box."""
        if not self.is_available():
            raise RuntimeError("PyTorch model is not loaded or available.")

        # Convert to PIL Image
        if isinstance(image, (str, Path)):
            pil_img = Image.open(str(image)).convert("RGB")
        elif isinstance(image, np.ndarray):
            pil_img = Image.fromarray(image.astype(np.uint8)).convert("RGB")
        elif isinstance(image, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image)).convert("RGB")
        elif isinstance(image, Image.Image):
            pil_img = image.convert("RGB")
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

        # Crop region if requested
        crop_img = self._extract_crop(pil_img, region)

        # Preprocess tensor
        tensor = self.transform(crop_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            outputs = self.model(tensor)
            probs = torch.softmax(outputs, dim=1).squeeze(0).cpu().numpy()

        # Build top-k
        sorted_indices = np.argsort(probs)[::-1]
        best_idx = sorted_indices[0]
        best_material = self.classes[best_idx]
        best_conf = float(probs[best_idx])

        # Confidence status
        if best_conf < self.confidence_threshold:
            status = "LOW_CONFIDENCE"
            recommendation = "Material classification requires verification or additional imagery."
        else:
            status = "CONFIDENT"
            recommendation = f"Material classified as {best_material}."

        top_k = []
        for idx in sorted_indices[: min(3, len(sorted_indices))]:
            top_k.append({
                "material": self.classes[idx],
                "confidence": round(float(probs[idx]), 4),
            })

        return {
            "material": best_material,
            "confidence": round(best_conf, 4),
            "status": status,
            "recommendation": recommendation,
            "top_k": top_k,
            "model_name": self.name,
            "model_version": self.version,
            "inference_mode": "real_trained",
            "is_demo": False,
            "region": region,
            "disclaimer": (
                "Material classification outputs represent model predictions and associated confidence values. "
                "They should not be interpreted as definitive material identification without appropriate validation or expert verification."
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
