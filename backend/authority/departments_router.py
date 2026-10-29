"""
CIVICSOL - Authority Department Management Router
Provides municipal department administration and directory services.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuditLog, CivicIssue, Department, User

from .dependencies import (
    require_field_officer_or_higher,
    require_super_admin,
)
from .schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)


router = APIRouter(
    prefix="/authority/departments",
    tags=["Authority Departments"],
)


@router.get("/", response_model=List[DepartmentResponse])
def list_departments(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_field_officer_or_higher),
    db: Session = Depends(get_db),
):
    query = db.query(Department)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(Department.name.ilike(s) | Department.code.ilike(s))

    if is_active is not None:
        query = query.filter(Department.is_active == is_active)

    depts = query.order_by(Department.name.asc()).all()
    results = []

    for d in depts:
        officer_count = (
            db.query(User)
            .filter(User.department_id == d.id, User.is_active == True)
            .count()
        )
        open_count = (
            db.query(CivicIssue)
            .filter(
                CivicIssue.department_id == d.id,
                CivicIssue.status.notin_(["Resolved", "Rejected"]),
            )
            .count()
        )
        results.append(
            DepartmentResponse(
                id=d.id,
                name=d.name,
                code=d.code,
                description=d.description,
                contact_email=d.contact_email,
                contact_phone=d.contact_phone,
                is_active=d.is_active,
                created_at=d.created_at,
                updated_at=d.updated_at,
                active_officers_count=officer_count,
                open_issues_count=open_count,
            )
        )

    return results


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreateRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    code_clean = payload.code.strip().upper()
    name_clean = payload.name.strip()

    if db.query(Department).filter(Department.code == code_clean).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Department with code '{code_clean}' already exists.",
        )

    if db.query(Department).filter(Department.name == name_clean).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Department with name '{name_clean}' already exists.",
        )

    dept = Department(
        name=name_clean,
        code=code_clean,
        description=payload.description.strip() if payload.description else None,
        contact_email=payload.contact_email.strip() if payload.contact_email else None,
        contact_phone=payload.contact_phone.strip() if payload.contact_phone else None,
        is_active=payload.is_active,
    )
    db.add(dept)
    db.flush()

    # Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="DEPARTMENT_CREATED",
        entity_type="department",
        entity_id=dept.id,
        details=f"Created department {dept.name} ({dept.code}).",
        ip_address=client_ip,
    )
    db.add(audit)
    db.commit()
    db.refresh(dept)

    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        contact_email=dept.contact_email,
        contact_phone=dept.contact_phone,
        is_active=dept.is_active,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
        active_officers_count=0,
        open_issues_count=0,
    )


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdateRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    dept = db.query(Department).filter(Department.id == department_id).first()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    # Deactivation check
    if payload.is_active is False and dept.is_active is True:
        open_count = (
            db.query(CivicIssue)
            .filter(
                CivicIssue.department_id == dept.id,
                CivicIssue.status.notin_(["Resolved", "Rejected"]),
            )
            .count()
        )
        if open_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot deactivate department '{dept.name}'. It currently has {open_count} unresolved civic issues. Please reassign those issues first.",
            )

    if payload.name:
        dept.name = payload.name.strip()
    if payload.description is not None:
        dept.description = payload.description.strip()
    if payload.contact_email is not None:
        dept.contact_email = payload.contact_email.strip()
    if payload.contact_phone is not None:
        dept.contact_phone = payload.contact_phone.strip()
    if payload.is_active is not None:
        dept.is_active = payload.is_active

    dept.updated_at = datetime.utcnow()

    # Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="DEPARTMENT_UPDATED",
        entity_type="department",
        entity_id=dept.id,
        details=f"Updated department {dept.name} ({dept.code}). Active status: {dept.is_active}.",
        ip_address=client_ip,
    )
    db.add(audit)
    db.commit()
    db.refresh(dept)

    officer_count = (
        db.query(User)
        .filter(User.department_id == dept.id, User.is_active == True)
        .count()
    )
    open_count = (
        db.query(CivicIssue)
        .filter(
            CivicIssue.department_id == dept.id,
            CivicIssue.status.notin_(["Resolved", "Rejected"]),
        )
        .count()
    )

    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        contact_email=dept.contact_email,
        contact_phone=dept.contact_phone,
        is_active=dept.is_active,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
        active_officers_count=officer_count,
        open_issues_count=open_count,
    )
