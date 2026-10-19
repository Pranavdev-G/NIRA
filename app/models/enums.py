"""
Enumerations for Aegis Ambient Care MCP Server.
"""

from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WellnessState(str, Enum):
    IDLE = "IDLE"
    PENDING_CHECK = "PENDING_CHECK"
    SAFE_RESOLVED = "SAFE_RESOLVED"
    DISTRESS_ELEVATED = "DISTRESS_ELEVATED"
    TIMEOUT_ESCALATED = "TIMEOUT_ESCALATED"


class MovementStatus(str, Enum):
    NONE = "none"
    SLIGHT_TWITCH = "slight_twitch"
    CRAWLING = "crawling"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class WearableStatus(str, Enum):
    WORN_NORMAL = "worn_normal"
    HIGH_HEART_RATE = "high_heart_rate"
    LOW_HEART_RATE = "low_heart_rate"
    ARRHYTHMIA_FLAG = "arrhythmia_flag"
    DISCONNECTED = "disconnected"
    CHARGING = "charging"


class NotificationChannel(str, Enum):
    ALEXA_DROP_IN = "alexa_drop_in"
    PUSH_NOTIFICATION = "push_notification"
    SMS = "sms"
    CAREGIVER_PORTAL = "caregiver_portal"


class EmergencyDispatchStatus(str, Enum):
    PENDING = "PENDING"
    TRANSMITTED = "TRANSMITTED"
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
