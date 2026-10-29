"""
CIVICSOL - Authority Command Center Comprehensive Test Suite
Tests authority login, RBAC, issue management, assignments, state machine,
resolution evidence with Pillow, Civic Credits award, department & officer management,
dashboard statistics, GIS map, and audit logging.

Isolated test database: In-memory SQLite with StaticPool (never touches development PostgreSQL).
"""

import io
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth.security import hash_password
from backend.core.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    AuditLog,
    CivicCreditTransaction,
    CivicIssue,
    Department,
    IssueStatusHistory,
    User,
)


TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def generate_test_image(image_format="PNG", size=(100, 100), color=(0, 200, 100)) -> bytes:
    """Generate in-memory valid image bytes for resolution testing."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=image_format)
    return buf.getvalue()


class TestAuthorityCommandCenter(unittest.TestCase):
    """
    Complete end-to-end test suite for the CIVICSOL Authority Command Center.
    """

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)

    def setUp(self):
        self.db = TestingSessionLocal()

        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        self.test_upload_dir = tempfile.mkdtemp(prefix="civicsol_auth_test_uploads_")
        from pathlib import Path
        self.patcher_routes = patch("backend.routes.issues.UPLOAD_DIR", new=Path(self.test_upload_dir))
        self.patcher_auth_routes = patch("backend.authority.issues_router.UPLOAD_DIR", new=Path(self.test_upload_dir))
        self.patcher_routes.start()
        self.patcher_auth_routes.start()

        self._seed_test_data()

    def tearDown(self):
        self.patcher_routes.stop()
        self.patcher_auth_routes.stop()
        if os.path.exists(self.test_upload_dir):
            shutil.rmtree(self.test_upload_dir, ignore_errors=True)
        self.db.close()
        app.dependency_overrides.clear()

    def _seed_test_data(self):
        """Prepare departments, super admin, department officer, field officer, and citizen."""
        # 1. Departments
        self.dept_roads = Department(
            name="Roads & Bridges",
            code="ROADS_BRIDGES",
            description="Roads maintenance",
            contact_email="roads@test.gov",
            is_active=True,
        )
        self.dept_sanitation = Department(
            name="Solid Waste Management",
            code="SOLID_WASTE",
            description="Sanitation",
            contact_email="sanitation@test.gov",
            is_active=True,
        )
        self.db.add_all([self.dept_roads, self.dept_sanitation])
        self.db.commit()

        # 2. Users
        pass_hash = hash_password("Password123!")

        # Super Admin
        self.super_admin = User(
            name="Chief Commissioner",
            mobile="9900000001",
            email="admin@civicsol.gov",
            password_hash=pass_hash,
            citizen_id="CIVIC-ADM001",
            employee_id="ADM-00001",
            role="SUPER_ADMIN",
            is_active=True,
        )
        # Roads Dept Officer
        self.dept_officer_roads = User(
            name="Roads Officer Sharma",
            mobile="9900000002",
            email="sharma@roads.gov",
            password_hash=pass_hash,
            citizen_id="CIVIC-OFF001",
            employee_id="DEP-00001",
            role="DEPARTMENT_OFFICER",
            department_id=self.dept_roads.id,
            is_active=True,
        )
        # Roads Field Officer
        self.field_officer_roads = User(
            name="Inspector Patel",
            mobile="9900000003",
            email="patel@roads.gov",
            password_hash=pass_hash,
            citizen_id="CIVIC-OFF002",
            employee_id="FLD-00001",
            role="FIELD_OFFICER",
            department_id=self.dept_roads.id,
            is_active=True,
        )
        # Citizen
        self.citizen = User(
            name="Ramesh Citizen",
            mobile="9800000001",
            email="ramesh@citizen.com",
            password_hash=pass_hash,
            citizen_id="CIVIC-900001",
            role="CITIZEN",
            is_active=True,
        )
        # Deactivated Officer
        self.deactivated_officer = User(
            name="Ex Officer",
            mobile="9900000099",
            email="ex@civicsol.gov",
            password_hash=pass_hash,
            citizen_id="CIVIC-OFF099",
            employee_id="FLD-00099",
            role="FIELD_OFFICER",
            department_id=self.dept_roads.id,
            is_active=False,
        )

        self.db.add_all([
            self.super_admin,
            self.dept_officer_roads,
            self.field_officer_roads,
            self.citizen,
            self.deactivated_officer,
        ])
        self.db.commit()

        # Login tokens
        self.admin_token = self._login_authority("ADM-00001", "Password123!")
        self.dept_officer_token = self._login_authority("DEP-00001", "Password123!")
        self.field_officer_token = self._login_authority("FLD-00001", "Password123!")

    def _login_authority(self, identifier: str, password: str) -> str:
        res = self.client.post(
            "/authority/auth/login",
            json={"identifier": identifier, "password": password},
        )
        self.assertEqual(res.status_code, 200, f"Authority login failed: {res.text}")
        return res.json()["access_token"]

    # ==========================================================================
    # 1. AUTHORITY AUTHENTICATION & SECURITY
    # ==========================================================================
    def test_01_successful_authority_login_and_claims(self):
        """Verify authority login succeeds via employee ID and returns valid token with officer claims."""
        res = self.client.post(
            "/authority/auth/login",
            json={"identifier": "ADM-00001", "password": "Password123!"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "SUPER_ADMIN")
        self.assertEqual(data["employee_id"], "ADM-00001")
        self.assertIn("access_token", data)

        # Verify /authority/auth/me profile endpoint
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_res = self.client.get("/authority/auth/me", headers=headers)
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.json()
        self.assertEqual(me_data["name"], "Chief Commissioner")
        self.assertEqual(me_data["role"], "SUPER_ADMIN")
        self.assertIn("all:access", me_data["permissions"])

    def test_02_citizen_rejected_from_authority_login_with_403(self):
        """Verify that a citizen account is strictly rejected from authority login with HTTP 403."""
        res = self.client.post(
            "/authority/auth/login",
            json={"identifier": "9800000001", "password": "Password123!"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("citizen", res.json().get("detail", "").lower())

    def test_03_deactivated_authority_account_rejected_with_403(self):
        """Verify that an inactive authority officer is rejected with HTTP 403."""
        res = self.client.post(
            "/authority/auth/login",
            json={"identifier": "FLD-00099", "password": "Password123!"},
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("deactivated", res.json().get("detail", "").lower())

    def test_04_invalid_credentials_returns_401(self):
        """Verify bad password returns HTTP 401 without revealing whether the account exists."""
        res = self.client.post(
            "/authority/auth/login",
            json={"identifier": "ADM-00001", "password": "WrongPassword!"},
        )
        self.assertEqual(res.status_code, 401)
        res_nonexistent = self.client.post(
            "/authority/auth/login",
            json={"identifier": "DOES_NOT_EXIST", "password": "WrongPassword!"},
        )
        self.assertEqual(res_nonexistent.status_code, 401)

    def test_05_public_citizen_signup_cannot_choose_authority_role(self):
        """Verify public /auth/signup always defaults to CITIZEN even if an attacker passes 'role'."""
        res = self.client.post(
            "/auth/signup",
            json={
                "name": "Attacker",
                "mobile": "9812345678",
                "password": "Password123!",
                "email": "attacker@test.com",
                "role": "SUPER_ADMIN",  # Attacker attempt
            },
        )
        self.assertEqual(res.status_code, 201)
        # Inspect database record
        attacker = self.db.query(User).filter(User.mobile == "9812345678").first()
        self.assertEqual(attacker.role, "CITIZEN", "Public signup must never allow authority role selection.")

    # ==========================================================================
    # 2. ROLE-BASED ACCESS CONTROL (RBAC)
    # ==========================================================================
    def test_06_field_officer_forbidden_from_department_creation(self):
        """Field officers must receive HTTP 403 when attempting department management."""
        headers = {"Authorization": f"Bearer {self.field_officer_token}"}
        res = self.client.post(
            "/authority/departments/",
            json={"name": "Horticulture", "code": "HORTICULTURE"},
            headers=headers,
        )
        self.assertEqual(res.status_code, 403)

    def test_07_field_officer_forbidden_from_officer_provisioning(self):
        """Field officers must receive HTTP 403 when attempting to provision accounts."""
        headers = {"Authorization": f"Bearer {self.field_officer_token}"}
        res = self.client.post(
            "/authority/officers/",
            json={
                "name": "New Officer",
                "mobile": "9911223344",
                "password": "Password123!",
                "role": "FIELD_OFFICER",
            },
            headers=headers,
        )
        self.assertEqual(res.status_code, 403)

    # ==========================================================================
    # 3. ISSUE MANAGEMENT, ASSIGNMENT, STATE MACHINE & RESOLUTION
    # ==========================================================================
    def test_08_issue_workflow_assignment_state_machine_and_resolution_rewards(self):
        """
        Comprehensive test of issue lifecycle:
        1. Citizen creates issue (Status: Reported).
        2. Super Admin assigns to Roads Department & Field Officer (Status: Assigned).
        3. Field Officer transitions to In Progress.
        4. Field Officer uploads resolution evidence notes + photo (Status: Resolved).
        5. Verify reporting citizen receives exactly +20 authority_verification Civic Credits.
        6. Verify retrying resolution does not duplicate credit award.
        """
        # 1. Citizen creates issue
        citizen_token = self.client.post(
            "/auth/signin",
            json={"mobile": "9800000001", "password": "Password123!"},
        ).json()["access_token"]
        cit_headers = {"Authorization": f"Bearer {citizen_token}"}

        create_res = self.client.post(
            "/issues/",
            data={
                "title": "Severe Pothole on Ashram Road",
                "description": "Deep asphalt depression causing vehicular swerving.",
                "category": "Road Damage",
                "severity": "High",
                "location": "Ashram Road, Ahmedabad",
                "latitude": "23.030000",
                "longitude": "72.570000",
            },
            files={"image": ("pothole.png", generate_test_image("PNG"), "image/png")},
            headers=cit_headers,
        )
        self.assertEqual(create_res.status_code, 200)
        issue_id = create_res.json()["issue"]["id"]

        # 2. Super Admin assigns issue to Roads Department & Inspector Patel
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        assign_res = self.client.put(
            f"/authority/issues/{issue_id}/assign",
            json={
                "department_id": self.dept_roads.id,
                "assigned_officer_id": self.field_officer_roads.id,
                "comment": "Assigned to Ward 3 Roads team for immediate dispatch.",
            },
            headers=admin_headers,
        )
        self.assertEqual(assign_res.status_code, 200)
        self.assertEqual(assign_res.json()["status"], "Assigned")

        # Verify DB assignment and status history
        db_issue = self.db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        self.assertEqual(db_issue.assigned_officer_id, self.field_officer_roads.id)
        self.assertEqual(db_issue.department_id, self.dept_roads.id)
        self.assertEqual(db_issue.status, "Assigned")

        hist_entries = (
            self.db.query(IssueStatusHistory)
            .filter(IssueStatusHistory.issue_id == issue_id)
            .all()
        )
        self.assertTrue(any(h.to_status == "Assigned" for h in hist_entries))

        # 3. Field Officer starts work (Assigned -> In Progress)
        field_headers = {"Authorization": f"Bearer {self.field_officer_token}"}
        status_res = self.client.put(
            f"/authority/issues/{issue_id}/status",
            json={"status": "In Progress", "comment": "Repair truck en route with bitumen patch."},
            headers=field_headers,
        )
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.json()["to_status"], "In Progress")

        # 4. Field Officer resolves issue with photo evidence
        res_bytes = generate_test_image("JPEG", color=(0, 150, 255))
        resolve_res = self.client.post(
            f"/authority/issues/{issue_id}/resolve",
            data={"resolution_notes": "Pothole filled with cold-mix asphalt, leveled and roller compacted."},
            files={"image": ("repaired_road.jpg", res_bytes, "image/jpeg")},
            headers=field_headers,
        )
        self.assertEqual(resolve_res.status_code, 200)
        self.assertEqual(resolve_res.json()["status"], "Resolved")
        self.assertEqual(resolve_res.json()["citizen_credits_awarded"], 20)

        # 5. Verify database resolution record
        self.db.expire_all()
        db_issue_resolved = self.db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        self.assertEqual(db_issue_resolved.status, "Resolved")
        self.assertIsNotNone(db_issue_resolved.resolution_image_path)
        self.assertIsNotNone(db_issue_resolved.resolved_at)
        self.assertEqual(db_issue_resolved.resolved_by_id, self.field_officer_roads.id)

        # 6. Verify citizen Civic Credits (+20 authority_verification)
        auth_credit_txs = (
            self.db.query(CivicCreditTransaction)
            .filter(
                CivicCreditTransaction.issue_id == issue_id,
                CivicCreditTransaction.action == "authority_verification",
            )
            .all()
        )
        self.assertEqual(len(auth_credit_txs), 1, "Expected exactly 1 authority_verification credit transaction.")
        self.assertEqual(auth_credit_txs[0].credits, 20)

    def test_09_invalid_status_transition_rejected(self):
        """Direct transition from Reported to In Progress without assignment must return HTTP 400."""
        # Create issue
        issue = CivicIssue(
            title="Garbage Dump",
            category="Garbage",
            location="Market",
            latitude=23.01,
            longitude=72.58,
            image_path="uploads/test.png",
            status="Reported",
        )
        self.db.add(issue)
        self.db.commit()

        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.put(
            f"/authority/issues/{issue.id}/status",
            json={"status": "In Progress"},
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalid", res.json().get("detail", "").lower())

    def test_10_rejection_without_reason_rejected(self):
        """Rejecting an issue without a non-empty rejection_reason must return HTTP 400."""
        issue = CivicIssue(
            title="False Report",
            category="Road Damage",
            location="Test",
            latitude=23.01,
            longitude=72.58,
            image_path="uploads/test.png",
            status="Reported",
        )
        self.db.add(issue)
        self.db.commit()

        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.put(
            f"/authority/issues/{issue.id}/status",
            json={"status": "Rejected"},
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("reason", res.json().get("detail", "").lower())

    # ==========================================================================
    # 4. DEPARTMENT & OFFICER MANAGEMENT
    # ==========================================================================
    def test_11_super_admin_creates_department_and_prevents_duplicate_code(self):
        """Super Admin creates department; duplicate code returns HTTP 409."""
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.post(
            "/authority/departments/",
            json={
                "name": "Parks & Gardens",
                "code": "PARKS_GARDENS",
                "description": "Public park maintenance.",
            },
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["code"], "PARKS_GARDENS")

        # Duplicate attempt
        res_dup = self.client.post(
            "/authority/departments/",
            json={"name": "Parks Duplicate", "code": "PARKS_GARDENS"},
            headers=admin_headers,
        )
        self.assertEqual(res_dup.status_code, 409)

    def test_12_super_admin_provisions_officer(self):
        """Super Admin provisions a new Field Officer."""
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.post(
            "/authority/officers/",
            json={
                "name": "Inspector Dave",
                "mobile": "9900000055",
                "email": "dave@roads.gov",
                "password": "Password123!",
                "role": "FIELD_OFFICER",
                "department_id": self.dept_roads.id,
                "designation": "Assistant Road Inspector",
            },
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["role"], "FIELD_OFFICER")
        self.assertIsNotNone(res.json()["employee_id"])

        # Audit log verification
        audit = self.db.query(AuditLog).filter(AuditLog.action == "OFFICER_PROVISIONED").first()
        self.assertIsNotNone(audit)

    def test_13_deactivating_final_super_admin_is_prevented(self):
        """System must prevent deactivating the final active Super Admin account."""
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.put(
            f"/authority/officers/{self.super_admin.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("final active super admin", res.json().get("detail", "").lower())

    # ==========================================================================
    # 5. DASHBOARD STATISTICS & GIS MAP
    # ==========================================================================
    def test_14_dashboard_statistics_match_real_database_records(self):
        """Overview stats must return accurate database-backed counts."""
        # Add 1 reported issue and 1 resolved issue
        i1 = CivicIssue(
            title="Open Drain", category="Drainage", location="Zone 1",
            latitude=23.01, longitude=72.58, image_path="uploads/t1.png",
            status="Reported", department_id=self.dept_roads.id,
        )
        i2 = CivicIssue(
            title="Fixed Light", category="Street Lighting", location="Zone 2",
            latitude=23.02, longitude=72.59, image_path="uploads/t2.png",
            status="Resolved", department_id=self.dept_roads.id,
        )
        self.db.add_all([i1, i2])
        self.db.commit()

        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.get("/authority/stats/overview", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_issues"], 2)
        self.assertEqual(data["reported"], 1)
        self.assertEqual(data["resolved"], 1)
        self.assertEqual(data["resolution_rate_percent"], 50.0)

    def test_15_gis_map_issues_endpoint(self):
        """GIS map issues returns compact coordinate payload."""
        issue = CivicIssue(
            title="Fallen Tree", category="Public Infrastructure",
            location="Law Garden", latitude=23.025, longitude=72.565,
            image_path="uploads/t.png", status="Reported",
        )
        self.db.add(issue)
        self.db.commit()

        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.get("/authority/map/issues", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["total"], 1)
        first = data["issues"][0]
        self.assertIn("latitude", first)
        self.assertIn("longitude", first)
        self.assertIn("status", first)

    # ==========================================================================
    # 6. AUDIT LOGS
    # ==========================================================================
    def test_16_audit_logs_retrieval_restricted_to_super_admin(self):
        """Only Super Admin can retrieve full audit logs; Field Officer is forbidden."""
        admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.get("/authority/audit-logs/", headers=admin_headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("logs", res.json())

        field_headers = {"Authorization": f"Bearer {self.field_officer_token}"}
        field_res = self.client.get("/authority/audit-logs/", headers=field_headers)
        self.assertEqual(field_res.status_code, 403)


if __name__ == "__main__":
    unittest.main()
