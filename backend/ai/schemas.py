"""
CIVICSOL - AI Analysis Pydantic Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AIReviewDecisionRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=500, description="Optional authority review notes")
    apply_department: bool = Field(True, description="Apply suggested department on approval")
    apply_severity: bool = Field(True, description="Apply suggested severity on approval")
    apply_priority: bool = Field(True, description="Apply suggested priority on approval")


class AIFalsePositiveRequest(BaseModel):
    class_name: str = Field(..., max_length=100, description="Name of the false positive class detected")
    reason: str = Field(..., min_length=3, max_length=500, description="Authority explanation for why detection is false positive")
    bbox: Optional[List[float]] = Field(None, description="Optional bounding box coordinates flagged")


class AIDuplicateLinkRequest(BaseModel):
    primary_issue_id: int = Field(..., description="ID of primary existing civic issue")
    action: str = Field("LINK", description="Action type: LINK or MERGE")
    notes: Optional[str] = Field(None, max_length=500, description="Authority notes regarding the duplicate relationship")


class AIAnalysisItemResponse(BaseModel):
    id: int
    issue_id: int
    model_name: str
    model_version: str
    predicted_category: Optional[str] = None
    confidence_score: Optional[float] = None
    detected_objects: List[Dict[str, Any]] = []
    suggested_severity: Optional[str] = None
    suggested_priority: Optional[str] = None
    suggested_department_id: Optional[int] = None
    suggested_department_name: Optional[str] = None
    suggested_department_code: Optional[str] = None
    explanation: Optional[str] = None
    annotated_image_path: Optional[str] = None
    processing_status: str
    review_status: str = "PENDING"
    reviewed_by_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    similar_nearby_reports: List[Dict[str, Any]] = []
    analysis_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class AIAnalysisEnvelopeResponse(BaseModel):
    has_analysis: bool
    message: str
    issue_id: int
    official_values: Dict[str, Any]
    analysis: Optional[AIAnalysisItemResponse] = None
    latest_analysis: Optional[AIAnalysisItemResponse] = None


class AIAnalysisHistoryResponse(BaseModel):
    issue_id: int
    total: int
    history: List[AIAnalysisItemResponse]

