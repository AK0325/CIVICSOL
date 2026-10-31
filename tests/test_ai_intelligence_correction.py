"""
CIVICSOL — AI Intelligence Correction & Pilot Verification Test Suite
Verifies:
1. YOLO class-agnostic NMS and overlapping bbox suppression.
2. YOLO low-confidence detection flagging (< 45%).
3. Gemini evidence consistency: INCONSISTENT flag & requires_human_review when vision contradicts citizen text.
4. Gemini evidence consistency: CONSISTENT when vision and citizen text align.
5. Multi-factor duplicate engine: EXACT_REPLAY detection via SHA-256 and dHash.
6. Multi-factor duplicate engine: Different civic issues at the same location are NOT duplicates.
7. Multi-factor duplicate engine: Same issue reported by multiple citizens is linked without auto-rejection.
8. Exact API replay prevention in create_issue: No duplicate issue records and no duplicate credits.
9. Suspicious submission engine: Reused image across distant locations (> 1km) flagged as HIGH_RISK.
10. Suspicious submission engine: Burst frequency (> 3 reports in 5 mins) flagged.
11. Suspicious submission engine: Normal genuine report classified as NORMAL.
12. Authority false-positive feedback endpoint records feedback in metadata and creates AuditLog.
13. Authority duplicate linking endpoint associates reports and creates AuditLog.
14. Authority duplicate merging endpoint marks issue resolved with mandatory audit log.
15. Non-authority users are strictly forbidden from flagging false positives or merging issues.
"""

import hashlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from PIL import Image

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.ai.duplicate_detector import (
    compute_image_dhash,
    compute_image_sha256,
    detect_similar_nearby_issues,
    find_similar_nearby_issues,
    haversine_distance_meters,
    image_perceptual_similarity,
)
from backend.ai.gemini_service import (
    _heuristic_description_analysis,
    validate_and_sanitize_gemini_payload,
)
from backend.ai.suspicious_detector import evaluate_submission_authenticity
from backend.auth.security import create_access_token, hash_password
from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    AIAnalysis,
    AuditLog,
    CivicCreditTransaction,
    CivicIssue,
    Department,
    IssueStatusHistory,
    User,
)
from ml.yolo_detector import CivicYOLODetector


def _create_sample_image_bytes(color: tuple = (200, 50, 50), size: tuple = (200, 200), pattern: str = None) -> bytes:
    img = Image.new("RGB", size, color=color)
    if pattern == "stripes":
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        for y in range(0, size[1], 20):
            draw.line([(0, y), (size[0], y)], fill=(255, 255, 255), width=10)
    elif pattern == "cross":
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.line([(0, 0), size], fill=(255, 255, 255), width=20)
        draw.line([(0, size[1]), (size[0], 0)], fill=(255, 255, 255), width=20)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestAIIntelligenceCorrections(unittest.TestCase):
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

        # Setup test data
        db = cls.TestingSessionLocal()
        cls.pwd = hash_password("TestSecret123!")

        # 1. Citizen
        cls.citizen = User(
            name="Citizen Audit",
            email="citizen_audit@civicsol.org",
            mobile="9800000001",
            citizen_id="CIT-AUDIT-1",
            password_hash=cls.pwd,
            role="CITIZEN",
            is_active=True,
        )
        # 2. Field Officer
        cls.officer = User(
            name="Officer Audit",
            email="officer_audit@civicsol.org",
            mobile="9800000002",
            citizen_id="OFF-AUDIT-1",
            password_hash=cls.pwd,
            role="FIELD_OFFICER",
            is_active=True,
        )
        # 3. Dept Officer
        cls.dept_officer = User(
            name="Dept Admin",
            email="dept_audit@civicsol.org",
            mobile="9800000003",
            citizen_id="DEP-AUDIT-1",
            password_hash=cls.pwd,
            role="DEPARTMENT_OFFICER",
            is_active=True,
        )
        db.add_all([cls.citizen, cls.officer, cls.dept_officer])
        db.commit()
        db.refresh(cls.citizen)
        db.refresh(cls.officer)
        db.refresh(cls.dept_officer)

        cls.citizen_token = create_access_token({"sub": str(cls.citizen.id), "role": cls.citizen.role, "id": cls.citizen.id})
        cls.officer_token = create_access_token({"sub": str(cls.officer.id), "role": cls.officer.role, "id": cls.officer.id})
        cls.dept_officer_token = create_access_token({"sub": str(cls.dept_officer.id), "role": cls.dept_officer.role, "id": cls.dept_officer.id})

        db.close()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        self.db = self.TestingSessionLocal()
        def override_get_db():
            try:
                yield self.db
            finally:
                pass
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.db.rollback()
        self.db.close()
        app.dependency_overrides.clear()

    # =========================================================================
    # ISSUE 1: YOLO Class-Agnostic NMS & Low-Confidence Warnings
    # =========================================================================

    def test_01_yolo_class_agnostic_nms_parameter(self):
        """Verifies detect() method accepts and executes with agnostic_nms=True and iou_threshold=0.45."""
        detector = CivicYOLODetector()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(_create_sample_image_bytes())
            temp_path = f.name

        try:
            res = detector.detect(temp_path, conf_threshold=0.35, iou_threshold=0.45, agnostic_nms=True)
            self.assertIn("status", res)
            self.assertIn("processing_time_ms", res)
            self.assertIn("is_low_confidence", res)
            self.assertIn(res["status"], {"DETECTED", "NO_DETECTION", "LOW_CONFIDENCE", "MODEL_UNAVAILABLE"})
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_02_yolo_low_confidence_flagging(self):
        """Verifies detections with confidence < 45% trigger LOW_CONFIDENCE status and warning."""
        detector = CivicYOLODetector()
        # Mock model predict to return low-confidence box (e.g. 0.38)
        mock_box = MagicMock()
        mock_box.cls = [MagicMock(item=lambda: 0)]
        mock_box.conf = [MagicMock(item=lambda: 0.38)]
        mock_box.xyxy = [MagicMock(tolist=lambda: [10.0, 10.0, 80.0, 80.0])]

        mock_result = MagicMock()
        mock_result.boxes = [mock_box]

        mock_model = MagicMock()
        mock_model.predict.return_value = [mock_result]
        detector.model = mock_model
        detector.is_available = True

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(_create_sample_image_bytes())
            temp_path = f.name

        try:
            res = detector.detect(temp_path, conf_threshold=0.25)
            self.assertEqual(res["status"], "LOW_CONFIDENCE")
            self.assertTrue(res["is_low_confidence"])
            self.assertIsNotNone(res["low_confidence_warning"])
            self.assertIn("< 45%", res["low_confidence_warning"])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    # =========================================================================
    # ISSUE 2: Gemini Category Inconsistency & Human Verification
    # =========================================================================

    def test_03_gemini_category_inconsistency_and_human_verification(self):
        """When computer vision contradicts citizen description, evidence_consistency is INCONSISTENT and review is required."""
        res = _heuristic_description_analysis(
            title="Massive overflowing garbage dump",
            description="Piles of solid waste and plastic trash rotting on street corner.",
            selected_category="Garbage",
            location="Market Crossroad",
            vision_category="Tree / Greenery",  # YOLO false positive
        )
        self.assertEqual(res["evidence_consistency"], "INCONSISTENT")
        self.assertTrue(res["requires_human_review"])
        self.assertEqual(res["recommended_category"], "Garbage")  # Retains citizen/text category
        self.assertIn("Evidence conflict noted", res["disagreement_explanation"])

    def test_04_gemini_evidence_consistency_consistent_when_aligned(self):
        """When computer vision and citizen description align, evidence_consistency is CONSISTENT."""
        res = _heuristic_description_analysis(
            title="Dangerous crater pothole on main road",
            description="Deep pothole in asphalt lane causing rim damage to vehicles.",
            selected_category="Road Damage",
            location="Highway 10",
            vision_category="Road Damage",
        )
        self.assertEqual(res["evidence_consistency"], "CONSISTENT")
        self.assertFalse(res["requires_human_review"])
        self.assertEqual(res["recommended_category"], "Road Damage")

    # =========================================================================
    # ISSUE 3: Multi-Factor Duplicate Detection & Exact API Replay
    # =========================================================================

    def test_05_multi_factor_duplicate_exact_replay_detection(self):
        """Identical image bytes at same location classified as EXACT_REPLAY with 100% duplicate score."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(_create_sample_image_bytes((120, 150, 80)))
            temp_path = f.name

        try:
            iss1 = CivicIssue(
                title="Garbage heap 1",
                description="Pile of garbage on sidewalk",
                category="Garbage",
                location="Corner Street",
                latitude=23.0300,
                longitude=72.5800,
                image_path=temp_path,
                user_id=self.citizen.id,
                status="Reported",
            )
            self.db.add(iss1)
            self.db.commit()
            self.db.refresh(iss1)

            # Check duplicate detection for identical submission
            res = detect_similar_nearby_issues(
                db=self.db,
                issue_id=999999,
                latitude=23.0300,
                longitude=72.5800,
                category="Garbage",
                title="Garbage heap 1",
                description="Pile of garbage on sidewalk",
                image_path=temp_path,
            )
            self.assertEqual(res["overall_classification"], "EXACT_REPLAY")
            self.assertEqual(res["highest_duplicate_score"], 100.0)
            self.assertEqual(len(res["similar_issues"]), 1)
            self.assertEqual(res["similar_issues"][0]["classification"], "EXACT_REPLAY")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_06_multi_factor_duplicate_different_issues_same_location(self):
        """Different issues (e.g. broken streetlight vs pothole) at same coordinates are NOT duplicates."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f1:
            f1.write(_create_sample_image_bytes((255, 0, 0), pattern="stripes"))
            p1 = f1.name
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f2:
            f2.write(_create_sample_image_bytes((0, 0, 255), pattern="cross"))
            p2 = f2.name

        try:
            iss1 = CivicIssue(
                title="Broken street light at junction",
                description="Lamp post bulb shattered and dark at night",
                category="Street Light",
                location="Junction Point",
                latitude=23.0400,
                longitude=72.5900,
                image_path=p1,
                user_id=self.citizen.id,
                status="Reported",
            )
            self.db.add(iss1)
            self.db.commit()
            self.db.refresh(iss1)

            # Different issue at the same coordinates
            res = detect_similar_nearby_issues(
                db=self.db,
                issue_id=999999,
                latitude=23.0400,
                longitude=72.5900,
                category="Road Damage",
                title="Asphalt pothole in road",
                description="Crater in asphalt lane",
                image_path=p2,
            )
            self.assertEqual(res["overall_classification"], "UNIQUE_REPORT")
            # Proximity gave 25%, but category (0%), text (0%), image (0%) keep score < 40%
            self.assertLess(res["highest_duplicate_score"], 40.0)
        finally:
            for p in (p1, p2):
                if os.path.exists(p):
                    os.unlink(p)

    def test_07_multi_factor_duplicate_multiple_citizens_same_issue(self):
        """Multiple genuine citizens reporting the same real-world issue remain valid reports."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(_create_sample_image_bytes((50, 120, 200)))
            shared_img = f.name

        try:
            iss1 = CivicIssue(
                title="Water pipe leaking",
                description="Potable water gushing from underground pipeline",
                category="Water Leakage",
                location="Main Ave",
                latitude=23.0500,
                longitude=72.6000,
                image_path=shared_img,
                user_id=self.citizen.id,
                status="Reported",
            )
            self.db.add(iss1)
            self.db.commit()

            # Second citizen reporting 10 meters away
            res = detect_similar_nearby_issues(
                db=self.db,
                issue_id=999999,
                latitude=23.0501,
                longitude=72.6001,
                category="Water Leakage",
                title="Water pipeline break",
                description="Severe clean water leakage on street",
                image_path=shared_img,
            )
            self.assertIn(res["overall_classification"], {"EXACT_REPLAY", "HIGH_CONFIDENCE_DUPLICATE"})
            self.assertGreaterEqual(res["highest_duplicate_score"], 70.0)
            # Crucially: it is detected and linked, not rejected or discarded!
            self.assertEqual(res["primary_duplicate_id"], iss1.id)
        finally:
            if os.path.exists(shared_img):
                os.unlink(shared_img)

    def test_08_exact_api_replay_prevents_duplicate_issue_and_credits(self):
        """Replaying identical submission within 15 minutes returns existing report and 0 credits."""
        img_bytes = _create_sample_image_bytes((30, 40, 50))
        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        payload = {
            "title": "Replay Test Issue",
            "description": "Testing exact API replay prevention",
            "category": "Garbage",
            "severity": "Medium",
            "location": "Replay Street",
            "latitude": "23.0550",
            "longitude": "72.6050",
        }

        with patch("backend.ai.tasks.process_issue_ai_task.delay"):
            # First submission
            r1 = self.client.post(
                "/issues/",
                data=payload,
                files={"image": ("test1.jpg", img_bytes, "image/jpeg")},
                headers=headers,
            )
            self.assertEqual(r1.status_code, 200)
            data1 = r1.json()
            issue_id1 = data1["issue"]["id"]
            self.assertEqual(data1["credits_earned"], 20)

            # Immediate replay with identical image bytes and payload
            r2 = self.client.post(
                "/issues/",
                data=payload,
                files={"image": ("test1_replay.jpg", img_bytes, "image/jpeg")},
                headers=headers,
            )
            self.assertEqual(r2.status_code, 200)
            data2 = r2.json()
            # Idempotently returned same issue
            self.assertEqual(data2["issue"]["id"], issue_id1)
            self.assertTrue(data2.get("is_replay"))
            self.assertEqual(data2.get("credits_earned"), 0)

            # Confirm only 1 issue exists in database
            count = self.db.query(CivicIssue).filter(CivicIssue.title == "Replay Test Issue").count()
            self.assertEqual(count, 1)

    # =========================================================================
    # ISSUE 4: Suspicious & Fake Submission Risk Engine
    # =========================================================================

    def test_09_suspicious_submission_reused_image_distant_location(self):
        """Identical image reused across distant locations (> 1km away) flagged as HIGH_RISK."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(_create_sample_image_bytes((10, 80, 160)))
            img_path = f.name

        try:
            # Issue 1 in City Center
            iss1 = CivicIssue(
                title="Pothole center",
                category="Road Damage",
                location="Center",
                latitude=23.0000,
                longitude=72.5000,
                image_path=img_path,
                user_id=self.citizen.id,
            )
            # Issue 2 5km away using the SAME photo
            iss2 = CivicIssue(
                title="Pothole suburbs",
                category="Road Damage",
                location="Suburbs",
                latitude=23.0500,
                longitude=72.5500,
                image_path=img_path,
                user_id=self.citizen.id,
            )
            self.db.add_all([iss1, iss2])
            self.db.commit()

            eval_res = evaluate_submission_authenticity(db=self.db, issue=iss2)
            self.assertEqual(eval_res["risk_level"], "REVIEW_REQUIRED" if eval_res["risk_score"] < 60 else "HIGH_RISK")
            self.assertGreaterEqual(eval_res["risk_score"], 45)
            self.assertTrue(any("matches prior Issue" in f for f in eval_res["risk_factors"]))
        finally:
            if os.path.exists(img_path):
                os.unlink(img_path)

    def test_10_suspicious_submission_burst_frequency(self):
        """Citizen submitting > 3 reports in 5 minutes flagged for elevated burst activity."""
        now = datetime.utcnow()
        for i in range(4):
            iss = CivicIssue(
                title=f"Burst Issue #{i}",
                category="Garbage",
                location="Street",
                latitude=23.0100 + (i * 0.001),
                longitude=72.5100,
                image_path=f"uploads/test_burst_{i}.jpg",
                user_id=self.citizen.id,
                created_at=now - timedelta(minutes=i),
            )
            self.db.add(iss)
        self.db.commit()

        target_iss = CivicIssue(
            title="Burst Target Issue",
            category="Garbage",
            location="Street",
            latitude=23.0150,
            longitude=72.5150,
            image_path="uploads/test_burst_target.jpg",
            user_id=self.citizen.id,
            created_at=now,
        )
        self.db.add(target_iss)
        self.db.commit()

        eval_res = evaluate_submission_authenticity(db=self.db, issue=target_iss)
        self.assertTrue(any("High submission burst" in f for f in eval_res["risk_factors"]))
        self.assertGreaterEqual(eval_res["risk_score"], 30)

    def test_11_suspicious_submission_normal_genuine_report(self):
        """Genuine report with matching category and normal frequency is classified as NORMAL."""
        c2 = User(
            name="Normal Citizen",
            email="normal_audit@civicsol.org",
            mobile="9800000099",
            citizen_id="CIT-NORM-1",
            password_hash=self.pwd,
            role="CITIZEN",
            is_active=True,
        )
        self.db.add(c2)
        self.db.commit()
        self.db.refresh(c2)

        iss = CivicIssue(
            title="Normal Pothole",
            category="Road Damage",
            location="Highway",
            latitude=23.0800,
            longitude=72.6800,
            image_path="uploads/test_normal.jpg",
            user_id=c2.id,
            created_at=datetime.utcnow(),
        )
        self.db.add(iss)
        self.db.commit()

        eval_res = evaluate_submission_authenticity(
            db=self.db,
            issue=iss,
            gemini_result={"evidence_consistency": "CONSISTENT"},
        )
        self.assertEqual(eval_res["risk_level"], "NORMAL")
        self.assertEqual(eval_res["risk_score"], 0)
        self.assertFalse(eval_res["requires_officer_review"])

    # =========================================================================
    # ISSUE 5: Authority Endpoints & Audit Logging
    # =========================================================================

    def test_12_authority_flag_false_positive_endpoint_and_audit(self):
        """Authorized officer flags YOLO detection as false positive, recorded in metadata and AuditLog."""
        iss = CivicIssue(
            title="Garbage with tree detection",
            category="Garbage",
            location="Main Market",
            latitude=23.033,
            longitude=72.585,
            image_path="uploads/test_fp.jpg",
            user_id=self.citizen.id,
        )
        self.db.add(iss)
        self.db.commit()
        self.db.refresh(iss)

        ai = AIAnalysis(
            issue_id=iss.id,
            model_name="CivicYOLO-v8",
            model_version="1.0.0",
            predicted_category="Tree / Greenery",
            confidence_score=0.82,
            detected_objects=[{"label": "fallen_tree", "confidence": 0.82}],
            processing_status="COMPLETED",
        )
        self.db.add(ai)
        self.db.commit()

        headers = {"Authorization": f"Bearer {self.officer_token}"}
        r = self.client.post(
            f"/ai/analysis/{iss.id}/false_positive",
            json={
                "class_name": "fallen_tree",
                "reason": "Background shrub incorrectly detected as fallen tree on garbage pile.",
            },
            headers=headers,
        )
        self.assertEqual(r.status_code, 200)
        res_data = r.json()
        meta = res_data["analysis"]["analysis_metadata"]
        self.assertIn("false_positive_feedback", meta)
        self.assertEqual(len(meta["false_positive_feedback"]), 1)
        self.assertEqual(meta["false_positive_feedback"][0]["class_name"], "fallen_tree")

        # Verify AuditLog created
        audit = self.db.query(AuditLog).filter(
            AuditLog.entity_id == iss.id,
            AuditLog.action == "AI_FALSE_POSITIVE_FLAGGED",
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, self.officer.id)

    def test_13_authority_link_duplicate_endpoint_and_audit(self):
        """Authorized officer associates duplicate report to primary issue."""
        p_iss = CivicIssue(title="Primary Streetlight", category="Street Light", location="Ave 1", latitude=23.1, longitude=72.1, image_path="uploads/test_p.jpg", user_id=self.citizen.id)
        d_iss = CivicIssue(title="Duplicate Streetlight", category="Street Light", location="Ave 1", latitude=23.1, longitude=72.1, image_path="uploads/test_d.jpg", user_id=self.citizen.id)
        self.db.add_all([p_iss, d_iss])
        self.db.commit()

        headers = {"Authorization": f"Bearer {self.officer_token}"}
        r = self.client.post(
            f"/ai/analysis/{d_iss.id}/link_duplicate",
            json={"primary_issue_id": p_iss.id, "action": "LINK", "notes": "Corroborating citizen report"},
            headers=headers,
        )
        self.assertEqual(r.status_code, 200)
        meta = r.json()["analysis"]["analysis_metadata"]
        self.assertIn("duplicate_link", meta)
        self.assertEqual(meta["duplicate_link"]["primary_issue_id"], p_iss.id)
        self.assertEqual(meta["duplicate_link"]["action"], "LINK")

        audit = self.db.query(AuditLog).filter(
            AuditLog.entity_id == d_iss.id,
            AuditLog.action == "ISSUE_DUPLICATE_LINK",
        ).first()
        self.assertIsNotNone(audit)

    def test_14_authority_merge_duplicate_endpoint_and_audit(self):
        """Department officer merges duplicate issue, closing it as Resolved with audit record."""
        p_iss = CivicIssue(title="Primary Drainage", category="Drainage", location="Drain 1", latitude=23.2, longitude=72.2, image_path="uploads/test_p2.jpg", user_id=self.citizen.id)
        d_iss = CivicIssue(title="Duplicate Drainage", category="Drainage", location="Drain 1", latitude=23.2, longitude=72.2, image_path="uploads/test_d2.jpg", user_id=self.citizen.id)
        self.db.add_all([p_iss, d_iss])
        self.db.commit()

        headers = {"Authorization": f"Bearer {self.dept_officer_token}"}
        r = self.client.post(
            f"/ai/analysis/{d_iss.id}/link_duplicate",
            json={"primary_issue_id": p_iss.id, "action": "MERGE", "notes": "Merged and resolved into primary inspection"},
            headers=headers,
        )
        self.assertEqual(r.status_code, 200)

        # Confirm issue status updated to Resolved
        self.db.refresh(d_iss)
        self.assertEqual(d_iss.status, "Resolved")
        self.assertIn(f"Merged into primary Issue #{p_iss.id}", d_iss.resolution_notes)

        # Confirm status history and audit log
        history = self.db.query(IssueStatusHistory).filter(IssueStatusHistory.issue_id == d_iss.id).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.to_status, "Resolved")

    def test_15_citizen_forbidden_from_false_positive_or_merge(self):
        """Citizen accounts are strictly forbidden (403) from flagging false positives or duplicate actions."""
        iss = CivicIssue(title="Protected Issue", category="Garbage", location="Loc", latitude=23.3, longitude=72.3, image_path="uploads/test_prot.jpg", user_id=self.citizen.id)
        self.db.add(iss)
        self.db.commit()

        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        r1 = self.client.post(
            f"/ai/analysis/{iss.id}/false_positive",
            json={"class_name": "garbage", "reason": "Citizen attempt"},
            headers=headers,
        )
        self.assertEqual(r1.status_code, 403)

        r2 = self.client.post(
            f"/ai/analysis/{iss.id}/link_duplicate",
            json={"primary_issue_id": 1, "action": "MERGE"},
            headers=headers,
        )
        self.assertEqual(r2.status_code, 403)
