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

    # Multi-Room Vision Configuration (Phases 69-70)
    VISION_ENABLED: bool = os.getenv("VISION_ENABLED", "true").lower() in ("true", "1", "yes")
    MULTI_CAMERA_ENABLED: bool = os.getenv("MULTI_CAMERA_ENABLED", "true").lower() in ("true", "1", "yes")
    CAMERA_INFERENCE_FPS: float = float(os.getenv("CAMERA_INFERENCE_FPS", "12.0"))
    PERSON_CONFIDENCE_THRESHOLD: float = float(os.getenv("PERSON_CONFIDENCE_THRESHOLD", "0.45"))
    FALL_CONFIRMATION_FRAMES: int = int(os.getenv("FALL_CONFIRMATION_FRAMES", "3"))
    PERSON_LOST_GRACE_SECONDS: float = float(os.getenv("PERSON_LOST_GRACE_SECONDS", "3.0"))

    # Inactivity Configuration (Phases 14, 27, 69)
    INACTIVITY_WARNING_SECONDS: float = float(os.getenv("INACTIVITY_WARNING_SECONDS", "300.0"))
    INACTIVITY_PROLONGED_SECONDS: float = float(os.getenv("INACTIVITY_PROLONGED_SECONDS", "480.0"))
    INACTIVITY_CRITICAL_SECONDS: float = float(os.getenv("INACTIVITY_CRITICAL_SECONDS", "600.0"))

    # Zone Dwell Configuration (Phases 14, 15, 69, 70)
    ZONE_DWELL_WARNING_RATIO: float = float(os.getenv("ZONE_DWELL_WARNING_RATIO", "1.2"))
    ZONE_DWELL_CHECKIN_RATIO: float = float(os.getenv("ZONE_DWELL_CHECKIN_RATIO", "1.5"))
    ZONE_DWELL_CRITICAL_RATIO: float = float(os.getenv("ZONE_DWELL_CRITICAL_RATIO", "2.0"))

    # Initial Room Priors (Seconds) (Phases 17, 70)
    BATHROOM_INITIAL_EXPECTED_DURATION_SECONDS: float = float(os.getenv("BATHROOM_INITIAL_EXPECTED_DURATION_SECONDS", "600.0"))
    KITCHEN_INITIAL_EXPECTED_DURATION_SECONDS: float = float(os.getenv("KITCHEN_INITIAL_EXPECTED_DURATION_SECONDS", "600.0"))
    HALLWAY_INITIAL_EXPECTED_DURATION_SECONDS: float = float(os.getenv("HALLWAY_INITIAL_EXPECTED_DURATION_SECONDS", "300.0"))
    LIVING_ROOM_INITIAL_EXPECTED_DURATION_SECONDS: float = float(os.getenv("LIVING_ROOM_INITIAL_EXPECTED_DURATION_SECONDS", "3600.0"))
    BEDROOM_INITIAL_EXPECTED_DURATION_SECONDS: float = float(os.getenv("BEDROOM_INITIAL_EXPECTED_DURATION_SECONDS", "7200.0"))

    # Voice & Conversational Check-In (Phases 28-37, 69, 70)
    WELLNESS_RESPONSE_TIMEOUT_SECONDS: float = float(os.getenv("WELLNESS_RESPONSE_TIMEOUT_SECONDS", "12.0"))
    VOICE_CONTINUOUS_MONITORING: bool = os.getenv("VOICE_CONTINUOUS_MONITORING", "true").lower() in ("true", "1", "yes")
    VOICE_VAD_ENABLED: bool = os.getenv("VOICE_VAD_ENABLED", "true").lower() in ("true", "1", "yes")
    VOICE_MIN_SPEECH_SECONDS: float = float(os.getenv("VOICE_MIN_SPEECH_SECONDS", "0.5"))
    VOICE_MAX_SEGMENT_SECONDS: float = float(os.getenv("VOICE_MAX_SEGMENT_SECONDS", "10.0"))
    VOICE_RETRY_SECONDS: float = float(os.getenv("VOICE_RETRY_SECONDS", "5.0"))

    # Routine Baseline Engine (Phases 16, 47-49, 69)
    BASELINE_MIN_OBSERVATIONS: int = int(os.getenv("BASELINE_MIN_OBSERVATIONS", "5"))
    BASELINE_LEARNING_ENABLED: bool = os.getenv("BASELINE_LEARNING_ENABLED", "true").lower() in ("true", "1", "yes")

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
