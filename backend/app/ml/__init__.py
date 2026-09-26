"""
ML module for Cultural Heritage Material Classification.
Provides model factory, registry, and dataset validation utilities.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.ml.base import MaterialClassifier
from app.ml.demo_classifier import DemoMaterialClassifier
from app.ml.pytorch_classifier import PyTorchMaterialClassifier, HAS_TORCH
from app.ml.dataset_validator import DatasetValidator

logger = logging.getLogger(__name__)

# Base directory for saved model artifacts
DEFAULT_MODELS_DIR = Path("models/material")


def list_available_models(models_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Scans the models directory for packaged material models and returns metadata.
    Always includes the built-in Demo Classifier for research transparency.
    """
    base_dir = Path(models_dir) if models_dir else DEFAULT_MODELS_DIR
    models_list = []

    # 1. Built-in Demo Classifier
    demo_inst = DemoMaterialClassifier()
    models_list.append(demo_inst.get_model_info())

    # 2. Check disk for trained PyTorch models
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
                            "architecture": cfg.get("architecture", "unknown"),
                            "device": cfg.get("device", "cpu"),
                            "classes": cfg.get("classes", []),
                            "is_demo": False,
                            "is_active": (item.name == "active"),
                            "metrics": metrics_data,
                            "path": str(item),
                            "created_at": cfg.get("created_at"),
                            "disclaimer": "Validated on specific dataset split. Does not guarantee field certainty."
                        })
                    except Exception as e:
                        logger.warning(f"Failed to read model directory {item}: {e}")

    return models_list


def get_material_classifier(model_id: Optional[str] = None) -> MaterialClassifier:
    """
    Factory function returning the requested or optimal material classifier.
    - If model_id is specified and exists, loads that model.
    - If no model_id is specified, checks for 'models/material/active'.
    - If no trained model is available or PyTorch cannot load it, falls back to DemoMaterialClassifier.
    """
    base_dir = DEFAULT_MODELS_DIR

    # Check for specific or active model
    candidate_dirs = []
    if model_id and model_id != "demo":
        candidate_dirs.append(base_dir / model_id)
    candidate_dirs.append(base_dir / "active")

    for c_dir in candidate_dirs:
        if c_dir.exists() and (c_dir / "weights.pt").exists() and HAS_TORCH:
            try:
                clf = PyTorchMaterialClassifier(model_dir=c_dir)
                if clf.is_available():
                    logger.info(f"Loaded trained PyTorch material model from {c_dir}")
                    return clf
            except Exception as e:
                logger.warning(f"Could not load PyTorch model from {c_dir}: {e}")

    logger.info("Using DemoMaterialClassifier (heuristic/demo mode).")
    return DemoMaterialClassifier()


from app.ml.base_detector import DeteriorationDetector
from app.ml.demo_detector import DemoDeteriorationDetector
from app.ml.pytorch_detector import PyTorchDeteriorationDetector
from app.ml.deterioration_validator import DeteriorationDatasetValidator
from app.ml.deterioration_factory import get_deterioration_detector, list_deterioration_models, DEFAULT_DETERIORATION_MODELS_DIR

__all__ = [
    "MaterialClassifier",
    "DemoMaterialClassifier",
    "PyTorchMaterialClassifier",
    "DatasetValidator",
    "get_material_classifier",
    "list_available_models",
    "DEFAULT_MODELS_DIR",
    "DeteriorationDetector",
    "DemoDeteriorationDetector",
    "PyTorchDeteriorationDetector",
    "DeteriorationDatasetValidator",
    "get_deterioration_detector",
    "list_deterioration_models",
    "DEFAULT_DETERIORATION_MODELS_DIR",
]

