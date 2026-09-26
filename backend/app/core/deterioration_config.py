"""
Configurable Deterioration Classes & Defect Registry.
Manages the taxonomy of physical deterioration types for cultural heritage sites.
Supports adding, disabling, renaming, and persisting defect classes
without hard-coding assumptions that all sites share identical deterioration patterns.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings

CONFIG_FILE = settings.DATA_DIR / "config" / "deterioration_classes.json"

DEFAULT_DETERIORATION_CLASSES: List[Dict[str, Any]] = [
    {
        "id": "crack",
        "name": "Structural & Surface Cracking",
        "description": "Linear fractures, fissures, or joint separations in stone masonry, brick, or mortar.",
        "color": "#ef4444",
        "enabled": True,
        "is_default": True,
        "severity_weight": 0.85,
    },
    {
        "id": "erosion",
        "name": "Erosion / Material Loss",
        "description": "Surface recession, granular disintegration, flaking, or powdering of masonry substrates.",
        "color": "#f97316",
        "enabled": True,
        "is_default": True,
        "severity_weight": 0.70,
    },
    {
        "id": "spalling",
        "name": "Spalling / Flaking",
        "description": "Detachment of surface fragments or flakes resulting from thermal cycles, salt crystallization, or mechanical stress.",
        "color": "#eab308",
        "enabled": True,
        "is_default": True,
        "severity_weight": 0.80,
    },
    {
        "id": "discoloration",
        "name": "Discoloration / Staining",
        "description": "Chromatic shifts, efflorescence salt deposits, atmospheric soot, or moisture capillary damp.",
        "color": "#8b5cf6",
        "enabled": True,
        "is_default": True,
        "severity_weight": 0.40,
    },
    {
        "id": "biological_growth",
        "name": "Biological Growth",
        "description": "Colonization by lichen, moss, algae, micro-vegetation, or microbial biofilm.",
        "color": "#10b981",
        "enabled": True,
        "is_default": True,
        "severity_weight": 0.50,
    },
]


def _ensure_config_dir():
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_deterioration_classes(include_disabled: bool = True) -> List[Dict[str, Any]]:
    """Loads configured deterioration classes from disk or returns default set."""
    _ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                classes = json.load(f)
                if isinstance(classes, list) and len(classes) > 0:
                    if not include_disabled:
                        return [c for c in classes if c.get("enabled", True)]
                    return classes
        except Exception:
            pass

    # Save defaults if not present
    save_deterioration_classes(DEFAULT_DETERIORATION_CLASSES)
    if not include_disabled:
        return [c for c in DEFAULT_DETERIORATION_CLASSES if c.get("enabled", True)]
    return list(DEFAULT_DETERIORATION_CLASSES)


def save_deterioration_classes(classes: List[Dict[str, Any]]) -> None:
    """Persists deterioration class definitions to disk."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(classes, f, indent=2)


def get_enabled_deterioration_classes() -> List[Dict[str, Any]]:
    """Returns only currently enabled deterioration classes."""
    return load_deterioration_classes(include_disabled=False)


def get_deterioration_class_by_id(class_id: str) -> Optional[Dict[str, Any]]:
    """Looks up a deterioration class by its identifier."""
    classes = load_deterioration_classes(include_disabled=True)
    clean_id = class_id.lower().strip()
    for c in classes:
        if c["id"].lower() == clean_id:
            return c
    return None


def add_deterioration_class(
    class_id_or_data: Any,
    name: Optional[str] = None,
    description: str = "",
    color: str = "#ef4444",
    severity_weight: float = 0.5,
) -> Dict[str, Any]:
    """Adds a new deterioration class to the registry. Supports dict or kwargs."""
    if isinstance(class_id_or_data, dict):
        clean_id = class_id_or_data["id"].lower().strip().replace(" ", "_")
        name_val = class_id_or_data.get("name", clean_id.capitalize()).strip()
        desc_val = class_id_or_data.get("description", "").strip()
        color_val = class_id_or_data.get("color", "#ef4444")
        sev_val = float(class_id_or_data.get("severity_weight", 0.5))
    else:
        clean_id = str(class_id_or_data).lower().strip().replace(" ", "_")
        name_val = (name or clean_id.capitalize()).strip()
        desc_val = description.strip()
        color_val = color
        sev_val = float(severity_weight)

    classes = load_deterioration_classes(include_disabled=True)
    if any(c["id"] == clean_id for c in classes):
        raise ValueError(f"Deterioration class with ID '{clean_id}' already exists.")

    new_class = {
        "id": clean_id,
        "name": name_val,
        "description": desc_val,
        "color": color_val,
        "enabled": True,
        "is_default": False,
        "severity_weight": sev_val,
    }
    classes.append(new_class)
    save_deterioration_classes(classes)
    return new_class


def update_deterioration_class(
    class_id: str,
    data_or_name: Any = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    enabled: Optional[bool] = None,
    severity_weight: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Updates an existing deterioration class. Supports dict or kwargs."""
    clean_id = class_id.lower().strip()
    classes = load_deterioration_classes(include_disabled=True)
    target = None
    for c in classes:
        if c["id"].lower() == clean_id:
            target = c
            break

    if not target:
        return None

    if isinstance(data_or_name, dict):
        if "name" in data_or_name and data_or_name["name"] is not None:
            target["name"] = str(data_or_name["name"]).strip()
        if "description" in data_or_name and data_or_name["description"] is not None:
            target["description"] = str(data_or_name["description"]).strip()
        if "color" in data_or_name and data_or_name["color"] is not None:
            target["color"] = str(data_or_name["color"])
        if "enabled" in data_or_name and data_or_name["enabled"] is not None:
            target["enabled"] = bool(data_or_name["enabled"])
        if "severity_weight" in data_or_name and data_or_name["severity_weight"] is not None:
            target["severity_weight"] = float(data_or_name["severity_weight"])
    else:
        if data_or_name is not None:
            target["name"] = str(data_or_name).strip()
        if description is not None:
            target["description"] = str(description).strip()
        if color is not None:
            target["color"] = str(color)
        if enabled is not None:
            target["enabled"] = bool(enabled)
        if severity_weight is not None:
            target["severity_weight"] = float(severity_weight)

    save_deterioration_classes(classes)
    return target


def reset_deterioration_classes() -> List[Dict[str, Any]]:
    """Resets the deterioration class registry to initial default set."""
    save_deterioration_classes(DEFAULT_DETERIORATION_CLASSES)
    return list(DEFAULT_DETERIORATION_CLASSES)
