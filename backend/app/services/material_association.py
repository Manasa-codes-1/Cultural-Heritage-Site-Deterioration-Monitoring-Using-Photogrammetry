"""
Material-Damage Association Service.
Associates physical deterioration detections with construction substrates (Phase 4),
supporting spatial bounding box overlap, multi-material candidate ambiguity,
and honest fallback to 'UNKNOWN' when material data is unavailable.

STRICT RESEARCH INTEGRITY:
- Never invents material labels.
- If no material detection is found, marks 'UNKNOWN' and 'MATERIAL_ASSOCIATION_UNAVAILABLE'.
- Accurately tracks overlapping material boundaries with coverage ratios.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def compute_intersection_over_min(box_a: Dict[str, Any], box_b: Dict[str, Any]) -> Tuple[float, float]:
    """
    Computes intersection coverage ratio and IoU between two bounding boxes:
    box = {'x': int, 'y': int, 'w': int, 'h': int}

    Returns:
        (coverage_of_a, iou):
            coverage_of_a = intersection_area / area_a
            iou = intersection_area / union_area
    """
    ax1, ay1 = box_a.get("x", 0), box_a.get("y", 0)
    ax2, ay2 = ax1 + max(1, box_a.get("w", 1)), ay1 + max(1, box_a.get("h", 1))

    bx1, by1 = box_b.get("x", 0), box_b.get("y", 0)
    bx2, by2 = bx1 + max(1, box_b.get("w", 1)), by1 + max(1, box_b.get("h", 1))

    # Overlap rectangle
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0, 0.0

    inter_area = float((ix2 - ix1) * (iy2 - iy1))
    area_a = float((ax2 - ax1) * (ay2 - ay1))
    area_b = float((bx2 - bx1) * (by2 - by1))
    union_area = area_a + area_b - inter_area

    coverage = inter_area / area_a if area_a > 0 else 0.0
    iou = inter_area / union_area if union_area > 0 else 0.0

    return round(coverage, 4), round(iou, 4)


def associate_deterioration_with_materials(
    det_box: Optional[Dict[str, Any]],
    material_detections: List[Any],
) -> Dict[str, Any]:
    """
    Determines substrate material association for a deterioration defect.

    Args:
        det_box: Deterioration bounding box: {'x': int, 'y': int, 'w': int, 'h': int} or None.
        material_detections: List of MaterialDetection ORM records for the image.

    Returns:
        Dict containing:
            material_class: str ("brick", "sandstone", or "UNKNOWN")
            material_confidence: Optional[float]
            material_association_status: str ("ASSOCIATED", "OVERLAPPING_MULTIPLE", "MATERIAL_ASSOCIATION_UNAVAILABLE")
            candidate_materials: List[Dict[str, Any]]
            material_id: Optional[str]
            notes: Optional[str]
    """
    if not material_detections:
        return {
            "material_class": "UNKNOWN",
            "material_confidence": None,
            "material_association_status": "MATERIAL_ASSOCIATION_UNAVAILABLE",
            "candidate_materials": [],
            "material_id": None,
            "notes": "No material classification exists for this image."
        }

    # Separate region-based material crops from full-image material detections
    region_materials = [m for m in material_detections if getattr(m, "bounding_box", None) is not None]
    full_image_materials = [m for m in material_detections if getattr(m, "bounding_box", None) is None]

    # Strategy A: Deterioration has a bounding box and there are spatial material regions
    if det_box and region_materials:
        candidates = []
        for mat in region_materials:
            coverage, iou = compute_intersection_over_min(det_box, mat.bounding_box)
            if coverage > 0.05 or iou > 0.05:
                candidates.append({
                    "material_id": str(mat.id),
                    "material": str(mat.material_class),
                    "coverage_ratio": coverage,
                    "iou": iou,
                    "confidence": float(mat.confidence) if mat.confidence is not None else None,
                })

        # Sort candidates by coverage descending
        candidates.sort(key=lambda c: (c["coverage_ratio"], c["iou"]), reverse=True)

        if len(candidates) == 1:
            best = candidates[0]
            return {
                "material_class": best["material"],
                "material_confidence": best["confidence"],
                "material_association_status": "ASSOCIATED",
                "candidate_materials": candidates,
                "material_id": best["material_id"],
                "notes": f"Spatial overlap of {best['coverage_ratio']*100:.1f}% with substrate boundary."
            }
        elif len(candidates) > 1:
            best = candidates[0]
            return {
                "material_class": best["material"],
                "material_confidence": best["confidence"],
                "material_association_status": "OVERLAPPING_MULTIPLE",
                "candidate_materials": candidates,
                "material_id": best["material_id"],
                "notes": f"Overlaps {len(candidates)} substrates; primary is {best['material']} ({best['coverage_ratio']*100:.1f}% coverage)."
            }

    # Strategy B: Fallback to full-image substrate classification
    if full_image_materials:
        primary_mat = full_image_materials[0]
        return {
            "material_class": str(primary_mat.material_class),
            "material_confidence": float(primary_mat.confidence) if primary_mat.confidence is not None else None,
            "material_association_status": "ASSOCIATED",
            "candidate_materials": [{
                "material_id": str(primary_mat.id),
                "material": str(primary_mat.material_class),
                "coverage_ratio": 1.0,
                "iou": 1.0,
                "confidence": float(primary_mat.confidence) if primary_mat.confidence is not None else None,
            }],
            "material_id": str(primary_mat.id),
            "notes": "Associated via image-level substrate classification."
        }

    # Strategy C: No association possible
    return {
        "material_class": "UNKNOWN",
        "material_confidence": None,
        "material_association_status": "MATERIAL_ASSOCIATION_UNAVAILABLE",
        "candidate_materials": [],
        "material_id": None,
        "notes": "Deterioration does not spatially intersect any classified substrate boundary."
    }
