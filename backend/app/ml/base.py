"""
Base interface and abstractions for Heritage Material Classification models.
Decouples inference pipelines from specific ML framework backends.
"""
import abc
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image


class MaterialClassifier(abc.ABC):
    """Abstract base class defining the contract for all material classifiers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Identifier name of the classifier."""
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Version identifier string."""
        pass

    @property
    @abc.abstractmethod
    def is_demo(self) -> bool:
        """Whether this classifier operates in synthetic demo mode."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check whether required libraries and model weights are accessible."""
        pass

    @abc.abstractmethod
    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """Loads weights from disk or initializes architecture."""
        pass

    @abc.abstractmethod
    def get_classes(self) -> List[Dict[str, Any]]:
        """Returns the list of material class definitions supported by the model."""
        pass

    @abc.abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Returns provenance metadata: architecture, training date, parameters,
        and evaluation status.
        """
        pass

    @abc.abstractmethod
    def predict(
        self,
        image: Union[np.ndarray, Image.Image, Path, str],
        region: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Performs material classification on a full image or cropped region.

        Args:
            image: Image data as NumPy array (RGB/BGR), PIL Image, or file path.
            region: Optional crop bounding box: {'x': int, 'y': int, 'w': int, 'h': int}.

        Returns:
            Dictionary matching MaterialPredictionResponse schema:
                material: str
                confidence: float (0.0 to 1.0)
                status: 'CONFIDENT' or 'LOW_CONFIDENCE'
                recommendation: Optional[str]
                top_k: List[Dict[str, Any]]
                model_name: str
                model_version: str
                inference_mode: str ('real_trained' or 'demo')
                is_demo: bool
                region: Optional[Dict[str, Any]]
                disclaimer: str
        """
        pass

    @abc.abstractmethod
    def predict_batch(
        self,
        images: List[Union[np.ndarray, Image.Image, Path, str]],
        regions: Optional[List[Optional[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """Performs batch prediction over a collection of images/crops."""
        pass
