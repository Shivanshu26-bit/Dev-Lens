from typing import List, Union
import json
from pydantic import field_validator
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
            try:
                # Try parsing if it's a JSON array format
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            
            # Fallback to comma separated
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(item) for item in v]
        raise ValueError(f"Invalid CORS origins format: {v}")

    # Future integration placeholders (optional/empty defaults for Phase 1)
    DATABASE_URL: str = ""
    GITHUB_TOKEN: str = ""
    GEMINI_API_KEY: str = ""

    # Phase 3 Analysis limits configurations
    MAX_FILES_ANALYZED: int = 100
    MAX_FILE_SIZE_BYTES: int = 200 * 1024  # 200 KB
    MAX_TOTAL_CONTENT_BYTES: int = 5 * 1024 * 1024  # 5 MB

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
