from typing import List, Union
import json
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevLens"
    
    # CORS Origins configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_trimmed = v.strip()
            if not v_trimmed:
                return []
            try:
                # Try parsing if it's a JSON array format
                parsed = json.loads(v_trimmed)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
            
            # Fallback to comma separated
            return [i.strip() for i in v_trimmed.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        raise ValueError(f"Invalid CORS origins format: {v}")

    # Database Configuration (Phase 5A)
    DATABASE_URL: str = "postgresql+psycopg://devlens:devlens@localhost:5432/devlens"
    DB_ECHO: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str) and v.strip():
            v_clean = v.strip()
            if v_clean.startswith("postgresql://"):
                return v_clean.replace("postgresql://", "postgresql+psycopg://", 1)
            if v_clean.startswith("postgres://"):
                return v_clean.replace("postgres://", "postgresql+psycopg://", 1)
        return v
    
    # Credentials & API Keys
    GITHUB_TOKEN: str = ""
    GEMINI_API_KEY: str = ""

    # GitHub OAuth & Authentication (Phase 5B)
    SECRET_KEY: str = "devlens-insecure-secret-key-change-in-production-32b"
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/auth/github/callback"
    FRONTEND_URL: str = "http://localhost:5173"
    SESSION_COOKIE_NAME: str = "devlens_session"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_EXPIRE_SECONDS: int = 7 * 24 * 3600  # 7 days

    # Phase 3 Analysis limits configurations
    MAX_FILES_ANALYZED: int = 100
    MAX_FILE_SIZE_BYTES: int = 200 * 1024  # 200 KB
    MAX_TOTAL_CONTENT_BYTES: int = 5 * 1024 * 1024  # 5 MB

    # Phase 4 AI limits & configurations
    GEMINI_MODEL: str = "gemini-3.6-flash"
    MAX_EVIDENCE_FILES: int = 12
    MAX_CHARS_PER_FILE: int = 12000
    MAX_TOTAL_EVIDENCE_CHARS: int = 60000
    AI_REQUEST_TIMEOUT_SECONDS: float = 60.0

    # API Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = True
    REDIS_URL: str = ""
    RATE_LIMIT_STORAGE_URL: str = ""
    RATE_LIMIT_AUTH_LOGIN: str = "20/minute"
    RATE_LIMIT_ANALYZE: str = "30/minute"
    RATE_LIMIT_AI_ANALYZE: str = "10/minute"

    @model_validator(mode="after")
    def validate_production_security_settings(self) -> "Settings":
        # 1. Insecure default SECRET_KEY check for production
        insecure_default = "devlens-insecure-secret-key-change-in-production-32b"
        if self.SESSION_COOKIE_SECURE and (self.SECRET_KEY == insecure_default or "devlens-insecure" in self.SECRET_KEY):
            raise ValueError(
                "Insecure default SECRET_KEY cannot be used in production when SESSION_COOKIE_SECURE is enabled. "
                "Please configure a strong, unique SECRET_KEY."
            )

        # 2. Cookie SameSite validation
        samesite_lower = self.SESSION_COOKIE_SAMESITE.lower().strip()
        if samesite_lower not in {"lax", "strict", "none"}:
            raise ValueError(
                f"Invalid SESSION_COOKIE_SAMESITE: '{self.SESSION_COOKIE_SAMESITE}'. Must be 'lax', 'strict', or 'none'."
            )
        self.SESSION_COOKIE_SAMESITE = samesite_lower

        # 3. Modern browser requirement: SameSite=None requires Secure=True
        if self.SESSION_COOKIE_SAMESITE == "none" and not self.SESSION_COOKIE_SECURE:
            raise ValueError(
                "SESSION_COOKIE_SAMESITE='none' requires SESSION_COOKIE_SECURE=True in modern browsers to prevent cookie rejection."
            )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
