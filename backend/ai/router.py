"""
CIVICSOL - AI Intelligence & Analysis Router
Provides secure endpoints for triggering, viewing, re-analysing, and approving/rejecting
AI civic issue analysis:
- POST /ai/analyze/{issue_id}
- GET  /ai/analysis/{issue_id}
- GET  /ai/analysis/{issue_id}/history
- POST /ai/reanalyze/{issue_id}
- POST /ai/analysis/{issue_id}/approve
- POST /ai/analysis/{issue_id}/reject
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from backend.auth.dependencies import get_current_user
from backend.authority.dependencies import (
    require_department_officer,
    require_field_officer_or_higher,
)
from backend.core.rate_limiter import SlidingWindowRateLimiter
from backend.database import get_db
from backend.models import AIAnalysis, AuditLog, CivicIssue, Department, IssueStatusHistory, User

from .duplicate_detector import find_similar_nearby_issues
from .pipeline import run_issue_ai_analysis
from .schemas import (
    AIAnalysisEnvelopeResponse,
    AIAnalysisHistoryResponse,
    AIAnalysisItemResponse,
    AIDuplicateLinkRequest,
    AIFalsePositiveRequest,
    AIReviewDecisionRequest,
)


router = APIRouter(
    prefix="/ai",
    tags=["AI Civic Intelligence"],
)

# Rate limiter for expensive AI analysis operations (max 15 requests per 60s per user)
ai_rate_limiter = SlidingWindowRateLimiter()

AUTHORITY_ROLES = {"SUPER_ADMIN", "DEPARTMENT_OFFICER", "FIELD_OFFICER"}

PRIORITY_MAP_TO_ISSUE = {
    "URGENT": "Critical",
    "CRITICAL": "Critical",
    "HIGH": "High",
    "NORMAL": "Medium",
    "MEDIUM": "Medium",
    "LOW": "Low",
}

SEVERITY_MAP_TO_ISSUE = {
    "CRITICAL": "Critical",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}


def _check_issue_access(issue: CivicIssue, current_user: User, require_authority: bool = False) -> None:
    """
    Verifies that the user is authorized to access or trigger AI analysis for the issue.
    - Citizens can only access their own reported issues (unless require_authority=True).
    - Authority officers can access issues within their role scope.
    """
    if require_authority and current_user.role not in AUTHORITY_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Authority officer privileges required for this AI operation.",
        )

    if current_user.role == "CITIZEN":
        if issue.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You may only view or analyze your own reported civic issues.",
            )
    elif current_user.role == "FIELD_OFFICER":
        if issue.assigned_officer_id and issue.assigned_officer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Issue is assigned to another field officer.",
            )
    elif current_user.role == "DEPARTMENT_OFFICER":
        if (
            current_user.department_id
            and issue.department_id
            and issue.department_id != current_user.department_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Issue belongs to another municipal department.",
            )


def _serialize_analysis(
    analysis: AIAnalysis,
    db: Session,
    issue: CivicIssue,
    is_citizen: bool = False,
) -> AIAnalysisItemResponse:
    """Serializes an AIAnalysis ORM object into AIAnalysisItemResponse."""
    dept_name = None
    dept_code = None
    if analysis.suggested_department_id:
        dept = db.query(Department).filter(Department.id == analysis.suggested_department_id).first()
        if dept:
            dept_name = dept.name
            dept_code = dept.code

    reviewer_name = None
    if analysis.reviewed_by_id and not is_citizen:
        rev_user = db.query(User).filter(User.id == analysis.reviewed_by_id).first()
        if rev_user:
            reviewer_name = rev_user.name

    meta = dict(analysis.analysis_metadata or {})
    similar_reports = meta.get("similar_nearby_reports")
    if similar_reports is None and not is_citizen:
        similar_reports = find_similar_nearby_issues(
            db=db,
            issue_id=issue.id,
            latitude=issue.latitude,
            longitude=issue.longitude,
            category=analysis.predicted_category or issue.category,
            title=issue.title,
            description=issue.description,
            created_at=issue.created_at,
        )

    # Redact internal authority metadata for citizen portal requests
    if is_citizen:
        safe_meta = {
            "vision_status": meta.get("vision_status"),
            "analysis_timestamp": meta.get("analysis_timestamp"),
        }
        similar_reports = []
    else:
        safe_meta = meta

    return AIAnalysisItemResponse(
        id=analysis.id,
        issue_id=analysis.issue_id,
        model_name=analysis.model_name,
        model_version=analysis.model_version,
        predicted_category=analysis.predicted_category,
        confidence_score=analysis.confidence_score,
        detected_objects=analysis.detected_objects or [],
        suggested_severity=analysis.suggested_severity,
        suggested_priority=analysis.suggested_priority,
        suggested_department_id=analysis.suggested_department_id,
        suggested_department_name=dept_name,
        suggested_department_code=dept_code,
        explanation=analysis.explanation,
        annotated_image_path=analysis.annotated_image_path,
        processing_status=analysis.processing_status,
        review_status=analysis.review_status or "PENDING",
        reviewed_by_id=None if is_citizen else analysis.reviewed_by_id,
        reviewed_by_name=reviewer_name,
        reviewed_at=None if is_citizen else analysis.reviewed_at,
        review_comment=None if is_citizen else analysis.review_comment,
        similar_nearby_reports=similar_reports or [],
        analysis_metadata=safe_meta,
        created_at=analysis.created_at,
    )


def _build_official_values(issue: CivicIssue, db: Session) -> Dict[str, Any]:
    dept_name = "Unassigned"
    if issue.department_id:
        dept = db.query(Department).filter(Department.id == issue.department_id).first()
        if dept:
            dept_name = dept.name
    elif issue.department:
        dept_name = issue.department

    return {
        "category": issue.category,
        "severity": issue.severity,
        "priority": issue.priority,
        "status": issue.status,
        "department_id": issue.department_id,
        "department_name": dept_name,
    }


@router.post("/analyze/{issue_id}", response_model=AIAnalysisEnvelopeResponse)
def analyze_issue(
    issue_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs AI analysis on a civic issue report.
    If an analysis is already currently PROCESSING, avoids duplicate concurrent execution.
    If a COMPLETED/NO_DETECTION analysis already exists, returns it (use /reanalyze to force new run).
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Civic issue not found.")

    _check_issue_access(issue, current_user, require_authority=False)

    rate_key = f"ai_analyze:{current_user.id}"
    ai_rate_limiter.check_and_record(key=rate_key, max_attempts=15, window_seconds=60)
    ai_rate_limiter.record_attempt(rate_key)

    existing = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at), desc(AIAnalysis.id))
        .first()
    )

    if existing and existing.processing_status == "PROCESSING":
        ser = _serialize_analysis(existing, db, issue, is_citizen=(current_user.role == "CITIZEN"))
        return AIAnalysisEnvelopeResponse(
            has_analysis=True,
            message="AI analysis is currently in progress.",
            issue_id=issue.id,
            official_values=_build_official_values(issue, db),
            analysis=ser,
            latest_analysis=ser,
        )

    if existing and existing.processing_status in {"COMPLETED", "NO_DETECTION"}:
        ser = _serialize_analysis(existing, db, issue, is_citizen=(current_user.role == "CITIZEN"))
        return AIAnalysisEnvelopeResponse(
            has_analysis=True,
            message="AI analysis retrieved.",
            issue_id=issue.id,
            official_values=_build_official_values(issue, db),
            analysis=ser,
            latest_analysis=ser,
        )

    analysis = run_issue_ai_analysis(db=db, issue=issue)

    if current_user.role in AUTHORITY_ROLES:
        client_ip = request.client.host if request.client else "127.0.0.1"
        db.add(AuditLog(
            user_id=current_user.id,
            action="AI_ANALYSIS_EXECUTED",
            entity_type="issue",
            entity_id=issue.id,
            details=f"Executed AI analysis #{analysis.id} on Issue #{issue.id} (status: {analysis.processing_status}).",
            ip_address=client_ip,
        ))
        db.commit()

    ser = _serialize_analysis(analysis, db, issue, is_citizen=(current_user.role == "CITIZEN"))
    return AIAnalysisEnvelopeResponse(
        has_analysis=True,
        message="AI analysis completed.",
        issue_id=issue.id,
        official_values=_build_official_values(issue, db),
        analysis=ser,
        latest_analysis=ser,
    )


@router.get("/analysis/{issue_id}", response_model=AIAnalysisEnvelopeResponse)
def get_issue_analysis(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the latest AI analysis for the specified issue.
    Returns has_analysis=False with a clear message if no analysis has been performed yet.
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Civic issue not found.")

    _check_issue_access(issue, current_user, require_authority=False)

    latest = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at), desc(AIAnalysis.id))
        .first()
    )

    if not latest:
        return AIAnalysisEnvelopeResponse(
            has_analysis=False,
            message="AI analysis has not been performed yet.",
            issue_id=issue.id,
            official_values=_build_official_values(issue, db),
            analysis=None,
            latest_analysis=None,
        )

    ser = _serialize_analysis(latest, db, issue, is_citizen=(current_user.role == "CITIZEN"))
    return AIAnalysisEnvelopeResponse(
        has_analysis=True,
        message="Latest AI analysis loaded.",
        issue_id=issue.id,
        official_values=_build_official_values(issue, db),
        analysis=ser,
        latest_analysis=ser,
    )


@router.get("/analysis/{issue_id}/history", response_model=AIAnalysisHistoryResponse)
def get_issue_analysis_history(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns all historical AI analysis runs for an issue without overwriting past records.
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Civic issue not found.")

    _check_issue_access(issue, current_user, require_authority=False)

    records = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at), desc(AIAnalysis.id))
        .all()
    )

    is_cit = current_user.role == "CITIZEN"
    items = [_serialize_analysis(r, db, issue, is_citizen=is_cit) for r in records]

    return AIAnalysisHistoryResponse(
        issue_id=issue.id,
        total=len(items),
        history=items,
    )


@router.post("/reanalyze/{issue_id}", response_model=AIAnalysisEnvelopeResponse)
def reanalyze_issue(
    issue_id: int,
    request: Request,
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Triggers a fresh AI analysis run for an issue and stores a new historical AIAnalysis entry.
    Restricted to authorized municipal officers.
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Civic issue not found.")

    _check_issue_access(issue, current_user, require_authority=True)

    rate_key = f"ai_reanalyze:{current_user.id}"
    ai_rate_limiter.check_and_record(key=rate_key, max_attempts=10, window_seconds=60)
    ai_rate_limiter.record_attempt(rate_key)

    latest = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at), desc(AIAnalysis.id))
        .first()
    )
    if latest and latest.processing_status == "PROCESSING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An AI analysis is already in progress for this issue.",
        )

    analysis = run_issue_ai_analysis(db=db, issue=issue)

    client_ip = request.client.host if request.client else "127.0.0.1"
    db.add(AuditLog(
        user_id=current_user.id,
        action="AI_REANALYSIS_EXECUTED",
        entity_type="issue",
        entity_id=issue.id,
        details=f"Re-analysed Issue #{issue.id} (Analysis #{analysis.id}, status: {analysis.processing_status}).",
        ip_address=client_ip,
    ))
    db.commit()

    ser = _serialize_analysis(analysis, db, issue, is_citizen=False)
    return AIAnalysisEnvelopeResponse(
        has_analysis=True,
        message="Image and report re-analysed successfully.",
        issue_id=issue.id,
        official_values=_build_official_values(issue, db),
        analysis=ser,
        latest_analysis=ser,
    )


@router.post("/analysis/{issue_id}/approve", response_model=AIAnalysisEnvelopeResponse)
def approve_ai_recommendation(
    issue_id: int,
    payload: AIReviewDecisionRequest,
    request: Request,
    current_user: User = Depends(require_department_officer),
    db: Session = Depends(get_db),
):
    """
    Explicitly approves the latest AI recommendation for an issue.
    Applies recommended department, severity, and priority to the official CivicIssue
    record and logs the authority decision in AuditLog.
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Civic issue not found.")

    _check_issue_access(issue, current_user, require_authority=True)

    latest = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at), desc(AIAnalysis.id))
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve recommendation: AI analysis has not been performed yet.",
        )

    changes_applied: List[str] = []

    if payload.apply_department and latest.suggested_department_id:
        dept = db.query(Department).filter(Department.id == latest.suggested_department_id).first()
        if dept:
            issue.department_id = dept.id
            issue.department = dept.name
            changes_applied.append(f"Department -> {dept.name}")

    if payload.apply_severity and latest.suggested_severity:
        mapped_sev = SEVERITY_MAP_TO_ISSUE.get(latest.suggested_severity.upper(), issue.severity)
        issue.severity = mapped_sev
        changes_applied.append(f"Severity -> {mapped_sev}")

    if payload.apply_priority and latest.suggested_priority:
        mapped_prio = PRIORITY_MAP_TO_ISSUE.get(latest.suggested_priority.upper(), issue.priority)
        issue.priority = mapped_prio
        changes_applied.append(f"Priority -> {mapped_prio}")

    latest.review_status = "APPROVED"
    latest.reviewed_by_id = current_user.id
    latest.reviewed_at = datetime.utcnow()
    latest.review_comment = payload.comment or "AI recommendation approved by authority."

    client_ip = request.client.host if request.client else "127.0.0.1"
    summary_str = ", ".join(changes_applied) if changes_applied else "No field overrides selected"
    db.add(AuditLog(
        user_id=current_user.id,
        action="AI_RECOMMENDATION_APPROVED",
        entity_type="issue",
        entity_id=issue.id,
        details=(
            f"Approved AI analysis #{latest.id} for Issue #{issue.id} ({summary_str}). "
            f"Comment: {latest.review_comment}"
        ),
        ip_address=client_ip,
    ))

    db.commit()
    db.refresh(issue)
    db.refresh(latest)

    ser = _serialize_analysis(latest, db, issue, is_citizen=False)
    return AIAnalysisEnvelopeResponse(
        has_analysis=True,
        message="AI recommendation approved and applied to official issue values.",
        issue_id=issue.id,
        official_values=_build_official_values(issue, db),
        analysis=ser,
        latest_analysis=ser,
    )


@router.post("/analysis/{issue_id}/reject", response_model=AIAnalysisEnvelopeResponse)
def reject_ai_recommendation(
    issue_id: int,
    payload: AIReviewDecisionRequest,
    request: Request,
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    """
    Explicitly rejects the latest AI recommendation for an issue without modifying
    official issue values. Records the authority decision in AuditLog.
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Civic issue not found.")

    _check_issue_access(issue, current_user, require_authority=True)

    latest = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at), desc(AIAnalysis.id))
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject recommendation: AI analysis has not been performed yet.",
        )

    if not payload.comment or not payload.comment.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A specific rejection reason is mandatory when rejecting AI recommendations.",
        )

    latest.review_status = "REJECTED"
    latest.reviewed_by_id = current_user.id
    latest.reviewed_at = datetime.utcnow()
    latest.review_comment = payload.comment.strip()

    client_ip = request.client.host if request.client else "127.0.0.1"
    db.add(AuditLog(
        user_id=current_user.id,
        action="AI_RECOMMENDATION_REJECTED",
        entity_type="issue",
        entity_id=issue.id,
        details=f"Rejected AI analysis #{latest.id} for Issue #{issue.id}. Reason: {latest.review_comment}",
        ip_address=client_ip,
    ))

    db.commit()
    db.refresh(latest)

    ser = _serialize_analysis(latest, db, issue, is_citizen=False)
    return AIAnalysisEnvelopeResponse(
        has_analysis=True,
        message="AI recommendation rejected. Official issue values remain unchanged.",
        issue_id=issue.id,
        official_values=_build_official_values(issue, db),
        analysis=ser,
        latest_analysis=ser,
    )


@router.post("/analysis/{issue_id}/false_positive", response_model=AIAnalysisEnvelopeResponse)
def flag_ai_false_positive(
    issue_id: int,
    req: AIFalsePositiveRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows authorized municipal officers to flag a YOLO detection as a false positive.
    Persists feedback in analysis_metadata and logs an audit trail.
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Civic issue #{issue_id} not found.",
        )

    _check_issue_access(issue, current_user, require_authority=True)

    latest = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at))
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No AI analysis found for Issue #{issue_id} to flag.",
        )

    meta = dict(latest.analysis_metadata or {})
    fp_list = list(meta.get("false_positive_feedback") or [])
    fp_entry = {
        "class_name": req.class_name,
        "reason": req.reason,
        "bbox": req.bbox,
        "officer_id": current_user.id,
        "officer_email": current_user.email,
        "created_at": datetime.utcnow().isoformat(),
    }
    fp_list.append(fp_entry)
    meta["false_positive_feedback"] = fp_list
    latest.analysis_metadata = meta
    flag_modified(latest, "analysis_metadata")

    client_ip = request.client.host if request.client else "unknown"
    db.add(AuditLog(
        user_id=current_user.id,
        action="AI_FALSE_POSITIVE_FLAGGED",
        entity_type="issue",
        entity_id=issue.id,
        details=(
            f"Officer {current_user.email} flagged YOLO detection '{req.class_name}' as false positive "
            f"on Issue #{issue.id}. Reason: {req.reason}"
        ),
        ip_address=client_ip,
    ))

    db.commit()
    db.refresh(latest)

    ser = _serialize_analysis(latest, db, issue, is_citizen=False)
    return AIAnalysisEnvelopeResponse(
        has_analysis=True,
        message=f"False positive feedback recorded for detection '{req.class_name}'.",
        issue_id=issue.id,
        official_values=_build_official_values(issue, db),
        analysis=ser,
        latest_analysis=ser,
    )


@router.post("/analysis/{issue_id}/link_duplicate", response_model=AIAnalysisEnvelopeResponse)
def link_or_merge_duplicate(
    issue_id: int,
    req: AIDuplicateLinkRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows authorized officers to associate or merge a duplicate report with an existing primary issue.
    Enforces audit logging and role restrictions for merges.
    """
    issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Civic issue #{issue_id} not found.",
        )

    _check_issue_access(issue, current_user, require_authority=True)

    primary = db.query(CivicIssue).filter(CivicIssue.id == req.primary_issue_id).first()
    if not primary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Primary civic issue #{req.primary_issue_id} not found.",
        )

    if primary.id == issue.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link an issue as a duplicate of itself.",
        )

    action_type = req.action.strip().upper()
    if action_type not in {"LINK", "MERGE"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action type. Must be 'LINK' or 'MERGE'.",
        )

    latest = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.issue_id == issue_id)
        .order_by(desc(AIAnalysis.created_at))
        .first()
    )
    if not latest:
        # Create minimal analysis record if none exists yet
        latest = AIAnalysis(
            issue_id=issue.id,
            model_name="Manual-Authority",
            model_version="1.0.0",
            processing_status="COMPLETED",
            review_status="PENDING",
        )
        db.add(latest)
        db.flush()

    meta = dict(latest.analysis_metadata or {})
    meta["duplicate_link"] = {
        "primary_issue_id": primary.id,
        "action": action_type,
        "notes": req.notes,
        "officer_id": current_user.id,
        "officer_email": current_user.email,
        "linked_at": datetime.utcnow().isoformat(),
    }
    latest.analysis_metadata = meta
    flag_modified(latest, "analysis_metadata")

    client_ip = request.client.host if request.client else "unknown"

    if action_type == "MERGE":
        if current_user.role not in {"DEPARTMENT_OFFICER", "SUPER_ADMIN"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Merging issues requires DEPARTMENT_OFFICER or SUPER_ADMIN role.",
            )
        old_status = issue.status
        issue.status = "Resolved"
        issue.resolution_notes = f"Merged into primary Issue #{primary.id}. Notes: {req.notes or 'Corroborating duplicate report'}"
        issue.resolved_at = datetime.utcnow()
        issue.resolved_by_id = current_user.id

        db.add(IssueStatusHistory(
            issue_id=issue.id,
            from_status=old_status,
            to_status="Resolved",
            changed_by_id=current_user.id,
            comment=f"Duplicate merged into Issue #{primary.id}. Notes: {req.notes or 'Resolved as duplicate'}",
        ))

    db.add(AuditLog(
        user_id=current_user.id,
        action=f"ISSUE_DUPLICATE_{action_type}",
        entity_type="issue",
        entity_id=issue.id,
        details=(
            f"Officer {current_user.email} executed {action_type} for Issue #{issue.id} "
            f"pointing to primary Issue #{primary.id}. Notes: {req.notes}"
        ),
        ip_address=client_ip,
    ))

    db.commit()
    db.refresh(latest)

    ser = _serialize_analysis(latest, db, issue, is_citizen=False)
    return AIAnalysisEnvelopeResponse(
        has_analysis=True,
        message=f"Duplicate action '{action_type}' recorded successfully with primary Issue #{primary.id}.",
        issue_id=issue.id,
        official_values=_build_official_values(issue, db),
        analysis=ser,
        latest_analysis=ser,
    )


@router.post("/maintenance/recover", tags=["AI Civic Intelligence"])
def trigger_ai_recovery(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Administrative maintenance endpoint to recover orphaned PENDING records
    and stale PROCESSING records after worker restarts or Redis reconnection.
    """
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only SUPER_ADMIN accounts can trigger AI maintenance recovery.",
        )

    from .tasks import recover_pending_or_stale_analyses
    result = recover_pending_or_stale_analyses()
    return {
        "status": "SUCCESS",
        "message": "AI maintenance recovery executed.",
        "details": result,
    }

