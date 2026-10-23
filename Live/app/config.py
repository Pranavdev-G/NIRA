"""
Live Configuration Settings for NIRA Real-Time System.
Amazon Developer Hackathon 2026.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

LIVE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = LIVE_DIR / ".env"


class LiveSettings(BaseSettings):
    # MongoDB Atlas
    MONGODB_URI: str = "mongodb+srv://dharaneesh0530_db_user:Dharaneesh!30@cluster0.hgkmalq.mongodb.net/?retryWrites=true&w=majority"
    MONGODB_DB_NAME: str = "nira_db"

    # TextBEE Live SMS Gateway
    SMS_PROVIDER: str = "textbee"
    TEXTBEE_API_KEY: str = "txb_3MJr75jHnsHzMbwxS2znyKFL7Dz2cRuS"
    TEXTBEE_DEVICE_ID: str = "6ada61efa4996b8ebf6dda9b"
    TEXTBEE_BASE_URL: str = "https://api.textbee.dev/api/v1"
    DEFAULT_EMERGENCY_RECIPIENT: str = "9489240892"

    # Whisper ASR
    WHISPER_MODEL_ID: str = "openai/whisper-large-v3-turbo"
    WHISPER_DEVICE: str = "auto"

    # App Host & URL
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"

    class Config:
        env_file = str(ENV_PATH) if ENV_PATH.exists() else None
        extra = "allow"


settings = LiveSettings()
