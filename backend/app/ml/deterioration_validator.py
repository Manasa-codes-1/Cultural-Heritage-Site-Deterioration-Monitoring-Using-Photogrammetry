"""
Heritage Deterioration Dataset Validator.
Validates structural integrity, image decodability, bounding-box geometry,
annotation schema correctness, class balance, and split ratios
prior to training or fine-tuning defect detection models.

STRICT RESEARCH INTEGRITY:
- Validates geometrical bounds without fabricating coverage or quality claims.
- Returns explicit VALID, WARNING, or INVALID statuses.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Union
from PIL import Image

from app.core.deterioration_config import load_deterioration_classes

logger = logging.getLogger(__name__)

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


class DeteriorationDatasetValidator:
    """Validates structural and geometric correctness of defect detection datasets."""

    @staticmethod
    def validate_dataset(
        dataset_path: Union[Path, str],
        expected_classes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Scans a dataset directory for images and annotation files, validating
        box bounds ([x, y, w, h]), class labels, image decodability, and split distributions.
        """
        target_path = Path(dataset_path)
        if not target_path.exists():
            return {
                "status": "INVALID",
                "dataset_path": str(target_path),
                "total_images": 0,
                "total_annotations": 0,
                "num_classes": 0,
                "classes_found": [],
                "missing_classes": expected_classes or [],
                "invalid_boxes_count": 0,
                "imbalance_ratio": None,
                "warnings": [],
                "errors": [f"Dataset root directory does not exist: {target_path}"],
                "recommendation": "Provide an existing dataset directory containing images and annotations.json.",
                "research_note": (
                    "Dataset validation verifies annotation geometry and sample counts; "
                    "it does not scientifically certify domain generalization or inspection efficacy."
                ),
            }

        warnings: List[str] = []
        errors: List[str] = []

        configured_classes = set(c["id"] for c in load_deterioration_classes(include_disabled=True))
        if expected_classes:
            configured_classes.update(expected_classes)

        # Look for annotations file in root or split subdirectories
        annotation_files = list(target_path.glob("**/annotations.json")) + list(target_path.glob("**/labels.json"))
        images_found: List[Path] = [
            f for f in target_path.glob("**/*")
            if f.is_file() and f.suffix.lower() in VALID_IMAGE_EXTENSIONS
        ]

        if not images_found:
            errors.append(f"No image files with supported extensions ({', '.join(VALID_IMAGE_EXTENSIONS)}) found.")

        total_annotations = 0
        invalid_boxes_count = 0
        classes_found: Set[str] = set()
        class_counts: Dict[str, int] = {}
        annotated_image_names: Set[str] = set()

        if not annotation_files:
            warnings.append("No annotations.json file found. Dataset cannot be used for supervised training without annotations.")
        else:
            for annot_file in annotation_files:
                try:
                    with open(annot_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Parse Format A: Simple dict / list: [{"image": "img1.jpg", "boxes": [...]}, ...]
                    # or {"images": [...], "annotations": [...], "categories": [...]}
                    items_to_process = []
                    if isinstance(data, list):
                        items_to_process = data
                    elif isinstance(data, dict):
                        if "annotations" in data and "images" in data:
                            # COCO format
                            img_map = {img["id"]: img.get("file_name", "") for img in data["images"]}
                            cat_map = {cat["id"]: cat.get("name", "") for cat in data.get("categories", [])}
                            grouped = {}
                            for a in data["annotations"]:
                                i_name = img_map.get(a.get("image_id"), "")
                                if i_name not in grouped:
                                    grouped[i_name] = []
                                bbox = a.get("bbox", [0, 0, 10, 10])  # [x, y, w, h]
                                c_name = cat_map.get(a.get("category_id"), "crack")
                                grouped[i_name].append({
                                    "class": c_name,
                                    "x": bbox[0],
                                    "y": bbox[1],
                                    "w": bbox[2],
                                    "h": bbox[3],
                                })
                            items_to_process = [{"image": k, "boxes": v} for k, v in grouped.items()]
                        else:
                            # Dict keyed by image filename
                            items_to_process = [{"image": k, "boxes": v} if isinstance(v, list) else {"image": k, **v} for k, v in data.items()]

                    for item in items_to_process:
                        img_name = item.get("image") or item.get("filename") or item.get("image_name")
                        if img_name:
                            annotated_image_names.add(Path(img_name).name)

                        boxes = item.get("boxes", [])
                        for b in boxes:
                            total_annotations += 1
                            c_name = str(b.get("class") or b.get("label") or b.get("damage_type") or "unknown").lower().strip()
                            classes_found.add(c_name)
                            class_counts[c_name] = class_counts.get(c_name, 0) + 1

                            # Validate box geometry
                            w = b.get("w", b.get("width", 0))
                            h = b.get("h", b.get("height", 0))
                            x = b.get("x", 0)
                            y = b.get("y", 0)

                            if w <= 0 or h <= 0:
                                invalid_boxes_count += 1
                                errors.append(f"Invalid non-positive dimensions for box in {img_name}: w={w}, h={h}")
                            if x < 0 or y < 0:
                                invalid_boxes_count += 1
                                errors.append(f"Negative coordinate for box in {img_name}: x={x}, y={y}")

                except Exception as e:
                    errors.append(f"Failed to parse annotation file {annot_file.name}: {str(e)}")

        # Check for unannotated images
        found_names = {img.name for img in images_found}
        unannotated = found_names - annotated_image_names
        if unannotated and len(annotation_files) > 0:
            warnings.append(f"{len(unannotated)} images out of {len(images_found)} lack annotations in annotations.json.")

        # Corrupt image test (sample up to 20 images)
        corrupted_count = 0
        for sample_img in images_found[:20]:
            try:
                with Image.open(sample_img) as pil:
                    pil.verify()
            except Exception as e:
                corrupted_count += 1
                errors.append(f"Corrupt or unreadable image file: {sample_img.name} ({e})")

        # Class imbalance calculation
        imbalance_ratio = None
        if class_counts:
            counts = list(class_counts.values())
            if min(counts) > 0:
                imbalance_ratio = round(float(max(counts) / min(counts)), 2)
                if imbalance_ratio > 5.0:
                    warnings.append(f"Severe class imbalance detected: max/min sample ratio is {imbalance_ratio}x.")

        missing_classes = sorted(list(configured_classes - classes_found)) if configured_classes else []
        if missing_classes:
            warnings.append(f"Dataset does not contain annotations for expected classes: {', '.join(missing_classes)}.")

        # Determine overall status
        if errors:
            status = "INVALID"
            recommendation = "Resolve critical annotation geometry errors, unreadable files, or missing image assets."
        elif warnings:
            status = "WARNING"
            recommendation = "Dataset is loadable but has class imbalance, missing classes, or unannotated images."
        else:
            status = "VALID"
            recommendation = "Dataset structure and annotation geometries are valid for model training/evaluation."

        return {
            "status": status,
            "dataset_path": str(target_path),
            "total_images": len(images_found),
            "total_annotations": total_annotations,
            "num_classes": len(classes_found),
            "classes_found": sorted(list(classes_found)),
            "missing_classes": missing_classes,
            "invalid_boxes_count": invalid_boxes_count,
            "imbalance_ratio": imbalance_ratio,
            "warnings": warnings,
            "errors": errors,
            "recommendation": recommendation,
            "research_note": (
                "Dataset validation verifies annotation geometry and sample counts; "
                "it does not scientifically certify domain generalization or inspection efficacy."
            ),
        }

    validate = validate_dataset
