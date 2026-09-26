"""
Base interface and abstractions for Heritage Deterioration Detectors / Segmenters.
Decouples inference pipelines from specific ML framework backends.
"""
import abc
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image


class DeteriorationDetector(abc.ABC):
    """Abstract base class defining the contract for all physical defect detectors."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Identifier name of the detector."""
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Version identifier string."""
        pass

    @property
    @abc.abstractmethod
    def is_demo(self) -> bool:
        """Whether this detector operates in synthetic/heuristic demo mode."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Checks whether required libraries and model weights are accessible."""
        pass

    @abc.abstractmethod
    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """Loads weights from disk or initializes architecture."""
        pass

    @abc.abstractmethod
    def get_classes(self) -> List[Dict[str, Any]]:
        """Returns the list of deterioration class definitions supported by the model."""
        pass

    @abc.abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Returns provenance metadata: architecture, training date, parameters, and status."""
        pass

    @abc.abstractmethod
    def predict(
        self,
        image: Union[np.ndarray, Image.Image, Path, str, bytes],
        confidence_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes deterioration detection/segmentation on an image.

        Returns list of detection dictionaries:
            damage_type: str
            confidence: float (0.0 to 1.0)
            status: 'CONFIDENT' or 'LOW_CONFIDENCE'
            severity_hint: 'minor', 'moderate', 'severe'
            bounding_box: {'x': int, 'y': int, 'w': int, 'h': int}
            polygon: Optional[List[Dict[str, int]]]
            notes: Optional[str]
        """
        pass

    @abc.abstractmethod
    def predict_batch(
        self,
        images: List[Union[np.ndarray, Image.Image, Path, str, bytes]],
        confidence_threshold: Optional[float] = None,
    ) -> List[List[Dict[str, Any]]]:
        """Performs batch detection over multiple images."""
        pass
