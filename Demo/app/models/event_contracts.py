"""
Unified Event Model & Contracts for NIRA Ambient Care.
Amazon Developer Hackathon 2026.

Defines the core data contracts for the multimodal event pipeline:
  - UnifiedEvent: Standard envelope for all sensor, vision, wearable, voice, and system events.
  - SafetyState: Multimodal safety state progression and recovery tiers.
  - ResidentStateSnapshot: Authoritative realtime state of resident and rooms.
  - EvidenceItem: Structured evidence trail retained for every decision.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# 1. State & Source Enumerations
# ---------------------------------------------------------------------------

class SafetyState(str, Enum):
    """
    Standard progression and recovery lifecycle for ambient elder safety:
      NORMAL -> ANOMALY -> ELEVATED -> HIGH -> CRITICAL
      Recovery: CRITICAL -> RESPONDING -> RESOLVED (-> NORMAL)
    """
    NORMAL = "NORMAL"
    ANOMALY = "ANOMALY"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    RESPONDING = "RESPONDING"
    RESOLVED = "RESOLVED"


class EventSource(str, Enum):
    WEARABLE = "wearable"
    RADAR = "radar"
    CAMERA_POSE = "camera_pose"
    AUDIO_VOICE = "audio_voice"
    ENVIRONMENT = "environment"
    STATE_MACHINE = "state_machine"
    MANUAL = "manual"
    SYSTEM = "system"


class EventType(str, Enum):
    # Wearable Telemetry
    WEARABLE_TELEMETRY = "wearable_telemetry"
    HEART_RATE_READING = "heart_rate_reading"
    TACHYCARDIA_ALERT = "tachycardia_alert"
    BRADYCARDIA_ALERT = "bradycardia_alert"
    ARRHYTHMIA_DETECTED = "arrhythmia_detected"
    WEARABLE_CONNECTIVITY = "wearable_connectivity"

    # Radar & Room Occupancy
    ROOM_OCCUPANCY = "room_occupancy"
    RADAR_PRESENCE = "radar_presence"
    MOTION_DETECTED = "motion_detected"
    IMMOBILITY_DETECTED = "immobility_detected"

    # Environment Conditions
    ENVIRONMENT_READING = "environment_reading"
    FLOOR_MOISTURE_DETECTED = "floor_moisture_detected"
    AMBIENT_LIGHT_LEVEL = "ambient_light_level"
    TEMPERATURE_ALERT = "temperature_alert"

    # Vision & Pose Analysis
    POSE_FALL_DETECTED = "pose_fall_detected"
    RAPID_DESCENT = "rapid_descent"
    IMPACT_HORIZONTAL = "impact_horizontal"
    POSE_RECOVERED = "pose_recovered"

    # Voice & Conversational Verification
    VOICE_CHECKIN_PROMPT = "voice_checkin_prompt"
    VOICE_RESPONSE_SAFE = "voice_response_safe"
    VOICE_RESPONSE_DISTRESS = "voice_response_distress"
    VOICE_TIMEOUT = "voice_timeout"

    # Incident & Emergency Lifecycle
    WELLNESS_TIMEOUT = "wellness_timeout"
    EMERGENCY_CAD_DISPATCHED = "emergency_cad_dispatched"
    CAREGIVER_NOTIFIED = "caregiver_notified"
    INCIDENT_RESOLVED = "incident_resolved"
    STATE_TRANSITION = "state_transition"


# ---------------------------------------------------------------------------
# 2. Specific Payload Models for Strong Typing
# ---------------------------------------------------------------------------

class WearablePayload(BaseModel):
    heart_rate_bpm: Optional[int] = Field(None, ge=0, le=300)
    movement_index: Optional[float] = Field(None, ge=0.0, le=1.0)
    wearable_status: Optional[str] = "worn_normal"
    arrhythmia_detected: Optional[bool] = False
    step_cadence_spm: Optional[int] = Field(None, ge=0)
    battery_percentage: Optional[int] = Field(None, ge=0, le=100)
    skin_contact: Optional[bool] = True


class EnvironmentPayload(BaseModel):
    temperature_c: Optional[float] = Field(None, ge=-20.0, le=60.0)
    humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    lighting_lux: Optional[float] = Field(None, ge=0.0, le=100000.0)
    ambient_noise_db: Optional[float] = Field(None, ge=0.0, le=150.0)
    floor_moisture_detected: Optional[bool] = False
    environment_label: Optional[str] = "well_lit"


class RadarPayload(BaseModel):
    presence: bool = True
    motion_level: float = Field(..., ge=0.0, le=1.0)
    occupancy_count: int = Field(1, ge=0)
    zone: Optional[str] = None


class PoseFallPayload(BaseModel):
    fall_confirmed: bool = True
    aspect_ratio: Optional[float] = None
    torso_angle: Optional[float] = None
    downward_velocity_norm: Optional[float] = None
    movement_after_event: str = Field("none", description="none, slight_twitch, crawling, normal")
    keypoint_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class VoiceResponsePayload(BaseModel):
    transcript: Optional[str] = None
    is_timeout: bool = False
    intent: Optional[str] = Field(None, description="'safe', 'distress', 'timeout'")
    confidence: Optional[float] = Field(0.95, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# 3. Unified Event Model (Non-Negotiable Mandatory Fields)
# ---------------------------------------------------------------------------

class UnifiedEvent(BaseModel):
    """
    Core envelope for all NIRA events.
    Guarantees consistent schema across edge devices, simulators, and services.
    """
    event_id: str = Field(..., min_length=3, description="Globally unique event ID")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp string e.g. 2026-10-19T22:00:00Z")
    resident_id: str = Field(..., min_length=2, description="Identifier of the monitored senior")
    room_id: str = Field(..., min_length=2, description="Room where event occurred, e.g. bathroom, living_room")
    source: str = Field(..., description="Originating sensor or subsystem, e.g. wearable, radar, camera_pose")
    event_type: str = Field(..., description="Classification of the event")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event-specific metadata dictionary")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    correlation_id: str = Field(..., min_length=3, description="Distributed correlation ID for tracing across incident lifecycle")

    @field_validator("timestamp")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            # Parse ISO timestamp ensuring validity
            clean_ts = v.replace("Z", "+00:00")
            _ = datetime.fromisoformat(clean_ts)
            return v
        except Exception as exc:
            raise ValueError(f"timestamp must be a valid ISO 8601 string: {exc}")


# ---------------------------------------------------------------------------
# 4. Evidence Item (Traceable Decision Trail)
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    """
    Structured evidence item retained with every risk evaluation or state transition.
    Ensures complete explainability and prevents ungrounded emergency escalations.
    """
    evidence_id: str = Field(..., description="Unique ID for this evidence record")
    timestamp: str
    source: str
    event_type: str
    room_id: str
    confidence: float
    description: str
    metric_key: Optional[str] = None
    metric_value: Optional[Any] = None
    weight: float = Field(1.0, ge=0.0)


# ---------------------------------------------------------------------------
# 5. Resident & Ambient State Snapshot
# ---------------------------------------------------------------------------

class ResidentStateSnapshot(BaseModel):
    """
    Authoritative state of the monitored resident and residence.
    Broadcast in real-time to all dashboard, caregiver, and emergency clients.
    """
    resident_id: str
    patient_name: str = "Eleanor Vance"
    age: int = 79
    safety_state: str = SafetyState.NORMAL.value
    risk_level: str = "LOW"
    composite_risk_score: float = 0.0
    active_room: str = "living_room"
    
    # Live telemetry summaries
    vitals: Dict[str, Any] = Field(default_factory=lambda: {
        "heart_rate_bpm": 72,
        "wearable_status": "worn_normal",
        "arrhythmia_detected": False,
        "movement_index": 0.8,
        "last_seen": datetime.now(timezone.utc).isoformat()
    })
    environment: Dict[str, Any] = Field(default_factory=lambda: {
        "temperature_c": 21.5,
        "humidity_pct": 42.0,
        "lighting_lux": 380.0,
        "floor_moisture_detected": False,
        "environment_label": "well_lit"
    })
    smart_home: Dict[str, Any] = Field(default_factory=lambda: {
        "smart_lock_unlocked": False,
        "pathway_lighting": "NORMAL",
        "audio_bridge_active": False
    })
    
    # Active incident reference & accumulated evidence trail
    active_incident_id: Optional[str] = None
    accumulated_evidence: List[EvidenceItem] = Field(default_factory=list)
    last_event_id: Optional[str] = None
    last_event_timestamp: Optional[str] = None
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = "init-bootstrap"
    clinical_disclaimer: str = (
        "NIRA Ambient Safety Engine: Evaluates situational fall risk and physical emergencies. "
        "Not a medical diagnosis."
    )


class EventIngestResult(BaseModel):
    """Result returned after ingesting a UnifiedEvent."""
    status: str = Field(..., description="'ACCEPTED', 'DUPLICATE_IGNORED', 'STALE_FLAGGED', 'REJECTED'")
    event_id: str
    correlation_id: str
    safety_state: str
    risk_level: str
    composite_risk_score: float
    active_incident_id: Optional[str] = None
    evidence_count: int = 0
    state_changed: bool = False
    ingested_at: str
