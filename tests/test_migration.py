"""
CIVICSOL - Milestone 1: Database Migration & Schema Extension Test Suite
Tests schema extensions, legacy record preservation, default CITIZEN role,
idempotent department seeding, and secure Super Admin bootstrap refusal.

Isolated test database: In-memory SQLite with StaticPool (never touches development PostgreSQL).
"""

import unittest
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import (
    AuditLog,
    CivicIssue,
    Department,
    IssueStatusHistory,
    User,
)
from backend.scripts.bootstrap_super_admin import bootstrap_super_admin
from backend.scripts.seed_departments import seed_default_departments, DEFAULT_DEPARTMENTS


class TestDatabaseMigrationAndSafety(unittest.TestCase):
    """
    Test suite verifying schema extension safety, legacy data preservation,
    idempotent department seeding, and Super Admin bootstrap security.
    """

    def setUp(self):
        """Create a dedicated, fresh in-memory SQLite database for each test."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def tearDown(self):
        """Dispose of the test database engine."""
        self.engine.dispose()

    # ==========================================================================
    # 1. LEGACY RECORD PRESERVATION AND CITIZEN ROLE DEFAULT
    # ==========================================================================
    def test_01_legacy_users_receive_citizen_role_and_remain_active(self):
        """
        Simulate an older schema where users had no 'role' or 'is_active' columns.
        Verify that applying schema extensions assigns role='CITIZEN' and is_active=True
        without corrupting name, mobile, email, or citizen_id.
        """
        legacy_meta = MetaData()
        legacy_users = Table(
            "users",
            legacy_meta,
            Column("id", Integer, primary_key=True),
            Column("name", String(100), nullable=False),
            Column("email", String(255), nullable=True),
            Column("mobile", String(15), nullable=False),
            Column("password_hash", String(255), nullable=False),
            Column("preferred_language", String(20), default="English"),
            Column("citizen_id", String(50), nullable=False),
            Column("ward", String(100), nullable=True),
            Column("zone", String(100), nullable=True),
            Column("created_at", DateTime, default=datetime.utcnow),
        )
        legacy_meta.create_all(bind=self.engine)

        # Insert 2 simulated legacy citizen records
        with self.engine.begin() as conn:
            conn.execute(
                legacy_users.insert(),
                [
                    {
                        "id": 1,
                        "name": "Legacy Citizen One",
                        "email": "citizen1@example.com",
                        "mobile": "9876543210",
                        "password_hash": "legacy_hashed_pass_1",
                        "citizen_id": "CIVIC-111111",
                        "created_at": datetime.utcnow(),
                    },
                    {
                        "id": 2,
                        "name": "Legacy Citizen Two",
                        "email": "citizen2@example.com",
                        "mobile": "9876543211",
                        "password_hash": "legacy_hashed_pass_2",
                        "citizen_id": "CIVIC-222222",
                        "created_at": datetime.utcnow(),
                    },
                ],
            )

        # Apply schema extensions (simulate migration DDL)
        with self.engine.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN role VARCHAR(30) DEFAULT 'CITIZEN' NOT NULL;")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN department_id INTEGER;")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN designation VARCHAR(100);")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN employee_id VARCHAR(50);")
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1 NOT NULL;")

        # Query via SQLAlchemy ORM model User
        db: Session = self.SessionLocal()
        try:
            users = db.query(User).order_by(User.id).all()
            self.assertEqual(len(users), 2)

            u1 = users[0]
            self.assertEqual(u1.id, 1)
            self.assertEqual(u1.name, "Legacy Citizen One")
            self.assertEqual(u1.mobile, "9876543210")
            self.assertEqual(u1.role, "CITIZEN")
            self.assertTrue(u1.is_active)
            self.assertIsNone(u1.department_id)
            self.assertIsNone(u1.employee_id)

            u2 = users[1]
            self.assertEqual(u2.id, 2)
            self.assertEqual(u2.name, "Legacy Citizen Two")
            self.assertEqual(u2.role, "CITIZEN")
            self.assertTrue(u2.is_active)
        finally:
            db.close()

    # ==========================================================================
    # 2. LEGACY CIVIC ISSUES PRESERVED WITH NULLABLE EXTENSIONS
    # ==========================================================================
    def test_02_legacy_civic_issues_preserved_with_nullable_assignment_fields(self):
        """
        Verify that existing civic issue records are preserved and new
        assignment/resolution columns are initialized to None (NULL).
        """
        Base.metadata.create_all(bind=self.engine)
        db: Session = self.SessionLocal()
        try:
            # Create a citizen and an existing reported issue
            citizen = User(
                name="Citizen Reporter",
                mobile="9800000001",
                password_hash="fakehash",
                citizen_id="CIVIC-999001",
                role="CITIZEN",
            )
            db.add(citizen)
            db.commit()

            legacy_issue = CivicIssue(
                user_id=citizen.id,
                title="Pothole on Main Street",
                description="Large pothole near traffic signal.",
                category="Road Damage",
                severity="High",
                location="Main Street, Navrangpura",
                latitude=23.03,
                longitude=72.56,
                image_path="uploads/test_pothole.jpg",
                status="Reported",
                priority="Medium",
            )
            db.add(legacy_issue)
            db.commit()
            db.refresh(legacy_issue)

            # Assert new authority fields default to None without error
            self.assertIsNone(legacy_issue.department_id)
            self.assertIsNone(legacy_issue.assigned_officer_id)
            self.assertIsNone(legacy_issue.assigned_by_id)
            self.assertIsNone(legacy_issue.assigned_at)
            self.assertIsNone(legacy_issue.resolution_notes)
            self.assertIsNone(legacy_issue.resolution_image_path)
            self.assertIsNone(legacy_issue.resolved_by_id)
            self.assertIsNone(legacy_issue.resolved_at)
            self.assertIsNone(legacy_issue.rejection_reason)

            # Assert core existing attributes remain identical
            self.assertEqual(legacy_issue.title, "Pothole on Main Street")
            self.assertEqual(legacy_issue.category, "Road Damage")
            self.assertEqual(legacy_issue.status, "Reported")
            self.assertEqual(legacy_issue.user_id, citizen.id)
        finally:
            db.close()

    # ==========================================================================
    # 3. IDEMPOTENT DEPARTMENT SEEDING
    # ==========================================================================
    def test_03_department_seeding_is_idempotent(self):
        """
        Verify that running seed_default_departments multiple times
        results in exactly 6 departments without creating duplicates.
        """
        Base.metadata.create_all(bind=self.engine)
        db: Session = self.SessionLocal()
        try:
            # Run 1st seed
            result1 = seed_default_departments(db)
            self.assertEqual(result1["created"], 6)
            self.assertEqual(result1["existing"], 0)
            self.assertEqual(db.query(Department).count(), 6)

            # Run 2nd seed immediately after
            result2 = seed_default_departments(db)
            self.assertEqual(result2["created"], 0)
            self.assertEqual(result2["existing"], 6)
            self.assertEqual(db.query(Department).count(), 6)

            # Verify standard department codes exist
            expected_codes = {
                "ROADS_BRIDGES",
                "SOLID_WASTE",
                "STREET_LIGHTING",
                "WATER_SEWERAGE",
                "DRAINAGE",
                "PUBLIC_INFRA",
            }
            actual_codes = {d.code for d in db.query(Department).all()}
            self.assertEqual(actual_codes, expected_codes)
        finally:
            db.close()

    # ==========================================================================
    # 4. SUPER ADMIN ONE-TIME BOOTSTRAP SECURITY
    # ==========================================================================
    def test_04_super_admin_bootstrap_and_refuse_overwrite(self):
        """
        Verify that bootstrap_super_admin creates the initial Super Admin account,
        records an audit log, and strictly refuses if a Super Admin already exists.
        """
        Base.metadata.create_all(bind=self.engine)
        db: Session = self.SessionLocal()
        try:
            # First bootstrap should succeed
            res = bootstrap_super_admin(
                db=db,
                name="Municipal Commissioner",
                mobile="9898000001",
                email="commissioner@civicsol.gov.in",
                password="SecureAdminPassword123!",
                employee_id="ADM-00001",
            )
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["role"], "SUPER_ADMIN")
            self.assertEqual(res["employee_id"], "ADM-00001")

            # Verify user record in database
            admin = db.query(User).filter(User.employee_id == "ADM-00001").first()
            self.assertIsNotNone(admin)
            self.assertEqual(admin.role, "SUPER_ADMIN")
            self.assertTrue(admin.is_active)

            # Verify audit log was recorded
            audit = db.query(AuditLog).filter(AuditLog.action == "BOOTSTRAP_SUPER_ADMIN").first()
            self.assertIsNotNone(audit)
            self.assertEqual(audit.user_id, admin.id)

            # Second bootstrap attempt MUST raise ValueError (refuse overwrite)
            with self.assertRaises(ValueError) as ctx:
                bootstrap_super_admin(
                    db=db,
                    name="Intruder Admin",
                    mobile="9898000002",
                    email="intruder@example.com",
                    password="AnotherPassword123!",
                    employee_id="ADM-00002",
                )
            self.assertIn("refused", str(ctx.exception).lower())

            # Verify no second admin was created
            admin_count = db.query(User).filter(User.role == "SUPER_ADMIN").count()
            self.assertEqual(admin_count, 1)
        finally:
            db.close()

    def test_05_super_admin_bootstrap_rejects_weak_password(self):
        """
        Verify that bootstrap_super_admin rejects passwords that don't meet complexity rules.
        """
        Base.metadata.create_all(bind=self.engine)
        db: Session = self.SessionLocal()
        try:
            weak_passwords = ["short", "alllowercase123", "NOLOWERCASES123!", "NoSpecialChar123"]
            for weak in weak_passwords:
                with self.assertRaises(ValueError):
                    bootstrap_super_admin(
                        db=db,
                        name="Test Admin",
                        mobile=f"98980000{len(weak)}",
                        email=f"admin{len(weak)}@civicsol.gov.in",
                        password=weak,
                    )
        finally:
            db.close()

    def test_06_provision_initial_authority_accounts_idempotent(self):
        """
        Verify that provision_initial_authority_accounts safely and idempotently
        creates the three requested initial authority accounts with correct roles and departments.
        """
        from backend.auth.security import verify_password
        from backend.scripts.bootstrap_initial_authority_accounts import provision_initial_authority_accounts

        Base.metadata.create_all(bind=self.engine)
        db: Session = self.SessionLocal()
        try:
            # 1. First run: should create all 3 accounts
            res1 = provision_initial_authority_accounts(db)
            self.assertEqual(len(res1["created"]), 3)
            self.assertEqual(len(res1["already_existed"]), 0)
            self.assertEqual(len(res1["errors"]), 0)

            # Verify Super Admin
            admin = db.query(User).filter(User.employee_id == "ADM-001").first()
            self.assertIsNotNone(admin)
            self.assertEqual(admin.role, "SUPER_ADMIN")
            self.assertTrue(admin.is_active)
            self.assertIsNone(admin.department_id)
            self.assertTrue(verify_password("Civicsol@Admin2026!", admin.password_hash))

            # Verify Department Officer
            dept_officer = db.query(User).filter(User.employee_id == "AUTH-001").first()
            self.assertIsNotNone(dept_officer)
            self.assertEqual(dept_officer.role, "DEPARTMENT_OFFICER")
            self.assertTrue(dept_officer.is_active)
            self.assertEqual(dept_officer.department.code, "ROADS_BRIDGES")
            self.assertTrue(verify_password("Civicsol@Auth2026!", dept_officer.password_hash))

            # Verify Field Officer
            field_officer = db.query(User).filter(User.employee_id == "AUTH-002").first()
            self.assertIsNotNone(field_officer)
            self.assertEqual(field_officer.role, "FIELD_OFFICER")
            self.assertTrue(field_officer.is_active)
            self.assertEqual(field_officer.department.code, "STREET_LIGHTING")
            self.assertTrue(verify_password("Civicsol@Field2026!", field_officer.password_hash))

            # 2. Second run: MUST NOT create duplicate accounts or overwrite passwords
            res2 = provision_initial_authority_accounts(db)
            self.assertEqual(len(res2["created"]), 0)
            self.assertEqual(len(res2["already_existed"]), 3)
            self.assertEqual(len(res2["errors"]), 0)

            # Ensure total authority user count is still 3
            total_auth_users = db.query(User).filter(User.role != "CITIZEN").count()
            self.assertEqual(total_auth_users, 3)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
