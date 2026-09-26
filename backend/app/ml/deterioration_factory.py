"""
Deterioration Detector Factory and Model Registry.
Scans for packaged PyTorch defect detectors and provides clean fallback to demo detector.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.ml.base_detector import DeteriorationDetector
from app.ml.demo_detector import DemoDeteriorationDetector
from app.ml.pytorch_detector import PyTorchDeteriorationDetector, HAS_TORCH

logger = logging.getLogger(__name__)

DEFAULT_DETERIORATION_MODELS_DIR = Path("models/deterioration")


def list_deterioration_models(models_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Scans models directory for packaged deterioration detectors and returns metadata.
    Always includes DemoDeteriorationDetector for complete research transparency.
    """
    base_dir = Path(models_dir) if models_dir else DEFAULT_DETERIORATION_MODELS_DIR
    models_list = []

    # 1. Built-in Demo Detector
    demo_inst = DemoDeteriorationDetector()
    models_list.append(demo_inst.get_model_info())

    # 2. Packaged PyTorch detectors
    if base_dir.exists():
        for item in base_dir.iterdir():
            if item.is_dir():
                weights_path = item / "weights.pt"
                config_path = item / "config.json"
                if weights_path.exists() and config_path.exists():
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        metrics_data = None
                        metrics_path = item / "metrics.json"
                        if metrics_path.exists():
                            with open(metrics_path, "r", encoding="utf-8") as mf:
                                metrics_data = json.load(mf)

                        models_list.append({
                            "id": item.name,
                            "name": cfg.get("name", item.name),
                            "version": cfg.get("version", "v1.0"),
                            "architecture": cfg.get("architecture", "fasterrcnn_mobilenet_v3_large_fpn"),
                            "classes": cfg.get("classes", []),
                            "is_demo": False,
                            "is_active": (item.name == "active"),
                            "metrics": metrics_data,
                            "path": str(item),
                            "disclaimer": "Validated on specific dataset split. Field verification by conservator required.",
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read deterioration model dir {item}: {e}")

    return models_list


def get_deterioration_detector(model_id: Optional[str] = None) -> DeteriorationDetector:
    """
    Factory function returning the active or requested deterioration detector.
    - If model_id is specified and exists on disk, loads that model.
    - If no model_id is specified, checks for 'models/deterioration/active'.
    - If no trained model exists or PyTorch is unavailable, falls back cleanly to DemoDeteriorationDetector.
    """
    base_dir = DEFAULT_DETERIORATION_MODELS_DIR

    candidate_dirs = []
    if model_id and model_id != "demo":
        candidate_dirs.append(base_dir / model_id)
    candidate_dirs.append(base_dir / "active")

    for c_dir in candidate_dirs:
        if c_dir.exists() and (c_dir / "weights.pt").exists() and HAS_TORCH:
            try:
                det = PyTorchDeteriorationDetector(model_dir=c_dir)
                if det.is_available():
                    logger.info(f"Loaded trained PyTorch deterioration detector from {c_dir}")
                    return det
            except Exception as e:
                logger.warning(f"Could not load PyTorch detector from {c_dir}: {e}")

    logger.info("Using DemoDeteriorationDetector (heuristic demo mode).")
    return DemoDeteriorationDetector()
