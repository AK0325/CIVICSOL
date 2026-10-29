from pydantic import BaseModel, EmailStr, Field, field_validator


# =========================================================
# SIGN UP
# =========================================================

class SignupRequest(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    mobile: str = Field(
        ...,
        min_length=10,
        max_length=10
    )

    email: EmailStr | None = None

    password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )

    preferred_language: str = Field(
        default="English",
        max_length=20
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):

        value = value.strip()

        if not value:
            raise ValueError(
                "Name cannot be empty."
            )

        return value

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str):

        value = value.strip()

        if not value.isdigit():
            raise ValueError(
                "Mobile number must contain only digits."
            )

        if len(value) != 10:
            raise ValueError(
                "Mobile number must be exactly 10 digits."
            )

        return value


class SignupResponse(BaseModel):

    message: str
    citizen_id: str
    name: str
    mobile: str
    email: str | None
    preferred_language: str


# =========================================================
# SIGN IN
# =========================================================

class SigninRequest(BaseModel):

    mobile: str = Field(
        ...,
        min_length=10,
        max_length=10
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, value: str):

        value = value.strip()

        if not value.isdigit():
            raise ValueError(
                "Mobile number must contain only digits."
            )

        if len(value) != 10:
            raise ValueError(
                "Mobile number must be exactly 10 digits."
            )

        return value


class SigninResponse(BaseModel):

    message: str
    access_token: str
    token_type: str
    citizen_id: str
    name: str


# =========================================================
# UPDATE PROFILE
# =========================================================

class UpdateProfileRequest(BaseModel):

    name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    email: EmailStr | None = None

    preferred_language: str = Field(
        default="English",
        max_length=20
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str):

        value = value.strip()

        if not value:
            raise ValueError(
                "Name cannot be empty."
            )

        return value

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, value: str):

        value = value.strip()

        allowed_languages = {
            "English",
            "Hindi",
            "Gujarati",
        }

        if value not in allowed_languages:
            raise ValueError(
                "Unsupported preferred language."
            )

        return value


class ProfileResponse(BaseModel):

    id: int
    citizen_id: str
    name: str
    mobile: str
    email: str | None
    preferred_language: str
    ward: str | None
    zone: str | None
    created_at: object


# =========================================================
# CHANGE PASSWORD
# =========================================================

class ChangePasswordRequest(BaseModel):

    current_password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(
        cls,
        value: str
    ):

        value = value.strip()

        if len(value) < 8:
            raise ValueError(
                "New password must contain at least 8 characters."
            )

        return value


# =========================================================
# PASSWORD RECOVERY
# =========================================================

class ForgotPasswordRequest(BaseModel):

    channel: str = Field(
        ...,
        min_length=5,
        max_length=20
    )

    destination: str = Field(
        ...,
        min_length=5,
        max_length=255
    )

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str):

        value = value.strip().lower()

        allowed_channels = {
            "mobile",
            "email",
        }

        if value not in allowed_channels:
            raise ValueError(
                "Recovery method must be mobile or email."
            )

        return value


class VerifyResetOTPRequest(BaseModel):

    destination: str = Field(
        ...,
        min_length=5,
        max_length=255
    )

    otp: str = Field(
        ...,
        min_length=6,
        max_length=6
    )

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str):

        value = value.strip()

        if not value.isdigit():
            raise ValueError(
                "OTP must contain only digits."
            )

        if len(value) != 6:
            raise ValueError(
                "OTP must be exactly 6 digits."
            )

        return value


class ResetPasswordRequest(BaseModel):

    destination: str = Field(
        ...,
        min_length=5,
        max_length=255
    )

    reset_token: str = Field(
        ...,
        min_length=20,
        max_length=500
    )

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128
    )

    @field_validator("new_password")
    @classmethod
    def validate_reset_password(
        cls,
        value: str
    ):

        value = value.strip()

        if len(value) < 8:
            raise ValueError(
                "Password must contain at least 8 characters."
            )

        return value