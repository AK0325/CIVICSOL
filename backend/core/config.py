from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


# =========================================================
# APPLICATION SETTINGS
# =========================================================

class Settings(BaseSettings):
    """
    Central configuration for CIVICSOL.
    Values are loaded from environment variables / .env.
    """

    # -----------------------------------------------------
    # APPLICATION
    # -----------------------------------------------------

    APP_NAME: str = "CIVICSOL"

    APP_VERSION: str = "1.0.0"

    APP_DESCRIPTION: str = (
        "AI-Based Civic Issue Detection and "
        "Civic Intelligence System"
    )

    DEBUG: bool = True

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    DATABASE_URL: str = (
        "postgresql://civicsol_user:"
        "civicsol_pass@localhost:5432/civicsol"
    )

    # -----------------------------------------------------
    # SECURITY
    # -----------------------------------------------------

    JWT_SECRET: str = "change-this-secret-in-production"

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # -----------------------------------------------------
    # AI
    # -----------------------------------------------------

    GEMINI_API_KEY: str = ""

    # -----------------------------------------------------
    # EMAIL / SMTP
    # -----------------------------------------------------

    SMTP_HOST: str = "smtp.gmail.com"

    SMTP_PORT: int = 587

    SMTP_USERNAME: str = ""

    SMTP_PASSWORD: str = ""

    SMTP_FROM_EMAIL: str = ""

    SMTP_FROM_NAME: str = "CIVICSOL"

    # -----------------------------------------------------
    # FILE UPLOADS
    # -----------------------------------------------------

    UPLOAD_DIR: str = "uploads"

    MAX_IMAGE_SIZE_MB: int = 10

    # -----------------------------------------------------
    # CORS & NETWORK
    # -----------------------------------------------------

    FRONTEND_URL: str = "http://localhost:5173"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # -----------------------------------------------------
    # RATE LIMITING & SECURITY
    # -----------------------------------------------------

    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 300  # 5 minutes

    # -----------------------------------------------------
    # PYDANTIC SETTINGS
    # -----------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# =========================================================
# SETTINGS SINGLETON
# =========================================================

@lru_cache
def get_settings() -> Settings:
    """
    Return a cached application settings instance.
    """

    return Settings()


settings = get_settings()