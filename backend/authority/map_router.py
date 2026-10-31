"""
CIVICSOL - Authority GIS Map Router
Provides lightweight spatial payloads for the Municipal GIS Command Map.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.core.sla import evaluate_issue_sla
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
    ai_status: Optional[str] = Query(None),
    ai_analyzed: Optional[bool] = Query(None),
    overdue_only: Optional[bool] = Query(None),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Returns lightweight coordinate payload of issues for real-time GIS map visualization,
    enriched with AI analysis status, department recommendations, nearby similar counts,
    and municipal SLA compliance / overdue tracking.
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

    if department_id and not hasattr(department_id, "default"):
        query = query.filter(CivicIssue.department_id == department_id)
    if status and not hasattr(status, "default"):
        query = query.filter(CivicIssue.status == status)
    if category and not hasattr(category, "default"):
        query = query.filter(CivicIssue.category == category)
    if severity and not hasattr(severity, "default"):
        query = query.filter(CivicIssue.severity == severity)

    issues = query.all()
    items = []

    ai_filter = ai_status if (ai_status and not hasattr(ai_status, "default")) else None
    if ai_filter is None and ai_analyzed is not None and not hasattr(ai_analyzed, "default"):
        ai_filter = "ANALYZED" if ai_analyzed else "NOT_ANALYZED"

    is_overdue_filter = overdue_only if (overdue_only is not None and not hasattr(overdue_only, "default")) else None

    for issue in issues:
        # Validate coordinates are valid numbers
        if issue.latitude is None or issue.longitude is None:
            continue
        if not (-90.0 <= issue.latitude <= 90.0) or not (-180.0 <= issue.longitude <= 180.0):
            continue

        dept_name = issue.department_rel.name if issue.department_rel else (issue.department or "Unassigned")
        officer_name = issue.assigned_officer.name if issue.assigned_officer else None

        latest_ai = issue.ai_analyses[0] if issue.ai_analyses else None
        ai_stat = latest_ai.processing_status if latest_ai else "NOT_ANALYZED"

        if ai_filter:
            if ai_filter == "ANALYZED" and ai_stat not in ("COMPLETED", "NO_DETECTION"):
                continue
            elif ai_filter == "NOT_ANALYZED" and ai_stat != "NOT_ANALYZED":
                continue
            elif ai_filter not in ("ANALYZED", "NOT_ANALYZED") and ai_stat != ai_filter:
                continue

        # SLA calculation
        sla_eval = evaluate_issue_sla(
            created_at=issue.created_at,
            priority=issue.priority,
            status=issue.status,
            resolved_at=issue.resolved_at,
        )

        if is_overdue_filter and not sla_eval["is_overdue"]:
            continue

        ai_dept_name = None
        nearby_cnt = 0
        if latest_ai:
            if latest_ai.suggested_department:
                ai_dept_name = latest_ai.suggested_department.name
            meta = latest_ai.analysis_metadata or {}
            sim = meta.get("similar_nearby_reports")
            if isinstance(sim, list):
                nearby_cnt = len(sim)

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
                ai_analysis_status=ai_stat,
                ai_predicted_category=latest_ai.predicted_category if latest_ai else None,
                ai_suggested_severity=latest_ai.suggested_severity if latest_ai else None,
                ai_suggested_priority=latest_ai.suggested_priority if latest_ai else None,
                ai_suggested_department=ai_dept_name,
                ai_review_status=latest_ai.review_status if latest_ai else None,
                nearby_similar_count=nearby_cnt,
                is_overdue=sla_eval["is_overdue"],
                sla_deadline=sla_eval["sla_deadline"],
                hours_remaining=sla_eval["hours_remaining"],
                compliance_status=sla_eval["compliance_status"],
            )
        )

    return MapIssuesResponse(total=len(items), issues=items)
