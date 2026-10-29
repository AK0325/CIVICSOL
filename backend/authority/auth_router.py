"""
CIVICSOL - Authority Authentication Router
Provides official authority sign-in, session profile, and role verification.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.auth.security import create_access_token, verify_password
from backend.database import get_db
from backend.models import AuditLog, Department, User

from .dependencies import get_current_authority_user, get_role_permissions
from .schemas import (
    AuthorityLoginRequest,
    AuthorityLoginResponse,
    AuthorityProfileResponse,
)


router = APIRouter(
    prefix="/authority/auth",
    tags=["Authority Authentication"],
)


from backend.core.config import settings
from backend.core.rate_limiter import login_rate_limiter


@router.post(
    "/login",
    response_model=AuthorityLoginResponse,
)
def authority_login(
    payload: AuthorityLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Authenticate an authority officer using Employee ID, Official Email, or Mobile.
    Rejects CITIZEN accounts with HTTP 403.
    Rejects deactivated accounts.
    Uses centralized JWT configuration and does not reveal whether account exists on bad credentials.
    Protected with brute-force sliding window rate limiting.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    raw_ident = payload.identifier.strip()
    ident_lower = raw_ident.lower()
    rate_key = f"authority_login:{client_ip}:{ident_lower}"

    login_rate_limiter.check_and_record(
        key=rate_key,
        max_attempts=settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    )

    # Query by employee_id, email, or mobile
    user = (
        db.query(User)
        .filter(
            (User.employee_id == raw_ident)
            | (User.email == ident_lower)
            | (User.mobile == raw_ident)
        )
        .first()
    )

    if not user or not verify_password(payload.password, user.password_hash):
        login_rate_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid official identifier or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset rate limiting counter on valid credential verification
    login_rate_limiter.reset(rate_key)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authority account has been deactivated. Please contact your municipal administrator.",
        )

    if user.role == "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Citizen accounts cannot log in to the Authority Command Center.",
        )

    # Resolve department name if assigned
    dept_name = None
    if user.department_id:
        dept = db.query(Department).filter(Department.id == user.department_id).first()
        if dept:
            dept_name = dept.name

    # Create access token with centralized security settings
    token_claims = {
        "sub": str(user.id),
        "role": user.role,
        "department_id": user.department_id,
        "employee_id": user.employee_id,
        "name": user.name,
    }
    access_token = create_access_token(data=token_claims)

    # Record login audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit_entry = AuditLog(
        user_id=user.id,
        action="AUTHORITY_LOGIN",
        entity_type="user",
        entity_id=user.id,
        details=f"Officer {user.name} ({user.role}) logged in.",
        ip_address=client_ip,
    )
    db.add(audit_entry)
    db.commit()

    return AuthorityLoginResponse(
        message="Authority authenticated successfully.",
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        name=user.name,
        role=user.role,
        department_id=user.department_id,
        department_name=dept_name,
        employee_id=user.employee_id,
        designation=user.designation,
    )


@router.get(
    "/me",
    response_model=AuthorityProfileResponse,
)
def get_authority_profile(
    current_user: User = Depends(get_current_authority_user),
    db: Session = Depends(get_db),
):
    """
    Returns verified profile, role, department, and granted permissions for the authenticated authority.
    """
    dept_name = None
    if current_user.department_id:
        dept = db.query(Department).filter(Department.id == current_user.department_id).first()
        if dept:
            dept_name = dept.name

    permissions = get_role_permissions(current_user.role)

    return AuthorityProfileResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        mobile=current_user.mobile,
        role=current_user.role,
        employee_id=current_user.employee_id,
        designation=current_user.designation,
        department_id=current_user.department_id,
        department_name=dept_name,
        is_active=current_user.is_active,
        permissions=permissions,
        created_at=current_user.created_at,
    )
