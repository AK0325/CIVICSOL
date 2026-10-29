"""
CIVICSOL - Notification Router
Provides citizen and authority officer in-app notification retrieval and status management.
Restricted: users can ONLY access and update their own notifications.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database import get_db
from backend.models import Notification, User
from .schemas import NotificationListResponse, NotificationResponse

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get("/", response_model=NotificationListResponse)
def get_user_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve in-app notifications for the authenticated user.
    Enforces strict user isolation.
    """
    base_query = db.query(Notification).filter(Notification.user_id == current_user.id)

    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .count()
    )

    if unread_only:
        base_query = base_query.filter(Notification.is_read == False)

    total = base_query.count()
    records = base_query.order_by(desc(Notification.created_at)).limit(limit).all()

    return NotificationListResponse(
        total=total,
        unread_count=unread_count,
        notifications=records,
    )


@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Quick count of unread notifications for badge rendering.
    """
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .count()
    )
    return {"unread_count": count}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark a specific notification as read.
    Validates ownership; returns 404/403 if not found or unauthorized.
    """
    notif = db.query(Notification).filter(Notification.id == notification_id).first()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if notif.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this notification.",
        )

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark all notifications for the authenticated user as read.
    """
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == False)
        .update({Notification.is_read: True})
    )
    db.commit()
    return {"message": "All notifications marked as read.", "count": updated}
