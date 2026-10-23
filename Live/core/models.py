"""
Data models and contracts for NIRA Authoritative Safety Core.
Amazon Developer Hackathon 2026.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


from Live.core.time_provider import get_time_provider


class EventType(str, Enum):
    # Person Tracking & Multi-Room Handoff (Phases 3-6, 40)
    PERSON_DETECTED = "person_detected"
    PERSON_NOT_VISIBLE = "person_not_visible"
    ROOM_ENTRY = "room_entry"
    ROOM_EXIT = "room_exit"

    # Zone Dwell & Routine Behavior (Phases 14, 15, 22, 40)
    ZONE_DWELL_START = "zone_dwell_start"
    ZONE_DWELL_UPDATE = "zone_dwell_update"
    ZONE_DWELL_ANOMALY = "zone_dwell_anomaly"
    PROLONGED_ZONE_STAY = "prolonged_zone_stay"
    ABNORMAL_MOVEMENT = "abnormal_movement"
    UNUSUAL_ROUTINE = "unusual_routine"
    UNUSUAL_ROOM_SEQUENCE = "unusual_room_sequence"

    # Fall & Kinematics (Phases 10, 12, 13, 40)
    FALL_CANDIDATE = "fall_candidate"
    FALL_DETECTED = "fall_detected"
    POSTURE_CHANGE = "posture_change"
    RECOVERY_MOVEMENT = "recovery_movement"
    NO_RECOVERY = "no_recovery"
    PERSISTENT_FLOOR_POSTURE = "persistent_floor_posture"
    INACTIVITY_WARNING = "inactivity_warning"
    INACTIVITY_CRITICAL = "inactivity_critical"

    # Camera & Model Health (Phases 8, 40, 45)
    CAMERA_ONLINE = "camera_online"
    CAMERA_OFFLINE = "camera_offline"
    MODEL_READY = "model_ready"
    MODEL_ERROR = "model_error"
    FRAME_ERROR = "frame_error"

    # Voice Assistant & Spontaneous Speech (Phases 28-35, 40)
    VOICE_SPEECH_DETECTED = "voice_speech_detected"
    VOICE_TRANSCRIBED = "voice_transcribed"
    VOICE_WELLNESS_PROMPT = "voice_wellness_prompt"
    VOICE_HELP_REQUEST = "voice_help_request"
    VOICE_EMERGENCY = "voice_emergency"
    VOICE_RESPONSE_SAFE = "voice_response_safe"
    VOICE_RESPONSE_HELP = "voice_response_help"
    VOICE_SAFE = "voice_safe"
    VOICE_RISK = "voice_risk"
    VOICE_UNCERTAIN = "voice_uncertain"
    VOICE_TIMEOUT = "voice_timeout"
    VOICE_SILENCE_TIMEOUT = "voice_silence_timeout"
    VOICE_AMBIENT_DISTRESS = "voice_ambient_distress"
    MIC_ONLINE = "mic_online"
    MIC_OFFLINE = "mic_offline"
    MIC_RECOVERED = "mic_recovered"

    # Vitals & Wearable
    HEART_RATE_NORMAL = "heart_rate_normal"
    HEART_RATE_TACHYCARDIA = "heart_rate_tachycardia"
    HEART_RATE_BRADYCARDIA = "heart_rate_bradycardia"
    WEARABLE_DISCONNECTED = "wearable_disconnected"

    # Radar & Motion
    RADAR_PRESENCE = "radar_presence"
    RADAR_MOTION_CESSATION = "radar_motion_cessation"

    # Environmental & Smart Home
    ENVIRONMENTAL_HAZARD = "environmental_hazard"
    SMART_LOCK_STATE_CHANGE = "smart_lock_state_change"

    # Medication
    MEDICATION_SCHEDULED = "medication_scheduled"
    MEDICATION_TAKEN = "medication_taken"
    MEDICATION_MISSED = "medication_missed"

    # GPS & System
    GPS_LOCATION_UPDATE = "gps_location_update"
    SYSTEM_HEALTH_HEARTBEAT = "system_health_heartbeat"


class EventSource(str, Enum):
    CAMERA_VISION = "camera_vision"
    ROOM_TRACKER = "room_tracker"
    CAMERA_MANAGER = "camera_manager"
    FALL_DETECTOR = "fall_detector"
    INACTIVITY_MONITOR = "inactivity_monitor"
    VOICE_ASSISTANT = "voice_assistant"
    CONTINUOUS_MIC = "continuous_mic"
    WEARABLE_SENSOR = "wearable_sensor"
    HEART_RATE_MONITOR = "heart_rate_monitor"
    RADAR_MMWAVE = "radar_mmwave"
    ENVIRONMENTAL_SENSOR = "environmental_sensor"
    GPS_TRACKER = "gps_tracker"
    MEDICATION_MANAGER = "medication_manager"
    SMART_HOME = "smart_home"
    SYSTEM_MONITOR = "system_monitor"


class ZoneType(str, Enum):
    LIVING_ROOM = "living_room"
    BATHROOM = "bathroom"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    HALLWAY = "hallway"
    UNKNOWN = "unknown"


class SafetyState(str, Enum):
    NORMAL = "NORMAL"
    DETECTED = "DETECTED"
    VERIFYING = "VERIFYING"
    WELLNESS_CHECK = "WELLNESS_CHECK"
    WAITING_FOR_RESPONSE = "WAITING_FOR_RESPONSE"
    RESPONSIVE = "RESPONSIVE"
    CAREGIVER_ESCALATION = "CAREGIVER_ESCALATION"
    EMERGENCY_ESCALATION = "EMERGENCY_ESCALATION"
    DISPATCH_READY = "DISPATCH_READY"
    RESOLVED = "RESOLVED"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(str, Enum):
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    TRIGGER_WELLNESS_CHECK = "TRIGGER_WELLNESS_CHECK"
    ESCALATE_CAREGIVER = "ESCALATE_CAREGIVER"
    DISPATCH_EMERGENCY_CAD = "DISPATCH_EMERGENCY_CAD"
    RESOLVE_INCIDENT = "RESOLVE_INCIDENT"


class LocationModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    zone: ZoneType = ZoneType.UNKNOWN
    camera_id: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LiveEvent(BaseModel):
    """Authoritative normalized safety event consumed by Live Core."""
    model_config = ConfigDict(extra="ignore")

    event_id: str = Field(..., description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of the safety event")
    source: EventSource = Field(..., description="Originating sensor or subsystem")
    resident_id: str = Field(default="resident_eleanor_vance")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    location: LocationModel = Field(default_factory=LocationModel)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    correlation_id: str = Field(..., description="Correlation ID across multi-modal pipeline")
    device_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class SignalEvidence(BaseModel):
    """Evidence contributed by one of the 14 multimodal risk signals."""
    model_config = ConfigDict(extra="ignore")

    signal_name: str
    weight: float = Field(ge=0.0, le=1.0)
    raw_value: Any
    risk_contribution: float = Field(ge=0.0, le=1.0)
    is_abnormal: bool = False
    notes: Optional[str] = None


class ContextState(BaseModel):
    """Real-time room, environmental, and temporal context."""
    model_config = ConfigDict(extra="ignore")

    zone: ZoneType = ZoneType.LIVING_ROOM
    zone_risk_tier: str = "REST_ZONE"
    circadian_phase: str = "ACTIVE_DAY"
    is_night: bool = False
    is_afternoon_nap: bool = False
    hazard_multiplier: float = 1.0
    is_dark: bool = False
    is_wet_floor: bool = False
    temperature_c: Optional[float] = 21.5
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RiskAssessment(BaseModel):
    """Authoritative composite output of the Multimodal Risk Engine."""
    model_config = ConfigDict(extra="ignore")

    assessment_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resident_id: str = "resident_eleanor_vance"
    risk_level: SeverityLevel = SeverityLevel.LOW
    overall_score: float = Field(ge=0.0, le=1.0, description="Composite score between 0.0 and 1.0")
    confidence: float = Field(ge=0.0, le=1.0)
    contributing_signals: List[SignalEvidence] = Field(default_factory=list)
    context_modifiers: Dict[str, Any] = Field(default_factory=dict)
    baseline_tolerance_sec: float = 180.0
    recommended_action: RecommendedAction = RecommendedAction.CONTINUE_MONITORING


class TimelineEntry(BaseModel):
    """Immutable audit trail step for an incident."""
    model_config = ConfigDict(extra="ignore")

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    state: SafetyState
    action: str
    description: str
    actor: str = "NIRA_SAFETY_CORE"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceInteractionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str
    prompt_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resident_response: Optional[str] = None
    classification: Optional[str] = None  # SAFE, HELP, SILENCE, etc.
    duration_sec: Optional[float] = None


class CaregiverActionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action_type: str
    caregiver_name: str
    phone: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""


class EmergencyDispatchRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    service_type: str = "AMBULANCE_CAD"
    unit_id: str = "Medic-14"
    cad_incident_number: str
    dispatched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    eta_mins: float = 3.5
    status: str = "EN_ROUTE"
    smart_door_status: str = "LOCKED"
    smart_door_pin: str = "8492"


class IncidentRecord(BaseModel):
    """Authoritative Incident Record managed by IncidentManager."""
    model_config = ConfigDict(extra="ignore")

    incident_id: str
    resident_id: str = "resident_eleanor_vance"
    state: SafetyState = SafetyState.NORMAL
    severity: SeverityLevel = SeverityLevel.LOW
    risk_score: float = 0.0
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    location: LocationModel = Field(default_factory=LocationModel)
    trigger_event: Optional[Dict[str, Any]] = None
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    voice_interaction: Optional[VoiceInteractionRecord] = None
    caregiver_actions: List[CaregiverActionRecord] = Field(default_factory=list)
    emergency_dispatch: Optional[EmergencyDispatchRecord] = None
    resolution_summary: Optional[Dict[str, Any]] = None
    timeline: List[TimelineEntry] = Field(default_factory=list)


class EmergencyPacket(BaseModel):
    """Authoritative structured payload for Caregiver SMS and Paramedic CAD."""
    model_config = ConfigDict(extra="ignore")

    schema_version: str = "2.0.0"
    incident_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resident: Dict[str, Any]
    location: Dict[str, Any]
    safety_summary: Dict[str, Any]
    vitals: Dict[str, Any]
    voice_evidence: Optional[Dict[str, Any]] = None
    camera_evidence: Optional[Dict[str, Any]] = None
    caregiver_contact: Dict[str, Any]
    smart_home_state: Dict[str, Any]
    emergency_dispatch: Optional[Dict[str, Any]] = None
