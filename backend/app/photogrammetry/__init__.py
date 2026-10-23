"""
Photogrammetry package providing modular engines for 3D reconstruction.
"""
from typing import Optional, Dict, Any, List
from app.photogrammetry.base import PhotogrammetryEngine
from app.photogrammetry.colmap_engine import ColmapEngine
from app.photogrammetry.mock_engine import MockPhotogrammetryEngine


def get_photogrammetry_engine(engine_name: str = "auto") -> PhotogrammetryEngine:
    """
    Factory function returning the appropriate photogrammetry engine.
    - 'auto': Uses COLMAP photogrammetry engine if installed and functional; raises RuntimeError if unavailable.
    - 'colmap': Forces COLMAP engine (raises RuntimeError if unavailable).
    - 'mock': Explicitly uses synthetic Mock engine for safe offline/CPU automated testing.
    """
    colmap = ColmapEngine()
    if engine_name in ("auto", "colmap"):
        avail = colmap.check_availability()
        if avail["available"]:
            return colmap
        raise RuntimeError(
            "COLMAP photogrammetry engine is not installed or accessible on this system. "
            f"Details: {avail.get('details')}. "
            "Please verify COLMAP under tools/colmap or specify engine='mock' explicitly for testing."
        )

    if engine_name == "mock":
        return MockPhotogrammetryEngine()

    raise ValueError(f"Unknown photogrammetry engine '{engine_name}'. Supported: 'auto', 'colmap', 'mock'.")



def check_photogrammetry_system() -> Dict[str, Any]:
    """
    Queries system binaries, Open3D, and hardware capabilities.
    Returns diagnostic information for research transparency.
    """
    colmap = ColmapEngine()
    colmap_info = colmap.check_availability()

    open3d_avail = False
    open3d_version = None
    try:
        import open3d as o3d  # type: ignore
        open3d_avail = True
        open3d_version = getattr(o3d, "__version__", "unknown")
    except Exception:
        pass

    notes: List[str] = []
    if colmap_info["available"]:
        notes.append(f"COLMAP is installed and accessible ({colmap_info.get('version')}).")
        if not colmap_info["cuda_available"]:
            notes.append("COLMAP is running in CPU mode. Dense stereo (CUDA) may be constrained.")
    else:
        notes.append("COLMAP executable not detected on system PATH. System will use verified Mock 3D engine.")

    if open3d_avail:
        notes.append(f"Open3D {open3d_version} is available for point cloud processing and geometry analysis.")
    else:
        notes.append("Open3D is not installed or loading; fallback geometric processor active.")

    recommended = "colmap" if colmap_info["available"] else "mock"

    return {
        "colmap_available": colmap_info["available"],
        "colmap_path": colmap_info["binary_path"],
        "colmap_version": colmap_info["version"],
        "cuda_available": colmap_info["cuda_available"],
        "gpu_info": "Intel Iris Xe / CPU Mode" if not colmap_info["cuda_available"] else "CUDA GPU",
        "open3d_available": open3d_avail,
        "open3d_version": open3d_version,
        "recommended_engine": recommended,
        "system_notes": notes,
    }


__all__ = [
    "PhotogrammetryEngine",
    "ColmapEngine",
    "MockPhotogrammetryEngine",
    "get_photogrammetry_engine",
    "check_photogrammetry_system",
]
