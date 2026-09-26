from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class SiteBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Name of the cultural heritage site")
    location: str = Field(..., min_length=2, max_length=255, description="Geographical location or city")
    description: Optional[str] = Field(None, description="Architectural and historical description")
    historical_period: Optional[str] = Field(None, max_length=100, description="Era or construction century")
    primary_material: Optional[str] = Field(None, max_length=100, description="Dominant construction substrate")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    location: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    historical_period: Optional[str] = None
    primary_material: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SiteRead(SiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    survey_count: int = 0
