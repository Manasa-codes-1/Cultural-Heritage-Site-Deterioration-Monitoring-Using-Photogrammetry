"""
Unit tests for real deep learning detectors and classifiers.
Verifies DeepCrack CNN segmenter and fine-tuned MobileNetV3 material classifier.
"""
import pytest
import numpy as np
from PIL import Image
from pathlib import Path

from app.ml.deepcrack_detector import DeepCrackDetector
from app.ml.deterioration_factory import get_deterioration_detector, list_deterioration_models
from app.ml import get_material_classifier, list_available_models

def test_deepcrack_detector_info():
    det = DeepCrackDetector()
    assert det.is_available() is True
    assert det.is_demo is False
    assert "DeepCrack" in det.name
    
    classes = det.get_classes()
    assert len(classes) == 1
    assert classes[0]["id"] == "crack"
    
    info = det.get_model_info()
    assert info["is_demo"] is False
    assert info["is_active"] is True
    assert info["metrics"] is not None
    assert "pixel_accuracy" in info["metrics"]
    assert "pixel_f1" in info["metrics"]

def test_deterioration_factory_registry():
    models = list_deterioration_models()
    model_ids = [m["id"] for m in models]
    assert "demo" in model_ids
    assert "deepcrack" in model_ids

    # Explicit DeepCrack request returns real DeepCrack detector
    real_det = get_deterioration_detector("deepcrack")
    assert real_det.is_demo is False
    assert "DeepCrack" in real_det.name

    # Default request returns baseline demo detector
    default_det = get_deterioration_detector()
    assert default_det.is_demo is True

    # Explicit demo request should return demo
    demo_det = get_deterioration_detector("demo")
    assert demo_det.is_demo is True

def test_material_classifier_real():
    models = list_available_models()
    model_ids = [m["id"] for m in models]
    assert "active" in model_ids or "heritage_v1" in model_ids
    
    clf = get_material_classifier("active")
    assert clf.is_available() is True
    assert clf.is_demo is False
    assert set(clf.classes).issuperset({"brick", "granite", "sandstone"})

    # Default should return demo classifier for testing consistency
    demo_clf = get_material_classifier()
    assert demo_clf.is_demo is True

def test_deepcrack_predict_blank_image():
    # A solid white image should contain no cracks
    det = DeepCrackDetector()
    white_img = Image.new("RGB", (256, 256), color=(255, 255, 255))
    results = det.predict(white_img, confidence_threshold=0.5)
    # White image should produce 0 detections or very low noise
    assert isinstance(results, list)
    for r in results:
        assert r["damage_type"] == "crack"
        assert "bounding_box" in r
        assert "confidence" in r
