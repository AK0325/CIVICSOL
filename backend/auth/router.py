import secrets

from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from jose import jwt

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.rate_limiter import login_rate_limiter
from ..database import get_db

from ..models import (
    User,
    PasswordResetOTP,
)

from .dependencies import get_current_user

from .otp_service import (
    generate_otp,
    hash_otp,
    verify_otp,
    get_otp_expiry,
    mask_mobile,
    mask_email,
)

from .email_service import send_otp_email

from .schemas import (
    SignupRequest,
    SignupResponse,
    SigninRequest,
    SigninResponse,
    UpdateProfileRequest,
    ProfileResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    VerifyResetOTPRequest,
    ResetPasswordRequest,
)

from .security import (
    hash_password,
    verify_password,
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# =========================================================
# CITIZEN ID GENERATOR
# =========================================================

def generate_citizen_id(
    db: Session,
) -> str:

    while True:

        citizen_id = (
            f"CIVIC-{secrets.randbelow(900000) + 100000}"
        )

        existing_user = (
            db.query(User)
            .filter(
                User.citizen_id == citizen_id
            )
            .first()
        )

        if existing_user is None:
            return citizen_id


# =========================================================
# SIGN UP
# =========================================================

@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    data: SignupRequest,
    db: Session = Depends(get_db),
):

    existing_mobile = (
        db.query(User)
        .filter(
            User.mobile == data.mobile
        )
        .first()
    )

    if existing_mobile:

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An account with this mobile "
                "number already exists."
            ),
        )

    if data.email:

        existing_email = (
            db.query(User)
            .filter(
                User.email.ilike(str(data.email))
            )
            .first()
        )

        if existing_email:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An account with this email "
                    "already exists."
                ),
            )

    citizen_id = generate_citizen_id(db)

    password_hash = hash_password(
        data.password
    )

    user = User(
        name=data.name,
        mobile=data.mobile,
        email=(
            str(data.email).strip().lower()
            if data.email
            else None
        ),
        password_hash=password_hash,
        preferred_language=data.preferred_language,
        citizen_id=citizen_id,
    )

    try:

        db.add(user)

        db.commit()

        db.refresh(user)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create citizen account.",
        )

    return SignupResponse(
        message=(
            "Citizen account created successfully."
        ),
        citizen_id=user.citizen_id,
        name=user.name,
        mobile=user.mobile,
        email=user.email,
        preferred_language=user.preferred_language,
    )


# =========================================================
# SIGN IN
# =========================================================

@router.post(
    "/signin",
    response_model=SigninResponse,
)
def signin(
    data: SigninRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_key = f"citizen_signin:{client_ip}:{data.mobile}"

    login_rate_limiter.check_and_record(
        key=rate_key,
        max_attempts=settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    )

    user = (
        db.query(User)
        .filter(
            User.mobile == data.mobile
        )
        .first()
    )

    if not user:
        login_rate_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Invalid mobile number or password."
            ),
        )

    password_valid = verify_password(
        data.password,
        user.password_hash,
    )

    if not password_valid:
        login_rate_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Invalid mobile number or password."
            ),
        )

    # Reset rate limiting counter on valid login
    login_rate_limiter.reset(rate_key)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "citizen_id": user.citizen_id,
        }
    )

    return SigninResponse(
        message=(
            "Citizen signed in successfully."
        ),
        access_token=access_token,
        token_type="bearer",
        citizen_id=user.citizen_id,
        name=user.name,
    )


# =========================================================
# GET CURRENT PROFILE
# =========================================================

@router.get(
    "/me",
    response_model=ProfileResponse,
)
def get_my_profile(
    current_user: User = Depends(
        get_current_user
    ),
):

    return {
        "id": current_user.id,
        "citizen_id": current_user.citizen_id,
        "name": current_user.name,
        "mobile": current_user.mobile,
        "email": current_user.email,
        "preferred_language": (
            current_user.preferred_language
        ),
        "ward": current_user.ward,
        "zone": current_user.zone,
        "created_at": current_user.created_at,
    }


# =========================================================
# UPDATE CURRENT PROFILE
# =========================================================

@router.put(
    "/profile",
    response_model=ProfileResponse,
)
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    if data.email:

        existing_email = (
            db.query(User)
            .filter(
                User.email.ilike(str(data.email)),
                User.id != current_user.id,
            )
            .first()
        )

        if existing_email:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This email address is already "
                    "used by another citizen."
                ),
            )

    current_user.name = data.name.strip()

    current_user.email = (
        str(data.email).strip().lower()
        if data.email
        else None
    )

    current_user.preferred_language = (
        data.preferred_language
    )

    try:

        db.commit()

        db.refresh(current_user)

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to update citizen profile.",
        )

    return {
        "id": current_user.id,
        "citizen_id": current_user.citizen_id,
        "name": current_user.name,
        "mobile": current_user.mobile,
        "email": current_user.email,
        "preferred_language": (
            current_user.preferred_language
        ),
        "ward": current_user.ward,
        "zone": current_user.zone,
        "created_at": current_user.created_at,
    }


# =========================================================
# CHANGE CITIZEN PASSWORD
# =========================================================

@router.put(
    "/change-password",
)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    if verify_password(
        data.new_password,
        current_user.password_hash,
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "New password must be different "
                "from your current password."
            ),
        )

    current_password_valid = verify_password(
        data.current_password,
        current_user.password_hash,
    )

    if not current_password_valid:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(
        data.new_password
    )

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to change password.",
        )

    return {
        "message": (
            "Password changed successfully."
        )
    }


# =========================================================
# FORGOT PASSWORD — REQUEST OTP
# =========================================================

@router.post(
    "/forgot-password",
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):

    channel = data.channel.strip().lower()
    destination = data.destination.strip()

    # =====================================================
    # EMAIL RECOVERY
    # =====================================================

    if channel == "email":

        normalized_email = destination.lower()

        user = (
            db.query(User)
            .filter(
                User.email.ilike(normalized_email)
            )
            .first()
        )

        # -------------------------------------------------
        # Generic response
        # -------------------------------------------------

        if not user:

            return {
                "message": (
                    "If the account exists, "
                    "a verification code has been sent."
                )
            }

        # -------------------------------------------------
        # User has no email
        # -------------------------------------------------

        if not user.email:

            return {
                "message": (
                    "If the account exists, "
                    "a verification code has been sent."
                )
            }

        # -------------------------------------------------
        # OTP REQUEST RATE LIMIT
        #
        # Maximum 5 OTP requests in 15 minutes
        # for one citizen account.
        # -------------------------------------------------

        recent_otp_count = (
            db.query(PasswordResetOTP)
            .filter(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.created_at
                >= datetime.utcnow()
                - timedelta(minutes=15),
            )
            .count()
        )

        if recent_otp_count >= 5:

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many verification requests. "
                    "Please try again later."
                ),
            )

        # -------------------------------------------------
        # Generate secure 6-digit OTP
        # -------------------------------------------------

        otp = generate_otp()

        otp_hash_value = hash_otp(otp)

        expires_at = get_otp_expiry()

        # -------------------------------------------------
        # Invalidate previous OTP requests
        # -------------------------------------------------

        previous_otps = (
            db.query(PasswordResetOTP)
            .filter(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.used_at.is_(None),
            )
            .all()
        )

        for previous_otp in previous_otps:

            previous_otp.used_at = datetime.utcnow()

        # -------------------------------------------------
        # Create new OTP record
        # -------------------------------------------------

        reset_otp = PasswordResetOTP(
            user_id=user.id,
            channel="email",
            destination=normalized_email,
            otp_hash=otp_hash_value,
            expires_at=expires_at,
            attempts=0,
            verified=False,
        )

        db.add(reset_otp)

        try:

            # ---------------------------------------------
            # Flush so database errors happen here
            # ---------------------------------------------

            db.flush()

            # ---------------------------------------------
            # SEND REAL EMAIL
            # ---------------------------------------------

            email_sent = send_otp_email(
                recipient_email=user.email,
                otp=otp,
            )

            if not email_sent:

                db.rollback()

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Unable to send verification email. "
                        "Please try again later."
                    ),
                )

            # ---------------------------------------------
            # Save OTP
            # ---------------------------------------------

            db.commit()

            db.refresh(reset_otp)

        except HTTPException:

            raise

        except Exception:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Unable to start password recovery."
                ),
            )

        # -------------------------------------------------
        # Mask email before returning to React
        # -------------------------------------------------

        return {
            "message": (
                "Verification code sent successfully."
            ),
            "channel": "email",
            "destination": mask_email(
                normalized_email
            ),
            "expires_in_seconds": 600,
        }

    # =====================================================
    # MOBILE RECOVERY
    # =====================================================

    if channel == "mobile":

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=(
                "Mobile OTP delivery is not configured yet. "
                "Please use email recovery."
            ),
        )

    # =====================================================
    # INVALID CHANNEL
    # =====================================================

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Recovery method must be mobile or email."
        ),
    )


# =========================================================
# VERIFY PASSWORD RESET OTP
# =========================================================

@router.post(
    "/verify-reset-otp",
)
def verify_reset_otp(
    data: VerifyResetOTPRequest,
    db: Session = Depends(get_db),
):

    destination = data.destination.strip()

    # -----------------------------------------------------
    # Normalize email
    # -----------------------------------------------------

    if "@" in destination:

        destination = destination.lower()

    recovery_channel = (
        "email"
        if "@" in destination
        else "mobile"
    )

    # -----------------------------------------------------
    # Find latest active OTP
    #
    # Match BOTH destination and channel.
    # -----------------------------------------------------

    reset_otp = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.destination
            == destination,
            PasswordResetOTP.channel
            == recovery_channel,
            PasswordResetOTP.used_at.is_(None),
        )
        .order_by(
            PasswordResetOTP.created_at.desc()
        )
        .first()
    )

    if not reset_otp:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid or expired verification code."
            ),
        )

    # -----------------------------------------------------
    # Already verified
    # -----------------------------------------------------

    if reset_otp.verified:

        raise HTTPException(
            status_code=400,
            detail=(
                "This verification code has already "
                "been verified."
            ),
        )

    # -----------------------------------------------------
    # Check expiration
    # -----------------------------------------------------

    if datetime.utcnow() > reset_otp.expires_at:

        reset_otp.used_at = datetime.utcnow()

        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "Verification code has expired. "
                "Please request a new code."
            ),
        )

    # -----------------------------------------------------
    # Maximum incorrect attempts
    # -----------------------------------------------------

    if reset_otp.attempts >= 5:

        reset_otp.used_at = datetime.utcnow()

        db.commit()

        raise HTTPException(
            status_code=429,
            detail=(
                "Too many incorrect attempts. "
                "Please request a new verification code."
            ),
        )

    # -----------------------------------------------------
    # Verify OTP
    # -----------------------------------------------------

    if not verify_otp(
        data.otp,
        reset_otp.otp_hash,
    ):

        reset_otp.attempts += 1

        # Invalidate immediately on fifth wrong attempt.
        if reset_otp.attempts >= 5:

            reset_otp.used_at = datetime.utcnow()

        db.commit()

        remaining_attempts = max(
            0,
            5 - reset_otp.attempts,
        )

        if remaining_attempts == 0:

            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many incorrect attempts. "
                    "Please request a new verification code."
                ),
            )

        raise HTTPException(
            status_code=400,
            detail=(
                "Incorrect verification code. "
                f"{remaining_attempts} attempts remaining."
            ),
        )

    # -----------------------------------------------------
    # Mark OTP verified
    # -----------------------------------------------------

    reset_otp.verified = True

    db.commit()

    # -----------------------------------------------------
    # Create short-lived password reset token
    # -----------------------------------------------------

    reset_token_payload = {
        "sub": str(reset_otp.user_id),
        "otp_id": reset_otp.id,
        "type": "password_reset",
        "exp": (
            datetime.utcnow()
            + timedelta(minutes=10)
        ),
    }

    reset_token = jwt.encode(
        reset_token_payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    return {
        "message": (
            "Verification successful."
        ),
        "reset_token": reset_token,
    }


# =========================================================
# RESET PASSWORD
# =========================================================

@router.post(
    "/reset-password",
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):

    # -----------------------------------------------------
    # Decode reset token
    # -----------------------------------------------------

    try:

        payload = jwt.decode(
            data.reset_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail=(
                "Password reset session is invalid "
                "or expired."
            ),
        )

    # -----------------------------------------------------
    # Verify token type
    # -----------------------------------------------------

    if payload.get("type") != "password_reset":

        raise HTTPException(
            status_code=400,
            detail="Invalid password reset token.",
        )

    user_id = payload.get("sub")
    otp_id = payload.get("otp_id")

    if not user_id or not otp_id:

        raise HTTPException(
            status_code=400,
            detail="Invalid password reset token.",
        )

    # -----------------------------------------------------
    # Convert IDs
    # -----------------------------------------------------

    try:

        user_id = int(user_id)
        otp_id = int(otp_id)

    except (
        TypeError,
        ValueError,
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid password reset token.",
        )

    # -----------------------------------------------------
    # Find citizen
    # -----------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=400,
            detail="Invalid password reset request.",
        )

    # -----------------------------------------------------
    # Find OTP record
    # -----------------------------------------------------

    reset_otp = (
        db.query(PasswordResetOTP)
        .filter(
            PasswordResetOTP.id == otp_id,
            PasswordResetOTP.user_id == user.id,
        )
        .first()
    )

    if not reset_otp:

        raise HTTPException(
            status_code=400,
            detail="Invalid password reset request.",
        )

    # -----------------------------------------------------
    # OTP must be verified
    # -----------------------------------------------------

    if not reset_otp.verified:

        raise HTTPException(
            status_code=400,
            detail=(
                "Identity verification is required."
            ),
        )

    # -----------------------------------------------------
    # Reset request can only be used once
    # -----------------------------------------------------

    if reset_otp.used_at is not None:

        raise HTTPException(
            status_code=400,
            detail=(
                "This password reset request "
                "has already been used."
            ),
        )

    # -----------------------------------------------------
    # Make sure new password is different
    # -----------------------------------------------------

    if verify_password(
        data.new_password,
        user.password_hash,
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "New password must be different "
                "from your current password."
            ),
        )

    # -----------------------------------------------------
    # Hash new password
    # -----------------------------------------------------

    user.password_hash = hash_password(
        data.new_password
    )

    # -----------------------------------------------------
    # Consume reset request
    # -----------------------------------------------------

    reset_otp.used_at = datetime.utcnow()

    # -----------------------------------------------------
    # Save PostgreSQL changes
    # -----------------------------------------------------

    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to reset password."
            ),
        )

    return {
        "message": (
            "Password reset successfully."
        )
    }