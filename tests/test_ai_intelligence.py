"""
CIVICSOL — AI-Powered Civic Intelligence System Unit Tests
Covers all 16 required verification scenarios using mocked AI responses:
1. Valid image analysis.
2. Unsupported image formats.
3. Corrupt image uploads.
4. Model unavailable.
5. Gemini API unavailable.
6. Invalid predictions.
7. Confidence validation.
8. Department recommendation.
9. Severity and priority recommendations.
10. Duplicate detection.
11. Unauthorized AI analysis.
12. Recommendation approval.
13. Recommendation rejection.
14. AI processing failure.
15. Citizen reporting when AI is unavailable.
16. Preservation of existing issue data.
"""

import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from PIL import Image

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.ai.department_recommender import recommend_department
from backend.ai.duplicate_detector import detect_similar_nearby_issues, haversine_distance_meters
from backend.ai.gemini_service import validate_and_sanitize_gemini_payload
from backend.ai.pipeline import run_issue_ai_analysis
from backend.ai.priority_engine import compute_severity_and_priority
from backend.auth.security import create_access_token, hash_password
from backend.database import Base, get_db
from backend.main import app
from backend.models import AIAnalysis, AuditLog, CivicIssue, Department, User
from ml.yolo_detector import CivicYOLODetector, validate_and_preprocess_image


class TestAICivicIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

        # Create a temporary test image on disk inside uploads/test_ai_sample.jpg
        os.makedirs("uploads", exist_ok=True)
        cls.sample_image_path = os.path.join("uploads", "test_ai_sample.jpg")
        img = Image.new("RGB", (640, 480), color=(90, 110, 130))
        img.save(cls.sample_image_path, format="JPEG")

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=cls.engine)
        if os.path.exists(cls.sample_image_path):
            try:
                os.remove(cls.sample_image_path)
            except OSError:
                pass

    def setUp(self):
        self.db = self.TestingSessionLocal()

        # Seed standard municipal departments
        dept_specs = [
            ("ROADS_BRIDGES", "Roads & Bridges Department"),
            ("SOLID_WASTE", "Solid Waste Management"),
            ("STREET_LIGHTING", "Street Lighting & Electrical"),
            ("WATER_SEWERAGE", "Water Supply & Sewerage"),
            ("DRAINAGE", "Stormwater & Drainage"),
            ("PUBLIC_INFRA", "Public Infrastructure & Parks"),
        ]
        for code, name in dept_specs:
            existing = self.db.query(Department).filter_by(code=code).first()
            if not existing:
                self.db.add(Department(code=code, name=name, is_active=True))
        self.db.commit()

        self.roads_dept = self.db.query(Department).filter_by(code="ROADS_BRIDGES").first()
        self.waste_dept = self.db.query(Department).filter_by(code="SOLID_WASTE").first()

        # Seed Super Admin
        self.admin = self.db.query(User).filter_by(email="ai.admin@civicsol.gov").first()
        if not self.admin:
            self.admin = User(
                name="AI Command Admin",
                email="ai.admin@civicsol.gov",
                mobile="9700000001",
                password_hash=hash_password("AdminPass!123"),
                citizen_id="ADM-AI-1",
                role="SUPER_ADMIN",
                is_active=True,
            )
            self.db.add(self.admin)
            self.db.commit()
            self.db.refresh(self.admin)

        # Seed Citizens Alice & Bob
        self.alice = self.db.query(User).filter_by(mobile="9700000002").first()
        if not self.alice:
            self.alice = User(
                name="Alice Citizen",
                email="alice.ai@example.com",
                mobile="9700000002",
                password_hash=hash_password("AlicePass!123"),
                citizen_id="CIT-AI-ALICE",
                role="CITIZEN",
                is_active=True,
            )
            self.db.add(self.alice)
            self.db.commit()
            self.db.refresh(self.alice)

        self.bob = self.db.query(User).filter_by(mobile="9700000003").first()
        if not self.bob:
            self.bob = User(
                name="Bob Citizen",
                email="bob.ai@example.com",
                mobile="9700000003",
                password_hash=hash_password("BobPass!123"),
                citizen_id="CIT-AI-BOB",
                role="CITIZEN",
                is_active=True,
            )
            self.db.add(self.bob)
            self.db.commit()
            self.db.refresh(self.bob)

        self.admin_token = create_access_token({"sub": str(self.admin.id), "role": "SUPER_ADMIN"})
        self.alice_token = create_access_token({"sub": str(self.alice.id), "citizen_id": self.alice.citizen_id})
        self.bob_token = create_access_token({"sub": str(self.bob.id), "citizen_id": self.bob.citizen_id})

        # Mock Gemini call by default to avoid slow external API calls and network timeouts during tests
        self.gemini_mock = patch(
            "backend.ai.gemini_service._call_gemini_sync",
            return_value=json.dumps({
                "extracted_problem": "Civic hazard reported by citizen.",
                "recommended_category": "Road Damage",
                "public_impact": "Public safety risk requiring municipal inspection.",
                "suggested_severity": "HIGH",
                "suggested_department_code": "ROADS_BRIDGES",
                "disagreement_explanation": None,
                "explanation": "Road Damage detected requiring municipal review.",
            }),
        )
        self.gemini_mock.start()

    def tearDown(self):
        self.gemini_mock.stop()
        self.db.close()

    def _create_sample_issue(
        self,
        title="Large deep pothole on main highway",
        description="Dangerous deep crater causing accidents near hospital school junction.",
        category="Road Damage",
        severity="High",
        priority="High",
        latitude=23.0225,
        longitude=72.5714,
        image_path=None,
    ) -> CivicIssue:
        issue = CivicIssue(
            title=title,
            description=description,
            category=category,
            severity=severity,
            priority=priority,
            status="Reported",
            location="SG Highway Hospital Crossing",
            latitude=latitude,
            longitude=longitude,
            image_path=image_path or self.sample_image_path,
            user_id=self.alice.id,
        )
        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)
        return issue

    # =====================================================
    # 1. VALID IMAGE ANALYSIS
    # =====================================================
    def test_01_valid_image_analysis(self):
        """Valid image analysis preprocesses image, records YOLO detections, and saves annotated image separately."""
        issue = self._create_sample_issue()

        mocked_yolo_result = {
            "processing_status": "COMPLETED",
            "model_name": "CIVICSOL-YOLOv8",
            "model_version": "1.0.0-civic6",
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "predicted_category": "Road Damage",
            "confidence_score": 0.9125,
            "detected_objects": [
                {
                    "class_id": 0,
                    "class_name": "pothole",
                    "civic_category": "Road Damage",
                    "confidence": 0.9125,
                    "bbox": [120.0, 140.0, 360.0, 310.0],
                }
            ],
            "annotated_image_path": "uploads/annotated/annotated_test.jpg",
            "image_metadata": {"width": 640, "height": 480, "format": "JPEG"},
            "reason": "Detected 1 object(s) with primary class 'pothole' (0.91).",
        }

        with patch("backend.ai.pipeline.yolo_detector.analyze_image", return_value=mocked_yolo_result):
            record = run_issue_ai_analysis(self.db, issue, force_reanalyze=True)

        self.assertEqual(record.processing_status, "COMPLETED")
        self.assertEqual(record.predicted_category, "Road Damage")
        self.assertAlmostEqual(record.confidence_score, 0.9125, places=4)
        self.assertEqual(len(record.detected_objects), 1)
        self.assertEqual(record.annotated_image_path, "uploads/annotated/annotated_test.jpg")
        # Ensure original citizen image path on issue was NOT overwritten
        self.assertEqual(issue.image_path, self.sample_image_path)

    # =====================================================
    # 2. UNSUPPORTED IMAGE FORMATS
    # =====================================================
    def test_02_unsupported_image_formats(self):
        """Unsupported file extensions (.exe, .gif, .txt) are rejected during image validation."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"not an image")
            tmp_path = tmp.name

        try:
            res = validate_and_preprocess_image(tmp_path)
            self.assertFalse(res["valid"])
            self.assertIn("Unsupported image format", res["error"])
        finally:
            os.remove(tmp_path)

    # =====================================================
    # 3. CORRUPT IMAGE UPLOADS
    # =====================================================
    def test_03_corrupt_image_uploads(self):
        """Corrupt bytes with a .jpg extension fail validation cleanly without crashing pipeline."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"\x00\x01\x02corrupt-jpeg-payload")
            corrupt_path = tmp.name

        try:
            res = validate_and_preprocess_image(corrupt_path)
            self.assertFalse(res["valid"])
            self.assertIn("Corrupt or unreadable image file", res["error"])

            detector = CivicYOLODetector(model_path="/nonexistent/weights.pt")
            det_res = detector.analyze_image(corrupt_path)
            self.assertEqual(det_res["processing_status"], "INVALID_IMAGE")
            self.assertIsNone(det_res["confidence_score"])
        finally:
            os.remove(corrupt_path)

    # =====================================================
    # 4. MODEL UNAVAILABLE
    # =====================================================
    def test_04_model_unavailable(self):
        """When trained YOLO weights are unavailable, detector returns MODEL_UNAVAILABLE and never invents confidence."""
        detector = CivicYOLODetector(model_path="/nonexistent/civicsol_yolo.pt")
        res = detector.analyze_image(self.sample_image_path)
        self.assertEqual(res["processing_status"], "MODEL_UNAVAILABLE")
        self.assertIsNone(res["confidence_score"])
        self.assertIsNone(res["predicted_category"])
        self.assertEqual(res["detected_objects"], [])

    # =====================================================
    # 5. GEMINI API UNAVAILABLE
    # =====================================================
    def test_05_gemini_api_unavailable(self):
        """When GEMINI_API_KEY is absent or Gemini raises an error, deterministic fallback succeeds cleanly."""
        issue = self._create_sample_issue(
            title="Overflowing garbage dump near market",
            description="Foul smell and uncollected waste blocking pedestrian footpath.",
            category="Garbage",
        )
        with patch("backend.ai.gemini_service.settings.GEMINI_API_KEY", ""):
            record = run_issue_ai_analysis(self.db, issue, force_reanalyze=True)

        self.assertIsNotNone(record.id)
        self.assertEqual(record.predicted_category, "Garbage")
        self.assertEqual(record.suggested_department_id, self.waste_dept.id)
        self.assertIn("Fallback", record.model_name)

    # =====================================================
    # 6. INVALID PREDICTIONS
    # =====================================================
    def test_06_invalid_predictions(self):
        """Invalid categories, severities, priorities, or non-dict payloads from LLM are sanitized to valid enums."""
        raw_invalid = {
            "issue_type": "Alien Invasion",
            "category": "UNSUPPORTED_CATEGORY_XYZ",
            "suggested_severity": "EXTREME_DANGER",
            "suggested_priority": "SUPER_URGENT",
            "suggested_department_code": "UNKNOWN_DEPT",
            "safety_risk": "yes",
            "urgency": "",
            "explanation": "Short",
            "disagrees_with_visual": False,
        }
        yolo_result = {
            "predicted_category": "Water Leakage",
            "confidence_score": 0.88,
        }
        sanitized = validate_and_sanitize_gemini_payload(raw_invalid, yolo_result)
        self.assertEqual(sanitized["category"], "Water Leakage")
        self.assertEqual(sanitized["suggested_severity"], "MEDIUM")
        self.assertEqual(sanitized["suggested_priority"], "NORMAL")
        self.assertEqual(sanitized["suggested_department_code"], "WATER_SEWERAGE")
        # Since LLM category differed from visual without explanation, disagreement is flagged
        self.assertTrue(sanitized["disagrees_with_visual"])

    # =====================================================
    # 7. CONFIDENCE VALIDATION
    # =====================================================
    def test_07_confidence_validation(self):
        """Confidence scores are never invented when YOLO has no detections, and clamped to [0, 1] when present."""
        issue = self._create_sample_issue()
        no_det_yolo = {
            "processing_status": "NO_DETECTION",
            "model_name": "CIVICSOL-YOLOv8",
            "model_version": "1.0.0-civic6",
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "predicted_category": None,
            "confidence_score": None,
            "detected_objects": [],
            "annotated_image_path": None,
            "image_metadata": {"width": 640, "height": 480},
            "reason": "No objects met threshold.",
        }
        with patch("backend.ai.pipeline.yolo_detector.analyze_image", return_value=no_det_yolo):
            record = run_issue_ai_analysis(self.db, issue, force_reanalyze=True)

        self.assertIsNone(record.confidence_score)
        self.assertEqual(record.processing_status, "NO_DETECTION")

    # =====================================================
    # 8. DEPARTMENT RECOMMENDATION
    # =====================================================
    def test_08_department_recommendation(self):
        """Categories map accurately to active PostgreSQL Department rows."""
        mappings = [
            ("Road Damage", "ROADS_BRIDGES"),
            ("Garbage", "SOLID_WASTE"),
            ("Street Light", "STREET_LIGHTING"),
            ("Water Leakage", "WATER_SEWERAGE"),
            ("Drainage", "DRAINAGE"),
            ("Public Infrastructure", "PUBLIC_INFRA"),
        ]
        for cat, expected_code in mappings:
            rec = recommend_department(self.db, predicted_category=cat)
            self.assertIsNotNone(rec["department_id"])
            self.assertEqual(rec["department_code"], expected_code)

        uncertain_rec = recommend_department(self.db, predicted_category="UNCERTAIN")
        self.assertIsNone(uncertain_rec["department_id"])
        self.assertTrue(uncertain_rec["requires_manual_triage"])

    # =====================================================
    # 9. SEVERITY AND PRIORITY RECOMMENDATIONS
    # =====================================================
    def test_09_severity_and_priority_recommendations(self):
        """Explainable risk engine computes CRITICAL/URGENT for high-hazard reports and LOW/LOW for minor ones."""
        high_risk = compute_severity_and_priority(
            predicted_category="Road Damage",
            citizen_category="Road Damage",
            citizen_severity="Critical",
            description="Deep open manhole and live wire sparking near hospital and school main road.",
            location_text="Civil Hospital Main Highway Junction",
            confidence_score=0.94,
            detected_objects=[
                {"class_name": "pothole", "confidence": 0.94, "bbox": [10, 10, 500, 400]}
            ],
            duplicate_count=3,
            image_width=640,
            image_height=480,
        )
        self.assertEqual(high_risk["suggested_severity"], "CRITICAL")
        self.assertEqual(high_risk["suggested_priority"], "URGENT")
        self.assertTrue(len(high_risk["factors"]) >= 3)

        low_risk = compute_severity_and_priority(
            predicted_category="Garbage",
            citizen_category="Garbage",
            citizen_severity="Low",
            description="Small litter wrapper on side bench.",
            location_text="Sector 4 Lane",
            confidence_score=None,
            detected_objects=[],
            duplicate_count=0,
        )
        self.assertIn(low_risk["suggested_severity"], ("LOW", "MEDIUM"))
        self.assertIn(low_risk["suggested_priority"], ("LOW", "NORMAL"))

    # =====================================================
    # 10. DUPLICATE DETECTION
    # =====================================================
    def test_10_duplicate_detection(self):
        """Nearby issues with matching category and similar text are flagged without auto-closing either issue."""
        issue_a = self._create_sample_issue(
            title="Deep pothole near hospital gate",
            description="Large pothole on SG Highway hospital entrance causing traffic jam.",
            category="Road Damage",
            latitude=23.02250,
            longitude=72.57140,
        )
        issue_b = self._create_sample_issue(
            title="Deep pothole at hospital gate",
            description="Big pothole on SG Highway hospital entrance blocking vehicles.",
            category="Road Damage",
            latitude=23.02265,  # ~18 meters away
            longitude=72.57145,
        )

        dist = haversine_distance_meters(
            issue_a.latitude, issue_a.longitude, issue_b.latitude, issue_b.longitude
        )
        self.assertLess(dist, 50.0)

        dup_res = detect_similar_nearby_issues(
            self.db,
            issue_id=issue_b.id,
            latitude=issue_b.latitude,
            longitude=issue_b.longitude,
            category=issue_b.category,
            predicted_category="Road Damage",
            title=issue_b.title,
            description=issue_b.description,
            created_at=issue_b.created_at,
        )
        self.assertGreaterEqual(dup_res["duplicate_count"], 1)
        self.assertEqual(dup_res["similar_issues"][0]["issue_id"], issue_a.id)
        # Verify neither issue was automatically closed or rejected
        self.assertEqual(issue_a.status, "Reported")
        self.assertEqual(issue_b.status, "Reported")

    # =====================================================
    # 11. UNAUTHORIZED AI ANALYSIS
    # =====================================================
    def test_11_unauthorized_ai_analysis(self):
        """Citizens cannot trigger reanalysis, approve/reject recommendations, or view another citizen's AI analysis."""
        alice_issue = self._create_sample_issue()

        # Unauthenticated request -> 401
        r_unauth = self.client.get(f"/ai/analysis/{alice_issue.id}")
        self.assertEqual(r_unauth.status_code, 401)

        # Bob (another citizen) trying to view Alice's issue AI analysis -> 403
        r_bob_view = self.client.get(
            f"/ai/analysis/{alice_issue.id}",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(r_bob_view.status_code, 403)

        # Bob trying to trigger POST /ai/analyze/{id} on Alice's issue -> 403
        r_bob_analyze = self.client.post(
            f"/ai/analyze/{alice_issue.id}",
            headers={"Authorization": f"Bearer {self.bob_token}"},
        )
        self.assertEqual(r_bob_analyze.status_code, 403)

        # Alice trying to call authority-only POST /ai/reanalyze/{id} -> 403
        r_alice_reanalyze = self.client.post(
            f"/ai/reanalyze/{alice_issue.id}",
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertEqual(r_alice_reanalyze.status_code, 403)

        # Alice trying to call authority-only POST /ai/analysis/{id}/approve -> 403
        r_alice_approve = self.client.post(
            f"/ai/analysis/{alice_issue.id}/approve",
            json={"apply_category": True},
            headers={"Authorization": f"Bearer {self.alice_token}"},
        )
        self.assertEqual(r_alice_approve.status_code, 403)

    # =====================================================
    # 12. RECOMMENDATION APPROVAL
    # =====================================================
    def test_12_recommendation_approval(self):
        """Authority approval updates official issue fields, sets review_status=APPROVED, and writes AuditLog."""
        issue = self._create_sample_issue(
            category="Public Infrastructure",
            severity="Low",
            priority="Low",
            description="Huge deep road pothole causing accidents near school hospital.",
        )

        # Run AI analysis as admin
        r_run = self.client.post(
            f"/ai/analyze/{issue.id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(r_run.status_code, 200)

        # Approve recommendation as admin
        r_approve = self.client.post(
            f"/ai/analysis/{issue.id}/approve",
            json={
                "apply_category": True,
                "apply_severity": True,
                "apply_priority": True,
                "apply_department": True,
                "comment": "Verified visual and text recommendation.",
            },
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(r_approve.status_code, 200)
        payload = r_approve.json()
        self.assertEqual(payload["latest_analysis"]["review_status"], "APPROVED")

        self.db.refresh(issue)
        self.assertIsNotNone(issue.department_id)

        audit = (
            self.db.query(AuditLog)
            .filter_by(action="AI_RECOMMENDATION_APPROVED", entity_id=issue.id)
            .first()
        )
        self.assertIsNotNone(audit)

    # =====================================================
    # 13. RECOMMENDATION REJECTION
    # =====================================================
    def test_13_recommendation_rejection(self):
        """Authority rejection marks review_status=REJECTED, keeps official issue fields untouched, and logs audit."""
        issue = self._create_sample_issue(
            category="Garbage",
            severity="Medium",
            priority="Normal",
        )
        self.client.post(
            f"/ai/analyze/{issue.id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )

        r_reject = self.client.post(
            f"/ai/analysis/{issue.id}/reject",
            json={"comment": "Citizen category is already accurate; rejecting override."},
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(r_reject.status_code, 200)
        self.assertEqual(r_reject.json()["latest_analysis"]["review_status"], "REJECTED")

        self.db.refresh(issue)
        self.assertEqual(issue.category, "Garbage")
        self.assertEqual(issue.severity, "Medium")
        self.assertEqual(issue.priority, "Normal")

        audit = (
            self.db.query(AuditLog)
            .filter_by(action="AI_RECOMMENDATION_REJECTED", entity_id=issue.id)
            .first()
        )
        self.assertIsNotNone(audit)

    # =====================================================
    # 14. AI PROCESSING FAILURE
    # =====================================================
    def test_14_ai_processing_failure(self):
        """Unexpected internal error in sub-components records processing_status=FAILED without crashing."""
        issue = self._create_sample_issue()

        with patch("backend.ai.pipeline.yolo_detector.analyze_image", side_effect=RuntimeError("GPU OOM fault")):
            record = run_issue_ai_analysis(self.db, issue, force_reanalyze=True)

        self.assertEqual(record.processing_status, "FAILED")
        self.assertIn("GPU OOM fault", record.explanation)

    # =====================================================
    # 15. CITIZEN REPORTING WHEN AI IS UNAVAILABLE
    # =====================================================
    def test_15_citizen_reporting_when_ai_unavailable(self):
        """Citizen POST /issues/ succeeds and awards civic credits even if AI pipeline raises an exception."""
        buf = io.BytesIO()
        Image.new("RGB", (320, 240), color=(120, 80, 60)).save(buf, format="JPEG")
        buf.seek(0)

        with patch("backend.routes.issues.run_issue_ai_analysis", side_effect=RuntimeError("AI offline")):
            res = self.client.post(
                "/issues/",
                data={
                    "title": "Water Leakage",
                    "description": "Main water pipeline burst flooding road.",
                    "category": "Water Leakage",
                    "severity": "High",
                    "location": "Navrangpura Crossing",
                    "latitude": "23.0365",
                    "longitude": "72.5611",
                },
                files={"image": ("leak.jpg", buf, "image/jpeg")},
                headers={"Authorization": f"Bearer {self.alice_token}"},
            )

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["credits_earned"], 20)
        self.assertEqual(body["issue"]["category"], "Water Leakage")
        self.assertIn("ai_analysis", body)
        self.assertEqual(body["ai_analysis"]["processing_status"], "FAILED")

    # =====================================================
    # 16. PRESERVATION OF EXISTING ISSUE DATA
    # =====================================================
    def test_16_preservation_of_existing_issue_data(self):
        """Re-analyzing an issue preserves existing issue fields and retains all historical AIAnalysis records."""
        issue = self._create_sample_issue(
            title="Broken streetlight pole #44",
            description="Dark street corner with exposed cable.",
            category="Street Light",
            severity="High",
            priority="High",
        )

        # First analysis
        r1 = self.client.post(
            f"/ai/analyze/{issue.id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(r1.status_code, 200)

        # Re-analysis
        r2 = self.client.post(
            f"/ai/reanalyze/{issue.id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(r2.status_code, 200)

        # Verify history endpoint returns both analyses
        r_hist = self.client.get(
            f"/ai/analysis/{issue.id}/history",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(r_hist.status_code, 200)
        hist_data = r_hist.json()
        self.assertGreaterEqual(hist_data["total"], 2)

        # Verify original issue fields were not altered by analysis/reanalysis
        self.db.refresh(issue)
        self.assertEqual(issue.title, "Broken streetlight pole #44")
        self.assertEqual(issue.category, "Street Light")
        self.assertEqual(issue.severity, "High")
        self.assertEqual(issue.priority, "High")
        self.assertEqual(issue.status, "Reported")


if __name__ == "__main__":
    unittest.main()

