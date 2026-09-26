"""
PyTorch Heritage Material Classifier Trainer.
Implements transfer learning training, validation, evaluation, and packaging
for cultural heritage substrate classification.

STRICT RESEARCH INTEGRITY:
- All metrics (accuracy, precision, recall, F1, confusion matrix) are calculated directly
  from evaluated sample predictions.
- No synthetic or fabricated metrics are ever emitted.
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset, random_split
    from torchvision import datasets, transforms, models
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def calculate_classification_metrics(
    y_true: List[int],
    y_pred: List[int],
    class_names: List[str]
) -> Dict[str, Any]:
    """
    Computes genuine multi-class classification metrics directly from ground-truth and predictions.
    Avoids requiring scikit-learn dependency by implementing standard confusion matrix and macro metrics.
    """
    num_classes = len(class_names)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1

    total_samples = len(y_true)
    accuracy = float(np.trace(cm) / total_samples) if total_samples > 0 else 0.0

    per_class_metrics = {}
    precisions = []
    recalls = []
    f1s = []

    for idx, c_name in enumerate(class_names):
        tp = int(cm[idx, idx])
        fp = int(np.sum(cm[:, idx]) - tp)
        fn = int(np.sum(cm[idx, :]) - tp)
        support = int(np.sum(cm[idx, :]))

        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

        precisions.append(p)
        recalls.append(r)
        f1s.append(f1)

        per_class_metrics[c_name] = {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1_score": round(float(f1), 4),
            "support": support
        }

    macro_precision = float(np.mean(precisions)) if precisions else 0.0
    macro_recall = float(np.mean(recalls)) if recalls else 0.0
    macro_f1 = float(np.mean(f1s)) if f1s else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "total_evaluated_samples": total_samples,
        "per_class": per_class_metrics,
        "confusion_matrix": cm.tolist(),
        "class_labels": class_names,
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


class MaterialModelTrainer:
    """
    Manages fine-tuning, validation, and packaging of transfer-learning models
    for heritage materials.
    """

    def __init__(
        self,
        base_architecture: str = "mobilenet_v3_small",
        pretrained: bool = True,
        device: Optional[str] = None
    ):
        if not HAS_TORCH:
            raise RuntimeError("PyTorch is required for model training.")

        self.architecture = base_architecture
        self.pretrained = pretrained
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

    def _build_model(self, num_classes: int) -> nn.Module:
        """Instantiates and adapts transfer learning architecture."""
        weights = "DEFAULT" if self.pretrained else None

        if self.architecture == "mobilenet_v3_small":
            try:
                model = models.mobilenet_v3_small(weights=weights)
            except Exception:
                model = models.mobilenet_v3_small(pretrained=self.pretrained)
            in_features = model.classifier[3].in_features
            model.classifier[3] = nn.Linear(in_features, num_classes)
            return model

        elif self.architecture == "mobilenet_v3_large":
            try:
                model = models.mobilenet_v3_large(weights=weights)
            except Exception:
                model = models.mobilenet_v3_large(pretrained=self.pretrained)
            in_features = model.classifier[3].in_features
            model.classifier[3] = nn.Linear(in_features, num_classes)
            return model

        elif self.architecture == "resnet18":
            try:
                model = models.resnet18(weights=weights)
            except Exception:
                model = models.resnet18(pretrained=self.pretrained)
            in_features = model.fc.in_features
            model.fc = nn.Linear(in_features, num_classes)
            return model

        else:
            raise ValueError(f"Unsupported architecture: {self.architecture}")

    def train(
        self,
        dataset_dir: Path,
        output_dir: Path,
        epochs: int = 10,
        batch_size: int = 16,
        learning_rate: float = 1e-4,
        image_size: int = 224,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Trains model on structured dataset directory, evaluates performance, and outputs packaged artifact.
        """
        dataset_path = Path(dataset_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        train_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

        val_transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

        has_splits = (dataset_path / "train").exists() and (dataset_path / "val").exists()

        if has_splits:
            train_ds = datasets.ImageFolder(str(dataset_path / "train"), transform=train_transform)
            val_ds = datasets.ImageFolder(str(dataset_path / "val"), transform=val_transform)
            classes = train_ds.classes
            test_ds = None
            if (dataset_path / "test").exists():
                test_ds = datasets.ImageFolder(str(dataset_path / "test"), transform=val_transform)
        else:
            full_ds = datasets.ImageFolder(str(dataset_path), transform=train_transform)
            classes = full_ds.classes
            n_total = len(full_ds)
            n_train = int(0.7 * n_total)
            n_val = int(0.15 * n_total)
            n_test = n_total - n_train - n_val

            train_ds, val_subset, test_subset = random_split(
                full_ds, [n_train, n_val, n_test],
                generator=torch.Generator().manual_seed(42)
            )
            val_ds = val_subset
            test_ds = test_subset

        if len(classes) < 2:
            raise ValueError(f"Dataset must have at least 2 distinct classes. Found: {classes}")

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False) if test_ds else val_loader

        model = self._build_model(len(classes)).to(self.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)

        logger.info(f"Starting training for {epochs} epochs on device {self.device}")
        history = []

        for epoch in range(epochs):
            model.train()
            running_loss = 0.0
            correct = 0
            total = 0

            for images, labels in train_loader:
                images, labels = images.to(self.device), labels.to(self.device)
                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

                running_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

            train_loss = running_loss / total if total > 0 else 0.0
            train_acc = correct / total if total > 0 else 0.0

            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for images, labels in val_loader:
                    images, labels = images.to(self.device), labels.to(self.device)
                    outputs = model(images)
                    loss = criterion(outputs, labels)
                    val_loss += loss.item() * images.size(0)
                    _, predicted = outputs.max(1)
                    val_total += labels.size(0)
                    val_correct += predicted.eq(labels).sum().item()

            val_loss_epoch = val_loss / val_total if val_total > 0 else 0.0
            val_acc_epoch = val_correct / val_total if val_total > 0 else 0.0

            epoch_record = {
                "epoch": epoch + 1,
                "train_loss": round(train_loss, 4),
                "train_accuracy": round(train_acc, 4),
                "val_loss": round(val_loss_epoch, 4),
                "val_accuracy": round(val_acc_epoch, 4),
            }
            history.append(epoch_record)

            if progress_callback:
                progress_callback({
                    "stage": "training",
                    "epoch": epoch + 1,
                    "total_epochs": epochs,
                    "percent": int(((epoch + 1) / epochs) * 90),
                    "epoch_record": epoch_record
                })

        model.eval()
        all_preds = []
        all_targets = []
        with torch.no_grad():
            for images, labels in test_loader:
                images = images.to(self.device)
                outputs = model(images)
                _, predicted = outputs.max(1)
                all_preds.extend(predicted.cpu().numpy().tolist())
                all_targets.extend(labels.numpy().tolist() if hasattr(labels, "numpy") else list(labels))

        metrics = calculate_classification_metrics(all_targets, all_preds, classes)
        metrics["training_history"] = history

        weights_path = output_path / "weights.pt"
        torch.save(model.state_dict(), str(weights_path))

        classes_path = output_path / "classes.json"
        with open(classes_path, "w", encoding="utf-8") as f:
            json.dump(classes, f, indent=2)

        config_data = {
            "name": f"Heritage_{self.architecture.capitalize()}",
            "version": "v1.0",
            "architecture": self.architecture,
            "pretrained": self.pretrained,
            "classes": classes,
            "image_size": image_size,
            "num_classes": len(classes),
            "trained_epochs": epochs,
            "device": str(self.device),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "is_demo": False,
        }
        config_path = output_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        metrics_path = output_path / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        readme_content = f"""# Heritage Material Classification Model

- **Architecture**: {self.architecture}
- **Device**: {self.device}
- **Classes**: {', '.join(classes)}
- **Training Epochs**: {epochs}
- **Overall Accuracy**: {metrics['accuracy'] * 100:.2f}%
- **Macro F1**: {metrics['macro_f1']:.4f}
- **Total Evaluated Samples**: {metrics['total_evaluated_samples']}

## Research Safety Disclaimer
All metrics above were genuinely calculated from the test/validation dataset.
This model provides probabilistic classification confidence, not structural or material certainty.
"""
        with open(output_path / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

        if progress_callback:
            progress_callback({
                "stage": "complete",
                "percent": 100,
                "metrics": metrics,
                "model_dir": str(output_path)
            })

        return {
            "success": True,
            "model_dir": str(output_path),
            "config": config_data,
            "metrics": metrics
        }
