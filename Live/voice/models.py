"""
Data Models and Structured Contracts for NIRA Live Voice Interaction.
Amazon Developer Hackathon 2026.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceInteractionStatus(str, Enum):
    """Safety state determined from conversational response."""
    SAFE = "SAFE"
    UNCERTAIN = "UNCERTAIN"
    RISK = "RISK"
    EMERGENCY = "EMERGENCY"


class VoiceUrgencyLevel(str, Enum):
    """Urgency level associated with response analysis."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VoiceAction(str, Enum):
    """Recommended system downstream action."""
    NONE = "NONE"
    LOG_ONLY = "LOG_ONLY"
    REPEAT_CHECK_IN = "REPEAT_CHECK_IN"
    CREATE_INCIDENT = "CREATE_INCIDENT"
    ESCALATE_CAREGIVER = "ESCALATE_CAREGIVER"
    ESCALATE_EMERGENCY_CAD = "ESCALATE_EMERGENCY_CAD"


class TranscriptionResult(BaseModel):
    """
    Standardized result from Speech-to-Text inference.
    Confidence is exposed as true metrics (avg_logprob, no_speech_prob) rather than fabricated percentages.
    """
    transcript: str = Field(..., description="Recognized speech transcript")
    language: str = Field("en", description="Detected or specified spoken language code")
    duration_sec: float = Field(0.0, description="Duration of processed audio in seconds")
    processing_time_sec: float = Field(0.0, description="Inference execution time in seconds")
    model: str = Field("openai/whisper-large-v3-turbo", description="ASR model identifier")
    transcription_quality: Optional[str] = Field("good", description="Derived qualitative assessment (e.g. high, good, low, noisy)")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Raw model metrics e.g. avg_logprob, no_speech_prob, compression_ratio")


class VoiceAnalysisResult(BaseModel):
    """Result from conversational response analyzer."""
    status: VoiceInteractionStatus = Field(..., description="SAFE, UNCERTAIN, RISK, or EMERGENCY")
    urgency: VoiceUrgencyLevel = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    reason: str = Field(..., description="Human-readable explanation of safety classification")
    action: VoiceAction = Field(..., description="Recommended downstream action")
    is_negated: bool = Field(False, description="Flag indicating if a negation was detected")
    is_mixed: bool = Field(False, description="Flag indicating contradictory/mixed sentiment")
    emergency_signals: List[str] = Field(default_factory=list, description="Specific emergency cues detected")
    risk_signals: List[str] = Field(default_factory=list, description="Specific risk indicators detected")
    safe_signals: List[str] = Field(default_factory=list, description="Specific safety indicators detected")
    analyzed_language: str = Field("en", description="Language of analysis")


class VoiceInteractionResult(BaseModel):
    """
    Authoritative structured output of a NIRA Live Voice Interaction turn.
    Exposed cleanly to other LIVE modules (incidents, caregiver, emergency CAD).
    """
    interaction_id: str = Field(..., description="Unique ID for this voice turn")
    elderly_id: str = Field("PT-84920", description="Senior resident identifier")
    question: str = Field("Are you okay?", description="Question asked by NIRA voice assistant")
    transcript: str = Field(..., description="Transcribed speech from Whisper")
    language: str = Field("en", description="Spoken language")
    translated_transcript: Optional[str] = Field(None, description="English translation if spoken in another language")
    status: VoiceInteractionStatus = Field(..., description="SAFE / UNCERTAIN / RISK / EMERGENCY")
    urgency: VoiceUrgencyLevel = Field(..., description="LOW / MEDIUM / HIGH / CRITICAL")
    reason: str = Field(..., description="Detailed clinical reason")
    action: VoiceAction = Field(..., description="Action recommendation")
    model: str = Field("openai/whisper-large-v3-turbo", description="Speech recognition model used")
    timestamp: str = Field(default_factory=utc_now_iso, description="UTC ISO8601 timestamp")
    duration_sec: float = Field(0.0, description="Audio length in seconds")
    processing_time_sec: float = Field(0.0, description="Total pipeline latency in seconds")
    transcription_quality: Optional[str] = Field("good", description="ASR quality descriptor")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional debug/telemetry metadata")


class CheckInRequest(BaseModel):
    """Parameters for running a live voice check-in."""
    elderly_id: str = Field("PT-84920", description="Target resident identifier")
    question: str = Field("Are you okay?", description="Question prompt to speak or display")
    max_record_seconds: float = Field(10.0, description="Max recording duration window")
    silence_timeout_seconds: float = Field(2.5, description="Silence timeout to detect end-of-speech")
    language: Optional[str] = Field(None, description="Spoken language code or None for auto-detection")
    room_id: str = Field("living_room", description="Physical location of audio device")
    incident_id: Optional[str] = Field(None, description="Correlated incident ID if triggered by an alert")
