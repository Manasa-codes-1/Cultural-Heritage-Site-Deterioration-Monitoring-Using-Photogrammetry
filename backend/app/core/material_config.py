"""
Configurable Material Classes & Substrate Registry.
Manages the taxonomy of construction materials for heritage sites.
Supports adding, disabling, renaming, and persisting material classes
without hard-coding assumptions that all sites share identical materials.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings

CONFIG_FILE = settings.DATA_DIR / "config" / "material_classes.json"

DEFAULT_MATERIAL_CLASSES: List[Dict[str, Any]] = [
    {
        "id": "sandstone",
        "name": "Sandstone / Stone",
        "description": "Sedimentary sandstone or natural dressed stone masonry blocks.",
        "color": "#d97706",
        "enabled": True,
        "is_default": True,
    },
    {
        "id": "granite",
        "name": "Granite",
        "description": "Coarse-grained igneous crystalline stone with high hardness and quartz content.",
        "color": "#64748b",
        "enabled": True,
        "is_default": True,
    },
    {
        "id": "brick",
        "name": "Fired Clay Brick",
        "description": "Historic kiln-fired or sun-dried clay ceramic masonry units.",
        "color": "#dc2626",
        "enabled": True,
        "is_default": True,
    },
    {
        "id": "lime_mortar",
        "name": "Lime Mortar",
        "description": "Non-hydraulic or hydraulic lime-sand joint bedding and pointing mortar.",
        "color": "#cbd5e1",
        "enabled": True,
        "is_default": True,
    },
    {
        "id": "other",
        "name": "Other / Unspecified Substrate",
        "description": "Plaster, timber, metal fixings, or unidentified building substrate.",
        "color": "#a855f7",
        "enabled": True,
        "is_default": True,
    },
]


def _ensure_config_dir():
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_material_classes(include_disabled: bool = True) -> List[Dict[str, Any]]:
    """Loads configured material classes from disk or returns default set."""
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
    save_material_classes(DEFAULT_MATERIAL_CLASSES)
    if not include_disabled:
        return [c for c in DEFAULT_MATERIAL_CLASSES if c.get("enabled", True)]
    return list(DEFAULT_MATERIAL_CLASSES)


def save_material_classes(classes: List[Dict[str, Any]]) -> None:
    """Persists material class definitions to disk."""
    _ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(classes, f, indent=2)


def get_material_class_by_id(class_id: str) -> Optional[Dict[str, Any]]:
    """Looks up a material class by its identifier."""
    classes = load_material_classes(include_disabled=True)
    clean_id = class_id.lower().strip()
    for c in classes:
        if c["id"].lower() == clean_id:
            return c
    return None


def get_enabled_classes() -> List[Dict[str, Any]]:
    """Returns only currently enabled material classes."""
    return load_material_classes(include_disabled=False)


def add_material_class(
    class_id_or_data: Any,
    name: Optional[str] = None,
    description: str = "",
    color: str = "#38bdf8",
) -> Dict[str, Any]:
    """Adds a new material class to the registry. Supports dict or kwargs."""
    if isinstance(class_id_or_data, dict):
        clean_id = class_id_or_data["id"].lower().strip().replace(" ", "_")
        name_val = class_id_or_data.get("name", clean_id.capitalize()).strip()
        desc_val = class_id_or_data.get("description", "").strip()
        color_val = class_id_or_data.get("color", "#38bdf8")
    else:
        clean_id = str(class_id_or_data).lower().strip().replace(" ", "_")
        name_val = (name or clean_id.capitalize()).strip()
        desc_val = description.strip()
        color_val = color

    classes = load_material_classes(include_disabled=True)
    if any(c["id"] == clean_id for c in classes):
        raise ValueError(f"Material class with ID '{clean_id}' already exists.")

    new_class = {
        "id": clean_id,
        "name": name_val,
        "description": desc_val,
        "color": color_val,
        "enabled": True,
        "is_default": False,
    }
    classes.append(new_class)
    save_material_classes(classes)
    return new_class


def update_material_class(
    class_id: str,
    data_or_name: Any = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Updates an existing material class. Supports dict or kwargs."""
    clean_id = class_id.lower().strip()
    classes = load_material_classes(include_disabled=True)
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
    else:
        if data_or_name is not None:
            target["name"] = str(data_or_name).strip()
        if description is not None:
            target["description"] = str(description).strip()
        if color is not None:
            target["color"] = str(color)
        if enabled is not None:
            target["enabled"] = bool(enabled)

    save_material_classes(classes)
    return target


def reset_material_classes() -> List[Dict[str, Any]]:
    """Resets the material class registry to initial default set."""
    save_material_classes(DEFAULT_MATERIAL_CLASSES)
    return list(DEFAULT_MATERIAL_CLASSES)

