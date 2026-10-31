"""
CIVICSOL - Intelligent Department Recommendation Engine
Maps civic issue categories and AI-detected problem types to actual municipal
Department records in PostgreSQL.

Mapping Rules:
- Potholes / Road Damage -> ROADS_BRIDGES
- Garbage / Waste -> SOLID_WASTE
- Streetlights / Street Light -> STREET_LIGHTING
- Water leakage -> WATER_SEWERAGE
- Drainage -> DRAINAGE
- Public infrastructure -> PUBLIC_INFRA

Does NOT automatically assign issues; provides structured recommendations
for authority review and explicit approval.
"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from backend.models import Department


CATEGORY_TO_DEPT_CODE: Dict[str, str] = {
    "pothole": "ROADS_BRIDGES",
    "potholes": "ROADS_BRIDGES",
    "road damage": "ROADS_BRIDGES",
    "roads & bridges": "ROADS_BRIDGES",
    "road": "ROADS_BRIDGES",
    "garbage": "SOLID_WASTE",
    "garbage accumulation": "SOLID_WASTE",
    "solid waste": "SOLID_WASTE",
    "waste": "SOLID_WASTE",
    "sanitation": "SOLID_WASTE",
    "streetlight": "STREET_LIGHTING",
    "streetlights": "STREET_LIGHTING",
    "street light": "STREET_LIGHTING",
    "broken_streetlight": "STREET_LIGHTING",
    "broken streetlight": "STREET_LIGHTING",
    "lighting": "STREET_LIGHTING",
    "water leakage": "WATER_SEWERAGE",
    "water_leakage": "WATER_SEWERAGE",
    "water supply": "WATER_SEWERAGE",
    "pipeline leak": "WATER_SEWERAGE",
    "sewerage": "WATER_SEWERAGE",
    "drainage": "DRAINAGE",
    "drainage_problem": "DRAINAGE",
    "drainage problem": "DRAINAGE",
    "open drain": "DRAINAGE",
    "waterlogging": "DRAINAGE",
    "public infrastructure": "PUBLIC_INFRA",
    "damaged_infrastructure": "PUBLIC_INFRA",
    "damaged public infrastructure": "PUBLIC_INFRA",
    "footpath": "PUBLIC_INFRA",
    "tree / greenery": "PUBLIC_INFRA",
    "traffic": "ROADS_BRIDGES",
}

KEYWORD_TO_DEPT_CODE: Dict[str, str] = {
    "pothole": "ROADS_BRIDGES",
    "crater": "ROADS_BRIDGES",
    "asphalt": "ROADS_BRIDGES",
    "pavement": "ROADS_BRIDGES",
    "garbage": "SOLID_WASTE",
    "trash": "SOLID_WASTE",
    "dump": "SOLID_WASTE",
    "litter": "SOLID_WASTE",
    "waste": "SOLID_WASTE",
    "light": "STREET_LIGHTING",
    "lamp": "STREET_LIGHTING",
    "dark street": "STREET_LIGHTING",
    "pole": "STREET_LIGHTING",
    "leak": "WATER_SEWERAGE",
    "burst pipe": "WATER_SEWERAGE",
    "water main": "WATER_SEWERAGE",
    "drain": "DRAINAGE",
    "manhole": "DRAINAGE",
    "gutter": "DRAINAGE",
    "clogged": "DRAINAGE",
    "overflow": "DRAINAGE",
    "bench": "PUBLIC_INFRA",
    "railing": "PUBLIC_INFRA",
    "footpath": "PUBLIC_INFRA",
}


def resolve_department_code(
    predicted_category: Optional[str],
    citizen_category: Optional[str] = None,
    description: Optional[str] = None,
    llm_dept_code: Optional[str] = None,
) -> str:
    """
    Determines the target municipal department code from predicted category,
    LLM suggestion, citizen category, or description keywords.
    """
    valid_codes = {
        "ROADS_BRIDGES",
        "SOLID_WASTE",
        "STREET_LIGHTING",
        "WATER_SEWERAGE",
        "DRAINAGE",
        "PUBLIC_INFRA",
    }

    if predicted_category:
        norm_pred = predicted_category.strip().lower()
        if norm_pred in CATEGORY_TO_DEPT_CODE:
            return CATEGORY_TO_DEPT_CODE[norm_pred]
        for key, code in CATEGORY_TO_DEPT_CODE.items():
            if key in norm_pred:
                return code

    if llm_dept_code and llm_dept_code.strip().upper() in valid_codes:
        return llm_dept_code.strip().upper()

    if citizen_category:
        norm_cit = citizen_category.strip().lower()
        if norm_cit in CATEGORY_TO_DEPT_CODE:
            return CATEGORY_TO_DEPT_CODE[norm_cit]
        for key, code in CATEGORY_TO_DEPT_CODE.items():
            if key in norm_cit:
                return code

    if description:
        desc_lower = description.lower()
        for kw, code in KEYWORD_TO_DEPT_CODE.items():
            if kw in desc_lower:
                return code

    return "PUBLIC_INFRA"


def recommend_department(
    db: Session,
    predicted_category: Optional[str],
    citizen_category: Optional[str] = None,
    description: Optional[str] = None,
    llm_dept_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Looks up the actual Department record in PostgreSQL matching the resolved code.
    Returns structured department recommendation metadata.
    """
    norm_cat = (predicted_category or "").strip().lower()
    if norm_cat in {"uncertain", "no_detection", "unknown", "none"}:
        return {
            "department_id": None,
            "department_code": None,
            "department_name": None,
            "requires_manual_triage": True,
            "rationale": "Category is uncertain; manual triage required by authority.",
        }

    target_code = resolve_department_code(
        predicted_category=predicted_category,
        citizen_category=citizen_category,
        description=description,
        llm_dept_code=llm_dept_code,
    )

    dept = (
        db.query(Department)
        .filter(Department.code == target_code, Department.is_active == True)
        .first()
    )

    if not dept:
        # Fallback to any active department matching code case-insensitively or PUBLIC_INFRA
        dept = (
            db.query(Department)
            .filter(Department.code == "PUBLIC_INFRA", Department.is_active == True)
            .first()
        )
    if not dept:
        dept = db.query(Department).filter(Department.is_active == True).first()

    if dept:
        return {
            "department_id": dept.id,
            "department_code": dept.code,
            "department_name": dept.name,
            "requires_manual_triage": False,
            "rationale": f"Mapped category '{predicted_category or citizen_category or 'General'}' to {dept.name} ({dept.code}).",
        }

    return {
        "department_id": None,
        "department_code": target_code,
        "department_name": None,
        "requires_manual_triage": True,
        "rationale": f"Recommended department code {target_code} (no active department record found in DB).",
    }

