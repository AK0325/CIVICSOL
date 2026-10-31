"""
CIVICSOL - Idempotent Initial Authority Accounts Provisioning Script
Safely provisions the three initial municipal authority accounts:
1. Super Admin (ADM-001)
2. Department Officer - Roads & Bridges (AUTH-001)
3. Field Officer - Street Lighting (AUTH-002)

Preserves existing accounts and never overwrites credentials or hashes.
"""

import os
import secrets
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.auth.security import hash_password
from backend.database import SessionLocal
from backend.models import AuditLog, Department, User
from backend.scripts.seed_departments import seed_default_departments


INITIAL_ACCOUNTS: List[Dict[str, Any]] = [
    {
        "employee_id": "ADM-001",
        "name": "Municipal Administrator",
        "email": "admin@civicsol.gov.in",
        "mobile": "9876543210",
        "role": "SUPER_ADMIN",
        "department_code": None,
        "designation": "Chief Municipal Administrator",
        "password": "Civicsol@Admin2026!",
    },
    {
        "employee_id": "AUTH-001",
        "name": "Roads & Bridges Officer",
        "email": "officer.roads@civicsol.gov.in",
        "mobile": "9876543211",
        "role": "DEPARTMENT_OFFICER",
        "department_code": "ROADS_BRIDGES",
        "designation": "Executive Department Officer",
        "password": "Civicsol@Auth2026!",
    },
    {
        "employee_id": "AUTH-002",
        "name": "Street Lighting Officer",
        "email": "officer.lighting@civicsol.gov.in",
        "mobile": "9876543212",
        "role": "FIELD_OFFICER",
        "department_code": "STREET_LIGHTING",
        "designation": "Senior Field Operations Officer",
        "password": "Civicsol@Field2026!",
    },
]


def generate_unique_citizen_id(db: Session, prefix: str = "CIVIC-AUTH") -> str:
    """Generate a unique citizen ID for the authority user account."""
    while True:
        candidate = f"{prefix}{secrets.randbelow(90000) + 10000}"
        if not db.query(User).filter(User.citizen_id == candidate).first():
            return candidate


def provision_initial_authority_accounts(db: Session) -> Dict[str, Any]:
    """
    Safely and idempotently provisions the initial three authority accounts.
    1. Verifies/seeds departments.
    2. Checks if each account already exists by employee_id, email, or mobile.
    3. Provisions missing accounts using secure bcrypt hashing.
    4. Never overwrites or resets existing accounts.
    """
    # 1. Ensure departments are seeded
    dept_res = seed_default_departments(db)

    results = {
        "created": [],
        "already_existed": [],
        "errors": [],
    }

    for acc_info in INITIAL_ACCOUNTS:
        emp_id = acc_info["employee_id"]

        # Check existing by employee_id
        existing_by_emp = db.query(User).filter(User.employee_id == emp_id).first()
        if existing_by_emp:
            dept_name = existing_by_emp.department.name if existing_by_emp.department else "None"
            results["already_existed"].append({
                "employee_id": existing_by_emp.employee_id,
                "name": existing_by_emp.name,
                "role": existing_by_emp.role,
                "department": dept_name,
                "is_active": existing_by_emp.is_active,
            })
            continue

        # Check collisions on email or mobile
        clean_email = acc_info["email"].lower().strip()
        clean_mobile = acc_info["mobile"].strip()

        if db.query(User).filter(User.email == clean_email).first():
            results["errors"].append({
                "employee_id": emp_id,
                "error": f"Email '{clean_email}' is already taken by another account.",
            })
            continue

        if db.query(User).filter(User.mobile == clean_mobile).first():
            results["errors"].append({
                "employee_id": emp_id,
                "error": f"Mobile '{clean_mobile}' is already taken by another account.",
            })
            continue

        # Resolve department ID if department_code specified
        dept_id = None
        dept_display = "None (Global Access)"
        if acc_info["department_code"]:
            dept = db.query(Department).filter(Department.code == acc_info["department_code"]).first()
            if not dept:
                results["errors"].append({
                    "employee_id": emp_id,
                    "error": f"Department code '{acc_info['department_code']}' not found in database.",
                })
                continue
            dept_id = dept.id
            dept_display = dept.name

        # Create user
        citizen_id = generate_unique_citizen_id(db)
        hashed_pwd = hash_password(acc_info["password"])

        user = User(
            name=acc_info["name"],
            mobile=clean_mobile,
            email=clean_email,
            password_hash=hashed_pwd,
            citizen_id=citizen_id,
            role=acc_info["role"],
            employee_id=emp_id,
            designation=acc_info["designation"],
            department_id=dept_id,
            is_active=True,
        )
        db.add(user)
        db.flush()

        # Audit log entry
        audit = AuditLog(
            user_id=user.id,
            action="INITIAL_AUTHORITY_PROVISIONED",
            entity_type="user",
            entity_id=user.id,
            details=f"Initial authority account created with Employee ID {emp_id} (Role: {user.role}).",
            ip_address="127.0.0.1",
        )
        db.add(audit)

        results["created"].append({
            "employee_id": user.employee_id,
            "name": user.name,
            "role": user.role,
            "department": dept_display,
            "is_active": user.is_active,
        })

    db.commit()
    return results


def main():
    print("=" * 65)
    print("CIVICSOL - Provisioning Initial Authority Accounts")
    print("=" * 65)

    db = SessionLocal()
    try:
        results = provision_initial_authority_accounts(db)

        if results["created"]:
            print("\n[CREATED ACCOUNTS]:")
            for acc in results["created"]:
                print(f"  - Employee ID: {acc['employee_id']} | Role: {acc['role']} | Department: {acc['department']} | Active: {acc['is_active']}")

        if results["already_existed"]:
            print("\n[ALREADY EXISTING ACCOUNTS (PRESERVED)]:")
            for acc in results["already_existed"]:
                print(f"  - Employee ID: {acc['employee_id']} | Role: {acc['role']} | Department: {acc['department']} | Active: {acc['is_active']}")

        if results["errors"]:
            print("\n[ERRORS ENCOUNTERED]:")
            for err in results["errors"]:
                print(f"  - Employee ID: {err['employee_id']} | Error: {err['error']}")

        print("\nInitialization complete. Passwords securely hashed with bcrypt.")
    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] Provisioning failed: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
