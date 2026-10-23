"""
DeepCrack Real PyTorch Deterioration Detector.
Executes genuine deep-learning crack segmentation using the multi-scale feature fusion
architecture trained on concrete/masonry heritage surfaces (Liu et al., IEEE T-ITS).

Provides:
  - Genuine deep convolutional inference on CPU or CUDA
  - Accurate pixel-level crack localization
  - Bounding box and contour polygon extraction scaled to original image coordinates
  - True probabilistic model confidence scores without heuristic fabrication
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
    import cv2
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class DeepCrackDetector(DeteriorationDetector):
    """
    Inference engine for real DeepCrack CNN segmentation model.
    Detects cracks with pixel-level precision, spatial bounding boxes, and contour polygons.
    """
    _cached_model = None

    def __init__(
        self,
        checkpoint_path: Optional[Path] = None,
        model_dir: Optional[Path] = None,
        confidence_threshold: Optional[float] = None,
        device: str = "cpu",
    ):
        self.device = device
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(settings, "DETERIORATION_CONFIDENCE_THRESHOLD", 0.50)
        )
        self.model = None
        self.classes: List[str] = ["crack"]
        self.metrics: Optional[Dict[str, Any]] = None
        self.config: Dict[str, Any] = {}

        # Resolve paths
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        self.model_dir = Path(model_dir) if model_dir else project_root / "models" / "deterioration" / "deepcrack"
        
        default_ckpt = project_root / "data" / "temporal_dataset" / "DeepCrack_codes" / "checkpoints" / "MyDeepCrack_final.pth"
        if not default_ckpt.exists():
            default_ckpt = project_root / "data" / "temporal_dataset" / "DeepCrack_codes" / "checkpoints" / "DeepCrack_CT260_FT1.pth"
            
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else default_ckpt

        self.load_model()

    @property
    def name(self) -> str:
        return "DeepCrack CNN Feature-Fused Segmenter"

    @property
    def version(self) -> str:
        return "v1.0-benchmark"

    @property
    def is_demo(self) -> bool:
        return False

    def is_available(self) -> bool:
        return HAS_TORCH and self.model is not None

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """Loads DeepCrack architecture and pre-trained weights."""
        if not HAS_TORCH:
            logger.warning("PyTorch or OpenCV not available in environment.")
            return False

        # Load metrics and config if available
        if self.model_dir and self.model_dir.exists():
            metrics_file = self.model_dir / "metrics.json"
            if metrics_file.exists():
                try:
                    with open(metrics_file, "r", encoding="utf-8") as f:
                        self.metrics = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load DeepCrack metrics: {e}")

            config_file = self.model_dir / "config.json"
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load DeepCrack config: {e}")

        ckpt = Path(model_path) if model_path else self.checkpoint_path
        if not ckpt or not ckpt.exists():
            logger.warning(f"DeepCrack checkpoint not found at: {ckpt}")
            return False

        if model_path is None and DeepCrackDetector._cached_model is not None:
            self.model = DeepCrackDetector._cached_model
            return True

        try:
            # Import DeepCrack network architecture dynamically
            import sys
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            deepcrack_module_dir = project_root / "data" / "temporal_dataset" / "DeepCrack_codes"
            if str(deepcrack_module_dir) not in sys.path:
                sys.path.insert(0, str(deepcrack_module_dir))

            from model.deepcrack import DeepCrack

            model = DeepCrack().to(self.device)
            state = torch.load(str(ckpt), map_location=self.device, weights_only=False)
            if isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]

            new_state = {}
            for k, v in state.items():
                if k.startswith("module."):
                    new_state[k[len("module."):]] = v
                else:
                    new_state[k] = v

            model.load_state_dict(new_state, strict=True)
            model.eval()
            self.model = model
            if model_path is None:
                DeepCrackDetector._cached_model = model
            logger.info(f"Successfully loaded real DeepCrack PyTorch model from {ckpt}")
            return True
        except Exception as e:
            logger.error(f"Failed loading DeepCrack model: {e}")
            self.model = None
            return False

    def get_classes(self) -> List[Dict[str, Any]]:
        info = get_deterioration_class_by_id("crack")
        if info:
            return [info]
        return [{
            "id": "crack",
            "name": "Crack",
            "description": "Linear surface fissure or fracturing detected by DeepCrack CNN.",
            "color": "#ef4444",
            "enabled": True,
            "is_default": True,
            "severity_weight": 0.8,
        }]

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "id": "deepcrack",
            "name": self.name,
            "architecture": "DeepCrack (Multi-Scale Feature Fusion)",
            "version": self.version,
            "is_demo": False,
            "is_active": self.is_available(),
            "classes": ["crack"],
            "metrics": self.metrics,
            "checkpoint": str(self.checkpoint_path.name) if self.checkpoint_path else None,
            "disclaimer": "Validated on DeepCrack held-out dataset. Specializes in crack segmentation; other damage classes require separate annotations.",
        }

    def predict(
        self,
        image: Union[np.ndarray, Image.Image, Path, str, bytes],
        confidence_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("DeepCrack model is not loaded or available.")

        # Convert input to PIL Image
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

        orig_w, orig_h = pil_img.size
        th = confidence_threshold if confidence_threshold is not None else self.confidence_threshold

        # Preprocess: resize to 512x512
        img_resized = pil_img.resize((512, 512), Image.BILINEAR)
        img_np = np.array(img_resized, dtype=np.float32) / 255.0
        img_tensor = torch.from_numpy(img_np.transpose((2, 0, 1))).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(img_tensor)[0]
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()

        pred_bin = (prob > th).astype(np.uint8)
        crack_pixels = int(pred_bin.sum())

        if crack_pixels < 25:
            return []

        # Find connected crack components using OpenCV
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(pred_bin, connectivity=8)

        scale_x = orig_w / 512.0
        scale_y = orig_h / 512.0

        detections = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < 30:  # suppress tiny noise specs
                continue

            bx_512 = stats[i, cv2.CC_STAT_LEFT]
            by_512 = stats[i, cv2.CC_STAT_TOP]
            bw_512 = stats[i, cv2.CC_STAT_WIDTH]
            bh_512 = stats[i, cv2.CC_STAT_HEIGHT]

            # Scale to original dimensions
            bx = int(max(0, bx_512 * scale_x))
            by = int(max(0, by_512 * scale_y))
            bw = int(min(orig_w - bx, max(1, bw_512 * scale_x)))
            bh = int(min(orig_h - by, max(1, bh_512 * scale_y)))

            # Mean confidence across this connected component
            mask_comp = (labels == i)
            mean_conf = float(prob[mask_comp].mean())

            stat = "CONFIDENT" if mean_conf >= th else "LOW_CONFIDENCE"
            
            # Severity classification based on physical extent
            rel_area = (area * scale_x * scale_y) / (orig_w * orig_h)
            if rel_area > 0.05:
                severity = "severe"
            elif rel_area > 0.01:
                severity = "moderate"
            else:
                severity = "minor"

            # Optional polygon contour extraction
            comp_u8 = mask_comp.astype(np.uint8) * 255
            contours, _ = cv2.findContours(comp_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            polygon = None
            if contours:
                largest_c = max(contours, key=cv2.contourArea)
                # Downsample contour for clean payload
                epsilon = 0.02 * cv2.arcLength(largest_c, True)
                approx = cv2.approxPolyDP(largest_c, epsilon, True)
                if len(approx) >= 3:
                    polygon = [
                        {"x": int(pt[0][0] * scale_x), "y": int(pt[0][1] * scale_y)}
                        for pt in approx
                    ]

            detections.append({
                "damage_type": "crack",
                "confidence": round(mean_conf, 3),
                "status": stat,
                "severity_hint": severity,
                "bounding_box": {"x": bx, "y": by, "w": bw, "h": bh},
                "polygon": polygon,
                "notes": f"DeepCrack CNN segmented crack ({area} px at 512x512 resolution).",
            })

        # Sort detections by confidence descending
        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections

    def predict_batch(
        self,
        images: List[Union[np.ndarray, Image.Image, Path, str, bytes]],
        confidence_threshold: Optional[float] = None,
    ) -> List[List[Dict[str, Any]]]:
        return [self.predict(img, confidence_threshold=confidence_threshold) for img in images]
