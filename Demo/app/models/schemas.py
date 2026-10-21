"""
Pydantic Schemas for Aegis Ambient Care MCP Server.
Complies with Amazon Developer Hackathon 2026 specifications.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.models.enums import RiskLevel, WellnessState, EmergencyDispatchStatus


# ---------------------------------------------------------------------------
# Required Core Data Contracts
# ---------------------------------------------------------------------------

class Event(BaseModel):
    """
    Sensor or vision event captured by ambient devices (Echo Show, mmWave radar, microphone).
    """
    event_type: str = Field(..., description="Type of incident e.g., 'fall_detected', 'loud_thud', 'prolonged_inactivity'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    location: str = Field(..., description="Room or location e.g., 'living_room', 'bathroom', 'kitchen'")
    timestamp: str = Field(..., description="ISO 8601 timestamp string e.g. '2026-10-17T08:15:30Z'")
    movement_after_event: str = Field(..., description="Post-event telemetry e.g., 'none', 'slight_twitch', 'normal', 'crawling'")


class Context(BaseModel):
    """
    Ambient, wearable, and circadian baseline context surrounding the event.
    """
    activity: str = Field(..., description="Pre-event activity e.g., 'walking_to_kitchen', 'sleeping', 'showering'")
    time_context: str = Field(..., description="Circadian context e.g., 'night_time', 'early_morning', 'afternoon'")
    baseline_deviation: float = Field(..., description="Deviation from patient norm (0.0=normal, 1.0+=severe anomaly)")
    wearable_status: str = Field(..., description="Status e.g. 'worn_normal', 'high_heart_rate', 'disconnected'")
    environment: str = Field(..., description="Environmental status e.g., 'dark_room_wet_floor', 'well_lit'")


class Risk(BaseModel):
    """
    Evaluated risk assessment output with clinical/safety rationale.
    """
    risk_level: str = Field(..., description="Risk tier: 'LOW', 'MODERATE', 'HIGH', or 'CRITICAL'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Risk confidence score between 0.0 and 1.0")
    reasons: List[str] = Field(default_factory=list, description="List of explanatory factors driving the risk score")


# ---------------------------------------------------------------------------
# Endpoint 1: assess_risk schemas
# ---------------------------------------------------------------------------

class VoiceResponse(BaseModel):
    """Voice verification feedback from Alexa+ ambient wellness check."""
    transcript: Optional[str] = Field(None, description="Transcribed voice utterance from senior")
    is_timeout: bool = Field(False, description="True if senior remained silent during prompt window")
    intent: Optional[str] = Field(None, description="'safe', 'distress', 'timeout', or None")


class AssessRiskRequest(BaseModel):
    event: Event
    context: Context


class ReassessRiskRequest(BaseModel):
    event: Event
    context: Context
    voice_response: Optional[VoiceResponse] = None


class RiskAssessmentResponse(BaseModel):
    risk_level: str
    confidence: float
    reasons: List[str]
    recommended_action: str
    requires_wellness_check: bool
    requires_caregiver_alert: bool
    requires_emergency_escalation: bool
    telemetry_breakdown: Dict[str, Any] = Field(default_factory=dict)
    evaluated_at: str
    latency_ms: float = 0.0


class AssessRiskResponse(BaseModel):
    risk: Risk
    requires_wellness_check: bool
    requires_caregiver_alert: bool
    requires_emergency_escalation: bool
    recommended_action: str
    evaluated_at: str
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Endpoint 2: start_wellness_check & conversational state machine schemas
# ---------------------------------------------------------------------------

class StartWellnessCheckRequest(BaseModel):
    session_id: Optional[str] = None
    event: Optional[Event] = None
    context: Optional[Context] = None
    initial_risk: Optional[Risk] = None
    prompt_override: Optional[str] = None


class WellnessCheckResponse(BaseModel):
    session_id: str
    state: str = WellnessState.PENDING_CHECK.value
    prompt_text: str
    prompt_ssml: str
    timeout_seconds: int = 20
    quick_replies: List[str] = Field(
        default_factory=lambda: ["I'm okay", "Help me", "I fell down", "I'm fine"]
    )
    risk_level: str
    created_at: str


class WellnessCheckReplyRequest(BaseModel):
    session_id: str
    user_speech_transcript: Optional[str] = None
    is_timeout: bool = False


class WellnessCheckResolutionResponse(BaseModel):
    session_id: str
    previous_state: str
    new_state: str
    transcript_received: Optional[str]
    is_timeout: bool
    updated_risk: Risk
    action_taken: str
    triggered_caregiver_notification: bool = False
    triggered_emergency_escalation: bool = False
    alexa_speech_response: str
    resolved_at: str


# ---------------------------------------------------------------------------
# Endpoint 3: notify_caregiver schemas
# ---------------------------------------------------------------------------

class NotifyCaregiverRequest(BaseModel):
    risk: Risk
    event: Optional[Event] = None
    context: Optional[Context] = None
    custom_message: Optional[str] = None
    target_channels: Optional[List[str]] = None


class CaregiverNotificationChannelResult(BaseModel):
    channel: str
    status: str
    recipient: str
    delivery_latency_ms: float
    integration_type: str = "SIMULATED"
    disclaimer: Optional[str] = "SIMULATION ADAPTER - Simulated channel delivery."


class CaregiverNotificationResponse(BaseModel):
    notification_id: str
    patient_id: str
    risk_level: str
    headline: str
    body: str
    channels_delivered: List[CaregiverNotificationChannelResult]
    dispatched_at: str
    caregiver_contact: str
    integration_type: str = "SIMULATED"
    disclaimer: str = "SIMULATION ADAPTER - Multi-channel caregiver notification simulated."



# ---------------------------------------------------------------------------
# Endpoint 4: generate_emergency_packet schemas
# ---------------------------------------------------------------------------

class GenerateEmergencyPacketRequest(BaseModel):
    event: Event
    context: Context
    risk: Risk
    patient_id: Optional[str] = None


class PatientSnapshot(BaseModel):
    patient_id: str
    name: str
    age: int = 79
    residence_address: str
    medical_history: List[str] = Field(
        default_factory=lambda: [
            "Mild cognitive impairment (early stage)",
            "Hypertension",
            "History of slip & fall in bathroom (Jan 2026)",
            "Penicillin allergy"
        ]
    )
    emergency_contact: str
    dnr_order: bool = False


class EmergencyPacket(BaseModel):
    packet_id: str
    version: str = "2026.1"
    generated_at: str
    patient_profile: PatientSnapshot
    triage_priority: str
    risk_breakdown: Risk
    incident_metadata: Event
    temporal_signals: Context
    telemetry_summary: Dict[str, Any]
    formatted_ems_summary: str


# ---------------------------------------------------------------------------
# Endpoint 5: escalate_emergency schemas
# ---------------------------------------------------------------------------

class EscalateEmergencyRequest(BaseModel):
    emergency_packet: Optional[EmergencyPacket] = None
    event: Optional[Event] = None
    context: Optional[Context] = None
    risk: Optional[Risk] = None
    cad_agency_code: str = "EMS-CAD-MA-02108"
    caller_callback_number: str = "+1-555-010-9110"


class EscalateEmergencyResponse(BaseModel):
    dispatch_id: str
    emergency_packet_id: str
    status: str
    cad_agency_code: str
    estimated_arrival_minutes: int
    units_dispatched: List[str]
    audio_stream_active: bool
    door_lock_unlocked: bool
    transmitted_at: str
    dispatch_notes: str
    integration_type: str = "SIMULATED"
    disclaimer: str = "SIMULATION ADAPTER - Not connected to live external carrier/PSAP. No real 911 dispatch occurred."
    smart_lock_pin: Optional[str] = None

