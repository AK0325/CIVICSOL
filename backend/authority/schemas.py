"""
CIVICSOL - Authority Pydantic Schemas
Defines request and response models for Authority Authentication and Administration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# =========================================================
# AUTHORITY AUTH SCHEMAS
# =========================================================

class AuthorityLoginRequest(BaseModel):
    """
    Accepts official identifier (employee_id, email, or mobile) and password.
    """
    identifier: str = Field(..., description="Employee ID, official email, or mobile number")
    password: str = Field(..., min_length=1, description="Account password")


class AuthorityLoginResponse(BaseModel):
    """
    Response returned upon successful authority login.
    """
    message: str
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    role: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    employee_id: Optional[str] = None
    designation: Optional[str] = None


class AuthorityProfileResponse(BaseModel):
    """
    Detailed profile information for the authenticated authority officer.
    """
    id: int
    name: str
    email: Optional[str] = None
    mobile: str
    role: str
    employee_id: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: bool
    permissions: List[str]
    created_at: datetime


# =========================================================
# DEPARTMENT SCHEMAS
# =========================================================

class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool = True


class DepartmentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    active_officers_count: int = 0
    open_issues_count: int = 0


# =========================================================
# OFFICER SCHEMAS
# =========================================================

class OfficerCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    mobile: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    password: str = Field(..., min_length=8)
    role: str = Field(..., description="DEPARTMENT_OFFICER or FIELD_OFFICER")
    department_id: Optional[int] = None
    designation: Optional[str] = None
    employee_id: Optional[str] = None


class OfficerUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    designation: Optional[str] = None
    is_active: Optional[bool] = None


class OfficerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: Optional[str] = None
    mobile: str
    role: str
    employee_id: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: bool
    created_at: datetime


# =========================================================
# ISSUE MANAGEMENT SCHEMAS
# =========================================================

class IssueAssignRequest(BaseModel):
    department_id: Optional[int] = None
    assigned_officer_id: Optional[int] = None
    comment: Optional[str] = None


class IssueStatusUpdateRequest(BaseModel):
    status: str
    comment: Optional[str] = None
    rejection_reason: Optional[str] = None


class IssueStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    from_status: Optional[str] = None
    to_status: str
    changed_by_id: Optional[int] = None
    changed_by_name: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime


class AuthorityIssueDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    category: str
    severity: str
    priority: str
    location: str
    latitude: float
    longitude: float
    ward: Optional[str] = None
    image_path: str
    status: str

    department_id: Optional[int] = None
    department_name: Optional[str] = None
    assigned_officer_id: Optional[int] = None
    assigned_officer_name: Optional[str] = None
    assigned_officer_mobile: Optional[str] = None
    assigned_by_id: Optional[int] = None
    assigned_by_name: Optional[str] = None
    assigned_at: Optional[datetime] = None

    resolution_notes: Optional[str] = None
    resolution_image_path: Optional[str] = None
    resolved_by_id: Optional[int] = None
    resolved_by_name: Optional[str] = None
    resolved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    reporter_id: Optional[int] = None
    reporter_name: Optional[str] = None
    reporter_citizen_id: Optional[str] = None
    reporter_mobile_masked: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    # SLA Tracking
    sla_hours: Optional[int] = None
    sla_deadline: Optional[datetime] = None
    is_overdue: bool = False
    hours_remaining: Optional[float] = None
    compliance_status: Optional[str] = None

    status_history: List[IssueStatusHistoryResponse] = []


class AuthorityIssueListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    issues: List[Dict[str, Any]]


class ActivityFeedItem(BaseModel):
    id: int
    user_name: str
    user_role: str
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime
    actor_name: Optional[str] = None


# =========================================================
# STATS SCHEMAS
# =========================================================

class StatsOverviewResponse(BaseModel):
    total_issues: int
    reported: int
    under_review: int
    assigned: int
    in_progress: int
    resolved: int
    rejected: int
    reopened: int
    resolution_rate_percent: float
    avg_resolution_hours: Optional[float] = None
    urgent_count: int = 0
    unresolved_count: int = 0
    overdue_count: int = 0


class DepartmentStatItem(BaseModel):
    department_id: int
    name: str
    code: str
    total_issues: int
    open_issues: int
    resolved_issues: int
    resolution_rate_percent: float


class DepartmentStatsResponse(BaseModel):
    departments: List[DepartmentStatItem]


class TrendStatItem(BaseModel):
    date: str
    reported: int
    resolved: int


class TrendStatsResponse(BaseModel):
    days: int
    trends: List[TrendStatItem]


# =========================================================
# GIS MAP SCHEMAS
# =========================================================

class MapIssueItem(BaseModel):
    id: int
    title: str
    category: str
    status: str
    severity: str
    priority: str
    latitude: float
    longitude: float
    location: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    assigned_officer_id: Optional[int] = None
    assigned_officer_name: Optional[str] = None
    created_at: datetime
    ai_analysis_status: str = "NOT_ANALYZED"
    ai_predicted_category: Optional[str] = None
    ai_suggested_severity: Optional[str] = None
    ai_suggested_priority: Optional[str] = None
    ai_suggested_department: Optional[str] = None
    ai_review_status: Optional[str] = None
    nearby_similar_count: int = 0
    is_overdue: bool = False
    sla_deadline: Optional[datetime] = None
    hours_remaining: Optional[float] = None
    compliance_status: Optional[str] = "WITHIN_SLA"


class MapIssuesResponse(BaseModel):
    total: int
    issues: List[MapIssueItem]


# =========================================================
# AUDIT LOG SCHEMAS
# =========================================================

class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    logs: List[AuditLogItem]
