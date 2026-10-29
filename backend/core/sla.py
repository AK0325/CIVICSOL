"""
CIVICSOL - Municipal Service Level Agreement (SLA) Engine
Provides explicit municipal SLA policies, deadline calculations, and overdue metrics.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

# Municipal SLA Resolution Policies (in hours)
MUNICIPAL_SLA_HOURS: Dict[str, int] = {
    "Critical": 24,
    "High": 48,
    "Medium": 72,
    "Low": 120,
}

DEFAULT_SLA_HOURS = 72


def get_sla_hours_for_priority(priority: Optional[str]) -> int:
    """Return standard SLA resolution window in hours for the given priority."""
    if not priority:
        return DEFAULT_SLA_HOURS
    norm = priority.capitalize().strip()
    return MUNICIPAL_SLA_HOURS.get(norm, DEFAULT_SLA_HOURS)


def evaluate_issue_sla(
    created_at: datetime,
    priority: str,
    status: str,
    resolved_at: Optional[datetime] = None,
) -> dict:
    """
    Calculate explicit SLA compliance for a civic issue.
    Returns:
    - sla_hours: Total allotted window
    - sla_deadline: Target resolution timestamp
    - is_overdue: True if active and now > deadline, or if resolved and resolved_at > deadline
    - hours_remaining: Positive hours remaining before breach, or negative hours overdue
    - compliance_status: 'WITHIN_SLA', 'BREACHED', 'OVERDUE'
    """
    sla_hours = get_sla_hours_for_priority(priority)
    deadline = created_at + timedelta(hours=sla_hours)
    now = datetime.utcnow()

    is_terminal = status.capitalize() in ["Resolved", "Rejected"]

    if is_terminal and resolved_at:
        is_overdue = resolved_at > deadline
        overdue_delta = (resolved_at - deadline).total_seconds() / 3600.0
        hours_remaining = -overdue_delta if is_overdue else (deadline - resolved_at).total_seconds() / 3600.0
        compliance_status = "BREACHED" if is_overdue else "WITHIN_SLA"
    elif is_terminal:
        is_overdue = False
        hours_remaining = 0.0
        compliance_status = "WITHIN_SLA"
    else:
        is_overdue = now > deadline
        hours_remaining = (deadline - now).total_seconds() / 3600.0
        compliance_status = "OVERDUE" if is_overdue else "WITHIN_SLA"

    return {
        "sla_hours": sla_hours,
        "sla_deadline": deadline,
        "is_overdue": is_overdue,
        "hours_remaining": round(hours_remaining, 1),
        "compliance_status": compliance_status,
    }
