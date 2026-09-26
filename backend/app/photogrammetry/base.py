"""
Base interface and abstractions for Photogrammetry and 3D Reconstruction Engines.
Supports pluggable reconstruction pipelines (COLMAP, Open3D, and Mock/Demo fallback).
"""
import abc
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable


class PhotogrammetryEngine(abc.ABC):
    """Abstract base class for all photogrammetry reconstruction engines."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Engine name identifier (e.g. 'colmap', 'mock')."""
        pass

    @abc.abstractmethod
    def check_availability(self) -> Dict[str, Any]:
        """
        Check if the engine executable/library is installed and available.
        Returns:
            Dict containing:
                available: bool
                version: Optional[str]
                binary_path: Optional[str]
                cuda_available: bool
                details: str
        """
        pass

    @abc.abstractmethod
    def run_reconstruction(
        self,
        survey_id: str,
        image_paths: List[Path],
        workspace_dir: Path,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        dense: bool = True,
        generate_mesh: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the photogrammetric reconstruction workflow.

        Args:
            survey_id: Unique ID of the survey.
            image_paths: List of absolute paths to survey images.
            workspace_dir: Isolated directory where reconstruction files are stored.
            progress_callback: Optional callback fn(stage: str, percent: int, log_line: str).
            dense: Whether to run dense multi-view stereo.
            generate_mesh: Whether to reconstruct a surface mesh.

        Returns:
            Dictionary with reconstruction artifacts, metrics, and logs.
        """
        pass
