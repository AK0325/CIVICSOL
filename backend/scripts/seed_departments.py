"""
CIVICSOL - Idempotent Department Seeder
Seeds standard municipal departments without duplicating or corrupting existing records.
"""

from typing import Any, Dict, List
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Department


DEFAULT_DEPARTMENTS: List[Dict[str, Any]] = [
    {
        "name": "Roads & Bridges",
        "code": "ROADS_BRIDGES",
        "description": "Maintenance of city roads, potholes, pedestrian footpaths, flyovers, bridges, and road dividers.",
        "contact_email": "roads@civicsol.gov.in",
        "contact_phone": "+91 79 2555 1001",
        "is_active": True,
    },
    {
        "name": "Solid Waste Management",
        "code": "SOLID_WASTE",
        "description": "Garbage collection, overflowing community bins, dead animal disposal, and street sanitation.",
        "contact_email": "sanitation@civicsol.gov.in",
        "contact_phone": "+91 79 2555 1002",
        "is_active": True,
    },
    {
        "name": "Street Lighting",
        "code": "STREET_LIGHTING",
        "description": "Repair and maintenance of street lamps, junction boxes, high-mast lights, and electrical safety.",
        "contact_email": "lighting@civicsol.gov.in",
        "contact_phone": "+91 79 2555 1003",
        "is_active": True,
    },
    {
        "name": "Water Supply & Sewerage",
        "code": "WATER_SEWERAGE",
        "description": "Potable water pipeline repairs, leakages, contaminated water reports, and underground sewer lines.",
        "contact_email": "water@civicsol.gov.in",
        "contact_phone": "+91 79 2555 1004",
        "is_active": True,
    },
    {
        "name": "Drainage",
        "code": "DRAINAGE",
        "description": "Stormwater drains, open manholes, roadside gully pits, and monsoon waterlogging prevention.",
        "contact_email": "drainage@civicsol.gov.in",
        "contact_phone": "+91 79 2555 1005",
        "is_active": True,
    },
    {
        "name": "Public Infrastructure",
        "code": "PUBLIC_INFRA",
        "description": "Municipal parks, bus shelters, public toilets, civic library buildings, and civic boundary walls.",
        "contact_email": "infra@civicsol.gov.in",
        "contact_phone": "+91 79 2555 1006",
        "is_active": True,
    },
]


def seed_default_departments(db: Session) -> Dict[str, Any]:
    """
    Idempotently seeds default departments into the database.
    Checks existing records by unique code to prevent duplicate insertion.
    """
    created_count = 0
    updated_count = 0
    existing_count = 0
    department_records = []

    for item in DEFAULT_DEPARTMENTS:
        existing = db.query(Department).filter(Department.code == item["code"]).first()

        if existing:
            # Sync name or contact if changed, but preserve ID and custom configurations
            existing.description = item["description"]
            existing.contact_email = existing.contact_email or item["contact_email"]
            existing.contact_phone = existing.contact_phone or item["contact_phone"]
            department_records.append(existing)
            existing_count += 1
        else:
            dept = Department(
                name=item["name"],
                code=item["code"],
                description=item["description"],
                contact_email=item["contact_email"],
                contact_phone=item["contact_phone"],
                is_active=item["is_active"],
            )
            db.add(dept)
            department_records.append(dept)
            created_count += 1

    db.commit()

    return {
        "status": "success",
        "total_standard": len(DEFAULT_DEPARTMENTS),
        "created": created_count,
        "existing": existing_count,
        "departments": [
            {"id": d.id, "name": d.name, "code": d.code, "is_active": d.is_active}
            for d in department_records
        ],
    }


if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = seed_default_departments(db)
        print("Idempotent department seeding completed:")
        print(f"  Created: {result['created']}")
        print(f"  Existing/Updated: {result['existing']}")
        print(f"  Total standard departments: {result['total_standard']}")
    finally:
        db.close()
