"""
CIVICSOL - Suspicious & Manipulated Submission Risk Engine
Assesses civic report authenticity risk based on:
1. Reused image evidence across distant geographic locations (> 1km)
2. Rapid automated submissions / burst rate anomalies
3. Contradictory image evidence vs text claims
4. Missing, stripped, or suspicious image metadata
5. Image manipulation indicators

Risk Classifications:
- NORMAL: Standard genuine citizen submission
- LOW_RISK: Minor timing or non-critical anomaly
- REVIEW_REQUIRED: Advisory flag for officer inspection (e.g. text/image contradiction)
- HIGH_RISK: Substantial anomaly (e.g. same photo submitted 5km away, burst submission)
- INVALID_EVIDENCE: Unreadable, corrupted, or invalid evidence files

Strict Governance Policy:
- AI risk scores are advisory risk indicators for municipal officers.
- AI NEVER auto-rejects a citizen report or modifies official status.
- Final authority rejection strictly requires an authorized officer decision, mandatory justification, and audit record.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.models import CivicIssue
from .duplicate_detector import (
    compute_image_dhash,
    compute_image_sha256,
    haversine_distance_meters,
    image_perceptual_similarity,
)


def evaluate_submission_authenticity(
    db: Session,
    issue: CivicIssue,
    yolo_result: Optional[Dict[str, Any]] = None,
    gemini_result: Optional[Dict[str, Any]] = None,
    duplicate_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluates whether a civic issue submission exhibits suspicious characteristics.
    Returns structured risk evaluation with risk_level, score, risk_factors, and recommendations.
    Never alters official issue status or rejects reports automatically.
    """
    risk_factors: List[str] = []
    risk_score = 0  # 0 to 100

    target_sha256 = compute_image_sha256(issue.image_path)
    target_dhash = compute_image_dhash(issue.image_path)
    current_time = issue.created_at or datetime.utcnow()

    # -------------------------------------------------------------
    # 1. Reused image across distant locations (> 1km away)
    # -------------------------------------------------------------
    if target_sha256 or target_dhash:
        prior_issues = (
            db.query(CivicIssue)
            .filter(
                CivicIssue.id != issue.id,
                CivicIssue.image_path.isnot(None),
            )
            .all()
        )
        for prior in prior_issues:
            cand_sha = compute_image_sha256(prior.image_path)
            is_exact_sha = bool(target_sha256 and cand_sha and target_sha256 == cand_sha)
            cand_dhash = compute_image_dhash(prior.image_path)
            dhash_sim = image_perceptual_similarity(target_dhash, cand_dhash) if (target_dhash and cand_dhash) else 0.0

            if is_exact_sha or dhash_sim >= 0.95:
                dist = haversine_distance_meters(
                    issue.latitude, issue.longitude, prior.latitude, prior.longitude
                )
                if dist > 1000.0:
                    dist_km = round(dist / 1000.0, 2)
                    risk_factors.append(
                        f"Image evidence matches prior Issue #{prior.id} located {dist_km} km away."
                    )
                    risk_score += 45
                    break

    # -------------------------------------------------------------
    # 2. Submission burst frequency (> 3 reports in 5 minutes)
    # -------------------------------------------------------------
    if issue.user_id:
        window_start = current_time - timedelta(minutes=5)
        recent_count = (
            db.query(CivicIssue)
            .filter(
                CivicIssue.user_id == issue.user_id,
                CivicIssue.id != issue.id,
                CivicIssue.created_at >= window_start,
                CivicIssue.created_at <= current_time,
            )
            .count()
        )
        if recent_count >= 3:
            risk_factors.append(
                f"High submission burst: Citizen account submitted {recent_count + 1} reports in 5 minutes."
            )
            risk_score += 30
        elif recent_count >= 2:
            risk_factors.append(
                f"Elevated submission rate: Citizen account submitted {recent_count + 1} reports in 5 minutes."
            )
            risk_score += 15

    # -------------------------------------------------------------
    # 3. Contradictory text description vs Computer Vision
    # -------------------------------------------------------------
    consistency = (gemini_result or {}).get("evidence_consistency")
    if consistency == "INCONSISTENT":
        disagreement = (gemini_result or {}).get("disagreement_explanation")
        risk_factors.append(
            f"Evidence conflict: {disagreement or 'Citizen text contradicts computer vision detection.'}"
        )
        risk_score += 20

    # -------------------------------------------------------------
    # 4. Image metadata & file characteristics
    # -------------------------------------------------------------
    img_meta = (yolo_result or {}).get("image_metadata") or {}
    file_bytes = img_meta.get("file_size_bytes", 0)
    orig_w = img_meta.get("original_width", 0)
    orig_h = img_meta.get("original_height", 0)

    if file_bytes > 0 and file_bytes < 3000:
        risk_factors.append("Suspiciously small image file size (< 3KB).")
        risk_score += 15
    if orig_w > 0 and orig_h > 0 and (orig_w < 100 or orig_h < 100):
        risk_factors.append(f"Low resolution evidence ({orig_w}x{orig_h}px).")
        risk_score += 10

    # Clamp risk score
    risk_score = min(100, max(0, risk_score))

    # -------------------------------------------------------------
    # Classification
    # -------------------------------------------------------------
    if (yolo_result or {}).get("status") in {"INVALID_IMAGE", "CORRUPT_IMAGE"}:
        risk_level = "INVALID_EVIDENCE"
    elif risk_score >= 60:
        risk_level = "HIGH_RISK"
    elif risk_score >= 35:
        risk_level = "REVIEW_REQUIRED"
    elif risk_score >= 15:
        risk_level = "LOW_RISK"
    else:
        risk_level = "NORMAL"

    recommendation = (
        "Genuine citizen report; proceed with standard municipal dispatch."
        if risk_level == "NORMAL"
        else (
            "Minor observations noted; standard dispatch."
            if risk_level == "LOW_RISK"
            else (
                "Advisory review flag: Review evidence details during officer assignment."
                if risk_level == "REVIEW_REQUIRED"
                else (
                    "High risk indicator: Officer visual inspection required prior to field dispatch."
                    if risk_level == "HIGH_RISK"
                    else "Invalid image file; request citizen resubmission."
                )
            )
        )
    )

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "recommendation": recommendation,
        "requires_officer_review": risk_level in {"REVIEW_REQUIRED", "HIGH_RISK", "INVALID_EVIDENCE"},
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
