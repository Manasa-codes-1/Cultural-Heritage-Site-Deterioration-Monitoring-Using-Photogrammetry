import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))

from app.ml import list_available_models, get_material_classifier

def main():
    print("Available material models:")
    for m in list_available_models():
        print(f" - {m['name']} (id: {m['id']}, demo: {m['is_demo']}, active: {m.get('is_active')})")
        if m.get("metrics"):
            print(f"    acc={m['metrics'].get('accuracy')}, f1={m['metrics'].get('macro_f1')}")

    clf = get_material_classifier()
    print(f"\nActive classifier: {clf.name}")
    print(f"is_demo: {clf.is_demo}")
    print(f"is_available: {clf.is_available()}")
    print(f"classes: {clf.classes}")

    # Predict on a test image
    test_img = root_dir / "data" / "datasets" / "materials" / "val" / "brick" / "brick_val_001.jpg"
    if test_img.exists():
        res = clf.predict(test_img)
        print(f"\nPrediction on {test_img.name}:")
        print(f" - material: {res['material']}, conf: {res['confidence']}, status: {res['status']}")
        print(f" - top_k: {res['top_k']}")
        print(f" - mode: {res['inference_mode']}, is_demo: {res['is_demo']}")

if __name__ == "__main__":
    main()
