"""
CIVICSOL - Asynchronous AI Processing Test Suite
Verifies:
1. Successful background processing and fast citizen submission.
2. Handling of invalid and corrupt images in Celery worker.
3. Resilience when Redis broker is unavailable (graceful fallback & recovery).
4. Worker restart and safe retry resumption for PROCESSING records.
5. Duplicate task delivery idempotency (no duplicate AI records or notifications).
6. Citizen notification dispatch on completion and failure.
7. Safe lease renewal during long-running tasks.
8. Stale PROCESSING record recovery after simulated worker crash.
9. Preservation of official issue fields (AI recommendations remain strictly advisory).
"""

import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image

from backend.ai.tasks import (
    LeaseRenewer,
    process_issue_ai_task,
    recover_pending_or_stale_analyses,
)
from backend.auth.security import create_access_token
from backend.database import Base, SessionLocal, engine
from backend.main import app
from backend.models import (
    AIAnalysis,
    CivicCreditTransaction,
    CivicIssue,
    Notification,
    User,
)


class TestAsyncAIProcessing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Seed test citizen user
        self.user = self.db.query(User).filter(User.email == "citizen_async_test@civicsol.gov").first()
        if not self.user:
            self.user = User(
                name="Async Citizen",
                email="citizen_async_test@civicsol.gov",
                password_hash="test_hashed_password",
                role="CITIZEN",
                citizen_id="CIT-ASYNC-TEST",
                is_active=True,
            )
            self.db.add(self.user)
            self.db.commit()
            self.db.refresh(self.user)

        self.token = create_access_token({
            "sub": str(self.user.id),
            "role": "CITIZEN",
            "citizen_id": self.user.citizen_id,
        })
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db.close()

    def _create_test_image_bytes(self, color=(100, 150, 200), size=(200, 200)) -> bytes:
        import random
        buf = io.BytesIO()
        img = Image.new("RGB", size, color=color)
        img.putpixel((0, 0), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        img.save(buf, format="JPEG")
        return buf.getvalue()

    # =========================================================
    # 1. FAST SUBMISSION & SUCCESSFUL BACKGROUND PROCESSING
    # =========================================================
    def test_01_fast_submission_and_background_processing(self):
        """Citizen submission returns quickly with PENDING status, and background task completes analysis."""
        img_bytes = self._create_test_image_bytes()

        # Submit issue via API
        with patch("backend.ai.tasks.process_issue_ai_task.delay") as mock_delay:
            res = self.client.post(
                "/issues/",
                headers=self.headers,
                files={"image": ("hazard.jpg", img_bytes, "image/jpeg")},
                data={
                    "title": "Async Hazard Road Crack",
                    "description": "Large asphalt road crack observed near crossroad.",
                    "category": "Road Damage",
                    "severity": "Medium",
                    "location": "Sector 4 Crossroad",
                    "latitude": 23.0300,
                    "longitude": 72.5800,
                },
            )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        issue_id = data["issue"]["id"]
        self.assertEqual(data["credits_earned"], 20)
        self.assertEqual(data["ai_analysis"]["processing_status"], "PENDING")
        mock_delay.assert_called_once()

        # Check DB state immediately after submission
        analysis = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue_id).first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.processing_status, "PENDING")

        # Now execute the background Celery task
        task_res = process_issue_ai_task(issue_id=issue_id, analysis_id=analysis.id)
        self.assertIn(task_res["status"], ["COMPLETED", "NO_DETECTION"])

        # Verify DB updated
        self.db.refresh(analysis)
        self.assertIn(analysis.processing_status, ["COMPLETED", "NO_DETECTION"])
        self.assertIsNotNone(analysis.predicted_category)
        self.assertIsNotNone(analysis.suggested_severity)
        self.assertIsNotNone(analysis.suggested_priority)

        # Verify official issue fields were NOT automatically overwritten by AI
        issue = self.db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        self.assertEqual(issue.status, "Reported")
        self.assertEqual(issue.category, "Road Damage")
        self.assertEqual(issue.severity, "Medium")

    # =========================================================
    # 2. INVALID AND CORRUPT IMAGE HANDLING IN WORKER
    # =========================================================
    def test_02_corrupt_image_handling_in_worker(self):
        """Worker handles unreadable image bytes cleanly, setting status to FAILED without crashing."""
        from pathlib import Path
        corrupt_path = Path("uploads/corrupt_image_test_file.jpg")
        corrupt_path.write_bytes(b"INVALID_CORRUPT_BYTES_NOT_A_VALID_IMAGE_FILE")

        issue = CivicIssue(
            title="Corrupt Image Test",
            description="Testing corrupt file handling in async task.",
            category="Garbage",
            severity="Low",
            location="Test Area",
            latitude=23.00,
            longitude=72.00,
            image_path="uploads/corrupt_image_test_file.jpg",
            status="Reported",
            priority="Low",
            user_id=self.user.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        analysis = AIAnalysis(
            issue_id=issue.id,
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            processing_status="PENDING",
            review_status="PENDING",
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Run background task
        res = process_issue_ai_task(issue_id=issue.id, analysis_id=analysis.id)
        self.assertEqual(res["status"], "FAILED")

        self.db.refresh(analysis)
        self.assertEqual(analysis.processing_status, "FAILED")
        self.assertTrue(
            "validation" in analysis.explanation.lower()
            or "failed" in analysis.explanation.lower()
            or "unreadable" in analysis.explanation.lower()
        )

    # =========================================================
    # 3. REDIS BROKER UNAVAILABILITY & DATABASE-BACKED RECOVERY
    # =========================================================
    def test_03_redis_unavailability_and_pending_recovery(self):
        """When Redis is unreachable, submission still succeeds; recovery later picks up PENDING records."""
        img_bytes = self._create_test_image_bytes()

        # Simulate Redis connection failure during Celery dispatch
        with patch("backend.ai.tasks.process_issue_ai_task.delay", side_effect=Exception("Redis connection refused")):
            res = self.client.post(
                "/issues/",
                headers=self.headers,
                files={"image": ("offline.jpg", img_bytes, "image/jpeg")},
                data={
                    "title": "Redis Offline Issue",
                    "description": "Report submitted during Redis broker outage.",
                    "category": "Street Light",
                    "severity": "Low",
                    "location": "Offline Lane",
                    "latitude": 23.0310,
                    "longitude": 72.5810,
                },
            )

        # Submission is still 100% successful
        self.assertEqual(res.status_code, 200)
        data = res.json()
        issue_id = data["issue"]["id"]
        self.assertEqual(data["credits_earned"], 20)
        self.assertEqual(data["ai_analysis"]["processing_status"], "PENDING")

        # Record remains safely stored in DB as PENDING
        analysis = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue_id).first()
        self.assertEqual(analysis.processing_status, "PENDING")

        # Backdate created_at to trigger recovery window (> 60s)
        analysis.created_at = datetime.utcnow() - timedelta(seconds=120)
        self.db.commit()

        # Test recovery mechanism re-enqueuing PENDING record
        with patch("backend.ai.tasks.process_issue_ai_task.delay") as mock_delay:
            recovery_summary = recover_pending_or_stale_analyses(max_pending_age_seconds=60)
            self.assertGreaterEqual(recovery_summary["recovered_pending"], 1)
            mock_delay.assert_called()

    # =========================================================
    # 4. WORKER RESTART & RETRY BEHAVIOUR FOR PROCESSING RECORDS
    # =========================================================
    def test_04_worker_retry_resumption_for_processing_record(self):
        """A Celery retry can resume an analysis even when previously marked PROCESSING."""
        img_bytes = self._create_test_image_bytes()
        issue = CivicIssue(
            title="Retry Test Issue",
            description="Testing retry resumption in worker.",
            category="Road Damage",
            severity="Medium",
            location="Retry Zone",
            latitude=23.01,
            longitude=72.01,
            image_path="uploads/test_retry_img.jpg",
            status="Reported",
            priority="Medium",
            user_id=self.user.id,
        )
        # Write temporary image
        from pathlib import Path
        Path("uploads/test_retry_img.jpg").write_bytes(img_bytes)

        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        analysis = AIAnalysis(
            issue_id=issue.id,
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            processing_status="PROCESSING",  # Already in PROCESSING state
            review_status="PENDING",
            analysis_metadata={
                "claim": {
                    "task_id": "test-task-123",
                    "claimed_at": datetime.now(timezone.utc).isoformat(),
                    "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                    "retry_count": 0,
                }
            },
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Execute Celery task with retries = 1 (representing a Celery retry resumption)
        res = process_issue_ai_task.apply(args=[issue.id, analysis.id], retries=1).result
        self.assertIn(res["status"], ["COMPLETED", "NO_DETECTION"])

        self.db.refresh(analysis)
        self.assertIn(analysis.processing_status, ["COMPLETED", "NO_DETECTION"])

    # =========================================================
    # 5. DUPLICATE TASK DELIVERY & IDEMPOTENCY
    # =========================================================
    def test_05_duplicate_task_delivery_idempotency(self):
        """Duplicate task delivery for an already completed analysis exits early without creating extra rows."""
        img_bytes = self._create_test_image_bytes()
        from pathlib import Path
        Path("uploads/test_duplicate_img.jpg").write_bytes(img_bytes)

        issue = CivicIssue(
            title="Duplicate Test Issue",
            description="Testing idempotency on duplicate task delivery.",
            category="Garbage",
            severity="Medium",
            location="Dupe Zone",
            latitude=23.01,
            longitude=72.01,
            image_path="uploads/test_duplicate_img.jpg",
            status="Reported",
            priority="Medium",
            user_id=self.user.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        analysis = AIAnalysis(
            issue_id=issue.id,
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            processing_status="COMPLETED",
            review_status="PENDING",
            predicted_category="Garbage",
            suggested_severity="MEDIUM",
            suggested_priority="NORMAL",
            analysis_metadata={"notification_sent": True},
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        initial_count = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue.id).count()

        # Simulate redelivery of task for already COMPLETED issue
        res = process_issue_ai_task(issue_id=issue.id, analysis_id=analysis.id)
        self.assertEqual(res["status"], "ALREADY_COMPLETED")

        final_count = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue.id).count()
        self.assertEqual(initial_count, final_count)

    # =========================================================
    # 6. CITIZEN NOTIFICATION DISPATCH
    # =========================================================
    def test_06_citizen_notification_dispatch(self):
        """Worker dispatches an in-app notification to the citizen on completion, suppressed on duplicate runs."""
        img_bytes = self._create_test_image_bytes()
        from pathlib import Path
        Path("uploads/test_notif_img.jpg").write_bytes(img_bytes)

        issue = CivicIssue(
            title="Notification Test Issue",
            description="Testing citizen notification dispatch.",
            category="Water Leakage",
            severity="High",
            location="Water Works",
            latitude=23.05,
            longitude=72.55,
            image_path="uploads/test_notif_img.jpg",
            status="Reported",
            priority="High",
            user_id=self.user.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        analysis = AIAnalysis(
            issue_id=issue.id,
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            processing_status="PENDING",
            review_status="PENDING",
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        # Count existing notifications for this citizen
        notif_before = self.db.query(Notification).filter(
            Notification.user_id == self.user.id,
            Notification.entity_id == issue.id,
        ).count()

        # Run worker
        res = process_issue_ai_task(issue_id=issue.id, analysis_id=analysis.id)
        self.assertIn(res["status"], ["COMPLETED", "NO_DETECTION"])

        # Verify in-app notification was created
        notif_after = self.db.query(Notification).filter(
            Notification.user_id == self.user.id,
            Notification.entity_id == issue.id,
            Notification.notification_type == "ISSUE_AI_ANALYSIS_COMPLETED",
        ).count()
        self.assertEqual(notif_after, 1)

        # Run task a second time; verify notification count DOES NOT increase
        process_issue_ai_task(issue_id=issue.id, analysis_id=analysis.id)
        notif_final = self.db.query(Notification).filter(
            Notification.user_id == self.user.id,
            Notification.entity_id == issue.id,
            Notification.notification_type == "ISSUE_AI_ANALYSIS_COMPLETED",
        ).count()
        self.assertEqual(notif_final, 1)

    # =========================================================
    # 7. SAFE LEASE RENEWAL DURING LONG-RUNNING INFERENCE
    # =========================================================
    def test_07_lease_renewer_touches_heartbeat(self):
        """LeaseRenewer touches PostgreSQL heartbeat and renews TTL without errors."""
        analysis = AIAnalysis(
            issue_id=self.user.id,  # arbitrary valid integer
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            processing_status="PROCESSING",
            review_status="PENDING",
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        mock_redis = MagicMock()
        mock_redis.get.return_value = b"token-abc"

        with LeaseRenewer(
            redis_client=mock_redis,
            lock_key="test_lock",
            lock_token="token-abc",
            analysis_id=analysis.id,
            interval=0.1,
            lease_seconds=60,
        ):
            import time
            time.sleep(0.3)

        mock_redis.expire.assert_called_with("test_lock", 60)

    # =========================================================
    # 8. STALE RECORD RECOVERY AFTER WORKER CRASH
    # =========================================================
    def test_08_stale_processing_record_recovery(self):
        """Worker crash leaving stale PROCESSING record is recovered by recovery mechanism."""
        issue = CivicIssue(
            title="Stale Crash Issue",
            description="Simulating worker crash on issue.",
            category="Road Damage",
            severity="Medium",
            location="Crash Zone",
            latitude=23.01,
            longitude=72.01,
            image_path="uploads/test_crash_placeholder.jpg",
            status="Reported",
            priority="Medium",
            user_id=self.user.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        stale_time = (datetime.utcnow() - timedelta(seconds=300)).isoformat()
        analysis = AIAnalysis(
            issue_id=issue.id,
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            processing_status="PROCESSING",
            review_status="PENDING",
            created_at=datetime.utcnow() - timedelta(seconds=300),
            analysis_metadata={
                "claim": {
                    "task_id": "crashed-task-999",
                    "heartbeat_at": stale_time,
                }
            },
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        with patch("backend.ai.tasks.process_issue_ai_task.delay") as mock_delay:
            summary = recover_pending_or_stale_analyses(stale_processing_seconds=180)
            self.assertGreaterEqual(summary["recovered_stale"], 1)
            mock_delay.assert_called()

        self.db.refresh(analysis)
        self.assertEqual(analysis.processing_status, "PENDING")


if __name__ == "__main__":
    unittest.main()

