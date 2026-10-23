"""
NIRA Authoritative Safety Core.
Amazon Developer Hackathon 2026.

Central safety engine, multimodal risk intelligence, incident lifecycle management,
and deterministic emergency state machine for NIRA Live.
"""

from Live.core.models import (
    LiveEvent,
    EventType,
    EventSource,
    ZoneType,
    SafetyState,
    SeverityLevel,
    RiskAssessment,
    SignalEvidence,
    ContextState,
    IncidentRecord,
    TimelineEntry,
    EmergencyPacket,
)
from Live.core.core_service import CoreService, get_live_core

__all__ = [
    "LiveEvent",
    "EventType",
    "EventSource",
    "ZoneType",
    "SafetyState",
    "SeverityLevel",
    "RiskAssessment",
    "SignalEvidence",
    "ContextState",
    "IncidentRecord",
    "TimelineEntry",
    "EmergencyPacket",
    "CoreService",
    "get_live_core",
]
