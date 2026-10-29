"""
CIVICSOL - Authority Issue Management Router
Provides endpoints for issue searching, filtering, assignments, state transitions,
resolution evidence uploading, and audit history.
"""

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from PIL import Image
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from backend.auth.otp_service import mask_mobile
from backend.core.config import settings
from backend.core.sla import evaluate_issue_sla
from backend.database import get_db
from backend.models import (
    AuditLog,
    CivicCreditTransaction,
    CivicIssue,
    Department,
    IssueStatusHistory,
    User,
)
from backend.notifications.service import notify_citizen_and_officer
from backend.rewards.credit_engine import add_credit_transaction

from .dependencies import (
    get_current_authority_user,
    require_field_officer_or_higher,
)
from .schemas import (
    ActivityFeedItem,
    AuthorityIssueDetailResponse,
    AuthorityIssueListResponse,
    IssueAssignRequest,
    IssueStatusUpdateRequest,
)


router = APIRouter(
    prefix="/authority/issues",
    tags=["Authority Issues"],
)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# STATE MACHINE VALID TRANSITIONS
# =========================================================
ALLOWED_STATUS_TRANSITIONS = {
    "Reported": {"Under Review", "Assigned", "Rejected"},
    "Under Review": {"Assigned", "Rejected"},
    "Assigned": {"In Progress", "Resolved", "Rejected"},
    "In Progress": {"Resolved", "Assigned"},
    "Resolved": {"Reopened"},
    "Reopened": {"Under Review", "Assigned"},
    "Rejected": set(),  # Terminal state
}


def normalize_status(s: str) -> str:
    """Normalize status string to Title Case format matching DB standard."""
    raw = s.strip().lower()
    mapping = {
        "reported": "Reported",
        "under_review": "Under Review",
        "under review": "Under Review",
        "assigned": "Assigned",
        "in_progress": "In Progress",
        "in progress": "In Progress",
        "resolved": "Resolved",
        "rejected": "Rejected",
        "reopened": "Reopened",
    }
    return mapping.get(raw, s.strip())


# =========================================================
# 1. LIST & FILTER ISSUES
# =========================================================
@router.get("/", response_model=AuthorityIssueListResponse)
def list_authority_issues(
    search: Optional[str] = Query(None, description="Search in title, description, location"),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    assigned_officer_id: Optional[int] = Query(None),
    urgent: Optional[bool] = Query(None, description="Filter Critical or High severity/priority issues"),
    unresolved: Optional[bool] = Query(None, description="Filter active unresolved issues"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    query = db.query(CivicIssue)

    # Scoping by role
    if current_user.role == "FIELD_OFFICER":
        query = query.filter(CivicIssue.assigned_officer_id == current_user.id)
    elif current_user.role == "DEPARTMENT_OFFICER":
        if current_user.department_id:
            query = query.filter(
                (CivicIssue.department_id == current_user.department_id)
                | (CivicIssue.department_id.is_(None))
            )

    # Search filter
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            CivicIssue.title.ilike(s)
            | CivicIssue.description.ilike(s)
            | CivicIssue.location.ilike(s)
        )

    # Field filters
    if status:
        query = query.filter(CivicIssue.status == normalize_status(status))
    if category:
        query = query.filter(CivicIssue.category == category)
    if severity:
        query = query.filter(CivicIssue.severity == severity)
    if priority:
        query = query.filter(CivicIssue.priority == priority)
    if department_id:
        query = query.filter(CivicIssue.department_id == department_id)
    if assigned_officer_id:
        query = query.filter(CivicIssue.assigned_officer_id == assigned_officer_id)

    # Urgent & Unresolved filters
    if urgent:
        query = query.filter(
            (CivicIssue.priority.in_(["High", "Critical"]))
            | (CivicIssue.severity.in_(["High", "Critical"]))
        )
    if unresolved:
        query = query.filter(
            CivicIssue.status.in_(["Reported", "Under Review", "Assigned", "In Progress", "Reopened"])
        )

    if start_date:
        try:
            s_dt = datetime.fromisoformat(start_date)
            query = query.filter(CivicIssue.created_at >= s_dt)
        except ValueError:
            pass
    if end_date:
        try:
            e_dt = datetime.fromisoformat(end_date)
            query = query.filter(CivicIssue.created_at <= e_dt)
        except ValueError:
            pass

    # Sorting
    sort_column = getattr(CivicIssue, sort_by, CivicIssue.created_at)
    order_func = desc if sort_order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_column))

    total = query.count()
    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    results = []
    for issue in records:
        dept_name = issue.department_rel.name if issue.department_rel else (issue.department or "Unassigned")
        officer_name = issue.assigned_officer.name if issue.assigned_officer else None

        sla_eval = evaluate_issue_sla(
            created_at=issue.created_at,
            priority=issue.priority,
            status=issue.status,
            resolved_at=issue.resolved_at,
        )

        results.append({
            "id": issue.id,
            "title": issue.title,
            "category": issue.category,
            "severity": issue.severity,
            "priority": issue.priority,
            "status": issue.status,
            "location": issue.location,
            "latitude": issue.latitude,
            "longitude": issue.longitude,
            "image_path": issue.image_path,
            "department_id": issue.department_id,
            "department_name": dept_name,
            "assigned_officer_id": issue.assigned_officer_id,
            "assigned_officer_name": officer_name,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
            "sla_deadline": sla_eval["sla_deadline"].isoformat(),
            "is_overdue": sla_eval["is_overdue"],
            "hours_remaining": sla_eval["hours_remaining"],
            "compliance_status": sla_eval["compliance_status"],
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "issues": results,
    }



# =========================================================
# 2. CSV REPORT EXPORT (AUTHORIZED)
# =========================================================
@router.get("/export")
def export_authority_issues_csv(
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Stream a sanitized CSV export of civic issues.
    Applies role-based data scoping and protects citizen privacy (excludes private phone/email).
    """
    query = db.query(CivicIssue)

    # Role scoping
    if current_user.role == "FIELD_OFFICER":
        query = query.filter(CivicIssue.assigned_officer_id == current_user.id)
    elif current_user.role == "DEPARTMENT_OFFICER":
        if current_user.department_id:
            query = query.filter(
                (CivicIssue.department_id == current_user.department_id)
                | (CivicIssue.department_id.is_(None))
            )

    if status:
        query = query.filter(CivicIssue.status == normalize_status(status))
    if department_id:
        query = query.filter(CivicIssue.department_id == department_id)
    if category:
        query = query.filter(CivicIssue.category == category)
    if start_date:
        try:
            query = query.filter(CivicIssue.created_at >= datetime.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            query = query.filter(CivicIssue.created_at <= datetime.fromisoformat(end_date))
        except ValueError:
            pass

    records = query.order_by(desc(CivicIssue.created_at)).limit(1000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID",
        "Title",
        "Category",
        "Severity",
        "Priority",
        "Status",
        "Location",
        "Latitude",
        "Longitude",
        "Department",
        "Assigned Officer",
        "Created At",
        "Resolved At",
        "SLA Deadline",
        "Is Overdue",
    ])

    for issue in records:
        dept_name = issue.department_rel.name if issue.department_rel else (issue.department or "Unassigned")
        officer_name = issue.assigned_officer.name if issue.assigned_officer else "Unassigned"
        sla_eval = evaluate_issue_sla(
            created_at=issue.created_at,
            priority=issue.priority,
            status=issue.status,
            resolved_at=issue.resolved_at,
        )
        writer.writerow([
            issue.id,
            issue.title,
            issue.category,
            issue.severity,
            issue.priority,
            issue.status,
            issue.location,
            issue.latitude,
            issue.longitude,
            dept_name,
            officer_name,
            issue.created_at.strftime("%Y-%m-%d %H:%M:%S") if issue.created_at else "",
            issue.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if issue.resolved_at else "",
            sla_eval["sla_deadline"].strftime("%Y-%m-%d %H:%M:%S"),
            "YES" if sla_eval["is_overdue"] else "NO",
        ])

    output.seek(0)
    filename = f"civicsol_issues_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =========================================================
# 3. RECENT ADMINISTRATIVE ACTIVITY FEED
# =========================================================
@router.get("/activity/recent", response_model=List[ActivityFeedItem])
def get_recent_authority_activity(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Returns recent administrative operations for the Command Center live feed.
    """
    records = db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).all()

    items = []
    for log in records:
        items.append(ActivityFeedItem(
            id=log.id,
            user_name=log.user.name if log.user else "System",
            user_role=log.user.role if log.user else "SYSTEM",
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            created_at=log.created_at,
        ))

    return items


# =========================================================
# 4. GET ISSUE DETAIL
# =========================================================
@router.get("/{issue_id}", response_model=AuthorityIssueDetailResponse)
def get_authority_issue_detail(
    issue_id: int,
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):

    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Civic issue not found.",
        )

    # Role-based access validation
    if current_user.role == "FIELD_OFFICER" and issue.assigned_officer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Field officers can only view issues assigned to them.",
        )
    if (
        current_user.role == "DEPARTMENT_OFFICER"
        and current_user.department_id
        and issue.department_id
        and issue.department_id != current_user.department_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You cannot view issues from another department.",
        )

    # Format reporter contact with privacy boundary protection
    reporter_name = issue.user.name if issue.user else "Anonymous Citizen"
    if current_user.role == "FIELD_OFFICER":
        # Field officers only see incident details, not citizen personal phone/ID
        reporter_citizen_id = None
        masked_mob = None
    else:
        reporter_citizen_id = issue.user.citizen_id if issue.user else None
        masked_mob = mask_mobile(issue.user.mobile) if (issue.user and issue.user.mobile) else None

    # Status history
    history_items = []
    for h in issue.status_history:
        history_items.append({
            "id": h.id,
            "issue_id": h.issue_id,
            "from_status": h.from_status,
            "to_status": h.to_status,
            "changed_by_id": h.changed_by_id,
            "changed_by_name": h.changed_by.name if h.changed_by else "System",
            "comment": h.comment,
            "created_at": h.created_at,
        })

    sla_eval = evaluate_issue_sla(
        created_at=issue.created_at,
        priority=issue.priority,
        status=issue.status,
        resolved_at=issue.resolved_at,
    )

    return AuthorityIssueDetailResponse(
        id=issue.id,
        title=issue.title,
        description=issue.description,
        category=issue.category,
        severity=issue.severity,
        priority=issue.priority,
        location=issue.location,
        latitude=issue.latitude,
        longitude=issue.longitude,
        ward=issue.ward,
        image_path=issue.image_path,
        status=issue.status,
        department_id=issue.department_id,
        department_name=issue.department_rel.name if issue.department_rel else issue.department,
        assigned_officer_id=issue.assigned_officer_id,
        assigned_officer_name=issue.assigned_officer.name if issue.assigned_officer else None,
        assigned_officer_mobile=issue.assigned_officer.mobile if issue.assigned_officer else None,
        assigned_by_id=issue.assigned_by_id,
        assigned_by_name=issue.assigned_by.name if issue.assigned_by else None,
        assigned_at=issue.assigned_at,
        resolution_notes=issue.resolution_notes,
        resolution_image_path=issue.resolution_image_path,
        resolved_by_id=issue.resolved_by_id,
        resolved_by_name=issue.resolved_by.name if issue.resolved_by else None,
        resolved_at=issue.resolved_at,
        rejection_reason=issue.rejection_reason,
        reporter_id=issue.user_id,
        reporter_name=reporter_name,
        reporter_citizen_id=reporter_citizen_id,
        reporter_mobile_masked=masked_mob,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        sla_hours=sla_eval["sla_hours"],
        sla_deadline=sla_eval["sla_deadline"],
        is_overdue=sla_eval["is_overdue"],
        hours_remaining=sla_eval["hours_remaining"],
        compliance_status=sla_eval["compliance_status"],
        status_history=history_items,
    )



# =========================================================
# 3. ASSIGN ISSUE
# =========================================================
@router.put("/{issue_id}/assign")
def assign_authority_issue(
    issue_id: int,
    payload: IssueAssignRequest,
    request: Request,
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    if current_user.role == "FIELD_OFFICER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field officers cannot perform issue assignments.",
        )

    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Civic issue not found.",
        )

    # Department Officer boundary check
    if current_user.role == "DEPARTMENT_OFFICER":
        if current_user.department_id:
            if payload.department_id and payload.department_id != current_user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Department officers cannot assign issues to other departments.",
                )
            if issue.department_id and issue.department_id != current_user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot modify assignments for issues outside your department.",
                )

    target_dept_id = payload.department_id or issue.department_id

    # Validate officer if assigned
    assigned_officer = None
    if payload.assigned_officer_id:
        assigned_officer = (
            db.query(User)
            .filter(User.id == payload.assigned_officer_id, User.is_active == True)
            .first()
        )
        if not assigned_officer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned officer not found or is inactive.",
            )
        if assigned_officer.role not in ["FIELD_OFFICER", "DEPARTMENT_OFFICER"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user must be an authorized officer.",
            )
        if target_dept_id and assigned_officer.department_id and assigned_officer.department_id != target_dept_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Officer does not belong to the target department.",
            )

    prev_status = issue.status
    issue.department_id = target_dept_id
    issue.assigned_officer_id = payload.assigned_officer_id
    issue.assigned_by_id = current_user.id
    issue.assigned_at = datetime.utcnow()

    # If currently in Reported or Under Review, advance to Assigned
    if issue.status in ["Reported", "Under Review"]:
        issue.status = "Assigned"

    # Status history entry
    hist = IssueStatusHistory(
        issue_id=issue.id,
        from_status=prev_status,
        to_status=issue.status,
        changed_by_id=current_user.id,
        comment=payload.comment or f"Assigned to {assigned_officer.name if assigned_officer else 'Department'}.",
    )
    db.add(hist)

    # Audit log entry
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="ISSUE_ASSIGNED",
        entity_type="issue",
        entity_id=issue.id,
        details=f"Assigned issue #{issue.id} to officer {assigned_officer.name if assigned_officer else 'None'} in department {target_dept_id}.",
        ip_address=client_ip,
    )
    db.add(audit)

    # Dispatch notification to citizen and assigned officer
    dept_display = issue.department_rel.name if issue.department_rel else "Municipal Operations"
    notify_citizen_and_officer(
        db=db,
        citizen=issue.user,
        officer=assigned_officer,
        event="ASSIGNED",
        issue_id=issue.id,
        issue_title=issue.title,
        details={"department_name": dept_display},
    )

    db.commit()

    return {
        "message": "Issue assigned successfully.",
        "issue_id": issue.id,
        "department_id": issue.department_id,
        "assigned_officer_id": issue.assigned_officer_id,
        "status": issue.status,
    }


# =========================================================
# 4. UPDATE STATUS (STATE MACHINE)
# =========================================================
@router.put("/{issue_id}/status")
def update_authority_issue_status(
    issue_id: int,
    payload: IssueStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Civic issue not found.",
        )

    target_status = normalize_status(payload.status)
    current_status = issue.status

    # Validate state transition
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current_status}' to '{target_status}'. Allowed: {', '.join(allowed) if allowed else 'None'}",
        )

    # Validate role permissions for target status
    if current_user.role == "FIELD_OFFICER":
        if issue.assigned_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Field officers can only update status of their assigned issues.",
            )
        if target_status not in ["In Progress"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Field officers cannot transition to this status directly without resolution evidence.",
            )

    # Rejection requires reason
    if target_status == "Rejected":
        if not payload.rejection_reason or not payload.rejection_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is required to reject an issue.",
            )
        issue.rejection_reason = payload.rejection_reason.strip()

    issue.status = target_status
    issue.updated_at = datetime.utcnow()

    # Status history entry
    hist = IssueStatusHistory(
        issue_id=issue.id,
        from_status=current_status,
        to_status=target_status,
        changed_by_id=current_user.id,
        comment=payload.comment or (f"Rejected: {payload.rejection_reason}" if target_status == "Rejected" else None),
    )
    db.add(hist)

    # Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="ISSUE_STATUS_UPDATED",
        entity_type="issue",
        entity_id=issue.id,
        details=f"Status changed from '{current_status}' to '{target_status}'.",
        ip_address=client_ip,
    )
    db.add(audit)

    # Dispatch notification to citizen and officer
    event_name = "REJECTED" if target_status == "Rejected" else ("REOPENED" if target_status == "Reopened" else "STATUS_UPDATED")
    notify_citizen_and_officer(
        db=db,
        citizen=issue.user,
        officer=issue.assigned_officer,
        event=event_name,
        issue_id=issue.id,
        issue_title=issue.title,
        details={"to_status": target_status, "reason": payload.rejection_reason},
    )

    db.commit()

    return {
        "message": f"Issue status updated to '{target_status}'.",
        "issue_id": issue.id,
        "from_status": current_status,
        "to_status": target_status,
    }


# =========================================================
# 5. RESOLVE ISSUE (WITH EVIDENCE & REWARD)
# =========================================================
@router.post("/{issue_id}/resolve")
async def resolve_authority_issue(
    issue_id: int,
    request: Request,
    resolution_notes: str = Form(...),
    image: UploadFile = File(...),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Civic issue not found.",
        )

    # Role permission check
    if current_user.role == "FIELD_OFFICER" and issue.assigned_officer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field officers can only resolve issues assigned to them.",
        )

    # Validate transition from current status
    allowed = ALLOWED_STATUS_TRANSITIONS.get(issue.status, set())
    if "Resolved" not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve an issue from status '{issue.status}'. Allowed transitions: {', '.join(allowed)}",
        )

    if not resolution_notes or not resolution_notes.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolution notes are mandatory when closing an issue.",
        )

    # Validate image upload
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only valid image files are accepted for resolution evidence.",
        )

    contents = await image.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded resolution image is empty.",
        )

    max_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resolution image exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    try:
        with Image.open(io.BytesIO(contents)) as pil_img:
            pil_img.verify()
            img_format = (pil_img.format or "").upper()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid or readable image.",
        )

    ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    if img_format not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format: {img_format}. Allowed: JPEG, PNG, WEBP.",
        )

    extension = ALLOWED_FORMATS[img_format]
    filename = f"res_{uuid4().hex}{extension}"
    image_path = UPLOAD_DIR / filename
    image_path.write_bytes(contents)

    prev_status = issue.status
    issue.status = "Resolved"
    issue.resolution_notes = resolution_notes.strip()
    issue.resolution_image_path = f"uploads/{filename}"
    issue.resolved_by_id = current_user.id
    issue.resolved_at = datetime.utcnow()
    issue.updated_at = datetime.utcnow()

    # Status history entry
    hist = IssueStatusHistory(
        issue_id=issue.id,
        from_status=prev_status,
        to_status="Resolved",
        changed_by_id=current_user.id,
        comment=f"Issue resolved: {resolution_notes.strip()}",
    )
    db.add(hist)

    # Award +20 authority verification Civic Credits to the reporting citizen (idempotent check)
    credits_awarded = 0
    if issue.user_id:
        existing_credit = (
            db.query(CivicCreditTransaction)
            .filter(
                CivicCreditTransaction.issue_id == issue.id,
                CivicCreditTransaction.action == "authority_verification",
            )
            .first()
        )
        if not existing_credit:
            add_credit_transaction(
                db=db,
                user_id=issue.user_id,
                issue_id=issue.id,
                action="authority_verification",
                description="Issue resolved and verified by municipal authority.",
            )
            credits_awarded = 20

    # Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="ISSUE_RESOLVED",
        entity_type="issue",
        entity_id=issue.id,
        details=f"Issue #{issue.id} marked Resolved by {current_user.name}. Resolution photo uploaded.",
        ip_address=client_ip,
    )
    db.add(audit)

    # Dispatch resolution notification to citizen
    notify_citizen_and_officer(
        db=db,
        citizen=issue.user,
        officer=current_user,
        event="RESOLVED",
        issue_id=issue.id,
        issue_title=issue.title,
    )

    db.commit()

    return {
        "message": "Issue resolved successfully with evidence.",
        "issue_id": issue.id,
        "status": "Resolved",
        "resolution_notes": issue.resolution_notes,
        "resolution_image_path": issue.resolution_image_path,
        "citizen_credits_awarded": credits_awarded,
    }


