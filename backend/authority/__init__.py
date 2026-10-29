"""
CIVICSOL - Authority Module
Exports authority routers and RBAC dependencies.
"""

from .auth_router import router as authority_auth_router
from .issues_router import router as authority_issues_router
from .stats_router import router as authority_stats_router
from .departments_router import router as authority_departments_router
from .officers_router import router as authority_officers_router
from .map_router import router as authority_map_router
from .audit_router import router as authority_audit_router

__all__ = [
    "authority_auth_router",
    "authority_issues_router",
    "authority_stats_router",
    "authority_departments_router",
    "authority_officers_router",
    "authority_map_router",
    "authority_audit_router",
]
