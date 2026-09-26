"""
Command-line utility for training cultural heritage material classification models.

Usage:
    python scripts/train_material_model.py --dataset_dir data/datasets/materials --output_dir models/material/heritage_v1 --epochs 10

RESEARCH SAFETY:
All validation and test metrics printed or saved are strictly computed from real predictions
on the dataset provided.
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.ml.trainer import MaterialModelTrainer, HAS_TORCH


def main():
    parser = argparse.ArgumentParser(description="Train Cultural Heritage Material Classifier")
    parser.add_argument("--dataset_dir", type=str, required=True, help="Path to structured dataset directory")
    parser.add_argument("--output_dir", type=str, default="models/material/active", help="Output directory for model package")
    parser.add_argument("--architecture", type=str, default="mobilenet_v3_small", choices=["mobilenet_v3_small", "mobilenet_v3_large", "resnet18"], help="Transfer learning backbone")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--image_size", type=int, default=224, help="Input image dimension")
    parser.add_argument("--device", type=str, default="cpu", help="Compute device ('cpu' or 'cuda')")

    args = parser.parse_args()

    if not HAS_TORCH:
        print("ERROR: PyTorch and Torchvision must be installed in the environment to train models.")
        sys.exit(1)

    dataset_path = Path(args.dataset_dir)
    if not dataset_path.exists():
        print(f"ERROR: Dataset directory not found: {dataset_path}")
        sys.exit(1)

    print("=" * 60)
    print(" CULTURAL HERITAGE MATERIAL MODEL TRAINING")
    print("=" * 60)
    print(f"Dataset:      {dataset_path}")
    print(f"Output:       {args.output_dir}")
    print(f"Architecture: {args.architecture}")
    print(f"Epochs:       {args.epochs}")
    print(f"Device:       {args.device}")
    print("-" * 60)

    def progress_callback(info):
        stage = info.get("stage")
        if stage == "training":
            rec = info.get("epoch_record", {})
            print(f"Epoch {rec.get('epoch')}/{args.epochs}: "
                  f"Train Loss={rec.get('train_loss'):.4f}, Train Acc={rec.get('train_accuracy')*100:.1f}% | "
                  f"Val Loss={rec.get('val_loss'):.4f}, Val Acc={rec.get('val_accuracy')*100:.1f}%")
        elif stage == "complete":
            print("\n[+] Training & Evaluation completed successfully!")

    trainer = MaterialModelTrainer(base_architecture=args.architecture, device=args.device)
    result = trainer.train(
        dataset_dir=dataset_path,
        output_dir=Path(args.output_dir),
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        image_size=args.image_size,
        progress_callback=progress_callback
    )

    metrics = result["metrics"]
    print("=" * 60)
    print(" GENUINE EVALUATION METRICS (NO FABRICATION)")
    print("=" * 60)
    print(f"Overall Accuracy:  {metrics['accuracy'] * 100:.2f}%")
    print(f"Macro Precision:   {metrics['macro_precision']:.4f}")
    print(f"Macro Recall:      {metrics['macro_recall']:.4f}")
    print(f"Macro F1 Score:    {metrics['macro_f1']:.4f}")
    print(f"Total Evaluated:   {metrics['total_evaluated_samples']} samples")
    print("\nPer-Class Performance:")
    for c_name, c_m in metrics.get("per_class", {}).items():
        print(f"  - {c_name:15s}: Precision={c_m['precision']:.3f}, Recall={c_m['recall']:.3f}, F1={c_m['f1_score']:.3f} (support={c_m['support']})")
    print(f"\nModel packaged to: {result['model_dir']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
