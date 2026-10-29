"""
CIVICSOL - Extension Features and Security Boundaries Test Suite
Tests:
1. Citizen Notifications & Isolation
2. Citizen Issue Timeline & Authorized Reopen Workflow
3. Security Hardening: Brute-force rate limiting, security headers, path traversal protection
4. Reliability: Active health check endpoint, CSV export, recent activity feed, officer workloads, SLA policy
"""

import io
import unittest
from datetime import datetime, timedelta
from PIL import Image

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth.security import create_access_token, hash_password
from backend.core.rate_limiter import login_rate_limiter
from backend.core.sla import evaluate_issue_sla
from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    CivicIssue,
    Department,
    IssueStatusHistory,
    Notification,
    User,
)


class TestCivicSolExtensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Isolated SQLite in-memory test database with StaticPool
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )

        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        login_rate_limiter.clear_all()
        self.db = self.TestingSessionLocal()

        # Seed standard department
        self.dept = self.db.query(Department).filter_by(code="ROADS_BRIDGES").first()
        if not self.dept:
            self.dept = Department(
                name="Roads & Bridges",
                code="ROADS_BRIDGES",
                is_active=True,
            )
            self.db.add(self.dept)
            self.db.commit()
            self.db.refresh(self.dept)

        # Seed Super Admin
        self.admin = self.db.query(User).filter_by(email="admin.ext@civicsol.gov").first()
        if not self.admin:
            self.admin = User(
                name="Ext Admin",
                email="admin.ext@civicsol.gov",
                mobile="9800000001",
                password_hash=hash_password("AdminSecurePass!1"),
                citizen_id="ADM-001",
                role="SUPER_ADMIN",
                is_active=True,
            )
            self.db.add(self.admin)
            self.db.commit()
            self.db.refresh(self.admin)

        # Seed Field Officer
        self.officer = self.db.query(User).filter_by(email="officer.ext@civicsol.gov").first()
        if not self.officer:
            self.officer = User(
                name="Officer Dave",
                email="officer.ext@civicsol.gov",
                mobile="9800000002",
                password_hash=hash_password("OfficerSecurePass!1"),
                citizen_id="OFF-001",
                employee_id="OFF-DAVE",
                role="FIELD_OFFICER",
                department_id=self.dept.id,
                is_active=True,
            )
            self.db.add(self.officer)
            self.db.commit()
            self.db.refresh(self.officer)

        # Seed Citizens
        self.citizen_alice = self.db.query(User).filter_by(mobile="9800000003").first()
        if not self.citizen_alice:
            self.citizen_alice = User(
                name="Alice Citizen",
                email="alice@example.com",
                mobile="9800000003",
                password_hash=hash_password("AliceSecurePass!1"),
                citizen_id="CIT-ALICE",
                role="CITIZEN",
                is_active=True,
            )
            self.db.add(self.citizen_alice)
            self.db.commit()
            self.db.refresh(self.citizen_alice)

        self.citizen_bob = self.db.query(User).filter_by(mobile="9800000004").first()
        if not self.citizen_bob:
            self.citizen_bob = User(
                name="Bob Citizen",
                email="bob@example.com",
                mobile="9800000004",
                password_hash=hash_password("BobSecurePass!1"),
                citizen_id="CIT-BOB",
                role="CITIZEN",
                is_active=True,
            )
            self.db.add(self.citizen_bob)
            self.db.commit()
            self.db.refresh(self.citizen_bob)

        # Generate tokens
        self.alice_token = create_access_token({"sub": str(self.citizen_alice.id), "citizen_id": self.citizen_alice.citizen_id})
        self.bob_token = create_access_token({"sub": str(self.citizen_bob.id), "citizen_id": self.citizen_bob.citizen_id})
        self.admin_token = create_access_token({"sub": str(self.admin.id), "role": "SUPER_ADMIN"})
        self.officer_token = create_access_token({"sub": str(self.officer.id), "role": "FIELD_OFFICER"})

    def tearDown(self):
        self.db.close()

    # =====================================================
    # 1. NOTIFICATIONS TESTS
    # =====================================================
    def test_01_in_app_notification_creation_and_isolation(self):
        """Citizens only receive and access their own notifications."""
        # Create notification for Alice
        notif_alice = Notification(
            user_id=self.citizen_alice.id,
            title="Pothole Update",
            message="Your report has been assigned.",
            notification_type="ISSUE_ASSIGNED",
            entity_type="CIVIC_ISSUE",
            entity_id=1,
            is_read=False,
        )
        self.db.add(notif_alice)
        self.db.commit()
        self.db.refresh(notif_alice)

        # Alice retrieves notifications
        res_alice = self.client.get(
            "/notifications/",
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertEqual(res_alice.status_code, 200)
        data = res_alice.json()
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["notifications"][0]["title"], "Pothole Update")

        # Bob attempts to read Alice's notification -> 403 Forbidden
        res_bob = self.client.put(
            f"/notifications/{notif_alice.id}/read",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(res_bob.status_code, 403)

        # Alice marks her own notification as read -> 200 OK
        res_alice_read = self.client.put(
            f"/notifications/{notif_alice.id}/read",
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertEqual(res_alice_read.status_code, 200)
        self.assertTrue(res_alice_read.json()["is_read"])

    def test_02_notification_read_all_and_unread_count(self):
        """Test mark all notifications read and unread count endpoint."""
        for i in range(3):
            n = Notification(
                user_id=self.citizen_bob.id,
                title=f"Alert #{i}",
                message="Status changed.",
                notification_type="ISSUE_STATUS_UPDATED",
                is_read=False,
            )
            self.db.add(n)
        self.db.commit()

        # Check unread count
        count_res = self.client.get(
            "/notifications/unread-count",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(count_res.status_code, 200)
        self.assertGreaterEqual(count_res.json()["unread_count"], 3)

        # Mark all as read
        read_all_res = self.client.put(
            "/notifications/read-all",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(read_all_res.status_code, 200)

        # Re-check unread count -> 0
        count_res_after = self.client.get(
            "/notifications/unread-count",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(count_res_after.json()["unread_count"], 0)

    # =====================================================
    # 2. CITIZEN TIMELINE & REOPEN WORKFLOW
    # =====================================================
    def test_03_citizen_can_view_own_timeline_and_blocked_from_others(self):
        """Alice views her report timeline; Bob is blocked with HTTP 403."""
        issue = CivicIssue(
            title="Broken Streetlight",
            description="Dark street at night",
            category="Street Lighting",
            severity="Medium",
            priority="Medium",
            location="Market St",
            latitude=23.02,
            longitude=72.57,
            image_path="uploads/test.jpg",
            status="Under Review",
            user_id=self.citizen_alice.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        # Add a status history entry
        hist = IssueStatusHistory(
            issue_id=issue.id,
            from_status="Reported",
            to_status="Under Review",
            comment="Officer initiated inspection",
        )
        self.db.add(hist)
        self.db.commit()

        # Alice views her own timeline -> 200
        alice_res = self.client.get(
            f"/issues/{issue.id}",
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertEqual(alice_res.status_code, 200)
        self.assertEqual(len(alice_res.json()["status_timeline"]), 1)
        self.assertEqual(alice_res.json()["status_timeline"][0]["to_status"], "Under Review")

        # Bob attempts to view Alice's private issue dossier -> 403 Forbidden
        bob_res = self.client.get(
            f"/issues/{issue.id}",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(bob_res.status_code, 403)

    def test_04_citizen_reopen_workflow_success_and_restrictions(self):
        """Citizen can reopen Resolved issue with valid reason; blocked on active issue."""
        issue = CivicIssue(
            title="Water Leakage",
            description="Main pipe leakage",
            category="Water Supply",
            severity="High",
            priority="High",
            location="5th Cross",
            latitude=23.03,
            longitude=72.58,
            image_path="uploads/leak.jpg",
            status="Resolved",
            user_id=self.citizen_alice.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        # Attempt reopen with empty reason -> 422/400
        fail_res = self.client.post(
            f"/issues/{issue.id}/reopen-request",
            json={"reason": "bad"},  # less than 5 chars
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertIn(fail_res.status_code, [400, 422])

        # Attempt reopen by Bob (non-owner) -> 403 Forbidden
        bob_res = self.client.post(
            f"/issues/{issue.id}/reopen-request",
            json={"reason": "Water is still leaking everywhere."},
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(bob_res.status_code, 403)

        # Valid reopen by Alice -> 200 OK
        ok_res = self.client.post(
            f"/issues/{issue.id}/reopen-request",
            json={"reason": "The repair patch failed and water is still leaking onto the sidewalk."},
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertEqual(ok_res.status_code, 200)
        self.assertEqual(ok_res.json()["status"], "Reopened")

        # Verify status in database
        self.db.expire_all()
        reloaded = self.db.query(CivicIssue).filter_by(id=issue.id).first()
        self.assertEqual(reloaded.status, "Reopened")

        # Attempt to reopen again while now in 'Reopened' -> 400 Bad Request
        already_open_res = self.client.post(
            f"/issues/{issue.id}/reopen-request",
            json={"reason": "Another reopen request."},
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertEqual(already_open_res.status_code, 400)

    # =====================================================
    # 3. SECURITY HARDENING: BRUTE FORCE & SECURITY HEADERS
    # =====================================================
    def test_05_login_rate_limiting_triggers_429(self):
        """5 failed login attempts trigger HTTP 429 Too Many Requests."""
        login_rate_limiter.clear_all()

        # Submit 5 invalid login requests
        for _ in range(5):
            res = self.client.post(
                "/authority/auth/login",
                json={"identifier": "admin.ext@civicsol.gov", "password": "WrongPassword123!"},
            )
            self.assertEqual(res.status_code, 401)

        # 6th attempt should be blocked by rate limiter with 429
        blocked_res = self.client.post(
            "/authority/auth/login",
            json={"identifier": "admin.ext@civicsol.gov", "password": "AdminSecurePass!1"},
        )
        self.assertEqual(blocked_res.status_code, 429)
        self.assertIn("Retry-After", blocked_res.headers)

    def test_06_security_headers_present_in_responses(self):
        """Security headers (nosniff, DENY, CSP) are attached to responses."""
        res = self.client.get("/")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertIn("default-src 'self'", res.headers.get("Content-Security-Policy", ""))

    def test_07_path_traversal_attack_blocked(self):
        """Path traversal attempt in uploads endpoint returns HTTP 400 or 404."""
        res = self.client.get("/uploads/../../etc/passwd")
        self.assertIn(res.status_code, [400, 404])

    # =====================================================
    # 4. HEALTH, EXPORT, ACTIVITY & WORKLOADS
    # =====================================================
    def test_08_active_health_check_endpoint(self):
        """GET /health verifies database and storage connectivity."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["checks"]["database"], "healthy")
        self.assertEqual(data["checks"]["storage"], "writable")

    def test_09_authorized_csv_export(self):
        """GET /authority/issues/export streams a sanitized CSV."""
        res = self.client.get(
            "/authority/issues/export",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=civicsol_issues_export_", res.headers["content-disposition"])
        content = res.text
        self.assertIn("ID,Title,Category,Severity,Priority,Status", content)

    def test_10_recent_activity_feed(self):
        """GET /authority/issues/activity/recent returns latest administrative audit logs."""
        res = self.client.get(
            "/authority/issues/activity/recent",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_11_officer_workloads_comparison(self):
        """GET /authority/stats/officer-workloads returns officer assignments."""
        res = self.client.get(
            "/authority/stats/officer-workloads",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("officers", data)
        self.assertGreaterEqual(len(data["officers"]), 1)

    def test_12_sla_evaluation_policy(self):
        """Verify SLA evaluation identifies overdue issues based on municipal policy."""
        # Issue created 4 days ago with 'Critical' priority (24h window) -> overdue
        four_days_ago = datetime.utcnow() - timedelta(days=4)
        sla_result = evaluate_issue_sla(
            created_at=four_days_ago,
            priority="Critical",
            status="In Progress",
        )
        self.assertTrue(sla_result["is_overdue"])
        self.assertEqual(sla_result["compliance_status"], "OVERDUE")
        self.assertLess(sla_result["hours_remaining"], 0)

        # Issue created 1 hour ago with 'Low' priority (120h window) -> within SLA
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        sla_recent = evaluate_issue_sla(
            created_at=one_hour_ago,
            priority="Low",
            status="In Progress",
        )
        self.assertFalse(sla_recent["is_overdue"])
        self.assertEqual(sla_recent["compliance_status"], "WITHIN_SLA")
        self.assertGreater(sla_recent["hours_remaining"], 100)


if __name__ == "__main__":
    unittest.main()
