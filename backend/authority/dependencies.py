"""
CIVICSOL - Authority RBAC Dependencies
Enforces server-side authentication and role-based authorization for municipal authorities.
"""

from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.auth.security import decode_access_token
from backend.database import get_db
from backend.models import User


security = HTTPBearer(auto_error=False)


def get_current_authority_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Validates Bearer token, fetches user from database, and verifies:
    1. Token is cryptographically valid and unexpired.
    2. Account exists and is active.
    3. Account possesses an authority role (rejects CITIZEN with HTTP 403).
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authority authentication credentials missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authority authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authority token claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed authority user ID.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authority account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authority account has been deactivated. Contact the system administrator.",
        )

    # Strictly reject citizen users from authority portal
    if user.role == "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Citizen accounts cannot access the Authority Command Center.",
        )

    return user


def require_super_admin(
    current_user: User = Depends(get_current_authority_user),
) -> User:
    """Requires SUPER_ADMIN role for system-wide configuration and management."""
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Super Admin privileges are required for this action.",
        )
    return current_user


def require_department_officer(
    current_user: User = Depends(get_current_authority_user),
) -> User:
    """Requires DEPARTMENT_OFFICER or SUPER_ADMIN role."""
    if current_user.role not in ["SUPER_ADMIN", "DEPARTMENT_OFFICER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Department Officer or Super Admin privileges are required.",
        )
    return current_user


def require_field_officer_or_higher(
    current_user: User = Depends(get_current_authority_user),
) -> User:
    """Requires FIELD_OFFICER, DEPARTMENT_OFFICER, or SUPER_ADMIN role."""
    if current_user.role not in ["SUPER_ADMIN", "DEPARTMENT_OFFICER", "FIELD_OFFICER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Authorized authority officer privileges required.",
        )
    return current_user


def get_role_permissions(role: str) -> List[str]:
    """Returns permission list for an authority role for frontend capability negotiation."""
    if role == "SUPER_ADMIN":
        return [
            "all:access",
            "departments:manage",
            "officers:manage",
            "issues:assign_global",
            "issues:status_all",
            "issues:resolve",
            "stats:global",
            "audit_logs:view",
            "map:global",
        ]
    elif role == "DEPARTMENT_OFFICER":
        return [
            "departments:view",
            "officers:view_department",
            "issues:view_department",
            "issues:assign_department",
            "issues:status_department",
            "issues:resolve",
            "stats:department",
            "map:department",
        ]
    elif role == "FIELD_OFFICER":
        return [
            "issues:view_assigned",
            "issues:status_assigned",
            "issues:resolve_assigned",
            "map:assigned",
        ]
    return []
