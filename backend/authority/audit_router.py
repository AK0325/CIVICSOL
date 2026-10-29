"""
CIVICSOL - Authority Audit Log Router
Provides query and inspection of municipal administrative activity trails.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuditLog, User

from .dependencies import require_super_admin
from .schemas import AuditLogItem, AuditLogListResponse


router = APIRouter(
    prefix="/authority/audit-logs",
    tags=["Authority Audit Logs"],
)


@router.get("/", response_model=AuditLogListResponse)
def get_audit_logs(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Paginated retrieval of municipal audit logs. Restricted to Super Admin.
    Tracks all administrative actions, department modifications, and officer provisioning.
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action.strip()}%"))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if start_date:
        try:
            s_dt = datetime.fromisoformat(start_date)
            query = query.filter(AuditLog.created_at >= s_dt)
        except ValueError:
            pass
    if end_date:
        try:
            e_dt = datetime.fromisoformat(end_date)
            query = query.filter(AuditLog.created_at <= e_dt)
        except ValueError:
            pass

    query = query.order_by(desc(AuditLog.created_at))

    total = query.count()
    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    items = []
    for log in records:
        user_name = log.user.name if log.user else "System"
        user_role = log.user.role if log.user else "SYSTEM"
        items.append(
            AuditLogItem(
                id=log.id,
                user_id=log.user_id,
                user_name=user_name,
                user_role=user_role,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )

    return AuditLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        logs=items,
    )
