"""
CIVICSOL - Municipal Service Level Agreement (SLA) Engine
Provides explicit municipal SLA policies, deadline calculations, and overdue metrics.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

# Municipal SLA Resolution Policies (in hours)
MUNICIPAL_SLA_HOURS: Dict[str, int] = {
    "Critical": 24,
    "High": 48,
    "Medium": 72,
    "Low": 120,
}

DEFAULT_SLA_HOURS = 72


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Helper to ensure a datetime is timezone-aware in UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_sla_hours_for_priority(priority: Optional[str]) -> int:
    """Return standard SLA resolution window in hours for the given priority."""
    if not priority:
        return DEFAULT_SLA_HOURS
    norm = priority.capitalize().strip()
    return MUNICIPAL_SLA_HOURS.get(norm, DEFAULT_SLA_HOURS)


def evaluate_issue_sla(
    created_at: Optional[datetime],
    priority: Optional[str],
    status: Optional[str],
    resolved_at: Optional[datetime] = None,
) -> dict:
    """
    Calculate explicit SLA compliance for a civic issue.
    Handles both timezone-naive and timezone-aware datetimes seamlessly.
    Returns:
    - sla_hours: Total allotted window
    - sla_deadline: Target resolution timestamp
    - is_overdue: True if active and now > deadline, or if resolved and resolved_at > deadline
    - hours_remaining: Positive hours remaining before breach, or negative hours overdue
    - compliance_status: 'WITHIN_SLA', 'BREACHED', 'OVERDUE'
    """
    now = datetime.now(timezone.utc)
    created_utc = _to_utc(created_at) if created_at else now
    resolved_utc = _to_utc(resolved_at) if resolved_at else None

    sla_hours = get_sla_hours_for_priority(priority)
    deadline_utc = created_utc + timedelta(hours=sla_hours)

    status_str = (status or "Reported").strip().capitalize()
    is_terminal = status_str in ["Resolved", "Rejected"]

    if is_terminal and resolved_utc:
        is_overdue = resolved_utc > deadline_utc
        overdue_delta = (resolved_utc - deadline_utc).total_seconds() / 3600.0
        hours_remaining = -overdue_delta if is_overdue else (deadline_utc - resolved_utc).total_seconds() / 3600.0
        compliance_status = "BREACHED" if is_overdue else "WITHIN_SLA"
    elif is_terminal:
        is_overdue = False
        hours_remaining = 0.0
        compliance_status = "WITHIN_SLA"
    else:
        is_overdue = now > deadline_utc
        hours_remaining = (deadline_utc - now).total_seconds() / 3600.0
        compliance_status = "OVERDUE" if is_overdue else "WITHIN_SLA"

    # Preserve naive/aware convention of the input created_at
    if created_at is not None and created_at.tzinfo is None:
        return_deadline = deadline_utc.replace(tzinfo=None)
    else:
        return_deadline = deadline_utc

    return {
        "sla_hours": sla_hours,
        "sla_deadline": return_deadline,
        "is_overdue": is_overdue,
        "hours_remaining": round(hours_remaining, 1),
        "compliance_status": compliance_status,
    }
