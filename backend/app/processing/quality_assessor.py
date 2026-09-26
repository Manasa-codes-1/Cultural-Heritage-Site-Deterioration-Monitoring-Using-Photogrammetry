from pathlib import Path
from typing import Dict, Any, Tuple
import cv2
import numpy as np
from app.core.config import settings


class ImageQualityAssessor:
    """
    OpenCV-based Image Quality Assessment Module for Photogrammetric Heritage Surveys.
    
    Checks:
    - Validity: Image file readability and dimension integrity
    - Blur: Variance of the Laplacian operator
    - Resolution: Minimum dimension check for SfM feature resolution
    - Brightness / Exposure: Histogram & mean luminosity analysis
    - Photogrammetric Suitability: Keypoint density estimation via ORB
    
    Note: The composite quality score is a configurable heuristic designed for 
    pre-filtering acquisition defects and is not claimed to be an internationally 
    certified optical standard.
    """

    def __init__(
        self,
        blur_threshold: float = settings.QUALITY_BLUR_THRESHOLD,
        min_width: int = settings.QUALITY_MIN_WIDTH,
        min_height: int = settings.QUALITY_MIN_HEIGHT,
        underexposure_thresh: float = settings.QUALITY_UNDEREXPOSURE_THRESHOLD,
        overexposure_thresh: float = settings.QUALITY_OVEREXPOSURE_THRESHOLD,
        min_features: int = settings.QUALITY_MIN_FEATURES,
    ):
        self.blur_threshold = blur_threshold
        self.min_width = min_width
        self.min_height = min_height
        self.underexposure_thresh = underexposure_thresh
        self.overexposure_thresh = overexposure_thresh
        self.min_features = min_features

    def assess_file(self, file_path: Path) -> Dict[str, Any]:
        """Reads an image from disk and runs quality checks."""
        if not file_path.exists():
            return {
                "valid": False,
                "error": f"File does not exist: {file_path}",
                "quality_score": 0.0,
                "quality_status": "fail",
                "overall_recommendation": "File missing on storage; re-upload required.",
            }

        # Read using OpenCV
        img = cv2.imread(str(file_path))
        if img is None:
            return {
                "valid": False,
                "error": "Failed to decode image with OpenCV (unsupported format or corrupted data).",
                "quality_score": 0.0,
                "quality_status": "fail",
                "overall_recommendation": "Corrupted or non-standard image file; re-export and re-upload.",
            }

        return self.assess_array(img)

    def assess_array(self, img: np.ndarray) -> Dict[str, Any]:
        """Performs assessment directly on a BGR NumPy image array."""
        h, w = img.shape[:2]
        channels = img.shape[2] if len(img.shape) > 2 else 1

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if channels > 1 else img

        # 1. Blur evaluation (Variance of Laplacian)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blur_pass = laplacian_var >= self.blur_threshold
        blur_status = "pass" if blur_pass else "fail"
        blur_rec = (
            "Sharpness adequate for photogrammetric feature tracking."
            if blur_pass
            else f"Significant blur detected (variance {laplacian_var:.1f} < {self.blur_threshold}). Recapture with steady support or faster shutter."
        )

        # 2. Resolution evaluation
        res_pass = (w >= self.min_width) and (h >= self.min_height)
        res_status = "pass" if res_pass else "fail"
        res_rec = (
            f"Resolution {w}x{h} meets minimum photogrammetric requirements ({self.min_width}x{self.min_height})."
            if res_pass
            else f"Resolution {w}x{h} is below minimum ({self.min_width}x{self.min_height}); fine surface cracks may be lost."
        )

        # 3. Brightness / Exposure evaluation
        mean_brightness = float(np.mean(gray))
        if mean_brightness < self.underexposure_thresh:
            bright_status = "fail"
            bright_rec = f"Underexposed (mean brightness {mean_brightness:.1f} < {self.underexposure_thresh}). Increase exposure or ambient lighting."
        elif mean_brightness > self.overexposure_thresh:
            bright_status = "fail"
            bright_rec = f"Overexposed (mean brightness {mean_brightness:.1f} > {self.overexposure_thresh}). Decrease exposure to recover highlight detail."
        else:
            bright_status = "pass"
            bright_rec = f"Balanced exposure (mean brightness {mean_brightness:.1f} in acceptable range [{self.underexposure_thresh}, {self.overexposure_thresh}])."

        # 4. Feature point density (ORB detector)
        try:
            orb = cv2.ORB_create(nfeatures=1500)
            keypoints = orb.detect(gray, None)
            feature_count = len(keypoints)
        except Exception:
            feature_count = 0

        feat_pass = feature_count >= self.min_features
        feat_status = "pass" if feat_pass else "warning"
        feat_rec = (
            f"Adequate texture: {feature_count} keypoints detected."
            if feat_pass
            else f"Low feature count ({feature_count} < {self.min_features}). Homogeneous surface or poor focus may impede SfM matching."
        )

        # 5. Composite Quality Score Calculation (0 - 100)
        # Weights: Blur (35%), Brightness (25%), Resolution (20%), Features (20%)
        # Blur subscore: normalized using sigmoid-like clipping
        blur_subscore = min(100.0, (laplacian_var / max(self.blur_threshold * 1.5, 1.0)) * 100.0)

        # Brightness subscore: ideal is midpoint ~128
        ideal_lum = (self.underexposure_thresh + self.overexposure_thresh) / 2.0
        lum_diff = abs(mean_brightness - ideal_lum)
        max_diff = (self.overexposure_thresh - self.underexposure_thresh) / 2.0
        bright_subscore = max(0.0, 100.0 - (lum_diff / max(max_diff, 1.0)) * 100.0)

        # Resolution subscore
        res_subscore = 100.0 if res_pass else (min(w / self.min_width, h / self.min_height) * 80.0)

        # Feature subscore
        feat_subscore = min(100.0, (feature_count / max(self.min_features, 1)) * 100.0)

        composite_score = round(
            0.35 * blur_subscore + 0.25 * bright_subscore + 0.20 * res_subscore + 0.20 * feat_subscore,
            1,
        )

        # Overall Status
        if composite_score >= 70.0 and blur_pass and bright_status == "pass":
            overall_status = "pass"
            overall_rec = "Image approved for photogrammetric reconstruction."
        elif composite_score >= 50.0:
            overall_status = "warning"
            overall_rec = "Acceptable with minor degradation; consider supplementing with adjacent angles."
        else:
            overall_status = "fail"
            overall_rec = "Recapture recommended due to blur, low exposure, or inadequate resolution."

        return {
            "valid": True,
            "width": w,
            "height": h,
            "channels": channels,
            "quality_score": composite_score,
            "quality_status": overall_status,
            "overall_recommendation": overall_rec,
            "blur": {
                "score": round(laplacian_var, 2),
                "status": blur_status,
                "threshold": self.blur_threshold,
                "recommendation": blur_rec,
            },
            "brightness": {
                "score": round(mean_brightness, 2),
                "status": bright_status,
                "recommendation": bright_rec,
            },
            "resolution": {
                "width": w,
                "height": h,
                "status": res_status,
                "recommendation": res_rec,
            },
            "features": {
                "count": feature_count,
                "status": feat_status,
                "recommendation": feat_rec,
            },
        }


# Global default instance
quality_assessor = ImageQualityAssessor()
