"""
Database Models for Aegis Ambient Care Backend.
Amazon Developer Hackathon 2026.
SQLAlchemy 2.0 ORM Models for PostgreSQL / SQLite.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    """Senior patient profile and baseline parameters."""
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)  # e.g., "user_eleanor_vance"
    patient_id = Column(String(32), unique=True, index=True, default="PT-84920")
    name = Column(String(128), nullable=False, default="Eleanor Vance")
    age = Column(Integer, default=79)
    residence_address = Column(String(256), default="Residence Unit 4B - Beacon Hill, Boston MA")
    emergency_contact = Column(String(128), default="Sarah Vance (Daughter) - +1-555-019-2834")
    dnr_order = Column(Boolean, default=False)
    
    medical_history = Column(JSON, default=lambda: [
        "Mild cognitive impairment (early stage)",
        "Hypertension (managed with Lisinopril)",
        "Documented history of slip & fall in bathroom (Jan 2026)",
        "Penicillin allergy (Anaphylaxis risk)"
    ])
    baseline_parameters = Column(JSON, default=lambda: {
        "resting_heart_rate_bpm": 72,
        "average_sleep_start_hour": 23,
        "average_wake_hour": 7,
        "normal_gait_velocity_mps": 0.95
    })
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    incidents = relationship("IncidentModel", back_populates="user", cascade="all, delete-orphan")


class IncidentModel(Base):
    """Recorded safety incident or ambient anomaly."""
    __tablename__ = "incidents"

    id = Column(String(64), primary_key=True, index=True)  # e.g., "INC-20261017-A1B2"
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)        # "possible_fall", "loud_thud", etc.
    confidence = Column(Float, nullable=False)
    location = Column(String(64), nullable=False)          # "bathroom", "living_room", etc.
    movement_after_event = Column(String(32), default="none")
    
    initial_risk_level = Column(String(32), nullable=False)  # "LOW", "MODERATE", "HIGH", "CRITICAL"
    current_risk_level = Column(String(32), nullable=False)
    risk_confidence = Column(Float, default=0.90)
    risk_reasons = Column(JSON, default=list)

    status = Column(String(32), default="ACTIVE", index=True)  # "ACTIVE", "RESOLVED", "ESCALATED_CAREGIVER", "ESCALATED_CAD"
    workflow_state = Column(String(64), default="DETECTED", index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    idempotency_key = Column(String(128), nullable=True, index=True)
    recommended_action = Column(String(128), nullable=True)
    
    context_snapshot = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel", back_populates="incidents")
    timeline = relationship("IncidentTimelineModel", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentTimelineModel.timestamp")
    emergency_packet = relationship("EmergencyPacketModel", back_populates="incident", uselist=False, cascade="all, delete-orphan")


class IncidentTimelineModel(Base):
    """Chronological event log for an incident."""
    __tablename__ = "incident_timelines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, index=True)
    action_type = Column(String(64), nullable=False)  # "VISION_EVENT_INGESTED", "STATE_TRANSITION", etc.
    actor = Column(String(64), default="AEGIS_SYSTEM")  # "VISION_AI", "ALEXA_VOICE_AGENT", "PATIENT", etc.
    previous_state = Column(String(64), nullable=True)
    new_state = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    evidence = Column(JSON, default=dict)
    correlation_id = Column(String(64), nullable=True, index=True)
    description = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)

    # Relationships
    incident = relationship("IncidentModel", back_populates="timeline")


class EmergencyPacketModel(Base):
    """Compiled CAD-ready summary packet for critical incidents."""
    __tablename__ = "emergency_packets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(64), ForeignKey("incidents.id"), unique=True, nullable=False, index=True)
    packet_id = Column(String(64), unique=True, nullable=False, index=True)  # e.g., "EPK-84920-F1"
    triage_priority = Column(String(32), default="DELTA_CRITICAL")
    formatted_summary = Column(Text, nullable=False)
    packet_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    incident = relationship("IncidentModel", back_populates="emergency_packet")


class TelemetryEventModel(Base):
    """
    Persistent log for the NIRA Unified Multimodal Event Pipeline.
    Records every incoming sensor, radar, vision, wearable, and conversational event.
    """
    __tablename__ = "telemetry_events"

    id = Column(String(64), primary_key=True, index=True)  # event_id
    correlation_id = Column(String(64), nullable=False, index=True)
    resident_id = Column(String(64), nullable=False, index=True)
    room_id = Column(String(64), nullable=False, index=True)
    source = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    confidence = Column(Float, default=1.0)
    payload_json = Column(JSON, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    safety_state_after = Column(String(32), default="NORMAL")
    evidence_summary = Column(JSON, default=list)


class MedicationModel(Base):
    """Prescription schedule and daily adherence tracking."""
    __tablename__ = "medications"

    id = Column(String(64), primary_key=True, index=True)
    resident_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    medication_name = Column(String(128), nullable=False)
    dosage = Column(String(64), nullable=False)
    scheduled_time = Column(String(32), nullable=False)  # e.g., "08:00", "13:00", "18:00"
    instructions = Column(String(256), nullable=True)
    status = Column(String(32), default="SCHEDULED")  # SCHEDULED, TAKEN, MISSED, DELAYED
    taken_at = Column(DateTime(timezone=True), nullable=True)
    delay_minutes = Column(Integer, default=0)
    adherence_rate = Column(Float, default=1.0)
    caregiver_alerted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class NotificationModel(Base):
    """Caregiver and first responder notification audit logs."""
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True, index=True)
    recipient = Column(String(128), nullable=False)
    channel = Column(String(32), nullable=False)  # "SMS", "PUSH", "ECHO_DROP_IN"
    headline = Column(String(256), nullable=False)
    body = Column(Text, nullable=False)
    priority = Column(String(32), default="STANDARD")  # "STANDARD", "HIGH", "CRITICAL"
    status = Column(String(32), default="SENT")  # "SENT", "ACKNOWLEDGED", "TIMEOUT", "ESCALATED"
    is_simulation = Column(Boolean, default=True)
    incident_id = Column(String(64), nullable=True, index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    sent_at = Column(DateTime(timezone=True), default=utc_now)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

