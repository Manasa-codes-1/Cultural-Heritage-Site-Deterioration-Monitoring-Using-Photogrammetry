"""
Command-line utility for training cultural heritage deterioration detection models.

Usage:
    python scripts/train_deterioration_model.py --dataset_dir data/datasets/deterioration --output_dir models/deterioration/active --epochs 5

RESEARCH SAFETY:
All validation and test metrics printed or saved are strictly computed from real predictions
on the dataset provided.
"""
import argparse
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.ml.deterioration_trainer import DeteriorationModelTrainer, HAS_TORCH


def main():
    parser = argparse.ArgumentParser(description="Train Cultural Heritage Deterioration Detector")
    parser.add_argument("--dataset_dir", type=str, required=True, help="Path to structured dataset directory")
    parser.add_argument("--output_dir", type=str, default="models/deterioration/active", help="Output directory for model package")
    parser.add_argument("--architecture", type=str, default="fasterrcnn_mobilenet_v3_large_fpn", help="Backbone architecture")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--device", type=str, default="cpu", help="Compute device ('cpu' or 'cuda')")

    args = parser.parse_args()

    if not HAS_TORCH:
        print("ERROR: PyTorch and torchvision must be installed in the environment to train models.")
        sys.exit(1)

    dataset_path = Path(args.dataset_dir)
    if not dataset_path.exists():
        print(f"ERROR: Dataset directory not found: {dataset_path}")
        sys.exit(1)

    print("=" * 65)
    print(" CULTURAL HERITAGE DETERIORATION DETECTION MODEL TRAINING")
    print("=" * 65)
    print(f"Dataset:      {dataset_path}")
    print(f"Output:       {args.output_dir}")
    print(f"Architecture: {args.architecture}")
    print(f"Epochs:       {args.epochs}")
    print(f"Device:       {args.device}")
    print("-" * 65)

    trainer = DeteriorationModelTrainer(base_architecture=args.architecture, device=args.device)
    result = trainer.train(
        dataset_dir=dataset_path,
        output_dir=Path(args.output_dir),
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )

    metrics = result["metrics"]
    print("=" * 65)
    print(" GENUINE DETECTION EVALUATION METRICS (NO FABRICATION)")
    print("=" * 65)
    print(f"mAP@0.50:          {metrics['mAP_50'] * 100:.2f}%")
    print(f"Macro Precision:   {metrics['macro_precision']:.4f}")
    print(f"Macro Recall:      {metrics['macro_recall']:.4f}")
    print(f"Evaluated Images:  {metrics['total_evaluated_images']}")
    print("\nPer-Class Performance:")
    for c_name, c_m in metrics.get("per_class", {}).items():
        print(f"  - {c_name:18s}: Precision={c_m['precision']:.3f}, Recall={c_m['recall']:.3f}, AP@50={c_m['ap_50']:.3f} (GT={c_m['ground_truth_count']})")
    print(f"\nModel packaged to: {result['model_dir']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
