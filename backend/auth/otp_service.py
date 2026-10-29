import hashlib
import secrets
from datetime import datetime, timedelta

from ..core.config import settings


# =========================================================
# OTP CONFIGURATION
# =========================================================

OTP_EXPIRY_MINUTES = 10

MAX_OTP_ATTEMPTS = 5


# =========================================================
# OTP GENERATION
# =========================================================

def generate_otp() -> str:
    """
    Generate a cryptographically secure 6-digit OTP.
    """

    return f"{secrets.randbelow(1_000_000):06d}"


# =========================================================
# OTP HASHING
# =========================================================

def hash_otp(otp: str) -> str:
    """
    Hash OTP before storing it in the database.

    A dedicated OTP_SECRET is preferred.
    JWT_SECRET is used as a fallback for development.
    """

    secret = getattr(
        settings,
        "OTP_SECRET",
        None,
    ) or settings.JWT_SECRET

    value = (
        f"{secret}:{otp}"
        .encode("utf-8")
    )

    return hashlib.sha256(
        value
    ).hexdigest()


# =========================================================
# OTP VERIFICATION
# =========================================================

def verify_otp(
    otp: str,
    stored_hash: str,
) -> bool:
    """
    Verify a user-provided OTP
    against the stored hash.
    """

    return secrets.compare_digest(
        hash_otp(otp),
        stored_hash,
    )


# =========================================================
# OTP EXPIRY
# =========================================================

def get_otp_expiry() -> datetime:
    """
    Return the expiration timestamp
    for a newly generated OTP.
    """

    return (
        datetime.utcnow()
        + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )
    )


# =========================================================
# MOBILE MASKING
# =========================================================

def mask_mobile(
    mobile: str,
) -> str:
    """
    Mask a mobile number while
    keeping the final two digits visible.
    """

    mobile = str(mobile)

    if len(mobile) < 2:
        return "+91 ******"

    return (
        "+91 "
        + "*" * max(
            0,
            len(mobile) - 2,
        )
        + mobile[-2:]
    )


# =========================================================
# EMAIL MASKING
# =========================================================

def mask_email(
    email: str,
) -> str:
    """
    Mask an email address while
    keeping the domain visible.
    """

    if not email:
        return ""

    email = email.strip()

    if "@" not in email:
        return "********"

    username, domain = email.split(
        "@",
        1,
    )

    if len(username) <= 1:

        masked_username = "*"

    else:

        masked_username = (
            username[0]
            + "*" * min(
                5,
                len(username) - 1,
            )
        )

    return (
        masked_username
        + "@"
        + domain
    )