import os
import sys
from pathlib import Path

# Add backend directory to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))

from app.ml.deterioration_factory import get_deterioration_detector, list_deterioration_models

def main():
    print("Testing Deterioration Models List:")
    models = list_deterioration_models()
    for m in models:
        print(f" - {m.get('name')} (id: {m.get('id')}, demo: {m.get('is_demo')})")
        if m.get("metrics"):
            print(f"    Metrics: acc={m['metrics'].get('pixel_accuracy')}, f1={m['metrics'].get('pixel_f1')}")

    print("\nTesting Active Detector Instance:")
    det = get_deterioration_detector()
    print(f"Active Detector: {det.name} (is_demo={det.is_demo}, is_available={det.is_available()})")

    # Predict on one DeepCrack val image
    test_img = root_dir / "data" / "temporal_dataset" / "DeepCrack_codes" / "dataset" / "val" / "images" / "111212-1.jpg"
    print(f"\nPredicting on: {test_img.name}...")
    results = det.predict(test_img, confidence_threshold=0.5)
    print(f"Detected {len(results)} crack components:")
    for idx, r in enumerate(results[:5]):
        print(f" [{idx+1}] damage={r['damage_type']}, conf={r['confidence']}, status={r['status']}, severity={r['severity_hint']}, bbox={r['bounding_box']}")

if __name__ == "__main__":
    main()
