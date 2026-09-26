from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.image import ImageRead


class EnvironmentalInfo(BaseModel):
    temp_c: Optional[float] = Field(None, description="Ambient temperature in Celsius")
    humidity_pct: Optional[float] = Field(None, ge=0, le=100, description="Relative humidity percentage")
    rainfall_mm: Optional[float] = Field(None, ge=0, description="Recent precipitation in mm")
    uv_index: Optional[float] = Field(None, ge=0, description="UV index measurement")
    notes: Optional[str] = Field(None, description="Optional environmental observation remarks")


class SurveyBase(BaseModel):
    survey_code: str = Field(..., min_length=2, max_length=50, description="Unique survey code/tag, e.g. SRV-2026-01")
    survey_date: datetime = Field(default_factory=datetime.utcnow, description="Date and time of capture")
    description: Optional[str] = Field(None, description="Survey goals, scope, and target structures")
    operator: Optional[str] = Field(None, max_length=100, description="Surveyor or researcher name")
    camera_info: Optional[str] = Field(None, max_length=255, description="Camera body, lens, focal length")
    environmental_info: Optional[Dict[str, Any]] = Field(None, description="Optional climate & weather parameters")


class SurveyCreate(SurveyBase):
    site_id: str = Field(..., description="Target site identifier")


class SurveyUpdate(BaseModel):
    survey_code: Optional[str] = None
    survey_date: Optional[datetime] = None
    description: Optional[str] = None
    operator: Optional[str] = None
    camera_info: Optional[str] = None
    environmental_info: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class SurveyRead(SurveyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    site_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    image_count: int = 0
    average_quality_score: Optional[float] = None


class SurveyDetail(SurveyRead):
    images: List[ImageRead] = []
