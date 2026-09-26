"""
Heritage Material Dataset Validator.
Validates directory structures, image formats, corrupted files, class balance,
split ratios, and missing categories before training a transfer-learning classifier.
"""
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from PIL import Image


VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


class DatasetValidator:
    """Validates structural and numerical integrity of material classification datasets."""

    @staticmethod
    def validate_dataset(
        dataset_path: Path,
        expected_classes: Optional[List[str]] = None,
        min_samples_per_class: int = 5,
    ) -> Dict[str, Any]:
        """
        Scans dataset directory for train/val/test splits and evaluates class distributions,
        file corruptions, and structural balance.
        """
        dataset_path = Path(dataset_path)
        if not dataset_path.exists():
            return {
                "status": "INVALID",
                "dataset_path": str(dataset_path),
                "total_samples": 0,
                "num_classes": 0,
                "class_counts": {},
                "classes_found": [],
                "missing_classes": expected_classes or [],
                "imbalance_ratio": None,
                "warnings": [],
                "errors": [f"Dataset root directory does not exist: {dataset_path}"],
                "recommendation": "Provide a valid dataset path containing split directories (train/val/test).",
                "research_note": (
                    "Dataset validation verifies structural integrity and sample counts; "
                    "it does not scientifically certify domain generalization or dataset representativeness."
                ),
            }

        warnings: List[str] = []
        errors: List[str] = []

        # Detect splits
        splits = ["train", "val", "test"]
        split_dirs = {}
        for s in splits:
            sd = dataset_path / s
            if sd.is_dir():
                split_dirs[s] = sd

        # If no explicit train/val/test folders exist, check if class folders exist directly in root
        is_flat_structure = False
        if "train" not in split_dirs:
            subdirs = [d for d in dataset_path.iterdir() if d.is_dir()]
            if len(subdirs) > 0:
                is_flat_structure = True
                split_dirs = {"all": dataset_path}
                warnings.append(
                    "No explicit 'train', 'val', or 'test' split folders found. "
                    "Detected flat class directory structure. Automated split (e.g. 70/15/15) recommended."
                )
            else:
                errors.append(f"No subdirectories found in dataset root: {dataset_path}")
                return {
                    "status": "INVALID",
                    "dataset_path": str(dataset_path),
                    "total_samples": 0,
                    "num_classes": 0,
                    "class_counts": {},
                    "classes_found": [],
                    "missing_classes": expected_classes or [],
                    "imbalance_ratio": None,
                    "warnings": warnings,
                    "errors": errors,
                    "recommendation": "Populate dataset with class directories containing heritage substrate images.",
                    "research_note": (
                        "Dataset validation verifies structural integrity and sample counts; "
                        "it does not scientifically certify domain generalization or dataset representativeness."
                    ),
                }

        class_counts: Dict[str, Dict[str, int]] = {}
        classes_found: Set[str] = set()
        seen_filenames: Dict[str, str] = {}  # filename -> split path (duplicate check)
        corrupted_images: List[str] = []
        total_samples = 0

        # Scan each split
        for split_name, split_path in split_dirs.items():
            class_counts[split_name] = {}
            if is_flat_structure:
                class_dirs = [d for d in split_path.iterdir() if d.is_dir()]
            else:
                class_dirs = [d for d in split_path.iterdir() if d.is_dir()]

            for cdir in class_dirs:
                cname = cdir.name.lower()
                classes_found.add(cname)
                files = [f for f in cdir.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS]

                valid_in_class = 0
                for img_file in files:
                    # Check duplicate filenames
                    if img_file.name in seen_filenames:
                        warnings.append(
                            f"Duplicate filename detected: '{img_file.name}' in both "
                            f"'{seen_filenames[img_file.name]}' and '{split_name}/{cname}'."
                        )
                    seen_filenames[img_file.name] = f"{split_name}/{cname}"

                    # Verify image readability
                    try:
                        with Image.open(img_file) as im:
                            im.verify()
                        valid_in_class += 1
                    except Exception:
                        corrupted_images.append(str(img_file.relative_to(dataset_path)))

                class_counts[split_name][cname] = valid_in_class
                total_samples += valid_in_class

                if valid_in_class == 0:
                    warnings.append(f"Class folder '{split_name}/{cname}' is empty or contains no valid images.")

        if corrupted_images:
            errors.append(f"Found {len(corrupted_images)} unreadable/corrupted image file(s).")

        # Class counts across all splits
        combined_class_counts: Dict[str, int] = {}
        for sp, counts in class_counts.items():
            for cname, cnt in counts.items():
                combined_class_counts[cname] = combined_class_counts.get(cname, 0) + cnt

        # Check expected classes
        missing_classes: List[str] = []
        if expected_classes:
            for exp in expected_classes:
                if exp.lower() not in classes_found:
                    missing_classes.append(exp)
            if missing_classes:
                warnings.append(
                    f"Configured material classes not found in dataset: {', '.join(missing_classes)}."
                )

        # Evaluate class balance
        imbalance_ratio: Optional[float] = None
        counts_list = list(combined_class_counts.values())
        if counts_list and len(counts_list) > 1:
            min_c = min(counts_list)
            max_c = max(counts_list)
            if min_c > 0:
                imbalance_ratio = round(max_c / min_c, 2)
                if imbalance_ratio > 3.0:
                    warnings.append(
                        f"Significant class imbalance detected (ratio {imbalance_ratio}:1). "
                        f"Largest class has {max_c} samples, smallest has {min_c} samples."
                    )
            else:
                warnings.append("One or more material classes have 0 valid image samples.")

        # Check sample sufficiency
        for cname, cnt in combined_class_counts.items():
            if cnt < min_samples_per_class:
                warnings.append(
                    f"Class '{cname}' has only {cnt} sample(s), below recommended minimum of {min_samples_per_class}."
                )

        # Status determination
        if errors or total_samples == 0:
            status = "INVALID"
            recommendation = "Resolve dataset errors and ensure valid image files exist before training."
        elif warnings:
            status = "WARNING"
            recommendation = (
                "Dataset is structurally usable for transfer learning, but heed warnings "
                "regarding sample distribution and potential class imbalance."
            )
        else:
            status = "VALID"
            recommendation = "Dataset satisfies structural criteria. Ready for model training."

        return {
            "status": status,
            "dataset_path": str(dataset_path),
            "total_samples": total_samples,
            "num_classes": len(classes_found),
            "class_counts": class_counts,
            "classes_found": sorted(list(classes_found)),
            "missing_classes": missing_classes,
            "imbalance_ratio": imbalance_ratio,
            "warnings": warnings,
            "errors": errors,
            "recommendation": recommendation,
            "research_note": (
                "Dataset validation verifies structural integrity and sample counts; "
                "it does not scientifically certify domain generalization or dataset representativeness."
            ),
        }

    validate = validate_dataset

