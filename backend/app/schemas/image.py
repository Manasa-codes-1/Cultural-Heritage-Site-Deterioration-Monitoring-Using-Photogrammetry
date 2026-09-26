from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class QualityBreakdown(BaseModel):
    blur_score: float
    blur_status: str
    blur_recommendation: Optional[str] = None
    brightness_score: float
    brightness_status: str
    brightness_recommendation: Optional[str] = None
    resolution_status: str
    resolution_recommendation: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    estimated_features: Optional[int] = None
    overall_recommendation: Optional[str] = None


class ImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    survey_id: str
    filename: str
    file_size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    channels: Optional[int] = 3
    quality_score: Optional[float] = None
    quality_status: Optional[str] = "pending"
    blur_score: Optional[float] = None
    blur_status: Optional[str] = None
    brightness_score: Optional[float] = None
    brightness_status: Optional[str] = None
    resolution_status: Optional[str] = None
    feature_count: Optional[int] = None
    quality_details: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    captured_at: Optional[datetime] = None
    created_at: datetime


class ImageUploadResponse(BaseModel):
    uploaded_images: List[ImageRead]
    failed_images: List[Dict[str, str]]
    total_uploaded: int
    total_failed: int
