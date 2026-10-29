"""
CIVICSOL - Phase 2: Civic Issue Reporting Test Suite
Tests issue reporting endpoints, multipart upload validation, GPS validation,
Civic Credits award ledger (+20 credits), citizen ownership, and data isolation.

Isolated test database: In-memory SQLite with StaticPool (never touches production PostgreSQL).
Upload directory: Redirected to a temporary directory for tests to avoid polluting uploads/.
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

from backend.core.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models import CivicCreditTransaction, CivicIssue, User

# ==============================================================================
# ISOLATED TEST DATABASE SETUP (IN-MEMORY SQLITE)
# ==============================================================================
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


def generate_test_image(image_format="PNG", size=(100, 100), color=(255, 0, 0)) -> bytes:
    """Generate valid in-memory image bytes for testing."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=image_format)
    return buf.getvalue()


class TestIssueReporting(unittest.TestCase):
    """
    Test suite for Civic Issue Reporting workflow, file validation,
    GPS bounds, credit transactions, and citizen report isolation.
    """

    @classmethod
    def setUpClass(cls):
        """Create database tables once on the isolated in-memory engine."""
        Base.metadata.create_all(bind=test_engine)

    @classmethod
    def tearDownClass(cls):
        """Drop all tables after all tests in the class finish."""
        Base.metadata.drop_all(bind=test_engine)

    def setUp(self):
        """Prepare fresh DB session, temporary upload directory, and test client."""
        self.db = TestingSessionLocal()

        # Clear existing table data to ensure complete test isolation
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()

        # Override FastAPI get_db dependency
        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Isolated temporary upload directory
        self.test_upload_dir = tempfile.mkdtemp(prefix="civicsol_test_uploads_")
        self.upload_dir_patcher = patch(
            "backend.routes.issues.UPLOAD_DIR",
            new=self.test_upload_dir,
        )
        # In case UPLOAD_DIR is a Path object in routes
        from pathlib import Path
        self.upload_dir_patcher = patch(
            "backend.routes.issues.UPLOAD_DIR",
            new=Path(self.test_upload_dir),
        )
        self.upload_dir_patcher.start()

        # Helper to create an authenticated citizen and return auth headers
        self.citizen_one_token = self._create_user_and_login(
            name="Citizen One",
            mobile="9800000001",
            password="Password123!",
            email="citizen.one@example.com",
        )
        self.citizen_two_token = self._create_user_and_login(
            name="Citizen Two",
            mobile="9800000002",
            password="Password123!",
            email="citizen.two@example.com",
        )

    def tearDown(self):
        """Clean up database session, dependency overrides, and temporary files."""
        self.upload_dir_patcher.stop()
        if os.path.exists(self.test_upload_dir):
            shutil.rmtree(self.test_upload_dir, ignore_errors=True)

        self.db.close()
        app.dependency_overrides.clear()

    def _create_user_and_login(self, name: str, mobile: str, password: str, email: str) -> str:
        """Register a test citizen and return bearer access token."""
        self.client.post(
            "/auth/signup",
            json={
                "name": name,
                "mobile": mobile,
                "password": password,
                "email": email,
            },
        )
        res = self.client.post(
            "/auth/signin",
            json={"mobile": mobile, "password": password},
        )
        return res.json()["access_token"]

    # ==========================================================================
    # 1. SUCCESSFUL ISSUE CREATION
    # ==========================================================================
    def test_01_successful_issue_creation(self):
        """
        Submit a valid PNG image, category, description, and GPS coordinates.
        Verify successful HTTP 200 response, DB persistence, ownership, and +20 credits.
        """
        png_bytes = generate_test_image("PNG")
        headers = {"Authorization": f"Bearer {self.citizen_one_token}"}

        payload = {
            "title": "Broken Footpath Slab",
            "description": "A deep broken concrete slab on the pedestrian walkway.",
            "category": "Road Damage",
            "severity": "High",
            "location": "Near CG Road, Navrangpura",
            "latitude": "23.030000",
            "longitude": "72.560000",
        }
        files = {
            "image": ("pothole.png", png_bytes, "image/png"),
        }

        response = self.client.post(
            "/issues/",
            data=payload,
            files=files,
            headers=headers,
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200 OK, got {response.status_code}: {response.text}",
        )

        data = response.json()
        self.assertEqual(data.get("message"), "Civic issue created successfully.")
        self.assertEqual(data.get("credits_earned"), 20)

        issue_data = data.get("issue", {})
        self.assertIn("id", issue_data)
        issue_id = issue_data["id"]
        self.assertEqual(issue_data["category"], "Road Damage")
        self.assertEqual(issue_data["severity"], "High")
        self.assertEqual(float(issue_data["latitude"]), 23.03)
        self.assertEqual(float(issue_data["longitude"]), 72.56)
        self.assertEqual(issue_data["status"], "Reported")

        # Verify DB persistence
        issue_record = self.db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        self.assertIsNotNone(issue_record, "Issue was not persisted in database.")
        self.assertEqual(issue_record.title, payload["title"])
        self.assertEqual(issue_record.category, payload["category"])

        # Verify ownership by citizen one
        citizen_one = self.db.query(User).filter(User.mobile == "9800000001").first()
        self.assertEqual(issue_record.user_id, citizen_one.id)

        # Verify Civic Credit transactions (+10 report, +5 clear evidence, +5 GPS = +20 total)
        credit_txs = (
            self.db.query(CivicCreditTransaction)
            .filter(CivicCreditTransaction.issue_id == issue_id)
            .all()
        )
        self.assertEqual(
            len(credit_txs),
            3,
            f"Expected 3 credit transactions, found {len(credit_txs)}",
        )
        total_credits = sum(tx.credits for tx in credit_txs)
        self.assertEqual(
            total_credits,
            20,
            f"Expected 20 total credits awarded, got {total_credits}",
        )
        actions = [tx.action for tx in credit_txs]
        self.assertIn("valid_report", actions)
        self.assertIn("clear_evidence", actions)
        self.assertIn("gps_evidence", actions)

    # ==========================================================================
    # 2. FILE VALIDATION
    # ==========================================================================
    def test_02_reject_non_image_content_type(self):
        """
        Verify that uploading a file with a non-image MIME type (e.g. text/plain)
        is rejected with HTTP 400 and creates no records or credits.
        """
        headers = {"Authorization": f"Bearer {self.citizen_one_token}"}
        payload = {
            "title": "Text Upload Test",
            "description": "Uploading a text file instead of image.",
            "category": "Garbage",
            "severity": "Medium",
            "location": "Market Yard",
            "latitude": "23.020000",
            "longitude": "72.570000",
        }
        files = {
            "image": ("document.txt", b"Hello world text file", "text/plain"),
        }

        response = self.client.post("/issues/", data=payload, files=files, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.json().get("detail", "").lower())

        # Ensure no issue was created in DB
        issue_count = self.db.query(CivicIssue).count()
        self.assertEqual(issue_count, 0)
        credit_count = self.db.query(CivicCreditTransaction).count()
        self.assertEqual(credit_count, 0)

    def test_03_reject_corrupt_or_fake_image_content(self):
        """
        Verify that uploading corrupt bytes disguised as an image
        (e.g. text or invalid bytes with image/png MIME type) is rejected with HTTP 400.
        """
        headers = {"Authorization": f"Bearer {self.citizen_one_token}"}
        payload = {
            "title": "Corrupt File Test",
            "description": "Corrupt data disguised with image/png content-type.",
            "category": "Garbage",
            "severity": "Medium",
            "location": "Market Yard",
            "latitude": "23.020000",
            "longitude": "72.570000",
        }
        # Fake image: plain text pretending to be PNG
        files = {
            "image": ("fake_image.png", b"NOT_A_REAL_IMAGE_DATA_12345", "image/png"),
        }

        response = self.client.post("/issues/", data=payload, files=files, headers=headers)
        self.assertEqual(
            response.status_code,
            400,
            f"Expected HTTP 400 for corrupt/fake image content, got {response.status_code}: {response.text}",
        )

        # Ensure no issue was created
        issue_count = self.db.query(CivicIssue).count()
        self.assertEqual(issue_count, 0)
        credit_count = self.db.query(CivicCreditTransaction).count()
        self.assertEqual(credit_count, 0)

    def test_04_reject_oversized_upload(self):
        """
        Verify that uploading a file exceeding MAX_IMAGE_SIZE_MB (default 10MB)
        is rejected with HTTP 400 and creates no records or credits.
        """
        headers = {"Authorization": f"Bearer {self.citizen_one_token}"}
        payload = {
            "title": "Oversized Image Test",
            "description": "File exceeding configured size limit.",
            "category": "Garbage",
            "severity": "Medium",
            "location": "Market Yard",
            "latitude": "23.020000",
            "longitude": "72.570000",
        }

        # Create a payload larger than settings.MAX_IMAGE_SIZE_MB (e.g. 11MB)
        oversized_bytes = b"0" * ((settings.MAX_IMAGE_SIZE_MB + 1) * 1024 * 1024)
        files = {
            "image": ("huge_image.jpg", oversized_bytes, "image/jpeg"),
        }

        response = self.client.post("/issues/", data=payload, files=files, headers=headers)
        self.assertEqual(
            response.status_code,
            400,
            f"Expected HTTP 400 for oversized image upload, got {response.status_code}",
        )
        self.assertIn("size", response.json().get("detail", "").lower())

        # Ensure no issue was created in DB
        issue_count = self.db.query(CivicIssue).count()
        self.assertEqual(issue_count, 0)
        credit_count = self.db.query(CivicCreditTransaction).count()
        self.assertEqual(credit_count, 0)

    # ==========================================================================
    # 3. GPS VALIDATION
    # ==========================================================================
    def test_05_reject_invalid_gps_latitude(self):
        """
        Verify that out-of-bounds latitude (e.g. 95.0) is rejected with HTTP 400.
        """
        png_bytes = generate_test_image("PNG")
        headers = {"Authorization": f"Bearer {self.citizen_one_token}"}
        payload = {
            "title": "Invalid Lat Test",
            "description": "Latitude exceeds 90 degrees.",
            "category": "Water Leakage",
            "severity": "Medium",
            "location": "Test Area",
            "latitude": "95.0",
            "longitude": "72.570000",
        }
        files = {"image": ("leak.png", png_bytes, "image/png")}

        response = self.client.post("/issues/", data=payload, files=files, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("latitude", response.json().get("detail", "").lower())

        # Ensure no issue or credit created
        self.assertEqual(self.db.query(CivicIssue).count(), 0)
        self.assertEqual(self.db.query(CivicCreditTransaction).count(), 0)

    def test_06_reject_invalid_gps_longitude(self):
        """
        Verify that out-of-bounds longitude (e.g. 200.0) is rejected with HTTP 400.
        """
        png_bytes = generate_test_image("PNG")
        headers = {"Authorization": f"Bearer {self.citizen_one_token}"}
        payload = {
            "title": "Invalid Long Test",
            "description": "Longitude exceeds 180 degrees.",
            "category": "Street Light",
            "severity": "Low",
            "location": "Test Area",
            "latitude": "23.000000",
            "longitude": "200.0",
        }
        files = {"image": ("light.png", png_bytes, "image/png")}

        response = self.client.post("/issues/", data=payload, files=files, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertIn("longitude", response.json().get("detail", "").lower())

        self.assertEqual(self.db.query(CivicIssue).count(), 0)
        self.assertEqual(self.db.query(CivicCreditTransaction).count(), 0)

    def test_07_accept_boundary_gps_coordinates(self):
        """
        Verify that valid boundary coordinates (-90, 90, -180, 180) are accepted.
        """
        png_bytes = generate_test_image("PNG")
        headers = {"Authorization": f"Bearer {self.citizen_one_token}"}
        payload = {
            "title": "Boundary GPS Test",
            "description": "Testing valid coordinate limits.",
            "category": "Drainage",
            "severity": "Medium",
            "location": "South Pole Extreme",
            "latitude": "-90.0",
            "longitude": "180.0",
        }
        files = {"image": ("drainage.png", png_bytes, "image/png")}

        response = self.client.post("/issues/", data=payload, files=files, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.db.query(CivicIssue).count(), 1)

    # ==========================================================================
    # 4. CITIZEN DATA ISOLATION
    # ==========================================================================
    def test_08_citizen_data_isolation_on_my_reports(self):
        """
        Create reports for two different citizens.
        Verify that GET /issues/mine returns only the authenticated citizen's reports.
        """
        headers_one = {"Authorization": f"Bearer {self.citizen_one_token}"}
        headers_two = {"Authorization": f"Bearer {self.citizen_two_token}"}

        # Citizen One submits 2 issues
        for i in range(2):
            self.client.post(
                "/issues/",
                data={
                    "title": f"Citizen One Report #{i+1}",
                    "description": f"Description from citizen one {i+1}",
                    "category": "Road Damage",
                    "severity": "Medium",
                    "location": "Ward 1",
                    "latitude": "23.010000",
                    "longitude": "72.510000",
                },
                files={"image": (f"img1_{i}.png", generate_test_image("PNG"), "image/png")},
                headers=headers_one,
            )

        # Citizen Two submits 1 issue
        self.client.post(
            "/issues/",
            data={
                "title": "Citizen Two Report #1",
                "description": "Description from citizen two",
                "category": "Street Light",
                "severity": "High",
                "location": "Ward 5",
                "latitude": "23.050000",
                "longitude": "72.550000",
            },
            files={"image": ("img2_1.png", generate_test_image("PNG"), "image/png")},
            headers=headers_two,
        )

        # Total in DB should be 3
        self.assertEqual(self.db.query(CivicIssue).count(), 3)

        # GET /issues/mine for Citizen One must return exactly 2 reports
        res_one = self.client.get("/issues/mine", headers=headers_one)
        self.assertEqual(res_one.status_code, 200)
        reports_one = res_one.json()
        self.assertEqual(len(reports_one), 2)
        for r in reports_one:
            self.assertIn("Citizen One", r["title"])

        # GET /issues/mine for Citizen Two must return exactly 1 report
        res_two = self.client.get("/issues/mine", headers=headers_two)
        self.assertEqual(res_two.status_code, 200)
        reports_two = res_two.json()
        self.assertEqual(len(reports_two), 1)
        self.assertIn("Citizen Two", reports_two[0]["title"])

        # GET /issues/ (public feed) returns all 3 reports
        public_res = self.client.get("/issues/")
        self.assertEqual(public_res.status_code, 200)
        self.assertEqual(len(public_res.json()), 3)


if __name__ == "__main__":
    unittest.main()
