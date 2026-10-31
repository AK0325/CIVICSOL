"""
CIVICSOL - Secure Super Admin One-Time Bootstrap Script
Creates the initial Super Admin account through an interactive prompt or explicit environment configuration.
Refuses to execute if a Super Admin already exists. Never prints passwords or hashes.
"""

import getpass
import os
import re
import secrets
import sys

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from typing import Optional
from sqlalchemy.orm import Session

from backend.auth.security import hash_password
from backend.database import SessionLocal
from backend.models import AuditLog, User


PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_\-+={}\[\]:;\"'<>,./~`]).{8,}$"
)


def validate_password_strength(password: str) -> bool:
    """Ensure password is at least 8 characters with upper, lower, digit, and symbol."""
    return bool(PASSWORD_REGEX.match(password))


def generate_unique_citizen_id(db: Session) -> str:
    """Generate a unique citizen ID for the administrative user account."""
    while True:
        candidate = f"CIVIC-ADM{secrets.randbelow(90000) + 10000}"
        if not db.query(User).filter(User.citizen_id == candidate).first():
            return candidate


def bootstrap_super_admin(
    db: Session,
    name: str,
    mobile: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    employee_id: str = "ADM-00001",
    designation: str = "Municipal Commissioner / Chief Administrator",
) -> dict:
    """
    Safely bootstrap the initial Super Admin account.
    Refuses if any active Super Admin account already exists.
    """
    # 1. Refuse to overwrite existing Super Admin
    existing_super_admin = (
        db.query(User)
        .filter(User.role == "SUPER_ADMIN", User.is_active == True)
        .first()
    )
    if existing_super_admin:
        raise ValueError(
            f"Bootstrap refused: An active Super Admin account already exists "
            f"(ID: {existing_super_admin.id}, Employee ID: {existing_super_admin.employee_id})."
        )

    # 2. Check mobile uniqueness
    if db.query(User).filter(User.mobile == mobile).first():
        raise ValueError(f"Mobile number {mobile} is already registered in the system.")

    # 3. Check email uniqueness if provided
    if email and db.query(User).filter(User.email == email.lower().strip()).first():
        raise ValueError(f"Email address {email} is already registered in the system.")

    # 4. Check employee_id uniqueness
    if db.query(User).filter(User.employee_id == employee_id).first():
        raise ValueError(f"Employee ID {employee_id} is already taken.")

    # 5. Password validation
    if not password or not validate_password_strength(password):
        raise ValueError(
            "Password must be at least 8 characters long and contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )

    citizen_id = generate_unique_citizen_id(db)
    password_hash = hash_password(password)

    super_admin = User(
        name=name.strip(),
        mobile=mobile.strip(),
        email=email.lower().strip() if email else None,
        password_hash=password_hash,
        citizen_id=citizen_id,
        role="SUPER_ADMIN",
        employee_id=employee_id.strip(),
        designation=designation.strip(),
        is_active=True,
    )

    db.add(super_admin)
    db.flush()

    # 6. Audit log entry
    audit_entry = AuditLog(
        user_id=super_admin.id,
        action="BOOTSTRAP_SUPER_ADMIN",
        entity_type="user",
        entity_id=super_admin.id,
        details=f"Initial Super Admin account bootstrapped with Employee ID {employee_id}.",
        ip_address="127.0.0.1",
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(super_admin)

    return {
        "status": "success",
        "user_id": super_admin.id,
        "name": super_admin.name,
        "employee_id": super_admin.employee_id,
        "citizen_id": super_admin.citizen_id,
        "role": super_admin.role,
        "mobile": super_admin.mobile,
        "email": super_admin.email,
    }


def main():
    print("=" * 60)
    print("CIVICSOL - Authority Command Center Initial Super Admin Setup")
    print("=" * 60)

    db = SessionLocal()
    try:
        existing = (
            db.query(User)
            .filter(User.role == "SUPER_ADMIN", User.is_active == True)
            .first()
        )
        if existing:
            print(
                f"\n[ERROR] Bootstrap refused: An active Super Admin already exists "
                f"(ID: {existing.id}, Employee ID: {existing.employee_id}).\n"
            )
            sys.exit(1)

        name = os.getenv("BOOTSTRAP_ADMIN_NAME")
        if not name:
            name = input("Enter Super Admin Full Name: ").strip()

        mobile = os.getenv("BOOTSTRAP_ADMIN_MOBILE")
        if not mobile:
            mobile = input("Enter Official Mobile Number (10 digits): ").strip()

        email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
        if not email:
            email = input("Enter Official Email (e.g. admin@civicsol.gov.in): ").strip()

        employee_id = os.getenv("BOOTSTRAP_ADMIN_EMPLOYEE_ID", "ADM-00001")
        if not os.getenv("BOOTSTRAP_ADMIN_EMPLOYEE_ID"):
            entered_emp = input(f"Enter Employee ID [default: {employee_id}]: ").strip()
            if entered_emp:
                employee_id = entered_emp

        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
        if not password:
            while True:
                p1 = getpass.getpass("Enter Secure Password: ")
                p2 = getpass.getpass("Confirm Password: ")
                if p1 != p2:
                    print("Passwords do not match. Please try again.")
                    continue
                if not validate_password_strength(p1):
                    print(
                        "Password must be at least 8 characters long with uppercase, lowercase, number, and special char."
                    )
                    continue
                password = p1
                break

        res = bootstrap_super_admin(
            db=db,
            name=name,
            mobile=mobile,
            email=email,
            password=password,
            employee_id=employee_id,
        )

        print("\n[SUCCESS] Super Admin account successfully bootstrapped!")
        print(f"  User ID: {res['user_id']}")
        print(f"  Name: {res['name']}")
        print(f"  Role: {res['role']}")
        print(f"  Employee ID: {res['employee_id']}")
        print(f"  Mobile: {res['mobile']}")
        print(f"  Email: {res['email']}")
        print("\nNote: Credentials have been securely hashed. Do not share credentials.\n")

    except Exception as exc:
        db.rollback()
        print(f"\n[ERROR] Super Admin bootstrap failed: {exc}\n")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
