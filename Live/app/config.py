"""
Live Configuration Settings for NIRA Real-Time System.
Amazon Developer Hackathon 2026.

Secure, environment-driven configuration:
- Zero hardcoded secrets, keys, or telephone numbers
- Reads from system environment variables and local .env files
- Safe credential masking for logging
- Configurable CORS allowed origins
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

LIVE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = LIVE_DIR.parent

# Search for .env in Live/ or root directory
env_file_path = None
for candidate in [LIVE_DIR / ".env", ROOT_DIR / ".env"]:
    if candidate.exists():
        env_file_path = candidate
        break


def mask_secret(value: Optional[str] = None) -> str:
    """Safely masks sensitive tokens, API keys, and connection strings for logging."""
    if not value or len(str(value).strip()) == 0:
        return "[NOT_SET]"
    s = str(value).strip()
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}...{s[-3:]}"


class LiveSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(env_file_path) if env_file_path else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # MongoDB Atlas (Rotatable via MONGODB_URI environment variable)
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "nira_db")

    # Local SQLite fallback/mirror
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aegis_care.db")

    # TextBEE Live SMS Gateway (Rotatable via TEXTBEE_API_KEY environment variable)
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "textbee")
    TEXTBEE_API_KEY: str = os.getenv("TEXTBEE_API_KEY", "")
    TEXTBEE_DEVICE_ID: str = os.getenv("TEXTBEE_DEVICE_ID", "")
    TEXTBEE_BASE_URL: str = os.getenv("TEXTBEE_BASE_URL", "https://api.textbee.dev/api/v1")
    DEFAULT_EMERGENCY_RECIPIENT: str = os.getenv("DEFAULT_EMERGENCY_RECIPIENT", "")

    # Whisper ASR
    WHISPER_MODEL_ID: str = os.getenv("WHISPER_MODEL_ID", "openai/whisper-large-v3-turbo")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "auto")

    # App Host, Port & URLs
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000")

    # Configurable CORS
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "*")

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ALLOWED_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    def is_mongo_configured(self) -> bool:
        return bool(self.MONGODB_URI and "mongodb" in self.MONGODB_URI)

    def is_textbee_configured(self) -> bool:
        return bool(self.TEXTBEE_API_KEY and self.TEXTBEE_DEVICE_ID)


settings = LiveSettings()
