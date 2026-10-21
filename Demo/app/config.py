"""
Application configuration for Aegis Ambient Care MCP Server.
Amazon Developer Hackathon 2026.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core settings and latency budget parameters."""
    
    APP_NAME: str = "Aegis Ambient Care MCP Server"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    
    # Latency budget for Alexa+ Voice Agents (hard SLA < 500ms)
    LATENCY_BUDGET_MS: float = 500.0
    
    # Ambient Wellness Check settings
    WELLNESS_CHECK_TIMEOUT_SECONDS: int = 20
    DEFAULT_PATIENT_ID: str = "PT-84920"
    DEFAULT_PATIENT_NAME: str = "Eleanor Vance"
    DEFAULT_LOCATION_LABEL: str = "Residence Unit 4B - Beacon Hill"
    
    # Caregiver mock settings
    PRIMARY_CAREGIVER_NAME: str = "Sarah Vance (Daughter)"
    PRIMARY_CAREGIVER_PHONE: str = "+1-555-019-2834"
    PRIMARY_CAREGIVER_DEVICE_ID: str = "alexa_device_echo_show_15_sarah"
    
    # Emergency Service (EMS) simulated settings
    EMS_DISPATCH_ENDPOINT: str = "https://mock-cad.emergency-services.internal/v1/dispatch"
    EMS_DISPATCH_TIMEOUT_SEC: float = 0.250  # Fast internal timeout to preserve SLA
    
    # SMS & Notification Provider (simulated or textbee)
    SMS_PROVIDER: str = "simulated"
    TEXTBEE_API_KEY: Optional[str] = None
    TEXTBEE_DEVICE_ID: Optional[str] = None
    TEXTBEE_BASE_URL: str = "https://api.textbee.dev/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
