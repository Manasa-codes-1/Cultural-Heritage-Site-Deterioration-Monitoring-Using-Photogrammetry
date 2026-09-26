import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the repository (parent of backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Project metadata
    PROJECT_NAME: str = "Cultural Heritage Deterioration Monitoring"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/heritage_monitoring.db"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

    # File Storage Paths (always anchored to project root)
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "surveys"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    REPORTS_DIR: Path = BASE_DIR / "outputs" / "reports"
    MODELS_DIR: Path = BASE_DIR / "models"

    # Photogrammetry Settings
    COLMAP_PATH: str = "colmap"
    USE_MOCK_PHOTOGRAMMETRY: bool = True

    # ML Inference Settings
    USE_MOCK_ML: bool = True
    MODEL_DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.60
    DETERIORATION_CONFIDENCE_THRESHOLD: float = 0.60

    # Phase 6: 2D-to-3D Damage Mapping Settings
    REPROJECTION_ERROR_MAX_PX: float = 5.0  # Max allowable reprojection error in pixels
    SURFACE_RAYCAST_TOLERANCE: float = 0.05  # Point cloud nearest-neighbour proximity threshold (local units)
    DEFAULT_MAPPING_SAMPLING: str = "CENTER_ONLY"  # "CENTER_ONLY", "BOX_GRID", "POLYGON_VERTICES", "MASK_SAMPLES"
    RECONSTRUCTION_DEFAULT_SCALE_STATUS: str = "LOCAL"  # "LOCAL", "METRIC", "UNKNOWN"

    # Phase 7: Multi-Temporal Monitoring & Change Detection Settings
    ICP_MAX_CORRESPONDENCE_DISTANCE: float = 0.08  # Max distance for ICP point correspondences
    ICP_MAX_ITERATIONS: int = 50  # Max iterations for registration convergence
    ICP_RELATIVE_FITNESS: float = 1e-6
    ICP_RELATIVE_RMSE: float = 1e-6
    ICP_FITNESS_MIN_ACCEPTABLE: float = 0.60  # Minimum fitness below which ALIGNMENT_REQUIRES_REVIEW is assigned
    ICP_VOXEL_SIZE: float = 0.02  # Voxel size for downsampling during registration
    TEMPORAL_CHANGE_THRESHOLD: float = 0.02  # Distance threshold for GEOMETRIC_CHANGE_CANDIDATE
    DAMAGE_MATCHING_DISTANCE_THRESHOLD: float = 0.15  # 3D spatial radius for matching damage instances across surveys


    # Image Quality Assessment Thresholds (OpenCV)
    QUALITY_BLUR_THRESHOLD: float = 100.0  # Variance of Laplacian
    QUALITY_MIN_WIDTH: int = 800
    QUALITY_MIN_HEIGHT: int = 600
    QUALITY_UNDEREXPOSURE_THRESHOLD: float = 40.0  # Mean grayscale brightness lower bound
    QUALITY_OVEREXPOSURE_THRESHOLD: float = 220.0  # Mean grayscale brightness upper bound
    QUALITY_MIN_FEATURES: int = 300  # SIFT / ORB estimated keypoint count for photogrammetry suitability

    # Phase 2: Feature Matching & Photogrammetric Collection Readiness Settings
    MATCHING_MAX_FEATURES: int = 1500  # Number of ORB keypoints to extract
    MATCHING_RATIO_THRESH: float = 0.75  # Lowe's ratio test threshold (m.distance < ratio * n.distance)
    MATCHING_MIN_GOOD_MATCHES: int = 30  # Threshold for "GOOD" pair status
    MATCHING_WARN_GOOD_MATCHES: int = 15  # Threshold below which a pair is "POOR"
    MATCHING_MIN_KEYPOINTS: int = 100  # Threshold below which an image has insufficient features
    MATCHING_MAX_PAIRS_PER_SURVEY: int = 60  # Upper bound for pairwise comparisons on CPU
    MATCHING_IMAGE_MAX_DIM: int = 1280  # Max dimension for fast feature extraction

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Union[str, None]) -> str:
        if isinstance(v, str):
            return v
        return f"sqlite:///{BASE_DIR}/heritage_monitoring.db"

settings = Settings()

# Ensure directories exist
for folder in [
    settings.DATA_DIR,
    settings.UPLOAD_DIR,
    settings.PROCESSED_DIR,
    settings.OUTPUTS_DIR,
    settings.REPORTS_DIR,
    settings.MODELS_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)
