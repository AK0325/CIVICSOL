"""
CIVICSOL - Explainable AI Severity and Priority Recommendation Engine

Scoring Methodology (0 - 100 Composite Risk Scale):
1. Category Base Hazard Score (15 - 35 pts):
   - Drainage / Open Manhole: 32 pts (immediate fall/flooding/sanitation hazard)
   - Potholes / Road Damage: 28 pts (vehicular accident risk)
   - Water Leakage: 25 pts (structural erosion & water loss)
   - Broken Streetlights: 22 pts (nighttime public safety & pedestrian risk)
   - Damaged Public Infrastructure: 22 pts
   - Garbage Accumulation: 18 pts (public health & vector risk)
2. Public Safety & Hazard Evidence (0 - 30 pts):
   - Evaluates citizen description, visual bounding box coverage, and LLM risk insights
     for life-safety keywords (e.g., "accident", "open manhole", "live wire", "hospital", "school",
     "deep crater", "flooding", "injury", "blocked highway").
3. Location Sensitivity (0 - 15 pts):
   - High-traffic roads, intersections, schools, hospitals, bridges, and transit hubs.
4. Community Impact & Report Volume (0 - 12 pts):
   - Number of corroborating reports (`report_count`) and nearby unresolved similar issues.
5. Report Age / SLA Pressure (0 - 10 pts):
   - Escalates unresolved issues that have aged without intervention.

Thresholds:
- Composite Score >= 75 -> Severity: CRITICAL | Priority: URGENT
- Composite Score >= 52 -> Severity: HIGH     | Priority: HIGH
- Composite Score >= 30 -> Severity: MEDIUM   | Priority: NORMAL
- Composite Score <  30 -> Severity: LOW      | Priority: LOW

Important Invariant:
- Model detection confidence (e.g., 92% certainty of class label) is NEVER confused with
  issue severity. A high-confidence detection of a small litter pile remains LOW/MEDIUM severity.
- Recommendations never automatically alter official issue status or reject complaints.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


CATEGORY_BASE_SCORES: Dict[str, int] = {
    "drainage": 32,
    "drainage problem": 32,
    "drainage_problem": 32,
    "road damage": 28,
    "pothole": 28,
    "potholes": 28,
    "water leakage": 25,
    "water_leakage": 25,
    "street light": 22,
    "streetlights": 22,
    "broken_streetlight": 22,
    "public infrastructure": 22,
    "damaged_infrastructure": 22,
    "traffic": 26,
    "garbage": 18,
    "tree / greenery": 16,
}

CRITICAL_SAFETY_KEYWORDS = [
    "accident",
    "injured",
    "injury",
    "open manhole",
    "uncovered drain",
    "live wire",
    "electrocution",
    "sparking",
    "collapsed",
    "sinkhole",
    "deep crater",
    "severe flooding",
    "sewage overflow",
    "child",
    "children",
    "elderly",
    "ambulance",
    "emergency",
    "fatal",
]

HIGH_SAFETY_KEYWORDS = [
    "dangerous",
    "hazard",
    "blocked",
    "traffic jam",
    "burst",
    "gushing",
    "overflowing",
    "dark",
    "no light",
    "broken glass",
    "foul smell",
    "disease",
    "mosquito",
    "slippery",
    "sharp",
]

SENSITIVE_LOCATIONS = [
    "hospital",
    "clinic",
    "school",
    "college",
    "highway",
    "main road",
    "junction",
    "crossroad",
    "bridge",
    "flyover",
    "station",
    "bus stand",
    "market",
]


def _normalize_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_severity_and_priority(
    predicted_category: Optional[str] = None,
    citizen_category: Optional[str] = None,
    citizen_severity: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    location_text: Optional[str] = None,
    detected_objects: Optional[List[Dict[str, Any]]] = None,
    confidence_score: Optional[float] = None,
    llm_suggested_severity: Optional[str] = None,
    report_count: int = 1,
    duplicate_count: int = 0,
    nearby_similar_count: int = 0,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
    created_at: Optional[datetime] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Computes an explainable severity (CRITICAL, HIGH, MEDIUM, LOW)
    and priority (URGENT, HIGH, NORMAL, LOW) recommendation.
    """
    effective_cat = (predicted_category or citizen_category or "Public Infrastructure").strip()
    cat_key = effective_cat.lower()

    # 1. Category base score (15 - 35)
    base_score = CATEGORY_BASE_SCORES.get(cat_key, 20)
    for k, val in CATEGORY_BASE_SCORES.items():
        if k in cat_key:
            base_score = max(base_score, val)

    # 2. Public safety & severity evidence (0 - 30)
    effective_location = location_text or location or ""
    text_blob = f"{description or ''} {effective_location}".lower()
    safety_score = 0
    matched_safety_terms: List[str] = []

    for kw in CRITICAL_SAFETY_KEYWORDS:
        if kw in text_blob:
            safety_score += 14
            matched_safety_terms.append(kw)

    for kw in HIGH_SAFETY_KEYWORDS:
        if kw in text_blob:
            safety_score += 7
            matched_safety_terms.append(kw)

    # Consider citizen-reported severity and LLM severity assessment as evidence
    cit_sev = (citizen_severity or "").strip().upper()
    if cit_sev == "CRITICAL":
        safety_score += 10
    elif cit_sev == "HIGH":
        safety_score += 6

    llm_sev = (llm_suggested_severity or "").strip().upper()
    if llm_sev == "CRITICAL":
        safety_score += 12
    elif llm_sev == "HIGH":
        safety_score += 7

    # Consider number of distinct objects detected in scene (extent of damage, not confidence)
    obj_count = len(detected_objects) if detected_objects else 0
    if obj_count >= 3:
        safety_score += 8
    elif obj_count == 2:
        safety_score += 4

    safety_score = min(30, safety_score)

    # 3. Location sensitivity (0 - 15)
    location_score = 0
    matched_locations: List[str] = []
    loc_blob = (location or "").lower()
    for loc_kw in SENSITIVE_LOCATIONS:
        if loc_kw in loc_blob or loc_kw in text_blob:
            location_score += 8
            matched_locations.append(loc_kw)
    location_score = min(15, location_score)

    # 4. Community impact: report count & nearby cluster density (0 - 12)
    effective_dups = max(duplicate_count or 0, nearby_similar_count or 0)
    extra_reports = max(0, (report_count or 1) - 1) + effective_dups
    volume_score = min(12, extra_reports * 4)

    # 5. Report age / unresolved duration (0 - 10)
    age_score = 0
    age_hours = 0.0
    if created_at:
        now = datetime.now(timezone.utc)
        c_utc = _normalize_utc(created_at) or now
        age_hours = max(0.0, (now - c_utc).total_seconds() / 3600.0)
        if age_hours >= 72:
            age_score = 10
        elif age_hours >= 24:
            age_score = 5
        elif age_hours >= 12:
            age_score = 2

    composite_score = min(100, base_score + safety_score + location_score + volume_score + age_score)

    if composite_score >= 75:
        suggested_severity = "CRITICAL"
        suggested_priority = "URGENT"
    elif composite_score >= 52:
        suggested_severity = "HIGH"
        suggested_priority = "HIGH"
    elif composite_score >= 30:
        suggested_severity = "MEDIUM"
        suggested_priority = "NORMAL"
    else:
        suggested_severity = "LOW"
        suggested_priority = "LOW"

    # Build human-readable explanation
    reasons: List[str] = [f"Category '{effective_cat}' base risk ({base_score} pts)"]
    if matched_safety_terms:
        reasons.append(f"safety indicators ({', '.join(matched_safety_terms[:3])}: +{safety_score} pts)")
    elif safety_score > 0:
        reasons.append(f"severity evidence (+{safety_score} pts)")

    if matched_locations:
        reasons.append(f"sensitive location ({', '.join(matched_locations[:2])}: +{location_score} pts)")

    if volume_score > 0:
        reasons.append(f"corroborating/nearby reports (+{volume_score} pts)")

    if age_score > 0:
        reasons.append(f"unresolved age {round(age_hours, 1)}h (+{age_score} pts)")

    explanation = (
        f"Recommended Severity: {suggested_severity} | Priority: {suggested_priority} "
        f"(Composite Risk Score: {composite_score}/100). "
        f"Factors: {'; '.join(reasons)}."
    )

    return {
        "suggested_severity": suggested_severity,
        "suggested_priority": suggested_priority,
        "composite_score": composite_score,
        "scoring_breakdown": {
            "category_base": base_score,
            "safety_risk_evidence": safety_score,
            "location_sensitivity": location_score,
            "community_report_volume": volume_score,
            "report_age_factor": age_score,
        },
        "matched_safety_keywords": matched_safety_terms,
        "matched_sensitive_locations": matched_locations,
        "factors": reasons,
        "explanation": explanation,
    }

