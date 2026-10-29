import os
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .core.config import settings
from .core.logging import logger
from .database import Base, engine, get_db
from . import models

# Routers
from .routes.issues import router as issues_router
from .auth.router import router as auth_router
from .rewards.router import router as rewards_router
from .notifications.router import router as notifications_router
from .authority import (
    authority_auth_router,
    authority_issues_router,
    authority_stats_router,
    authority_departments_router,
    authority_officers_router,
    authority_map_router,
    authority_audit_router,
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

UPLOAD_DIR = BASE_DIR / settings.UPLOAD_DIR

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    debug=settings.DEBUG,
)


# =========================================================
# SECURITY HEADERS MIDDLEWARE
# =========================================================

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Apply standard security hardening headers to all HTTP responses.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline';"
    )
    return response


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# SAFE STATIC UPLOADS WITH PATH TRAVERSAL PROTECTION
# =========================================================

@app.get("/uploads/{file_path:path}")
def serve_upload_file(file_path: str):
    """
    Serve uploaded issue evidence and images safely.
    Strictly validates against path traversal (../) attacks.
    """
    clean_path = Path(file_path)
    if ".." in clean_path.parts or clean_path.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )

    target_file = (UPLOAD_DIR / clean_path).resolve()
    if not target_file.is_relative_to(UPLOAD_DIR.resolve()) or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file not found.",
        )

    return FileResponse(target_file)


# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "message": "CIVICSOL API is running",
    }


# =========================================================
# RELIABILITY & HEALTH CHECK ENDPOINT
# =========================================================

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Active health check monitoring database connectivity and storage health.
    Returns 503 if critical dependencies are unreachable.
    """
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {type(exc).__name__}"

    storage_writable = UPLOAD_DIR.exists() and os.access(str(UPLOAD_DIR), os.W_OK)
    storage_status = "writable" if storage_writable else "unwritable"

    is_healthy = (db_status == "healthy") and storage_writable

    payload = {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "checks": {
            "database": db_status,
            "storage": storage_status,
        },
    }

    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=payload,
        )

    return payload


# =========================================================
# API ROUTES
# =========================================================

app.include_router(issues_router)
app.include_router(auth_router)
app.include_router(rewards_router)
app.include_router(notifications_router)

# Authority Command Center routes
app.include_router(authority_auth_router)
app.include_router(authority_issues_router)
app.include_router(authority_stats_router)
app.include_router(authority_departments_router)
app.include_router(authority_officers_router)
app.include_router(authority_map_router)
app.include_router(authority_audit_router)