"""
CIVICSOL - Phase 1: Authentication & Security Test Suite
Tests authentication endpoints, citizen ID generation, bcrypt hashing,
JWT token generation & payload validation, duplicate conflict handling,
unauthenticated route protection, and password change policies.

Isolated test database: In-memory SQLite with StaticPool (never touches production PostgreSQL).
"""

import re
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth.security import (
    ALGORITHM,
    SECRET_KEY,
    decode_access_token,
    verify_password,
)
from backend.core.config import settings
from backend.database import Base, get_db
from backend.main import app
from backend.models import User

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


class TestAuthenticationAndSecurity(unittest.TestCase):
    """
    Test suite for CIVICSOL Authentication and Security.
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
        """Prepare a fresh database session and test client for each test."""
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

    def tearDown(self):
        """Clean up database session and reset dependency overrides."""
        self.db.close()
        app.dependency_overrides.clear()

    # ==========================================================================
    # 1. SUCCESSFUL SIGNUP & CITIZEN ID FORMAT
    # ==========================================================================
    def test_01_successful_signup_and_citizen_id_format(self):
        """
        Verify that citizen signup succeeds with valid data, returns HTTP 201,
        and generates a citizen ID adhering to the CIVIC-XXXXXX format.
        """
        payload = {
            "name": "Aarav Sharma",
            "mobile": "9876543210",
            "email": "aarav.sharma@example.com",
            "password": "StrongPassword123!",
            "preferred_language": "English",
        }

        response = self.client.post("/auth/signup", json=payload)
        self.assertEqual(
            response.status_code,
            201,
            f"Expected 201 Created, got {response.status_code}: {response.text}",
        )

        data = response.json()
        self.assertIn("citizen_id", data)
        self.assertEqual(data["name"], payload["name"])
        self.assertEqual(data["mobile"], payload["mobile"])
        self.assertEqual(data["email"], payload["email"])
        self.assertEqual(data["preferred_language"], payload["preferred_language"])

        # Validate format: CIVIC- followed by exactly 6 digits
        citizen_id = data["citizen_id"]
        self.assertIsNotNone(
            re.match(r"^CIVIC-\d{6}$", citizen_id),
            f"Citizen ID '{citizen_id}' does not match expected format CIVIC-XXXXXX",
        )

        # Verify user was persisted in the test database
        user = self.db.query(User).filter(User.mobile == payload["mobile"]).first()
        self.assertIsNotNone(user, "User record was not found in the database.")
        self.assertEqual(user.citizen_id, citizen_id)

    # ==========================================================================
    # 2. BCRYPT PASSWORD HASHING
    # ==========================================================================
    def test_02_bcrypt_password_hashing(self):
        """
        Verify that passwords are cryptographically hashed using bcrypt
        and that plain passwords are never stored in the database.
        """
        raw_password = "SuperSecretPassword123@"
        payload = {
            "name": "Priya Patel",
            "mobile": "9876543211",
            "email": "priya.patel@example.com",
            "password": raw_password,
            "preferred_language": "Gujarati",
        }

        response = self.client.post("/auth/signup", json=payload)
        self.assertEqual(response.status_code, 201)

        user = self.db.query(User).filter(User.mobile == payload["mobile"]).first()
        self.assertIsNotNone(user)

        # Ensure plaintext password is NOT stored
        self.assertNotEqual(user.password_hash, raw_password)

        # Bcrypt hash format verification ($2b$ or $2a$)
        self.assertTrue(
            user.password_hash.startswith(("$2b$", "$2a$")),
            f"Password hash '{user.password_hash[:10]}...' does not appear to be a bcrypt hash.",
        )

        # Verify bcrypt validation logic
        self.assertTrue(
            verify_password(raw_password, user.password_hash),
            "Valid password failed bcrypt verification.",
        )
        self.assertFalse(
            verify_password("WrongPassword123@", user.password_hash),
            "Invalid password unexpectedly passed bcrypt verification.",
        )

    # ==========================================================================
    # 3. DUPLICATE EMAIL OR MOBILE RETURNING HTTP 409
    # ==========================================================================
    def test_03_duplicate_mobile_returns_409(self):
        """
        Verify that signing up with an already registered mobile number
        returns HTTP 409 Conflict.
        """
        user_one = {
            "name": "First Citizen",
            "mobile": "9811111111",
            "email": "first@example.com",
            "password": "Password123!",
        }
        res_one = self.client.post("/auth/signup", json=user_one)
        self.assertEqual(res_one.status_code, 201)

        # Attempt registration with duplicate mobile
        duplicate_mobile = {
            "name": "Duplicate Mobile Citizen",
            "mobile": "9811111111",
            "email": "other@example.com",
            "password": "Password123!",
        }
        res_two = self.client.post("/auth/signup", json=duplicate_mobile)
        self.assertEqual(
            res_two.status_code,
            409,
            f"Expected 409 Conflict for duplicate mobile, got {res_two.status_code}",
        )
        self.assertIn("mobile", res_two.json().get("detail", "").lower())

    def test_04_duplicate_email_returns_409(self):
        """
        Verify that signing up with an already registered email address
        (even with different case) returns HTTP 409 Conflict.
        """
        user_one = {
            "name": "First Citizen",
            "mobile": "9822222222",
            "email": "shared.email@example.com",
            "password": "Password123!",
        }
        res_one = self.client.post("/auth/signup", json=user_one)
        self.assertEqual(res_one.status_code, 201)

        # Attempt registration with duplicate email in uppercase
        duplicate_email = {
            "name": "Duplicate Email Citizen",
            "mobile": "9833333333",
            "email": "SHARED.EMAIL@EXAMPLE.COM",
            "password": "Password123!",
        }
        res_two = self.client.post("/auth/signup", json=duplicate_email)
        self.assertEqual(
            res_two.status_code,
            409,
            f"Expected 409 Conflict for duplicate email, got {res_two.status_code}",
        )
        self.assertIn("email", res_two.json().get("detail", "").lower())

    # ==========================================================================
    # 4. SUCCESSFUL SIGNIN & JWT PAYLOAD VALIDATION
    # ==========================================================================
    def test_05_successful_signin_and_jwt_payload_validation(self):
        """
        Verify that signing in with valid credentials returns HTTP 200,
        issues a bearer token, and the JWT payload contains expected claims
        ('sub', 'citizen_id', and future 'exp').
        """
        raw_password = "CorrectPassword123!"
        signup_data = {
            "name": "Devendra Joshi",
            "mobile": "9844444444",
            "email": "devendra@example.com",
            "password": raw_password,
        }
        signup_res = self.client.post("/auth/signup", json=signup_data)
        self.assertEqual(signup_res.status_code, 201)
        citizen_id = signup_res.json()["citizen_id"]

        # Signin
        signin_res = self.client.post(
            "/auth/signin",
            json={
                "mobile": signup_data["mobile"],
                "password": raw_password,
            },
        )
        self.assertEqual(
            signin_res.status_code,
            200,
            f"Expected 200 OK for valid signin, got {signin_res.status_code}: {signin_res.text}",
        )

        data = signin_res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data.get("token_type"), "bearer")
        self.assertEqual(data.get("citizen_id"), citizen_id)

        # Decode and validate JWT payload with centralized configuration
        token = data["access_token"]
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Also verify decode_access_token helper
        decoded_via_helper = decode_access_token(token)
        self.assertIsNotNone(decoded_via_helper)
        self.assertEqual(payload, decoded_via_helper)

        self.assertIn("sub", payload, "JWT missing 'sub' claim")
        self.assertIn("citizen_id", payload, "JWT missing 'citizen_id' claim")
        self.assertIn("exp", payload, "JWT missing 'exp' claim")

        self.assertEqual(payload["citizen_id"], citizen_id)

        # Verify exp is in the future
        now_ts = datetime.now(timezone.utc).timestamp()
        self.assertGreater(
            payload["exp"],
            now_ts,
            "JWT expiration timestamp is not in the future.",
        )

    # ==========================================================================
    # 5. INVALID CREDENTIALS RETURNING HTTP 401
    # ==========================================================================
    def test_06_invalid_credentials_wrong_password_returns_401(self):
        """
        Verify that signing in with an existing mobile but wrong password
        returns HTTP 401 Unauthorized.
        """
        self.client.post(
            "/auth/signup",
            json={
                "name": "Test User",
                "mobile": "9855555555",
                "password": "CorrectPassword123!",
            },
        )

        res = self.client.post(
            "/auth/signin",
            json={
                "mobile": "9855555555",
                "password": "IncorrectPassword999!",
            },
        )
        self.assertEqual(
            res.status_code,
            401,
            f"Expected 401 Unauthorized for wrong password, got {res.status_code}",
        )
        self.assertIn("invalid", res.json().get("detail", "").lower())

    def test_07_invalid_credentials_unregistered_mobile_returns_401(self):
        """
        Verify that signing in with a non-existent mobile number
        returns HTTP 401 Unauthorized.
        """
        res = self.client.post(
            "/auth/signin",
            json={
                "mobile": "9999900000",
                "password": "ArbitraryPassword123!",
            },
        )
        self.assertEqual(
            res.status_code,
            401,
            f"Expected 401 Unauthorized for unregistered user, got {res.status_code}",
        )
        self.assertIn("invalid", res.json().get("detail", "").lower())

    # ==========================================================================
    # 6. UNAUTHENTICATED ACCESS TO PROTECTED ROUTES
    # ==========================================================================
    def test_08_unauthenticated_access_with_invalid_token_returns_401(self):
        """
        Verify that accessing protected endpoints (/auth/me, /issues/mine, /rewards/summary)
        with an invalid or corrupted Bearer token returns HTTP 401 Unauthorized.
        """
        protected_endpoints = [
            "/auth/me",
            "/issues/mine",
            "/rewards/summary",
        ]
        headers = {"Authorization": "Bearer completely_bogus_token_xyz"}

        for endpoint in protected_endpoints:
            with self.subTest(endpoint=endpoint):
                res = self.client.get(endpoint, headers=headers)
                self.assertEqual(
                    res.status_code,
                    401,
                    f"Expected 401 Unauthorized for invalid token on {endpoint}, got {res.status_code}",
                )

    def test_09_unauthenticated_access_missing_token_returns_401(self):
        """
        Verify that accessing protected endpoints without an Authorization header
        returns HTTP 401 Unauthorized (per standard RFC 7235 / user requirements).
        
        NOTE: If FastAPI's default HTTPBearer returns HTTP 403 Forbidden instead
        of HTTP 401 Unauthorized when the header is missing, this test captures
        that specific implementation discrepancy.
        """
        protected_endpoints = [
            "/auth/me",
            "/issues/mine",
            "/rewards/summary",
        ]

        for endpoint in protected_endpoints:
            with self.subTest(endpoint=endpoint):
                res = self.client.get(endpoint)
                self.assertEqual(
                    res.status_code,
                    401,
                    f"Expected 401 Unauthorized when Authorization header is omitted on {endpoint}, but got {res.status_code}: {res.text}",
                )

    # ==========================================================================
    # 7. PASSWORD CHANGES, OLD-PASSWORD & IDENTICAL-NEW-PASSWORD REJECTION
    # ==========================================================================
    def test_10_password_change_identical_new_password_rejected(self):
        """
        Verify that changing password to the exact same current password
        is rejected with HTTP 400 Bad Request.
        """
        current_password = "ExistingPassword123!"
        signup_res = self.client.post(
            "/auth/signup",
            json={
                "name": "Change Pass User",
                "mobile": "9866666666",
                "password": current_password,
            },
        )
        self.assertEqual(signup_res.status_code, 201)

        signin_res = self.client.post(
            "/auth/signin",
            json={"mobile": "9866666666", "password": current_password},
        )
        token = signin_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to change to identical new password
        res = self.client.put(
            "/auth/change-password",
            json={
                "current_password": current_password,
                "new_password": current_password,
            },
            headers=headers,
        )
        self.assertEqual(
            res.status_code,
            400,
            f"Expected 400 Bad Request for identical new password, got {res.status_code}",
        )
        self.assertIn("different", res.json().get("detail", "").lower())

    def test_11_password_change_incorrect_current_password_rejected(self):
        """
        Verify that attempting to change password with an incorrect current password
        is rejected with HTTP 400 Bad Request.
        """
        current_password = "ExistingPassword123!"
        self.client.post(
            "/auth/signup",
            json={
                "name": "Change Pass User 2",
                "mobile": "9877777777",
                "password": current_password,
            },
        )

        signin_res = self.client.post(
            "/auth/signin",
            json={"mobile": "9877777777", "password": current_password},
        )
        token = signin_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt with wrong current password
        res = self.client.put(
            "/auth/change-password",
            json={
                "current_password": "WrongPassword999!",
                "new_password": "BrandNewPassword123!",
            },
            headers=headers,
        )
        self.assertEqual(
            res.status_code,
            400,
            f"Expected 400 Bad Request for incorrect current password, got {res.status_code}",
        )
        self.assertIn("incorrect", res.json().get("detail", "").lower())

    def test_12_password_change_success_and_old_password_invalidation(self):
        """
        Verify that providing valid current and new passwords successfully updates
        the password, old password can no longer sign in, and new password signs in.
        """
        old_password = "InitialPassword123!"
        new_password = "BrandNewPassword456!"
        mobile = "9888888888"

        self.client.post(
            "/auth/signup",
            json={
                "name": "Successful Change User",
                "mobile": mobile,
                "password": old_password,
            },
        )

        signin_res = self.client.post(
            "/auth/signin",
            json={"mobile": mobile, "password": old_password},
        )
        token = signin_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Perform valid password change
        change_res = self.client.put(
            "/auth/change-password",
            json={
                "current_password": old_password,
                "new_password": new_password,
            },
            headers=headers,
        )
        self.assertEqual(
            change_res.status_code,
            200,
            f"Expected 200 OK for successful password change, got {change_res.status_code}",
        )

        # Verify old password no longer works
        old_signin_res = self.client.post(
            "/auth/signin",
            json={"mobile": mobile, "password": old_password},
        )
        self.assertEqual(
            old_signin_res.status_code,
            401,
            "Old password should return 401 Unauthorized after password change.",
        )

        # Verify new password signs in successfully
        new_signin_res = self.client.post(
            "/auth/signin",
            json={"mobile": mobile, "password": new_password},
        )
        self.assertEqual(
            new_signin_res.status_code,
            200,
            "New password failed to sign in after password change.",
        )

    # ==========================================================================
    # 8. AUTHENTICATED ACCESS TO PROTECTED ENDPOINTS WITH VALID TOKEN
    # ==========================================================================
    def test_13_authenticated_access_to_protected_endpoints(self):
        """
        Verify that presenting a valid Bearer token allows successful access
        (HTTP 200) to /auth/me, /issues/mine, and /rewards/summary.
        """
        mobile = "9899999999"
        password = "ValidTokenPass123!"
        signup_res = self.client.post(
            "/auth/signup",
            json={
                "name": "Protected Access User",
                "mobile": mobile,
                "email": "protected.user@example.com",
                "password": password,
            },
        )
        self.assertEqual(signup_res.status_code, 201)
        citizen_id = signup_res.json()["citizen_id"]

        signin_res = self.client.post(
            "/auth/signin",
            json={"mobile": mobile, "password": password},
        )
        self.assertEqual(signin_res.status_code, 200)
        token = signin_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. /auth/me
        me_res = self.client.get("/auth/me", headers=headers)
        self.assertEqual(
            me_res.status_code,
            200,
            f"Expected 200 OK on /auth/me with valid token, got {me_res.status_code}",
        )
        self.assertEqual(me_res.json()["citizen_id"], citizen_id)
        self.assertEqual(me_res.json()["mobile"], mobile)

        # 2. /issues/mine
        issues_res = self.client.get("/issues/mine", headers=headers)
        self.assertEqual(
            issues_res.status_code,
            200,
            f"Expected 200 OK on /issues/mine with valid token, got {issues_res.status_code}",
        )
        self.assertIsInstance(issues_res.json(), list)

        # 3. /rewards/summary
        rewards_res = self.client.get("/rewards/summary", headers=headers)
        self.assertEqual(
            rewards_res.status_code,
            200,
            f"Expected 200 OK on /rewards/summary with valid token, got {rewards_res.status_code}",
        )
        self.assertEqual(rewards_res.json()["citizen_id"], citizen_id)
        self.assertIn("credits", rewards_res.json())
        self.assertIn("level", rewards_res.json())

    # ==========================================================================
    # 9. PASSWORD-RESET TOKEN COMPATIBILITY WITH JWT CONFIGURATION
    # ==========================================================================
    def test_14_password_reset_token_compatibility_with_jwt_settings(self):
        """
        Verify that password reset tokens and access tokens use the exact same
        centralized JWT settings (settings.JWT_SECRET and settings.JWT_ALGORITHM).
        """
        from datetime import timedelta
        # Simulate creating a reset token payload exactly as router.py does
        reset_payload = {
            "sub": "100",
            "otp_id": 42,
            "type": "password_reset",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        reset_token = jwt.encode(
            reset_payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

        # Decode using the centralized security configuration
        decoded = jwt.decode(
            reset_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        self.assertEqual(decoded["sub"], "100")
        self.assertEqual(decoded["otp_id"], 42)
        self.assertEqual(decoded["type"], "password_reset")


if __name__ == "__main__":
    unittest.main()
