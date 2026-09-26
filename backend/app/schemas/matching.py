from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class PairMatchRequest(BaseModel):
    image_a_id: str = Field(..., description="UUID of first image")
    image_b_id: str = Field(..., description="UUID of second image")


class PairMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[str] = None
    survey_id: Optional[str] = None
    image_a_id: str
    image_b_id: str
    image_a_filename: Optional[str] = None
    image_b_filename: Optional[str] = None
    keypoints_a: int
    keypoints_b: int
    candidate_matches: int
    good_matches: int
    match_ratio: float
    estimated_overlap: str
    status: str  # GOOD, WARNING, POOR, INSUFFICIENT_FEATURES
    recommendation: Optional[str] = None
    algorithm: str = "ORB + BFMatcher(Hamming) + LoweRatio(0.75)"
    created_at: Optional[datetime] = None


class ConnectivityNode(BaseModel):
    id: str
    filename: str
    degree: int  # Number of valid edges with 'GOOD' status
    status: str  # 'well_connected', 'weakly_connected', 'isolated'


class ConnectivityEdge(BaseModel):
    source: str
    target: str
    good_matches: int
    match_ratio: float
    status: str


class SurveyReadinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    survey_id: str
    images_analyzed: int
    pairs_analyzed: int
    good_pairs: int
    warning_pairs: int
    poor_pairs: int
    average_good_matches: float
    readiness_status: str  # READY, READY_WITH_WARNINGS, INSUFFICIENT_IMAGE_CONNECTIVITY, RECAPTURE_REQUIRED
    isolated_image_ids: List[str] = []
    weakly_connected_image_ids: List[str] = []
    connectivity_nodes: List[ConnectivityNode] = []
    connectivity_edges: List[ConnectivityEdge] = []
    recommendations: List[str] = []
    is_heuristic: bool = True
    updated_at: Optional[datetime] = None
