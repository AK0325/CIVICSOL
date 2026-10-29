from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# CIVIC ISSUE RESPONSE
# =========================================================

class CivicIssueResponse(BaseModel):
    """
    Public representation of a civic issue.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int

    title: str
    description: str
    category: str
    severity: str

    location: str
    latitude: float
    longitude: float

    ward: Optional[str] = None

    image_path: str

    status: str
    department: Optional[str] = None

    # AI analysis
    ai_label: Optional[str] = None
    ai_confidence: Optional[float] = None

    # Priority intelligence
    priority: str
    priority_score: Optional[float] = None

    # Clustering
    cluster_id: Optional[int] = None
    report_count: int

    created_at: datetime
    updated_at: datetime


# =========================================================
# CIVIC ISSUE LIST RESPONSE
# =========================================================

class CivicIssueListResponse(BaseModel):
    """
    Response returned when multiple civic issues are requested.
    """

    total: int

    issues: list[CivicIssueResponse]


# =========================================================
# ISSUE CREATION RESPONSE
# =========================================================

class CivicIssueCreateResponse(BaseModel):
    """
    Response returned after successfully creating a civic issue.
    """

    message: str

    issue: CivicIssueResponse


# =========================================================
# HEALTH RESPONSE
# =========================================================

class HealthResponse(BaseModel):
    """
    API health-check response.
    """

    status: str


# =========================================================
# ERROR RESPONSE
# =========================================================

class ErrorResponse(BaseModel):
    """
    Standard API error response.
    """

    detail: str
