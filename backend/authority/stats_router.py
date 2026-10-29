"""
CIVICSOL - Authority Statistics & Analytics Router
Calculates real database-backed aggregation metrics for the Municipal Command Center.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import CivicIssue, Department, User

from .dependencies import require_field_officer_or_higher
from .schemas import (
    DepartmentStatsResponse,
    DepartmentStatItem,
    StatsOverviewResponse,
    TrendStatsResponse,
    TrendStatItem,
)


router = APIRouter(
    prefix="/authority/stats",
    tags=["Authority Statistics"],
)


from backend.core.sla import evaluate_issue_sla


@router.get("/overview", response_model=StatsOverviewResponse)
def get_stats_overview(
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Computes real, database-backed KPI statistics for the authority dashboard.
    Applies role-based scoping (Super Admin: global; Department Officer: department; Field Officer: assigned).
    Tracks urgent incidents, unresolved totals, and overdue metrics via explicit SLA policies.
    """
    query = db.query(CivicIssue)

    if current_user.role == "FIELD_OFFICER":
        query = query.filter(CivicIssue.assigned_officer_id == current_user.id)
    elif current_user.role == "DEPARTMENT_OFFICER" and current_user.department_id:
        query = query.filter(
            (CivicIssue.department_id == current_user.department_id)
            | (CivicIssue.department_id.is_(None))
        )

    all_issues = query.all()
    total = len(all_issues)

    counts = {
        "Reported": 0,
        "Under Review": 0,
        "Assigned": 0,
        "In Progress": 0,
        "Resolved": 0,
        "Rejected": 0,
        "Reopened": 0,
    }

    resolution_durations = []
    urgent_count = 0
    unresolved_count = 0
    overdue_count = 0

    for issue in all_issues:
        s = issue.status
        if s in counts:
            counts[s] += 1
        else:
            counts["Reported"] += 1

        # Urgent detection (Critical or High priority/severity)
        if (issue.priority in ["High", "Critical"]) or (issue.severity in ["High", "Critical"]):
            urgent_count += 1

        # Unresolved detection
        if s in ["Reported", "Under Review", "Assigned", "In Progress", "Reopened"]:
            unresolved_count += 1

        # SLA calculation
        sla_eval = evaluate_issue_sla(
            created_at=issue.created_at,
            priority=issue.priority,
            status=issue.status,
            resolved_at=issue.resolved_at,
        )
        if sla_eval["is_overdue"]:
            overdue_count += 1

        if issue.status == "Resolved" and issue.resolved_at and issue.created_at:
            delta = issue.resolved_at - issue.created_at
            hours = max(0.0, delta.total_seconds() / 3600.0)
            resolution_durations.append(hours)

    res_rate = round((counts["Resolved"] / total) * 100.0, 1) if total > 0 else 0.0
    avg_hours = round(sum(resolution_durations) / len(resolution_durations), 1) if resolution_durations else None

    return StatsOverviewResponse(
        total_issues=total,
        reported=counts["Reported"],
        under_review=counts["Under Review"],
        assigned=counts["Assigned"],
        in_progress=counts["In Progress"],
        resolved=counts["Resolved"],
        rejected=counts["Rejected"],
        reopened=counts["Reopened"],
        resolution_rate_percent=res_rate,
        avg_resolution_hours=avg_hours,
        urgent_count=urgent_count,
        unresolved_count=unresolved_count,
        overdue_count=overdue_count,
    )



@router.get("/departments", response_model=DepartmentStatsResponse)
def get_department_stats(
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Returns breakdown of total, open, and resolved issues by municipal department.
    """
    departments = db.query(Department).filter(Department.is_active == True).all()
    items = []

    for d in departments:
        # If department officer, only return their department details
        if current_user.role == "DEPARTMENT_OFFICER" and current_user.department_id:
            if d.id != current_user.department_id:
                continue

        dept_issues = db.query(CivicIssue).filter(CivicIssue.department_id == d.id).all()
        total_d = len(dept_issues)
        resolved_d = sum(1 for i in dept_issues if i.status == "Resolved")
        open_d = sum(1 for i in dept_issues if i.status not in ["Resolved", "Rejected"])
        rate_d = round((resolved_d / total_d) * 100.0, 1) if total_d > 0 else 0.0

        items.append(
            DepartmentStatItem(
                department_id=d.id,
                name=d.name,
                code=d.code,
                total_issues=total_d,
                open_issues=open_d,
                resolved_issues=resolved_d,
                resolution_rate_percent=rate_d,
            )
        )

    return DepartmentStatsResponse(departments=items)


@router.get("/trends", response_model=TrendStatsResponse)
def get_issue_trends(
    days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Returns daily time series for the previous N days tracking issues reported vs. resolved.
    """
    now = datetime.utcnow()
    start_date = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    query = db.query(CivicIssue).filter(CivicIssue.created_at >= start_date)
    if current_user.role == "FIELD_OFFICER":
        query = query.filter(CivicIssue.assigned_officer_id == current_user.id)
    elif current_user.role == "DEPARTMENT_OFFICER" and current_user.department_id:
        query = query.filter(CivicIssue.department_id == current_user.department_id)

    issues = query.all()

    # Pre-populate date map
    day_map = {}
    for i in range(days + 1):
        dt = start_date + timedelta(days=i)
        d_str = dt.strftime("%Y-%m-%d")
        day_map[d_str] = {"reported": 0, "resolved": 0}

    for issue in issues:
        c_str = issue.created_at.strftime("%Y-%m-%d") if issue.created_at else None
        if c_str in day_map:
            day_map[c_str]["reported"] += 1

        if issue.status == "Resolved" and issue.resolved_at:
            r_str = issue.resolved_at.strftime("%Y-%m-%d")
            if r_str in day_map:
                day_map[r_str]["resolved"] += 1

    trend_items = [
        TrendStatItem(date=d, reported=counts["reported"], resolved=counts["resolved"])
        for d, counts in sorted(day_map.items())
    ]

    return TrendStatsResponse(days=days, trends=trend_items)


@router.get("/officer-workloads")
def get_officer_workloads(
    department_id: Optional[int] = Query(None),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Returns comparative workload distribution across officers (assigned open vs resolved).
    """
    officer_query = db.query(User).filter(
        User.role.in_(["FIELD_OFFICER", "DEPARTMENT_OFFICER"]),
        User.is_active == True,
    )

    if current_user.role == "DEPARTMENT_OFFICER" and current_user.department_id:
        officer_query = officer_query.filter(User.department_id == current_user.department_id)
    elif department_id:
        officer_query = officer_query.filter(User.department_id == department_id)

    officers = officer_query.all()
    workload = []

    for off in officers:
        issues = db.query(CivicIssue).filter(CivicIssue.assigned_officer_id == off.id).all()
        total_assigned = len(issues)
        open_count = sum(1 for i in issues if i.status not in ["Resolved", "Rejected"])
        resolved_count = sum(1 for i in issues if i.status == "Resolved")
        dept_name = off.department.name if off.department else "Unassigned"

        workload.append({
            "officer_id": off.id,
            "officer_name": off.name,
            "role": off.role,
            "department_id": off.department_id,
            "department_name": dept_name,
            "total_assigned": total_assigned,
            "open_issues": open_count,
            "resolved_issues": resolved_count,
            "resolution_rate": round((resolved_count / total_assigned) * 100.0, 1) if total_assigned > 0 else 0.0,
        })

    return {"officers": workload}

