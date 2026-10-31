"""
CIVICSOL - Celery Application Factory
Configures the distributed asynchronous background task queue with Redis broker,
safe acknowledgments, serialization, and worker resilience settings.
"""

import os
from celery import Celery
from backend.core.config import settings

broker_url = os.getenv("CELERY_BROKER_URL", settings.CELERY_BROKER_URL)
backend_url = os.getenv("CELERY_RESULT_BACKEND", settings.CELERY_RESULT_BACKEND)

celery_app = Celery(
    "civicsol_tasks",
    broker=broker_url,
    backend=backend_url,
    include=["backend.ai.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker and task reliability settings
    task_acks_late=True,  # Acknowledge task only AFTER execution finishes
    task_reject_on_worker_lost=True,  # Re-queue task if worker process is abruptly killed
    worker_prefetch_multiplier=1,  # Distribute tasks fairly across workers
    task_track_started=True,  # Mark task as STARTED when worker begins execution
    task_always_eager=getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False),
    task_eager_propagates=True,
)

