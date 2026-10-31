"""
CIVICSOL - Notification Service
Handles in-app notifications and safe, non-blocking email delivery.
Ensures notification dispatch errors never roll back or disrupt the primary business transactions.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models import Notification, User


def create_in_app_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str,
    entity_type: Optional[str] = "CIVIC_ISSUE",
    entity_id: Optional[int] = None,
) -> Optional[Notification]:
    """
    Persist an in-app notification for a citizen or authority officer.
    Safely flushes and traps any local exceptions so the parent transaction is never invalidated.
    """
    if not user_id:
        return None

    try:
        notif = Notification(
            user_id=user_id,
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type.strip(),
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
        )
        db.add(notif)
        db.flush()
        return notif
    except Exception as exc:
        # Non-blocking: log safely without breaking primary operation
        print(f"[NOTIFICATION WARNING] Failed to create in-app notification: {exc}")
        return None


def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
) -> bool:
    """
    Attempt to send an email notification if SMTP is configured.
    Fail-safe: never exposes credentials or causes unhandled exceptions.
    """
    if not to_email or not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        # Email delivery not configured or destination missing; silently skip
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME}>"
        msg["To"] = to_email

        # Clean plain text part
        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], [to_email], msg.as_string())
        return True
    except Exception as exc:
        # Log sanitized notification warning
        print(f"[EMAIL NOTIFICATION WARNING] Failed to deliver email: {type(exc).__name__}")
        return False


def notify_citizen_and_officer(
    db: Session,
    citizen: Optional[User],
    officer: Optional[User],
    event: str,
    issue_id: int,
    issue_title: str,
    details: Optional[dict] = None,
):
    """
    Central dispatcher for civic issue lifecycle events.
    Events supported:
    - 'ASSIGNED'
    - 'STATUS_UPDATED'
    - 'RESOLVED'
    - 'REJECTED'
    - 'REOPENED'
    """
    details = details or {}

    # 1. Citizen Notification
    if citizen and citizen.id:
        if event == "ASSIGNED":
            dept_name = details.get("department_name", "Municipal Operations")
            title = f"Report #{issue_id} Assigned"
            msg = f"Your report '{issue_title}' has been dispatched to {dept_name} for active remediation."
        elif event == "STATUS_UPDATED":
            new_status = details.get("to_status", "Updated")
            title = f"Report #{issue_id} Status Updated"
            msg = f"Your report '{issue_title}' status has changed to: {new_status}."
        elif event == "RESOLVED":
            title = f"Report #{issue_id} Successfully Resolved!"
            msg = f"Your report '{issue_title}' has been verified and resolved by municipal authorities. +20 Civic Credits have been credited to your account!"
        elif event == "REJECTED":
            reason = details.get("reason", "Not provided")
            title = f"Report #{issue_id} Review Update"
            msg = f"Your report '{issue_title}' was reviewed and closed: {reason}."
        elif event == "REOPENED":
            title = f"Report #{issue_id} Reopened"
            msg = f"Your report '{issue_title}' has been reopened for additional inspection."
        elif event == "AI_ANALYSIS_COMPLETED":
            category = details.get("predicted_category", "Identified hazard")
            confidence = details.get("confidence_percent", "")
            conf_str = f" ({confidence}% confidence)" if confidence else ""
            title = f"AI Triage Completed: Report #{issue_id}"
            msg = f"Automated AI visual analysis for your report '{issue_title}' has completed: classified as {category}{conf_str}. Recommendations have been submitted for municipal authority review."
        elif event == "AI_ANALYSIS_FAILED":
            title = f"AI Triage Notice: Report #{issue_id}"
            msg = f"Automated visual analysis for your report '{issue_title}' could not be finalized. Your report remains securely filed and will be prioritized for manual officer review."
        else:
            title = f"Update on Report #{issue_id}"
            msg = f"There is a new administrative update on your civic issue report '{issue_title}'."

        create_in_app_notification(
            db=db,
            user_id=citizen.id,
            title=title,
            message=msg,
            notification_type=f"ISSUE_{event}",
            entity_type="CIVIC_ISSUE",
            entity_id=issue_id,
        )

        if citizen.email:
            send_email_notification(
                to_email=citizen.email,
                subject=f"CIVICSOL: {title}",
                body=f"Hello {citizen.name},\n\n{msg}\n\nTrack your report at http://localhost:5173/my-reports\n\nThank you,\nCIVICSOL Municipal Authority",
            )

    # 2. Officer Notification (when an issue is assigned to them)
    if officer and officer.id and event == "ASSIGNED":
        officer_title = f"New Work Assignment: Issue #{issue_id}"
        officer_msg = f"You have been assigned civic issue #{issue_id} ('{issue_title}'). Please review the dossier and schedule field remediation."
        
        create_in_app_notification(
            db=db,
            user_id=officer.id,
            title=officer_title,
            message=officer_msg,
            notification_type="OFFICER_ASSIGNED",
            entity_type="CIVIC_ISSUE",
            entity_id=issue_id,
        )

        if officer.email:
            send_email_notification(
                to_email=officer.email,
                subject=f"CIVICSOL Dispatch: {officer_title}",
                body=f"Officer {officer.name},\n\n{officer_msg}\n\nAccess dossier at http://localhost:5173/authority/issues/{issue_id}\n\nCIVICSOL Command Center",
            )
