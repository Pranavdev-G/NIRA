"""
Incidents and Event Orchestration REST API.
Amazon Developer Hackathon 2026.

Endpoints:
  - POST /api/v1/events: Ingests vision/sensor events, creates Incident, runs Risk Assessment, and logs timeline.
  - GET  /api/v1/incidents/active: Active incidents feed for React dashboard (Leela).
  - GET  /api/v1/incidents/{id}/timeline: Full chronological audit trail.
  - POST /api/v1/incidents/{id}/escalate: Triggers caregiver or emergency CAD dispatch.
  - POST /api/v1/incidents/{id}/respond-voice: Conversational verification hook.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import UserModel, IncidentModel, IncidentTimelineModel, EmergencyPacketModel
from app.models.schemas import Event, Context, VoiceResponse, RiskAssessmentResponse, Risk, EscalateEmergencyRequest
from app.models.enums import RiskLevel
from app.services.aegis_risk_engine import AegisRiskEngine
from app.services.caregiver_service import CaregiverService
from app.services.emergency_service import EmergencyService


router = APIRouter(prefix="/api/v1", tags=["Incidents & Telemetry Ingestion"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class EventIngestRequest(BaseModel):
    event: Event
    context: Optional[Context] = None
    user_id: str = "user_eleanor_vance"


class EventIngestResponse(BaseModel):
    incident_id: str
    event_type: str
    location: str
    status: str
    risk_assessment: RiskAssessmentResponse
    created_at: str


class IncidentSummaryResponse(BaseModel):
    id: str
    user_id: str
    event_type: str
    confidence: float
    location: str
    movement_after_event: str
    initial_risk_level: str
    current_risk_level: str
    status: str
    risk_reasons: List[str]
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None


class TimelineItemResponse(BaseModel):
    id: int
    incident_id: str
    timestamp: str
    action_type: str
    actor: str
    description: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class EscalateIncidentRequest(BaseModel):
    escalation_type: str = Field("caregiver", description="'caregiver' or 'emergency'")
    reason: Optional[str] = None
    custom_message: Optional[str] = None


class VoiceReplyIncidentRequest(BaseModel):
    transcript: Optional[str] = None
    is_timeout: bool = False


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.post("/events", response_model=EventIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_event(
    payload: EventIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests event JSON from vision detector (Nandana) or simulators.
    Creates Incident in database, runs AegisRiskEngine, and writes initial timeline logs.
    """
    now = datetime.now(timezone.utc)
    incident_id = f"INC-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # Verify user exists or fallback
    user = db.query(UserModel).filter(UserModel.id == payload.user_id).first()
    if not user:
        # Fallback to default user
        user = db.query(UserModel).first()
        user_id = user.id if user else "user_eleanor_vance"
    else:
        user_id = user.id

    # Fallback default context if omitted
    context = payload.context or Context(
        activity="unknown",
        time_context="afternoon",
        baseline_deviation=0.50,
        wearable_status="worn_normal",
        environment="well_lit"
    )

    # 1. Evaluate Initial Multimodal Risk (Dharaneesh)
    risk_eval = AegisRiskEngine.evaluate(payload.event, context, voice_response=None)

    # 2. Persist Incident
    incident = IncidentModel(
        id=incident_id,
        user_id=user_id,
        event_type=payload.event.event_type,
        confidence=payload.event.confidence,
        location=payload.event.location,
        movement_after_event=payload.event.movement_after_event,
        initial_risk_level=risk_eval.risk_level,
        current_risk_level=risk_eval.risk_level,
        risk_confidence=risk_eval.confidence,
        risk_reasons=risk_eval.reasons,
        status="ACTIVE",
        recommended_action=risk_eval.recommended_action,
        context_snapshot=context.model_dump(),
        created_at=now,
        updated_at=now
    )
    db.add(incident)

    # 3. Add Initial Timeline Entries
    t1 = IncidentTimelineModel(
        incident_id=incident_id,
        timestamp=now,
        action_type="VISION_EVENT_INGESTED",
        actor="VISION_AI",
        description=f"Detected {payload.event.event_type} in {payload.event.location} with {payload.event.confidence:.0%} confidence. Post-event movement: {payload.event.movement_after_event}.",
        metadata_json=payload.event.model_dump()
    )
    db.add(t1)

    t2 = IncidentTimelineModel(
        incident_id=incident_id,
        timestamp=now,
        action_type="RISK_ASSESSED",
        actor="AEGIS_RISK_ENGINE",
        description=f"Assessed risk as {risk_eval.risk_level} (confidence {risk_eval.confidence:.0%}). Recommended action: {risk_eval.recommended_action}.",
        metadata_json=risk_eval.model_dump()
    )
    db.add(t2)

    if risk_eval.requires_wellness_check:
        t3 = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="WELLNESS_CHECK_INITIATED",
            actor="ALEXA_VOICE_AGENT",
            description=f"Initiated Alexa+ ambient wellness check for {user.name if user else 'senior'}.",
            metadata_json={"room": payload.event.location, "timeout_seconds": 20}
        )
        db.add(t3)

    db.commit()
    db.refresh(incident)

    return EventIngestResponse(
        incident_id=incident.id,
        event_type=incident.event_type,
        location=incident.location,
        status=incident.status,
        risk_assessment=risk_eval,
        created_at=incident.created_at.isoformat()
    )


@router.get("/incidents/active", response_model=List[IncidentSummaryResponse])
def get_active_incidents(db: Session = Depends(get_db)):
    """
    Returns current active incidents for the React safety dashboard (Leela).
    """
    incidents = (
        db.query(IncidentModel)
        .filter(IncidentModel.status.in_(["ACTIVE", "ESCALATED_CAREGIVER", "ESCALATED_CAD"]))
        .order_by(IncidentModel.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        IncidentSummaryResponse(
            id=inc.id,
            user_id=inc.user_id,
            event_type=inc.event_type,
            confidence=inc.confidence,
            location=inc.location,
            movement_after_event=inc.movement_after_event,
            initial_risk_level=inc.initial_risk_level,
            current_risk_level=inc.current_risk_level,
            status=inc.status,
            risk_reasons=inc.risk_reasons or [],
            created_at=inc.created_at.isoformat(),
            updated_at=inc.updated_at.isoformat(),
            resolved_at=inc.resolved_at.isoformat() if inc.resolved_at else None
        )
        for inc in incidents
    ]


@router.get("/incidents/{incident_id}/timeline", response_model=List[TimelineItemResponse])
def get_incident_timeline(incident_id: str, db: Session = Depends(get_db)):
    """
    Returns full chronological timeline for an incident.
    """
    incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    timeline_items = (
        db.query(IncidentTimelineModel)
        .filter(IncidentTimelineModel.incident_id == incident_id)
        .order_by(IncidentTimelineModel.timestamp.asc())
        .all()
    )

    return [
        TimelineItemResponse(
            id=item.id,
            incident_id=item.incident_id,
            timestamp=item.timestamp.isoformat(),
            action_type=item.action_type,
            actor=item.actor,
            description=item.description,
            metadata_json=item.metadata_json or {}
        )
        for item in timeline_items
    ]


@router.post("/incidents/{incident_id}/escalate")
async def escalate_incident(
    incident_id: str,
    payload: EscalateIncidentRequest,
    db: Session = Depends(get_db)
):
    """
    Triggers simulated caregiver or emergency CAD notifications.
    Updates incident status, generates emergency packet if critical, and logs timeline.
    """
    incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    event = Event(
        event_type=incident.event_type,
        confidence=incident.confidence,
        location=incident.location,
        timestamp=now_iso,
        movement_after_event=incident.movement_after_event
    )
    context_dict = incident.context_snapshot or {}
    context = Context(
        activity=context_dict.get("activity", "resting"),
        time_context=context_dict.get("time_context", "afternoon"),
        baseline_deviation=float(context_dict.get("baseline_deviation", 0.8)),
        wearable_status=context_dict.get("wearable_status", "worn_normal"),
        environment=context_dict.get("environment", "well_lit")
    )
    risk = Risk(
        risk_level=incident.current_risk_level,
        confidence=incident.risk_confidence,
        reasons=incident.risk_reasons or []
    )

    if payload.escalation_type.lower() == "emergency":
        # Generate CAD Emergency Packet
        packet = EmergencyService.generate_packet(event, context, risk, patient_id="PT-84920")

        # Persist Emergency Packet
        packet_model = EmergencyPacketModel(
            incident_id=incident_id,
            packet_id=packet.packet_id,
            triage_priority=packet.triage_priority,
            formatted_summary=packet.formatted_ems_summary,
            packet_json=packet.model_dump(),
            created_at=now
        )
        db.add(packet_model)

        # Escalate to simulated CAD
        cad_resp = await EmergencyService.escalate_to_cad(
            EscalateEmergencyRequest(
                emergency_packet=packet,
                event=event,
                context=context,
                risk=risk,
                cad_agency_code="EMS-CAD-MA-02108"
            )
        )

        incident.status = "ESCALATED_CAD"
        incident.current_risk_level = RiskLevel.CRITICAL.value
        incident.updated_at = now

        # Add Timeline Log
        t = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="CAD_DISPATCHED",
            actor="EMS_CAD",
            description=f"Direct 911 CAD emergency escalation dispatched to EMS-CAD-MA-02108. Dispatch ID: {cad_resp.dispatch_id}. Units: {', '.join(cad_resp.units_dispatched)}.",
            metadata_json=cad_resp.model_dump()
        )
        db.add(t)
        db.commit()

        return {
            "incident_id": incident_id,
            "escalation_type": "emergency_cad",
            "status": incident.status,
            "dispatch_id": cad_resp.dispatch_id,
            "emergency_packet_id": packet.packet_id,
            "units_dispatched": cad_resp.units_dispatched,
            "door_lock_unlocked": cad_resp.door_lock_unlocked,
            "timestamp": now_iso
        }

    else:
        # Caregiver multi-channel notification
        from app.models.schemas import NotifyCaregiverRequest
        care_resp = await CaregiverService.dispatch_notification(
            NotifyCaregiverRequest(
                risk=risk,
                event=event,
                context=context,
                custom_message=payload.custom_message
            )
        )

        incident.status = "ESCALATED_CAREGIVER"
        incident.updated_at = now

        t = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="CAREGIVER_NOTIFIED",
            actor="CAREGIVER_HUB",
            description=f"Caregiver notified across {len(care_resp.channels_delivered)} channels (Alexa Drop-In, Push, SMS). Notification ID: {care_resp.notification_id}.",
            metadata_json=care_resp.model_dump()
        )
        db.add(t)
        db.commit()

        return {
            "incident_id": incident_id,
            "escalation_type": "caregiver",
            "status": incident.status,
            "notification_id": care_resp.notification_id,
            "channels_delivered": [c.model_dump() for c in care_resp.channels_delivered],
            "timestamp": now_iso
        }


@router.post("/incidents/{incident_id}/respond-voice")
async def respond_voice_incident(
    incident_id: str,
    payload: VoiceReplyIncidentRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests Alexa+ senior voice interaction and transitions incident state:
      - Safe response ('I am okay') -> Downgrades risk to LOW, marks incident RESOLVED.
      - Distress response ('Help me') -> Elevates to HIGH, auto-triggers caregiver alert.
      - Timeout/Silence -> Elevates to CRITICAL, auto-triggers CAD 911 dispatch.
    """
    incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    now = datetime.now(timezone.utc)
    event = Event(
        event_type=incident.event_type,
        confidence=incident.confidence,
        location=incident.location,
        timestamp=now.isoformat(),
        movement_after_event=incident.movement_after_event
    )
    context_dict = incident.context_snapshot or {}
    context = Context(
        activity=context_dict.get("activity", "resting"),
        time_context=context_dict.get("time_context", "afternoon"),
        baseline_deviation=float(context_dict.get("baseline_deviation", 0.5)),
        wearable_status=context_dict.get("wearable_status", "worn_normal"),
        environment=context_dict.get("environment", "well_lit")
    )
    voice_resp = VoiceResponse(transcript=payload.transcript, is_timeout=payload.is_timeout)

    # Reassess risk using AegisRiskEngine
    reassessment = AegisRiskEngine.evaluate(event, context, voice_response=voice_resp)

    # Update incident model
    incident.current_risk_level = reassessment.risk_level
    incident.risk_confidence = reassessment.confidence
    incident.risk_reasons = reassessment.reasons
    incident.recommended_action = reassessment.recommended_action
    incident.updated_at = now

    # Log voice interaction
    t_voice = IncidentTimelineModel(
        incident_id=incident_id,
        timestamp=now,
        action_type="VOICE_RESPONSE_RECEIVED",
        actor="PATIENT",
        description=f"Received voice reply: \"{payload.transcript}\"" if not payload.is_timeout else "No voice response received during prompt window (TIMEOUT).",
        metadata_json={"transcript": payload.transcript, "is_timeout": payload.is_timeout, "risk_level": reassessment.risk_level}
    )
    db.add(t_voice)

    # Handle transitions
    if reassessment.risk_level == RiskLevel.LOW.value:
        # False alarm / safe resolution
        incident.status = "RESOLVED"
        incident.resolved_at = now
        t_resolve = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="RESOLVED_SAFE",
            actor="AEGIS_SYSTEM",
            description="Senior verbally confirmed safety. Incident resolved and passive monitoring resumed.",
            metadata_json={"resolved_at": now.isoformat()}
        )
        db.add(t_resolve)
        db.commit()

        return {
            "incident_id": incident_id,
            "status": incident.status,
            "risk_level": incident.current_risk_level,
            "action_taken": "RESOLVED_SAFE_CANCELLED",
            "voice_intent": "safe"
        }

    elif payload.is_timeout:
        # Silent emergency -> Auto escalate CAD
        db.commit()  # Save voice log
        cad_result = await escalate_incident(
            incident_id=incident_id,
            payload=EscalateIncidentRequest(escalation_type="emergency", reason="Silent emergency - no response received"),
            db=db
        )
        return {
            "incident_id": incident_id,
            "status": "ESCALATED_CAD",
            "risk_level": RiskLevel.CRITICAL.value,
            "action_taken": "SILENT_EMERGENCY_CAD_DISPATCH",
            "cad_details": cad_result
        }

    else:
        # Distress -> Auto escalate caregiver
        db.commit()
        care_result = await escalate_incident(
            incident_id=incident_id,
            payload=EscalateIncidentRequest(escalation_type="caregiver", custom_message=f"Senior called for help: \"{payload.transcript}\""),
            db=db
        )
        return {
            "incident_id": incident_id,
            "status": "ESCALATED_CAREGIVER",
            "risk_level": reassessment.risk_level,
            "action_taken": "DISTRESS_CAREGIVER_ALERTED",
            "caregiver_details": care_result
        }
