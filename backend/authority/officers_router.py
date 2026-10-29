"""
CIVICSOL - Authority Officer Account Management Router
Provides secure officer provisioning, role assignments, and lifecycle management.
"""

import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.auth.security import hash_password
from backend.database import get_db
from backend.models import AuditLog, Department, User

from .dependencies import (
    require_department_officer,
    require_super_admin,
)
from .schemas import (
    OfficerCreateRequest,
    OfficerResponse,
    OfficerUpdateRequest,
)


router = APIRouter(
    prefix="/authority/officers",
    tags=["Authority Officers"],
)


def generate_officer_employee_id(db: Session, role: str) -> str:
    """Generate unique employee ID based on role prefix."""
    prefix = "DEP" if role == "DEPARTMENT_OFFICER" else "FLD"
    while True:
        candidate = f"{prefix}-{secrets.randbelow(90000) + 10000}"
        if not db.query(User).filter(User.employee_id == candidate).first():
            return candidate


def generate_officer_citizen_id(db: Session) -> str:
    """Generate unique citizen ID for the officer account."""
    while True:
        candidate = f"CIVIC-OFF{secrets.randbelow(90000) + 10000}"
        if not db.query(User).filter(User.citizen_id == candidate).first():
            return candidate


@router.get("/", response_model=List[OfficerResponse])
def list_officers(
    role: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_department_officer),
    db: Session = Depends(get_db),
):
    """
    List authority officers with role, department, and active status filters.
    Department officers can only view officers in their department.
    Super Admins can view all authority officers.
    Never returns citizen accounts or password hashes.
    """
    query = db.query(User).filter(User.role.in_(["SUPER_ADMIN", "DEPARTMENT_OFFICER", "FIELD_OFFICER"]))

    # Scoping
    if current_user.role == "DEPARTMENT_OFFICER":
        if current_user.department_id:
            query = query.filter(User.department_id == current_user.department_id)
        else:
            query = query.filter(User.id == current_user.id)

    if role:
        query = query.filter(User.role == role.upper())
    if department_id:
        query = query.filter(User.department_id == department_id)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            User.name.ilike(s)
            | User.email.ilike(s)
            | User.mobile.ilike(s)
            | User.employee_id.ilike(s)
        )

    officers = query.order_by(User.name.asc()).all()
    results = []

    for o in officers:
        dept_name = o.department.name if o.department else None
        results.append(
            OfficerResponse(
                id=o.id,
                name=o.name,
                email=o.email,
                mobile=o.mobile,
                role=o.role,
                employee_id=o.employee_id,
                designation=o.designation,
                department_id=o.department_id,
                department_name=dept_name,
                is_active=o.is_active,
                created_at=o.created_at,
            )
        )

    return results


@router.post("/", response_model=OfficerResponse, status_code=status.HTTP_201_CREATED)
def create_officer(
    payload: OfficerCreateRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Provision a new authority officer account. Super Admin only.
    No public registration is ever permitted.
    """
    target_role = payload.role.strip().upper()
    if target_role not in ["DEPARTMENT_OFFICER", "FIELD_OFFICER"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'DEPARTMENT_OFFICER' or 'FIELD_OFFICER'.",
        )

    clean_mobile = payload.mobile.strip()
    clean_email = payload.email.strip().lower() if payload.email else None

    if db.query(User).filter(User.mobile == clean_mobile).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mobile number '{clean_mobile}' is already registered.",
        )

    if clean_email and db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email address '{clean_email}' is already registered.",
        )

    # Department validation
    dept_name = None
    if payload.department_id:
        dept = db.query(Department).filter(Department.id == payload.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with ID {payload.department_id} does not exist.",
            )
        dept_name = dept.name

    employee_id = (
        payload.employee_id.strip()
        if payload.employee_id
        else generate_officer_employee_id(db, target_role)
    )

    if db.query(User).filter(User.employee_id == employee_id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee ID '{employee_id}' is already assigned to another account.",
        )

    password_hash = hash_password(payload.password)
    citizen_id = generate_officer_citizen_id(db)

    officer = User(
        name=payload.name.strip(),
        mobile=clean_mobile,
        email=clean_email,
        password_hash=password_hash,
        citizen_id=citizen_id,
        role=target_role,
        department_id=payload.department_id,
        designation=payload.designation.strip() if payload.designation else None,
        employee_id=employee_id,
        is_active=True,
    )

    db.add(officer)
    db.flush()

    # Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="OFFICER_PROVISIONED",
        entity_type="user",
        entity_id=officer.id,
        details=f"Provisioned officer {officer.name} ({officer.role}, Emp: {officer.employee_id}) in Dept {payload.department_id}.",
        ip_address=client_ip,
    )
    db.add(audit)
    db.commit()
    db.refresh(officer)

    return OfficerResponse(
        id=officer.id,
        name=officer.name,
        email=officer.email,
        mobile=officer.mobile,
        role=officer.role,
        employee_id=officer.employee_id,
        designation=officer.designation,
        department_id=officer.department_id,
        department_name=dept_name,
        is_active=officer.is_active,
        created_at=officer.created_at,
    )


@router.put("/{officer_id}", response_model=OfficerResponse)
def update_officer(
    officer_id: int,
    payload: OfficerUpdateRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Update officer role, department, designation, or active status. Super Admin only.
    Protects the final active Super Admin against accidental deactivation.
    """
    officer = db.query(User).filter(User.id == officer_id).first()
    if not officer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Officer account not found.",
        )

    # Protect the final active Super Admin
    if officer.role == "SUPER_ADMIN":
        if payload.is_active is False or (payload.role and payload.role != "SUPER_ADMIN"):
            active_super_admins = (
                db.query(User)
                .filter(User.role == "SUPER_ADMIN", User.is_active == True)
                .count()
            )
            if active_super_admins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate or change the role of the final active Super Admin account.",
                )

    if payload.name:
        officer.name = payload.name.strip()
    if payload.email is not None:
        officer.email = payload.email.strip().lower() if payload.email else None
    if payload.role:
        new_role = payload.role.strip().upper()
        if new_role not in ["SUPER_ADMIN", "DEPARTMENT_OFFICER", "FIELD_OFFICER"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role specified.",
            )
        officer.role = new_role
    if payload.department_id is not None:
        if payload.department_id > 0:
            dept = db.query(Department).filter(Department.id == payload.department_id).first()
            if not dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Department not found.",
                )
            officer.department_id = payload.department_id
        else:
            officer.department_id = None
    if payload.designation is not None:
        officer.designation = payload.designation.strip()
    if payload.is_active is not None:
        officer.is_active = payload.is_active

    # Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="OFFICER_UPDATED",
        entity_type="user",
        entity_id=officer.id,
        details=f"Updated officer {officer.name} ({officer.employee_id}). Active: {officer.is_active}, Role: {officer.role}.",
        ip_address=client_ip,
    )
    db.add(audit)
    db.commit()
    db.refresh(officer)

    dept_name = officer.department.name if officer.department else None

    return OfficerResponse(
        id=officer.id,
        name=officer.name,
        email=officer.email,
        mobile=officer.mobile,
        role=officer.role,
        employee_id=officer.employee_id,
        designation=officer.designation,
        department_id=officer.department_id,
        department_name=dept_name,
        is_active=officer.is_active,
        created_at=officer.created_at,
    )
