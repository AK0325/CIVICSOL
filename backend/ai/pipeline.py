"""
CIVICSOL - End-to-End AI Civic Issue Analysis Pipeline
Orchestrates:
1. Image validation & YOLO object detection
2. Gemini LLM description analysis (with deterministic fallback)
3. Duplicate & nearby similar issue detection
4. Explainable severity and priority scoring
5. PostgreSQL-backed department recommendation
6. Historical AIAnalysis persistence without altering official issue state
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.core.logging import logger
from backend.models import AIAnalysis, CivicIssue
from ml.yolo_detector import ImageValidationError, yolo_detector

from .department_recommender import recommend_department
from .duplicate_detector import detect_similar_nearby_issues, find_similar_nearby_issues
from .gemini_service import analyze_description_with_gemini
from .priority_engine import compute_severity_and_priority
from .suspicious_detector import evaluate_submission_authenticity


BASE_DIR = Path(__file__).resolve().parents[2]


def run_issue_ai_analysis(
    db: Session,
    issue: CivicIssue,
    detector=None,
    force_reanalyze: bool = False,
    existing_analysis_id: Optional[int] = None,
) -> AIAnalysis:
    """
    Executes the full AI analysis pipeline for a given CivicIssue and saves a new
    AIAnalysis record in the database (or updates an existing PENDING record).
    Preserves all previous AIAnalysis records for historical auditability and never
    overwrites official issue status/assignment.
    """
    active_detector = detector or yolo_detector

    analysis = None
    if existing_analysis_id:
        analysis = db.query(AIAnalysis).filter(AIAnalysis.id == existing_analysis_id).first()
        if analysis:
            analysis.processing_status = "PROCESSING"
            db.commit()
            db.refresh(analysis)

    # 1. Create initial PROCESSING record if not reusing an existing record
    if not analysis:
        analysis = AIAnalysis(
            issue_id=issue.id,
            model_name=active_detector.model_name,
            model_version=active_detector.model_version,
            processing_status="PROCESSING",
            review_status="PENDING",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

    try:
        # Resolve physical image path safely
        rel_img_path = (issue.image_path or "").lstrip("/")
        full_img_path = (BASE_DIR / rel_img_path).resolve()

        # 2. Run Computer Vision / YOLO Detection
        try:
            if hasattr(active_detector, "analyze_image"):
                vision_res = active_detector.analyze_image(full_img_path)
            else:
                vision_res = active_detector.detect(full_img_path)
        except ImageValidationError as img_err:
            analysis.processing_status = "FAILED"
            analysis.explanation = f"Image validation failed: {img_err}"
            analysis.analysis_metadata = {"error": str(img_err), "stage": "image_validation"}
            db.commit()
            db.refresh(analysis)
            return analysis

        vision_status = vision_res.get("processing_status") or vision_res.get("status", "NO_DETECTION")
        detected_objects: List[Dict[str, Any]] = vision_res.get("detected_objects") or []
        vision_category: Optional[str] = vision_res.get("predicted_category")
        vision_confidence: Optional[float] = vision_res.get("confidence_score")
        annotated_image_path: Optional[str] = vision_res.get("annotated_image_path")

        # Validate confidence score if present (never invent confidence scores)
        if vision_confidence is not None:
            try:
                vision_confidence = float(vision_confidence)
                if not (0.0 <= vision_confidence <= 1.0):
                    vision_confidence = None
            except (TypeError, ValueError):
                vision_confidence = None

        # 3. Multi-Factor Duplicate & Proximity Detection
        dup_res = detect_similar_nearby_issues(
            db=db,
            issue_id=issue.id,
            latitude=issue.latitude,
            longitude=issue.longitude,
            category=issue.category,
            predicted_category=vision_category or issue.category,
            title=issue.title,
            description=issue.description,
            image_path=issue.image_path,
            created_at=issue.created_at,
        )
        similar_issues = dup_res.get("similar_issues", [])

        # 4. Run Gemini Description Analysis (with deterministic fallback)
        llm_res = analyze_description_with_gemini(
            title=issue.title,
            description=issue.description,
            selected_category=issue.category,
            location=issue.location,
            vision_category=vision_category,
            vision_detections=detected_objects,
            duplicate_assessment=dup_res,
        )

        predicted_category = (
            vision_category
            or llm_res.get("recommended_category")
            or issue.category
            or "Public Infrastructure"
        )

        # 5. Suspicious & Manipulated Submission Risk Evaluation
        suspicious_res = evaluate_submission_authenticity(
            db=db,
            issue=issue,
            yolo_result=vision_res,
            gemini_result=llm_res,
            duplicate_result=dup_res,
        )
        llm_res["risk_level"] = suspicious_res.get("risk_level", "NORMAL")
        llm_res["duplicate_assessment"] = dup_res.get("overall_classification", "UNIQUE_REPORT")

        # 6. Compute Explainable Severity & Priority Recommendation
        prio_res = compute_severity_and_priority(
            predicted_category=predicted_category,
            citizen_category=issue.category,
            citizen_severity=issue.severity,
            description=issue.description,
            location=issue.location,
            detected_objects=detected_objects,
            llm_suggested_severity=llm_res.get("suggested_severity"),
            report_count=issue.report_count or 1,
            nearby_similar_count=len(similar_issues),
            created_at=issue.created_at,
        )

        # 7. Recommend Municipal Department from PostgreSQL
        dept_res = recommend_department(
            db=db,
            predicted_category=predicted_category,
            citizen_category=issue.category,
            description=issue.description,
            llm_dept_code=llm_res.get("suggested_department_code"),
        )

        # 8. Compose unified explanation
        vision_note = (
            f"YOLO ({vision_res.get('model_name')} v{vision_res.get('model_version')}): "
            f"Detected {len(detected_objects)} object(s) [{vision_category}, confidence {round(vision_confidence * 100, 1)}%]."
            if detected_objects and vision_confidence is not None
            else (
                f"YOLO ({vision_res.get('model_name')} v{vision_res.get('model_version')}): "
                f"{vision_res.get('unavailable_reason') or 'No objects detected above confidence threshold.'}"
            )
        )

        combined_explanation = (
            f"{llm_res.get('explanation', '')} "
            f"{prio_res.get('explanation', '')} "
            f"{dept_res.get('rationale', '')} "
            f"[{vision_note}]"
        ).strip()

        final_status = "COMPLETED" if detected_objects else "NO_DETECTION"
        if vision_status in {"FAILED", "INVALID_IMAGE", "PROCESSING_FAILED"}:
            final_status = "FAILED"
        elif vision_status == "MODEL_UNAVAILABLE":
            final_status = "NO_DETECTION"
        elif vision_status in {"COMPLETED", "DETECTED", "DETECTIONS_FOUND", "LOW_CONFIDENCE"}:
            final_status = "COMPLETED"

        base_model_name = str(vision_res.get("model_name") or active_detector.model_name)
        if llm_res.get("llm_used"):
            combined_model = f"{base_model_name} + {llm_res.get('llm_model')}"
        else:
            combined_model = f"{base_model_name} + FallbackRules"

        analysis.model_name = combined_model
        analysis.model_version = str(vision_res.get("model_version") or active_detector.model_version)
        analysis.predicted_category = predicted_category
        analysis.confidence_score = vision_confidence
        analysis.detected_objects = detected_objects
        analysis.suggested_severity = prio_res["suggested_severity"]
        analysis.suggested_priority = prio_res["suggested_priority"]
        analysis.suggested_department_id = dept_res["department_id"]
        analysis.explanation = combined_explanation
        analysis.annotated_image_path = annotated_image_path
        analysis.processing_status = final_status
        analysis.analysis_metadata = {
            "vision_status": vision_status,
            "model_available": vision_res.get("model_available", False),
            "unavailable_reason": vision_res.get("unavailable_reason"),
            "image_metadata": vision_res.get("image_metadata"),
            "is_low_confidence": vision_res.get("is_low_confidence", False),
            "low_confidence_warning": vision_res.get("low_confidence_warning"),
            "processing_time_ms": vision_res.get("processing_time_ms"),
            "llm_used": llm_res.get("llm_used", False),
            "llm_model": llm_res.get("llm_model"),
            "llm_fallback_reason": llm_res.get("fallback_reason"),
            "extracted_problem": llm_res.get("extracted_problem"),
            "public_impact": llm_res.get("public_impact"),
            "safety_concerns": llm_res.get("safety_concerns"),
            "disagreement_explanation": llm_res.get("disagreement_explanation"),
            "evidence_consistency": llm_res.get("evidence_consistency", "CONSISTENT"),
            "requires_human_review": llm_res.get("requires_human_review", False),
            "priority_scoring": prio_res,
            "department_recommendation": dept_res,
            "similar_nearby_reports": similar_issues,
            "duplicate_assessment": dup_res,
            "suspicious_assessment": suspicious_res,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Populate non-authoritative AI summary fields on issue without altering official status/priority/department
        issue.ai_label = predicted_category
        issue.ai_confidence = vision_confidence
        issue.priority_score = float(prio_res["composite_score"])

        db.commit()
        db.refresh(analysis)
        return analysis

    except Exception as exc:
        logger.error(f"AI analysis pipeline failed for issue #{issue.id}: {type(exc).__name__}: {exc}")
        db.rollback()
        analysis.processing_status = "FAILED"
        analysis.explanation = f"AI analysis encountered an unexpected error: {exc}"
        analysis.analysis_metadata = {"error": str(exc)}
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

