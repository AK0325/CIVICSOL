"""
CIVICSOL - Authority GIS Map Router
Provides lightweight spatial payloads for the Municipal GIS Command Map.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CivicIssue, User

from .dependencies import require_field_officer_or_higher
from .schemas import MapIssuesResponse, MapIssueItem


router = APIRouter(
    prefix="/authority/map",
    tags=["Authority GIS Map"],
)


@router.get("/issues", response_model=MapIssuesResponse)
def get_authority_map_issues(
    department_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Returns lightweight coordinate payload of issues for real-time GIS map visualization.
    Applies role-based scoping and handles coordinate bounds gracefully.
    """
    query = db.query(CivicIssue)

    # Scoping
    if current_user.role == "FIELD_OFFICER":
        query = query.filter(CivicIssue.assigned_officer_id == current_user.id)
    elif current_user.role == "DEPARTMENT_OFFICER" and current_user.department_id:
        query = query.filter(
            (CivicIssue.department_id == current_user.department_id)
            | (CivicIssue.department_id.is_(None))
        )

    if department_id:
        query = query.filter(CivicIssue.department_id == department_id)
    if status:
        query = query.filter(CivicIssue.status == status)
    if category:
        query = query.filter(CivicIssue.category == category)
    if severity:
        query = query.filter(CivicIssue.severity == severity)

    issues = query.all()
    items = []

    for issue in issues:
        # Validate coordinates are valid numbers
        if issue.latitude is None or issue.longitude is None:
            continue
        if not (-90.0 <= issue.latitude <= 90.0) or not (-180.0 <= issue.longitude <= 180.0):
            continue

        dept_name = issue.department_rel.name if issue.department_rel else (issue.department or "Unassigned")
        officer_name = issue.assigned_officer.name if issue.assigned_officer else None

        items.append(
            MapIssueItem(
                id=issue.id,
                title=issue.title,
                category=issue.category,
                status=issue.status,
                severity=issue.severity,
                priority=issue.priority,
                latitude=issue.latitude,
                longitude=issue.longitude,
                location=issue.location,
                department_id=issue.department_id,
                department_name=dept_name,
                assigned_officer_id=issue.assigned_officer_id,
                assigned_officer_name=officer_name,
                created_at=issue.created_at,
            )
        )

    return MapIssuesResponse(total=len(items), issues=items)
