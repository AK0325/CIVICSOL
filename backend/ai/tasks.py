"""
CIVICSOL - Celery AI Asynchronous Processing Tasks
Provides background execution for computer vision and LLM triage with:
1. Atomic PostgreSQL task claiming via row-level locking (SELECT ... FOR UPDATE).
2. Distributed Redis lock with continuous background lease renewal for long-running AI inference.
3. Safe Celery retry handling that supports re-entering PROCESSING states.
4. Automatic stale task recovery for worker crash/restart scenarios.
5. In-app and email notification dispatch with duplicate suppression.
"""

import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from celery.exceptions import MaxRetriesExceededError
import redis

from backend.core.celery_app import celery_app
from backend.core.config import settings
from backend.database import SessionLocal
from backend.models import AIAnalysis, CivicIssue, User
from backend.notifications.service import notify_citizen_and_officer

from .pipeline import run_issue_ai_analysis

logger = logging.getLogger("civicsol.ai_tasks")
logger.setLevel(logging.INFO)

# Transient exception types eligible for automatic Celery retries
TRANSIENT_ERRORS = (
    TimeoutError,
    ConnectionError,
    OSError,
)


class LeaseRenewer:
    """
    Background daemon thread that continuously renews a Redis lock lease
    and updates the database heartbeat while AI inference is executing.
    Prevents lock expiration if deep learning or LLM inference exceeds 120 seconds.
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis],
        lock_key: str,
        lock_token: str,
        analysis_id: int,
        interval: float = 25.0,
        lease_seconds: int = 120,
    ):
        self.redis_client = redis_client
        self.lock_key = lock_key
        self.lock_token = lock_token
        self.analysis_id = analysis_id
        self.interval = interval
        self.lease_seconds = lease_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _run(self):
        while not self._stop_event.wait(self.interval):
            try:
                # 1. Renew Redis lock TTL
                if self.redis_client:
                    val = self.redis_client.get(self.lock_key)
                    if val and val.decode("utf-8") == self.lock_token:
                        self.redis_client.expire(self.lock_key, self.lease_seconds)

                # 2. Update PostgreSQL heartbeat
                db = SessionLocal()
                try:
                    analysis = db.query(AIAnalysis).filter(AIAnalysis.id == self.analysis_id).first()
                    if analysis and analysis.processing_status == "PROCESSING":
                        meta = dict(analysis.analysis_metadata or {})
                        claim = dict(meta.get("claim") or {})
                        claim["heartbeat_at"] = datetime.now(timezone.utc).isoformat()
                        meta["claim"] = claim
                        analysis.analysis_metadata = meta
                        db.commit()
                except Exception as db_exc:
                    logger.warning(f"LeaseRenewer DB heartbeat warning: {db_exc}")
                    db.rollback()
                finally:
                    db.close()
            except Exception as exc:
                logger.warning(f"LeaseRenewer error renewing lease: {exc}")

    def __enter__(self):
        if self.redis_client:
            self._thread = threading.Thread(target=self._run, daemon=True, name="LeaseRenewer")
            self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)


def _get_redis_client() -> Optional[redis.Redis]:
    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=2)
        r.ping()
        return r
    except Exception:
        return None


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="civicsol.process_issue_ai",
)
def process_issue_ai_task(self, issue_id: int, analysis_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Asynchronous Celery background task executing AI analysis on a civic issue report.
    Guarantees:
    - Atomic PostgreSQL state claiming (with_for_update)
    - Redis distributed lock with dynamic lease renewal
    - Safe Celery retry resumption
    - Stale record recovery
    - Single citizen notification dispatch
    """
    logger.info(f"Task {self.request.id}: Started processing AI for issue #{issue_id} (analysis_id={analysis_id})")
    db = SessionLocal()
    r = _get_redis_client()
    lock_key = f"lock:ai:issue:{issue_id}"
    lock_token = str(uuid.uuid4())
    redis_lock_acquired = False

    try:
        # =========================================================
        # 1. ATOMIC POSTGRESQL CLAIM & STATE VALIDATION
        # =========================================================
        # Row-level lock ensures only one worker transaction can inspect/update this record at a time
        query = db.query(AIAnalysis)
        if analysis_id:
            query = query.filter(AIAnalysis.id == analysis_id)
        else:
            query = query.filter(AIAnalysis.issue_id == issue_id).order_by(AIAnalysis.created_at.desc())

        analysis = query.with_for_update().first()

        if not analysis:
            # Create PENDING record if none exists
            issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
            if not issue:
                logger.error(f"Issue #{issue_id} not found. Aborting AI processing.")
                return {"status": "ISSUE_NOT_FOUND", "issue_id": issue_id}
            analysis = AIAnalysis(
                issue_id=issue.id,
                model_name="CivicYOLO-v8",
                model_version="1.0.0",
                processing_status="PENDING",
                review_status="PENDING",
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)

        # ---------------------------------------------------------
        # Check current processing state
        # ---------------------------------------------------------
        if analysis.processing_status in {"COMPLETED", "NO_DETECTION"}:
            logger.info(f"Task {self.request.id}: Analysis #{analysis.id} already {analysis.processing_status}. Skipping duplicate.")
            return {
                "status": "ALREADY_COMPLETED",
                "issue_id": issue_id,
                "analysis_id": analysis.id,
            }

        meta = dict(analysis.analysis_metadata or {})
        claim = dict(meta.get("claim") or {})
        now_dt = datetime.now(timezone.utc)

        if analysis.processing_status == "PROCESSING":
            is_celery_retry = (self.request.retries > 0)
            is_same_task = (claim.get("task_id") == self.request.id)
            
            # Check for stale heartbeat (e.g. worker process crashed)
            heartbeat_str = claim.get("heartbeat_at") or claim.get("claimed_at")
            is_stale = False
            if heartbeat_str:
                try:
                    hb_dt = datetime.fromisoformat(heartbeat_str.replace("Z", "+00:00"))
                    if (now_dt - hb_dt).total_seconds() > settings.AI_STALE_PROCESSING_TIMEOUT_SECONDS:
                        is_stale = True
                except Exception:
                    is_stale = True
            else:
                is_stale = True

            # If not a retry and not stale, another worker is actively holding it
            if not (is_celery_retry or is_same_task or is_stale):
                logger.warning(f"Task {self.request.id}: Analysis #{analysis.id} is actively being processed by another worker. Exiting.")
                return {
                    "status": "ALREADY_PROCESSING",
                    "issue_id": issue_id,
                    "analysis_id": analysis.id,
                }
            logger.info(f"Task {self.request.id}: Resuming PROCESSING analysis #{analysis.id} (retry={is_celery_retry}, stale={is_stale})")

        # Atomically claim the task
        analysis.processing_status = "PROCESSING"
        claim.update({
            "task_id": self.request.id or str(uuid.uuid4()),
            "worker_id": getattr(self.request, "hostname", "worker-local"),
            "claimed_at": now_dt.isoformat(),
            "heartbeat_at": now_dt.isoformat(),
            "retry_count": self.request.retries,
        })
        meta["claim"] = claim
        analysis.analysis_metadata = meta
        db.commit()
        db.refresh(analysis)

        # =========================================================
        # 2. REDIS DISTRIBUTED LOCK SAFEGUARD
        # =========================================================
        if r:
            try:
                redis_lock_acquired = bool(r.set(lock_key, lock_token, nx=True, ex=settings.AI_PROCESSING_LEASE_SECONDS))
                if not redis_lock_acquired and not (self.request.retries > 0):
                    # Outer lock held; let lease expire or wait
                    logger.warning(f"Redis lock key {lock_key} held by another process.")
            except Exception as r_err:
                logger.warning(f"Redis lock check skipped due to Redis error: {r_err}")

        # =========================================================
        # 3. EXECUTE AI PIPELINE WITH DYNAMIC LEASE RENEWAL
        # =========================================================
        issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        if not issue:
            analysis.processing_status = "FAILED"
            analysis.explanation = f"CivicIssue #{issue_id} not found during processing."
            db.commit()
            return {"status": "FAILED", "error": "Issue not found"}

        with LeaseRenewer(
            redis_client=r if redis_lock_acquired else None,
            lock_key=lock_key,
            lock_token=lock_token,
            analysis_id=analysis.id,
            interval=25.0,
            lease_seconds=settings.AI_PROCESSING_LEASE_SECONDS,
        ):
            # Run existing tested AI pipeline with existing_analysis_id
            updated_analysis = run_issue_ai_analysis(
                db=db,
                issue=issue,
                existing_analysis_id=analysis.id,
            )

        # =========================================================
        # 4. DISPATCH CITIZEN NOTIFICATION (EXACTLY ONCE)
        # =========================================================
        try:
            db.refresh(updated_analysis)
            post_meta = dict(updated_analysis.analysis_metadata or {})
            if not post_meta.get("notification_sent"):
                citizen = db.query(User).filter(User.id == issue.user_id).first()
                if updated_analysis.processing_status in {"COMPLETED", "NO_DETECTION"}:
                    conf_pct = (
                        int(round(updated_analysis.confidence_score * 100))
                        if updated_analysis.confidence_score is not None
                        else None
                    )
                    notify_citizen_and_officer(
                        db=db,
                        citizen=citizen,
                        officer=None,
                        event="AI_ANALYSIS_COMPLETED",
                        issue_id=issue.id,
                        issue_title=issue.title,
                        details={
                            "predicted_category": updated_analysis.predicted_category,
                            "confidence_percent": conf_pct,
                        },
                    )
                elif updated_analysis.processing_status == "FAILED":
                    notify_citizen_and_officer(
                        db=db,
                        citizen=citizen,
                        officer=None,
                        event="AI_ANALYSIS_FAILED",
                        issue_id=issue.id,
                        issue_title=issue.title,
                    )
                post_meta["notification_sent"] = True
                updated_analysis.analysis_metadata = post_meta
                db.commit()
        except Exception as notif_err:
            logger.warning(f"Notification dispatch error in task {self.request.id}: {notif_err}")

        logger.info(f"Task {self.request.id}: Successfully finished analysis #{updated_analysis.id} with status={updated_analysis.processing_status}")
        return {
            "status": updated_analysis.processing_status,
            "issue_id": issue_id,
            "analysis_id": updated_analysis.id,
            "predicted_category": updated_analysis.predicted_category,
            "suggested_severity": updated_analysis.suggested_severity,
            "suggested_priority": updated_analysis.suggested_priority,
        }

    except TRANSIENT_ERRORS as transient_exc:
        logger.warning(f"Task {self.request.id}: Transient failure on issue #{issue_id}: {transient_exc}. Scheduling retry.")
        db.rollback()
        try:
            # Exponential backoff: 5s, 10s, 20s
            countdown = 5 * (2 ** self.request.retries)
            raise self.retry(exc=transient_exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error(f"Task {self.request.id}: Max retries exceeded for issue #{issue_id}.")
            try:
                if analysis_id:
                    a = db.query(AIAnalysis).filter(AIAnalysis.id == analysis_id).first()
                    if a:
                        a.processing_status = "FAILED"
                        a.explanation = f"AI processing failed after retries: {transient_exc}"
                        db.commit()
            except Exception:
                db.rollback()
            raise

    except Exception as unhandled_exc:
        logger.error(f"Task {self.request.id}: Terminal error processing issue #{issue_id}: {type(unhandled_exc).__name__}: {unhandled_exc}")
        db.rollback()
        try:
            if analysis_id:
                a = db.query(AIAnalysis).filter(AIAnalysis.id == analysis_id).first()
                if a:
                    a.processing_status = "FAILED"
                    a.explanation = f"Terminal failure in background task: {unhandled_exc}"
                    db.commit()
        except Exception:
            db.rollback()
        return {"status": "FAILED", "error": str(unhandled_exc)}

    finally:
        # Release Redis lock if held
        if r and redis_lock_acquired:
            try:
                curr_val = r.get(lock_key)
                if curr_val and curr_val.decode("utf-8") == lock_token:
                    r.delete(lock_key)
            except Exception:
                pass
        db.close()


def recover_pending_or_stale_analyses(
    max_pending_age_seconds: int = 60,
    stale_processing_seconds: int = 180,
    batch_size: int = 50,
) -> Dict[str, Any]:
    """
    Database-backed recovery mechanism for:
    1. PENDING records created when Redis was unavailable.
    2. Stale PROCESSING records left behind after worker crashes or abrupt restarts.
    Identifies eligible records and re-enqueues them to Celery.
    """
    db = SessionLocal()
    r = _get_redis_client()
    redis_available = (r is not None)

    recovered_pending = 0
    recovered_stale = 0
    errors = []

    try:
        now = datetime.utcnow()
        pending_cutoff = now - timedelta(seconds=max_pending_age_seconds)
        stale_cutoff = now - timedelta(seconds=stale_processing_seconds)

        # 1. Recover orphaned PENDING records
        pending_records = (
            db.query(AIAnalysis)
            .filter(
                AIAnalysis.processing_status == "PENDING",
                AIAnalysis.created_at <= pending_cutoff,
            )
            .order_by(AIAnalysis.created_at.asc())
            .limit(batch_size)
            .all()
        )

        for rec in pending_records:
            if redis_available:
                try:
                    process_issue_ai_task.delay(rec.issue_id, rec.id)
                    recovered_pending += 1
                except Exception as exc:
                    errors.append(f"Failed to re-enqueue PENDING #{rec.id}: {exc}")
            else:
                errors.append(f"Cannot recover PENDING #{rec.id}: Redis broker is offline.")

        # 2. Recover stale PROCESSING records
        processing_records = (
            db.query(AIAnalysis)
            .filter(
                AIAnalysis.processing_status == "PROCESSING",
                AIAnalysis.created_at <= stale_cutoff,
            )
            .order_by(AIAnalysis.created_at.asc())
            .limit(batch_size)
            .all()
        )

        for rec in processing_records:
            meta = dict(rec.analysis_metadata or {})
            claim = dict(meta.get("claim") or {})
            hb_str = claim.get("heartbeat_at") or claim.get("claimed_at")
            is_stale = False
            if hb_str:
                try:
                    hb_dt = datetime.fromisoformat(hb_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    if hb_dt <= stale_cutoff:
                        is_stale = True
                except Exception:
                    is_stale = True
            else:
                is_stale = True

            if is_stale:
                if redis_available:
                    try:
                        # Reset status to PENDING and re-enqueue
                        rec.processing_status = "PENDING"
                        claim["recovered_at"] = now.isoformat()
                        meta["claim"] = claim
                        rec.analysis_metadata = meta
                        db.commit()
                        process_issue_ai_task.delay(rec.issue_id, rec.id)
                        recovered_stale += 1
                    except Exception as exc:
                        errors.append(f"Failed to re-enqueue stale #{rec.id}: {exc}")
                else:
                    errors.append(f"Cannot recover stale #{rec.id}: Redis broker is offline.")

        return {
            "redis_available": redis_available,
            "recovered_pending": recovered_pending,
            "recovered_stale": recovered_stale,
            "errors": errors,
        }
    finally:
        db.close()

