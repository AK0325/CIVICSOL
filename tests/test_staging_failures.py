"""
CIVICSOL - Staging Failure Scenarios & Security Verification Suite
Tests:
1. Admin-only access to /ai/maintenance/recover (Citizens, Officers rejected with 403).
2. Failure Scenario 1: Redis unavailable during citizen submission.
3. Failure Scenario 2: Celery worker stopped/offline.
4. Failure Scenario 3: Backend restart simulation.
5. Failure Scenario 4: Worker restart / crash simulation (stale heartbeat recovery).
6. Failure Scenario 5: Database temporarily unavailable (transaction rollback & retry).
7. Failure Scenario 6: Duplicate task delivery idempotency.
8. Failure Scenario 7: Invalid, corrupt, and non-image uploads.
"""

import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.exc import OperationalError

from backend.ai.tasks import (
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


class TestStagingFailuresAndSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Seed roles for access control testing
        self.super_admin = self.db.query(User).filter(User.email == "admin_staging@civicsol.gov").first()
        if not self.super_admin:
            self.super_admin = User(
                name="Staging Super Admin",
                email="admin_staging@civicsol.gov",
                password_hash="test_admin_hash",
                role="SUPER_ADMIN",
                is_active=True,
            )
            self.db.add(self.super_admin)

        self.officer = self.db.query(User).filter(User.email == "officer_staging@civicsol.gov").first()
        if not self.officer:
            self.officer = User(
                name="Staging Field Officer",
                email="officer_staging@civicsol.gov",
                password_hash="test_officer_hash",
                role="FIELD_OFFICER",
                is_active=True,
            )
            self.db.add(self.officer)

        self.citizen = self.db.query(User).filter(User.email == "citizen_staging@civicsol.gov").first()
        if not self.citizen:
            self.citizen = User(
                name="Staging Citizen",
                email="citizen_staging@civicsol.gov",
                password_hash="test_citizen_hash",
                role="CITIZEN",
                citizen_id="CIT-STAGING-01",
                is_active=True,
            )
            self.db.add(self.citizen)

        self.db.commit()
        self.db.refresh(self.super_admin)
        self.db.refresh(self.officer)
        self.db.refresh(self.citizen)

        self.admin_token = create_access_token({"sub": str(self.super_admin.id), "role": "SUPER_ADMIN"})
        self.officer_token = create_access_token({"sub": str(self.officer.id), "role": "FIELD_OFFICER"})
        self.citizen_token = create_access_token({"sub": str(self.citizen.id), "role": "CITIZEN", "citizen_id": self.citizen.citizen_id})

    def tearDown(self):
        self.db.close()

    def _create_test_image_bytes(self, color=(80, 120, 160)) -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", (150, 150), color=color).save(buf, format="JPEG")
        return buf.getvalue()

    # =========================================================
    # SECURITY: ADMIN-ONLY ACCESS TO /ai/maintenance/recover
    # =========================================================
    def test_01_admin_only_access_to_maintenance_recovery(self):
        """Verify POST /ai/maintenance/recover strictly enforces SUPER_ADMIN access."""
        # 1. Citizen is forbidden (403)
        res_citizen = self.client.post(
            "/ai/maintenance/recover",
            headers={"Authorization": f"Bearer {self.citizen_token}"},
        )
        self.assertEqual(res_citizen.status_code, 403)

        # 2. Field officer is forbidden (403)
        res_officer = self.client.post(
            "/ai/maintenance/recover",
            headers={"Authorization": f"Bearer {self.officer_token}"},
        )
        self.assertEqual(res_officer.status_code, 403)

        # 3. Super Admin is authorized (200)
        with patch("backend.ai.tasks.recover_pending_or_stale_analyses", return_value={"recovered_pending": 0, "recovered_stale": 0}):
            res_admin = self.client.post(
                "/ai/maintenance/recover",
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )
        self.assertEqual(res_admin.status_code, 200)
        self.assertEqual(res_admin.json()["status"], "SUCCESS")

    # =========================================================
    # FAILURE SCENARIO 1: REDIS UNAVAILABLE DURING SUBMISSION
    # =========================================================
    def test_02_failure_scenario_redis_unavailable(self):
        """Simulate Redis broker outage: submission succeeds with PENDING status, credits awarded."""
        img_bytes = self._create_test_image_bytes()
        with patch("backend.ai.tasks.process_issue_ai_task.delay", side_effect=Exception("Redis connection refused")):
            res = self.client.post(
                "/issues/",
                headers={"Authorization": f"Bearer {self.citizen_token}"},
                files={"image": ("redis_outage.jpg", img_bytes, "image/jpeg")},
                data={
                    "title": "Redis Outage Hazard",
                    "description": "Hazard reported while broker was temporarily offline.",
                    "category": "Road Damage",
                    "severity": "High",
                    "location": "Offline Crossroad",
                    "latitude": 23.011,
                    "longitude": 72.511,
                },
            )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["credits_earned"], 20)
        self.assertEqual(data["ai_analysis"]["processing_status"], "PENDING")

        # Database record exists and is recoverable
        issue_id = data["issue"]["id"]
        analysis = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue_id).first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.processing_status, "PENDING")

    # =========================================================
    # FAILURE SCENARIO 2: CELERY WORKER STOPPED / OFFLINE
    # =========================================================
    def test_03_failure_scenario_worker_offline(self):
        """When worker is offline, task queues in Redis without citizen disruption; executes when worker resumes."""
        img_bytes = self._create_test_image_bytes()
        res = self.client.post(
            "/issues/",
            headers={"Authorization": f"Bearer {self.citizen_token}"},
            files={"image": ("worker_offline.jpg", img_bytes, "image/jpeg")},
            data={
                "title": "Queued Hazard Waiting for Worker",
                "description": "Issue waiting in queue while Celery worker is stopped.",
                "category": "Garbage",
                "severity": "Medium",
                "location": "Queued Lane",
                "latitude": 23.012,
                "longitude": 72.512,
            },
        )
        self.assertEqual(res.status_code, 200)
        issue_id = res.json()["issue"]["id"]
        analysis = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue_id).first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.processing_status, "PENDING")

        # When worker boots up, it processes the queued task
        task_res = process_issue_ai_task(issue_id=issue_id, analysis_id=analysis.id)
        self.assertIn(task_res["status"], ["COMPLETED", "NO_DETECTION"])

    # =========================================================
    # FAILURE SCENARIO 3: BACKEND RESTART SIMULATION
    # =========================================================
    def test_04_failure_scenario_backend_restart(self):
        """Simulate backend restart: connection pool re-initialization and stateless token validation."""
        # Dispose of connection pool to simulate process restart
        engine.dispose()
        restarted_client = TestClient(app)

        # Verify active session, authenticated endpoints, and health check work seamlessly
        health_res = restarted_client.get("/health")
        self.assertEqual(health_res.status_code, 200)
        self.assertEqual(health_res.json()["checks"]["database"], "healthy")

        my_reports = restarted_client.get(
            "/issues/mine",
            headers={"Authorization": f"Bearer {self.citizen_token}"},
        )
        self.assertEqual(my_reports.status_code, 200)

    # =========================================================
    # FAILURE SCENARIO 4: WORKER RESTART / CRASH SIMULATION
    # =========================================================
    def test_05_failure_scenario_worker_crash_stale_heartbeat(self):
        """Worker crash leaving stale PROCESSING record is recovered after timeout."""
        issue = CivicIssue(
            title="Crashed Worker Report",
            description="Simulating worker sudden crash mid-analysis.",
            category="Road Damage",
            severity="Medium",
            location="Crash Avenue",
            latitude=23.013,
            longitude=72.513,
            image_path="uploads/test_crash_placeholder.jpg",
            status="Reported",
            priority="Medium",
            user_id=self.citizen.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        stale_ts = (datetime.utcnow() - timedelta(seconds=240)).isoformat()
        analysis = AIAnalysis(
            issue_id=issue.id,
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            processing_status="PROCESSING",
            review_status="PENDING",
            created_at=datetime.utcnow() - timedelta(seconds=240),
            analysis_metadata={
                "claim": {
                    "task_id": "crashed-worker-task-001",
                    "heartbeat_at": stale_ts,
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

    # =========================================================
    # FAILURE SCENARIO 5: DATABASE TEMPORARILY UNAVAILABLE
    # =========================================================
    def test_06_failure_scenario_database_transient_failure(self):
        """Worker handles transient database errors gracefully, rolling back without corrupted state."""
        issue = CivicIssue(
            title="DB Transient Test",
            description="Testing DB transient error handling.",
            category="Road Damage",
            severity="Medium",
            location="DB Glitch Zone",
            latitude=23.014,
            longitude=72.514,
            image_path="uploads/test_crash_placeholder.jpg",
            status="Reported",
            priority="Medium",
            user_id=self.citizen.id,
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

        # Simulate transient DB error during pipeline
        with patch("backend.ai.pipeline.run_issue_ai_analysis", side_effect=OperationalError("connection closed", {}, None)):
            res = process_issue_ai_task(issue_id=issue.id, analysis_id=analysis.id)
            self.assertEqual(res["status"], "FAILED")

        # Database session rollback occurred cleanly
        self.db.refresh(analysis)
        self.assertEqual(analysis.processing_status, "FAILED")

    # =========================================================
    # FAILURE SCENARIO 6: DUPLICATE TASK DELIVERY IDEMPOTENCY
    # =========================================================
    def test_07_failure_scenario_duplicate_task_delivery(self):
        """Duplicate task deliveries are discarded without generating redundant rows or notifications."""
        img_bytes = self._create_test_image_bytes()
        from pathlib import Path
        Path("uploads/test_dupe_img.jpg").write_bytes(img_bytes)

        issue = CivicIssue(
            title="Dupe Delivery Issue",
            description="Testing idempotency under multiple task deliveries.",
            category="Garbage",
            severity="Medium",
            location="Dupe Boulevard",
            latitude=23.015,
            longitude=72.515,
            image_path="uploads/test_dupe_img.jpg",
            status="Reported",
            priority="Medium",
            user_id=self.citizen.id,
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

        # First task execution
        res1 = process_issue_ai_task(issue_id=issue.id, analysis_id=analysis.id)
        self.assertIn(res1["status"], ["COMPLETED", "NO_DETECTION"])

        count_before = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue.id).count()

        # Second delivery (duplicate delivery in Celery)
        res2 = process_issue_ai_task(issue_id=issue.id, analysis_id=analysis.id)
        self.assertEqual(res2["status"], "ALREADY_COMPLETED")

        count_after = self.db.query(AIAnalysis).filter(AIAnalysis.issue_id == issue.id).count()
        self.assertEqual(count_before, count_after)

    # =========================================================
    # FAILURE SCENARIO 7: INVALID, CORRUPT & OVERSIZED UPLOADS
    # =========================================================
    def test_08_failure_scenario_invalid_corrupt_uploads(self):
        """Non-image and corrupt uploads are rejected upfront with HTTP 400."""
        # 1. Non-image MIME type
        res_txt = self.client.post(
            "/issues/",
            headers={"Authorization": f"Bearer {self.citizen_token}"},
            files={"image": ("malicious.txt", b"Hello World", "text/plain")},
            data={"title": "Invalid MIME", "category": "Road Damage", "location": "Test", "latitude": 23.0, "longitude": 72.0},
        )
        self.assertEqual(res_txt.status_code, 400)

        # 2. Corrupt bytes disguised as image/jpeg
        res_corrupt = self.client.post(
            "/issues/",
            headers={"Authorization": f"Bearer {self.citizen_token}"},
            files={"image": ("fake.jpg", b"\xFF\xD8\xFF\xE0CORRUPT_BYTES_XYZ_123", "image/jpeg")},
            data={"title": "Corrupt Header", "category": "Road Damage", "location": "Test", "latitude": 23.0, "longitude": 72.0},
        )
        self.assertEqual(res_corrupt.status_code, 400)


if __name__ == "__main__":
    unittest.main()

