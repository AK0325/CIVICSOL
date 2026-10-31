"""
CIVICSOL - Gemini-Powered Civic Description & Multimodal Analysis Service
Integrates Google Gemini only when a valid API key is configured.

Capabilities:
1. Understands citizen descriptions and extracts civic problem details.
2. Recommends category, severity, and municipal department code.
3. Explains potential public impact for authorities.
4. Enforces visual-grounding rule: never overrides actual YOLO image detections
   without explicitly documenting the disagreement.
5. Gracefully falls back when Gemini API is unconfigured, unreachable, or times out.
6. Never exposes API keys in logs or responses.
"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.core.logging import logger


VALID_CATEGORIES = {
    "Road Damage",
    "Garbage",
    "Street Light",
    "Water Leakage",
    "Drainage",
    "Public Infrastructure",
    "Tree / Greenery",
    "Traffic",
}

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}

VALID_DEPT_CODES = {
    "ROADS_BRIDGES",
    "SOLID_WASTE",
    "STREET_LIGHTING",
    "WATER_SEWERAGE",
    "DRAINAGE",
    "PUBLIC_INFRA",
}

KEYWORD_CATEGORY_MAP = [
    (["pothole", "crater", "road damage", "asphalt", "broken road", "tar"], "Road Damage", "ROADS_BRIDGES"),
    (["garbage", "trash", "waste", "dump", "rubbish", "litter", "filth"], "Garbage", "SOLID_WASTE"),
    (["streetlight", "street light", "lamp", "pole light", "dark road", "bulb"], "Street Light", "STREET_LIGHTING"),
    (["water leak", "leakage", "burst pipe", "pipeline", "water supply"], "Water Leakage", "WATER_SEWERAGE"),
    (["drain", "drainage", "manhole", "sewer", "gutter", "waterlogging", "clogged"], "Drainage", "DRAINAGE"),
    (["footpath", "railing", "bench", "park", "bridge", "infrastructure", "wall"], "Public Infrastructure", "PUBLIC_INFRA"),
]


def validate_and_sanitize_gemini_payload(
    raw: Dict[str, Any],
    yolo_result: Optional[Dict[str, Any]] = None,
    selected_category: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates and sanitizes Gemini LLM response against strict civic taxonomy.
    Preserves citizen evidence and flags discrepancies between vision and text
    without silently overriding with computer vision false positives.
    """
    if not isinstance(raw, dict):
        raw = {}

    yolo_cat = (yolo_result or {}).get("predicted_category")
    raw_cat = str(raw.get("category") or raw.get("recommended_category") or "").strip()

    category = raw_cat if raw_cat in VALID_CATEGORIES else (selected_category or yolo_cat or "Public Infrastructure")
    disagrees = bool(raw.get("disagrees_with_visual", False))
    evidence_consistency = "CONSISTENT"
    requires_human_review = False

    if yolo_cat:
        if category.lower() != yolo_cat.lower() or (raw_cat and raw_cat.lower() != yolo_cat.lower()):
            disagrees = True
            evidence_consistency = "INCONSISTENT"
            requires_human_review = True
    else:
        evidence_consistency = "UNCERTAIN"

    raw_sev = str(raw.get("suggested_severity") or "").strip().upper()
    sev = raw_sev if raw_sev in VALID_SEVERITIES else "MEDIUM"

    valid_priorities = {"URGENT", "HIGH", "NORMAL", "LOW"}
    raw_prio = str(raw.get("suggested_priority") or "").strip().upper()
    prio = raw_prio if raw_prio in valid_priorities else "NORMAL"

    dept_map = {
        "Road Damage": "ROADS_BRIDGES",
        "Garbage": "SOLID_WASTE",
        "Street Light": "STREET_LIGHTING",
        "Water Leakage": "WATER_SEWERAGE",
        "Drainage": "DRAINAGE",
        "Public Infrastructure": "PUBLIC_INFRA",
        "Tree / Greenery": "PUBLIC_INFRA",
        "Traffic": "ROADS_BRIDGES",
    }
    raw_dept = str(raw.get("suggested_department_code") or "").strip().upper()
    dept_code = raw_dept if raw_dept in VALID_DEPT_CODES else dept_map.get(category, "PUBLIC_INFRA")

    return {
        "category": category,
        "recommended_category": category,
        "suggested_severity": sev,
        "suggested_priority": prio,
        "suggested_department_code": dept_code,
        "disagrees_with_visual": disagrees,
        "evidence_consistency": evidence_consistency,
        "requires_human_review": requires_human_review,
        "explanation": str(raw.get("explanation") or "Structured analysis generated."),
    }


def _heuristic_description_analysis(
    title: Optional[str],
    description: Optional[str],
    selected_category: Optional[str],
    location: Optional[str],
    vision_category: Optional[str] = None,
    vision_detections: Optional[List[Dict[str, Any]]] = None,
    fallback_reason: str = "Gemini API not configured or unavailable",
    duplicate_assessment: Optional[Dict[str, Any]] = None,
    suspicious_indicators: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministic rule-based analysis when Gemini LLM is unavailable.
    Never invents model confidence scores.
    """
    combined_text = f"{title or ''} {description or ''}".strip()
    text_lower = combined_text.lower()

    inferred_category = None
    inferred_dept = None
    for keywords, cat, dept_code in KEYWORD_CATEGORY_MAP:
        if any(kw in text_lower for kw in keywords):
            inferred_category = cat
            inferred_dept = dept_code
            break

    # Determine recommended category without silently overriding citizen evidence
    disagreement_explanation = None
    evidence_consistency = "CONSISTENT"
    requires_human_review = False

    cat_candidate = inferred_category or selected_category

    if vision_category and cat_candidate and vision_category.lower() != cat_candidate.lower():
        evidence_consistency = "INCONSISTENT"
        requires_human_review = True
        disagreement_explanation = (
            f"Evidence conflict noted: Citizen reported '{cat_candidate}' (supported by text analysis), whereas "
            f"computer vision detected '{vision_category}'. Needs human authority verification. "
            f"Preserving citizen-reported '{cat_candidate}' as primary recommendation."
        )
        recommended_category = cat_candidate
    elif vision_category and cat_candidate and vision_category.lower() == cat_candidate.lower():
        evidence_consistency = "CONSISTENT"
        requires_human_review = False
        recommended_category = vision_category
    elif vision_category and not cat_candidate:
        evidence_consistency = "CONSISTENT"
        requires_human_review = False
        recommended_category = vision_category
    elif cat_candidate:
        evidence_consistency = "UNCERTAIN" if not vision_category else "CONSISTENT"
        requires_human_review = False
        recommended_category = cat_candidate
    else:
        evidence_consistency = "UNCERTAIN"
        requires_human_review = False
        recommended_category = "Public Infrastructure"

    impact_summary = (
        f"Reported {recommended_category.lower()} issue at {location or 'specified coordinates'}."
    )
    if combined_text:
        impact_summary += f" Citizen notes: \"{combined_text[:140]}\"."

    safety_notes = "Standard civic hazard precautions advised for municipal inspection."
    if "pothole" in text_lower or "crater" in text_lower:
        safety_notes = "Caution: road surface irregularity poses immediate vehicular and pedestrian tripping hazard."
    elif "wire" in text_lower or "electric" in text_lower:
        safety_notes = "Caution: potential electrocution risk; restrict access until inspected."
    elif "manhole" in text_lower or "sewer" in text_lower:
        safety_notes = "Caution: open or damaged drain presents severe fall and contamination danger."

    return {
        "llm_used": False,
        "llm_model": None,
        "processing_status": "FALLBACK",
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "fallback_reason": fallback_reason,
        "extracted_problem": combined_text[:200] if combined_text else f"{recommended_category} reported by citizen",
        "recommended_category": recommended_category,
        "safety_concerns": safety_notes,
        "public_impact": impact_summary,
        "suggested_severity": None,
        "suggested_priority": None,
        "suggested_department_code": inferred_dept,
        "disagreement_explanation": disagreement_explanation,
        "evidence_consistency": evidence_consistency,
        "requires_human_review": requires_human_review,
        "explanation": (
            f"{impact_summary} "
            f"{disagreement_explanation + ' ' if disagreement_explanation else ''}"
            f"(Processed via deterministic civic ruleset: {fallback_reason})."
        ),
        # Phase 7 structured contract fields
        "citizen_reported_category": selected_category or "",
        "yolo_detected_categories": [vision_category] if vision_category else [],
        "category_confidence": round(float(vision_detections[0]["confidence"]), 2) if (vision_detections and vision_detections[0].get("confidence")) else 0.0,
        "severity": "MEDIUM",
        "priority": "NORMAL",
        "recommended_department": inferred_dept or "PUBLIC_INFRA",
        "risk_level": (suspicious_indicators or {}).get("risk_level", "NORMAL"),
        "duplicate_assessment": (duplicate_assessment or {}).get("overall_classification", "UNIQUE_REPORT"),
    }


def _call_gemini_sync(api_key: str, prompt: str, model_name: str = "gemini-3.5-flash") -> str:
    """Synchronous Gemini SDK call intended to be run inside a timeout-bounded executor."""
    from google import genai
    client = genai.Client(api_key=api_key)
    
    # Try primary model first, with automatic fallback if quota limit or unsupported error
    candidates = [model_name]
    if model_name != "gemini-3.5-flash-lite":
        candidates.append("gemini-3.5-flash-lite")
    
    last_err = None
    for cand in candidates:
        try:
            response = client.models.generate_content(
                model=cand,
                contents=prompt,
            )
            return response.text or ""
        except Exception as e:
            last_err = e
            err_str = str(e)
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "NOT_FOUND" in err_str:
                logger.warning(f"Gemini model {cand} hit quota/error ({type(e).__name__}); trying alternative...")
                continue
            raise e
            
    if last_err:
        raise last_err
    return ""


def analyze_description_with_gemini(
    title: Optional[str],
    description: Optional[str],
    selected_category: Optional[str],
    location: Optional[str],
    vision_category: Optional[str] = None,
    vision_detections: Optional[List[Dict[str, Any]]] = None,
    duplicate_assessment: Optional[Dict[str, Any]] = None,
    suspicious_indicators: Optional[Dict[str, Any]] = None,
    timeout_seconds: float = 6.0,
) -> Dict[str, Any]:
    """
    Analyses the citizen description using Gemini if a valid API key is configured.
    Enforces strict timeout and structured JSON validation.
    Never overrides actual image detections without explaining the disagreement.
    """
    api_key = (settings.GEMINI_API_KEY or "").strip()
    active_model = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash") or "gemini-3.5-flash"
    
    if not api_key or api_key.startswith("your-") or api_key == "changeme":
        return _heuristic_description_analysis(
            title=title,
            description=description,
            selected_category=selected_category,
            location=location,
            vision_category=vision_category,
            vision_detections=vision_detections,
            fallback_reason="Gemini API key not configured",
            duplicate_assessment=duplicate_assessment,
            suspicious_indicators=suspicious_indicators,
        )

    detections_summary = "None (no objects detected by YOLO)"
    if vision_detections:
        det_parts = [
            f"{d.get('label', 'object')} (conf={d.get('confidence', 0):.2f})"
            for d in vision_detections
        ]
        detections_summary = ", ".join(det_parts)

    dup_text = (duplicate_assessment or {}).get("overall_classification", "UNIQUE_REPORT")
    risk_text = (suspicious_indicators or {}).get("risk_level", "NORMAL")

    prompt = (
        "You are a municipal civic intelligence analyst for CIVICSOL.\n"
        "Analyze the following citizen complaint and return ONLY a valid JSON object.\n\n"
        f"Title: {title or 'N/A'}\n"
        f"Citizen Description: {description or 'N/A'}\n"
        f"Citizen Selected Category: {selected_category or 'N/A'}\n"
        f"Location: {location or 'N/A'}\n"
        f"Computer Vision Detections: {detections_summary}\n"
        f"Vision Predicted Category: {vision_category or 'None'}\n"
        f"Duplicate Assessment: {dup_text}\n"
        f"Suspicious Risk Level: {risk_text}\n\n"
        "Rules:\n"
        "1. Do NOT override actual computer vision detections without explaining the disagreement in 'disagreement_explanation'.\n"
        "2. Choose 'recommended_category' from: ['Road Damage', 'Garbage', 'Street Light', 'Water Leakage', 'Drainage', 'Public Infrastructure'].\n"
        "3. Choose 'suggested_severity' from: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].\n"
        "4. Choose 'suggested_priority' from: ['URGENT', 'HIGH', 'NORMAL', 'LOW'].\n"
        "5. Choose 'suggested_department_code' from: ['ROADS_BRIDGES', 'SOLID_WASTE', 'STREET_LIGHTING', 'WATER_SEWERAGE', 'DRAINAGE', 'PUBLIC_INFRA'].\n"
        "6. Provide specific 'safety_concerns' identifying risks to motorists, pedestrians, or public health.\n"
        "7. Evaluate evidence consistency between computer vision detections and citizen text:\n"
        "   - If vision and text align: set 'evidence_consistency': 'CONSISTENT', 'requires_human_review': false.\n"
        "   - If vision and text conflict: set 'evidence_consistency': 'INCONSISTENT', 'requires_human_review': true, and explain in 'disagreement_explanation'.\n"
        "   - If vision is absent: set 'evidence_consistency': 'UNCERTAIN', 'requires_human_review': false.\n\n"
        "Return strict JSON with keys:\n"
        "{\n"
        '  "extracted_problem": "concise summary",\n'
        '  "recommended_category": "...",\n'
        '  "public_impact": "concise explanation of public impact",\n'
        '  "safety_concerns": "specific safety risk description",\n'
        '  "suggested_severity": "CRITICAL|HIGH|MEDIUM|LOW",\n'
        '  "suggested_priority": "URGENT|HIGH|NORMAL|LOW",\n'
        '  "suggested_department_code": "...",\n'
        '  "evidence_consistency": "CONSISTENT|INCONSISTENT|UNCERTAIN",\n'
        '  "requires_human_review": true|false,\n'
        '  "disagreement_explanation": null or "string explaining why text disagrees with vision",\n'
        '  "explanation": "2-sentence summary and recommendation justification for municipal authorities"\n'
        "}"
    )

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_gemini_sync, api_key, prompt, active_model)
            raw_text = future.result(timeout=timeout_seconds)

        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.IGNORECASE)
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini output is not a JSON object.")

        rec_cat = str(parsed.get("recommended_category") or "").strip()
        if rec_cat not in VALID_CATEGORIES:
            rec_cat = selected_category or vision_category or "Public Infrastructure"

        disagreement = parsed.get("disagreement_explanation")
        raw_cons = str(parsed.get("evidence_consistency") or "").strip().upper()
        evidence_consistency = raw_cons if raw_cons in {"CONSISTENT", "INCONSISTENT", "UNCERTAIN"} else "CONSISTENT"
        requires_human_review = bool(parsed.get("requires_human_review", False))

        # Reconcile vision vs textual evidence without blindly overriding with vision false positives
        if vision_category and rec_cat.lower() != vision_category.lower():
            evidence_consistency = "INCONSISTENT"
            requires_human_review = True
            if not disagreement:
                disagreement = (
                    f"Evidence conflict noted: Text analysis recommends '{rec_cat}' (citizen selected '{selected_category}'), "
                    f"whereas computer vision detected '{vision_category}'. Marked for authority review."
                )
            # Retain citizen/LLM category when citizen and text agree, do not force vision_category
            if selected_category and selected_category.lower() == rec_cat.lower():
                pass
            elif not rec_cat and vision_category:
                rec_cat = vision_category
        elif not vision_category:
            evidence_consistency = "UNCERTAIN"
        else:
            evidence_consistency = "CONSISTENT"

        sev = str(parsed.get("suggested_severity") or "").strip().upper()
        if sev not in VALID_SEVERITIES:
            sev = None

        valid_priorities = {"URGENT", "HIGH", "NORMAL", "LOW"}
        raw_prio = str(parsed.get("suggested_priority") or "").strip().upper()
        prio = raw_prio if raw_prio in valid_priorities else None

        dept_code = str(parsed.get("suggested_department_code") or "").strip().upper()
        if dept_code not in VALID_DEPT_CODES:
            dept_code = None

        safety = str(parsed.get("safety_concerns") or "Identified hazards evaluated according to municipal risk protocols.").strip()
        explanation = str(parsed.get("explanation") or parsed.get("public_impact") or "").strip()
        if disagreement and disagreement not in explanation:
            explanation = f"{explanation} [{disagreement}]".strip()

        yolo_cats = [d.get("label") for d in (vision_detections or []) if d.get("label")]
        if not yolo_cats and vision_category:
            yolo_cats = [vision_category]

        top_conf = 0.0
        if vision_detections and vision_detections[0].get("confidence"):
            try:
                top_conf = round(float(vision_detections[0]["confidence"]), 2)
            except (ValueError, TypeError):
                top_conf = 0.0

        return {
            "llm_used": True,
            "llm_model": active_model,
            "processing_status": "SUCCESS",
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "fallback_reason": None,
            "extracted_problem": str(parsed.get("extracted_problem") or title or "").strip(),
            "recommended_category": rec_cat,
            "safety_concerns": safety,
            "public_impact": str(parsed.get("public_impact") or "").strip(),
            "suggested_severity": sev,
            "suggested_priority": prio,
            "suggested_department_code": dept_code,
            "evidence_consistency": evidence_consistency,
            "requires_human_review": requires_human_review,
            "disagreement_explanation": disagreement,
            "explanation": explanation,
            # Phase 7 structured contract fields
            "citizen_reported_category": selected_category or "",
            "yolo_detected_categories": yolo_cats,
            "category_confidence": top_conf,
            "severity": sev or "MEDIUM",
            "priority": prio or "NORMAL",
            "recommended_department": dept_code or "PUBLIC_INFRA",
            "risk_level": (suspicious_indicators or {}).get("risk_level", "NORMAL"),
            "duplicate_assessment": (duplicate_assessment or {}).get("overall_classification", "UNIQUE_REPORT"),
        }

    except FuturesTimeoutError:
        logger.warning("Gemini description analysis timed out; using deterministic fallback.")
        return _heuristic_description_analysis(
            title=title,
            description=description,
            selected_category=selected_category,
            location=location,
            vision_category=vision_category,
            vision_detections=vision_detections,
            fallback_reason="Gemini API request timed out",
            duplicate_assessment=duplicate_assessment,
            suspicious_indicators=suspicious_indicators,
        )
    except Exception as exc:
        logger.warning(f"Gemini description analysis unavailable ({type(exc).__name__}); using deterministic fallback.")
        return _heuristic_description_analysis(
            title=title,
            description=description,
            selected_category=selected_category,
            location=location,
            vision_category=vision_category,
            vision_detections=vision_detections,
            fallback_reason=f"Gemini service unavailable ({type(exc).__name__})",
            duplicate_assessment=duplicate_assessment,
            suspicious_indicators=suspicious_indicators,
        )

