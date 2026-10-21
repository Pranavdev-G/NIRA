"""
Incidents and Event Orchestration REST API.
Amazon Developer Hackathon 2026.

Endpoints:
  - POST /api/v1/events: Ingests vision/sensor events, creates/deduplicates Incident, runs Risk Assessment, and logs timeline.
  - GET  /api/v1/incidents/active: Active incidents feed for React dashboard.
  - GET  /api/v1/incidents/{id}/timeline: Full chronological audit trail.
  - POST /api/v1/incidents/{id}/escalate: Triggers caregiver or emergency CAD dispatch via simulated adapters.
  - POST /api/v1/incidents/{id}/respond-voice: Conversational verification hook (Scenarios A, B, C, D, E).
  - POST /api/v1/incidents/{id}/acknowledge: Caregiver acknowledgement hook (Scenario G).
  - POST /api/v1/incidents/{id}/sensor-update: Sensor evidence worsening hook (Scenario F).
  - POST /api/v1/incidents/{id}/caregiver-timeout: Caregiver non-acknowledgement timeout hook (Scenario H).
  - POST /api/v1/incidents/{id}/resolve: Explicit incident resolution hook (Scenario I).
  - POST /api/v1/incidents/{id}/false-alarm: Multimodal false alarm resolution hook (Scenario J).
  - GET  /api/v1/incidents/{id}/packet: Dynamically generated CAD Emergency Packet.
"""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import UserModel, IncidentModel, IncidentTimelineModel, EmergencyPacketModel
from app.models.schemas import Event, Context, VoiceResponse, RiskAssessmentResponse, Risk, EscalateEmergencyRequest
from app.models.enums import RiskLevel
from app.models.event_contracts import UnifiedEvent
from app.services.aegis_risk_engine import AegisRiskEngine
from app.services.caregiver_service import CaregiverService
from app.services.emergency_service import EmergencyService
from app.services.event_pipeline import global_pipeline
from app.services.emergency_workflow import EmergencyWorkflowEngine, EmergencyWorkflowState


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
    workflow_state: Optional[str] = "DETECTED"
    correlation_id: Optional[str] = None
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
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    reason: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    description: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class EscalateIncidentRequest(BaseModel):
    escalation_type: str = Field("caregiver", description="'caregiver' or 'emergency'")
    reason: Optional[str] = None
    custom_message: Optional[str] = None


class VoiceReplyIncidentRequest(BaseModel):
    transcript: Optional[str] = None
    is_timeout: bool = False


class CaregiverAckRequest(BaseModel):
    caregiver_actor: str = "Sarah Vance (Caregiver)"
    notes: str = "Caregiver acknowledged alert and assumed triage responsibility."


class SensorUpdateRequest(BaseModel):
    evidence: Dict[str, Any] = Field(default_factory=dict)
    reason: str = "Sensor evidence worsened during wellness check"


class ResolveIncidentRequest(BaseModel):
    actor: str = "AEGIS_SYSTEM"
    reason: str = "Incident resolved"
    evidence: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.post("/events", response_model=EventIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_event(
    payload: EventIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests event JSON from vision detector or simulators.
    Enforces idempotency and active incident deduplication.
    Evaluates risk and initializes emergency workflow.
    """
    now = datetime.now(timezone.utc)

    # Verify user exists or fallback
    user = db.query(UserModel).filter(UserModel.id == payload.user_id).first()
    if not user:
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

    # 1. Evaluate Initial Multimodal Risk
    risk_eval = AegisRiskEngine.evaluate(payload.event, context, voice_response=None)

    # 2. Idempotent Incident Creation / Deduplication
    corr_id = f"CORR-{uuid.uuid4().hex[:8].upper()}"
    incident, is_new = EmergencyWorkflowEngine.get_or_create_incident(
        db=db,
        resident_id=user_id,
        location=payload.event.location,
        event_type=payload.event.event_type,
        confidence=payload.event.confidence,
        initial_risk_level=risk_eval.risk_level,
        risk_confidence=risk_eval.confidence,
        risk_reasons=risk_eval.reasons,
        recommended_action=risk_eval.recommended_action,
        context_snapshot=context.model_dump(),
        movement_after_event=payload.event.movement_after_event,
        correlation_id=corr_id
    )

    # 3. Add Initial Timeline Entries
    t1 = IncidentTimelineModel(
        incident_id=incident.id,
        timestamp=now,
        action_type="VISION_EVENT_INGESTED",
        actor="VISION_AI",
        previous_state="NONE",
        new_state=incident.workflow_state or "DETECTED",
        reason=f"Detected {payload.event.event_type} in {payload.event.location} with {payload.event.confidence:.0%} confidence.",
        evidence=payload.event.model_dump(),
        correlation_id=incident.correlation_id or incident.id,
        description=f"Detected {payload.event.event_type} in {payload.event.location} with {payload.event.confidence:.0%} confidence. Post-event movement: {payload.event.movement_after_event}.",
        metadata_json=payload.event.model_dump()
    )
    db.add(t1)

    t2 = IncidentTimelineModel(
        incident_id=incident.id,
        timestamp=now,
        action_type="RISK_ASSESSED",
        actor="AEGIS_RISK_ENGINE",
        previous_state=incident.workflow_state or "DETECTED",
        new_state=incident.workflow_state or "DETECTED",
        reason=f"Assessed risk as {risk_eval.risk_level} (confidence {risk_eval.confidence:.0%}).",
        evidence=risk_eval.model_dump(),
        correlation_id=incident.correlation_id or incident.id,
        description=f"Assessed risk as {risk_eval.risk_level} (confidence {risk_eval.confidence:.0%}). Recommended action: {risk_eval.recommended_action}.",
        metadata_json=risk_eval.model_dump()
    )
    db.add(t2)

    if is_new and risk_eval.requires_wellness_check:
        t3 = IncidentTimelineModel(
            incident_id=incident.id,
            timestamp=now,
            action_type="WELLNESS_CHECK_INITIATED",
            actor="ALEXA_VOICE_AGENT",
            previous_state=incident.workflow_state or "DETECTED",
            new_state=EmergencyWorkflowState.WELLNESS_CHECK.value,
            reason=f"Initiated Alexa+ ambient wellness check for {user.name if user else 'senior'}.",
            evidence={"room": payload.event.location, "timeout_seconds": 20},
            correlation_id=incident.correlation_id or incident.id,
            description=f"Initiated Alexa+ ambient wellness check for {user.name if user else 'senior'}.",
            metadata_json={"room": payload.event.location, "timeout_seconds": 20}
        )
        db.add(t3)

        # Transition workflow to WELLNESS_CHECK and WAITING_FOR_RESPONSE
        EmergencyWorkflowEngine.transition(
            db=db,
            incident_id=incident.id,
            target_state=EmergencyWorkflowState.WELLNESS_CHECK,
            reason="Wellness check initiated for conversational verification.",
            evidence={"prompt": "Are you okay?", "room": payload.event.location},
            actor="ALEXA_VOICE_AGENT"
        )
        EmergencyWorkflowEngine.transition(
            db=db,
            incident_id=incident.id,
            target_state=EmergencyWorkflowState.WAITING_FOR_RESPONSE,
            reason="Listening for senior response or timeout window.",
            evidence={"timeout_seconds": 20},
            actor="ALEXA_VOICE_AGENT"
        )

    db.commit()
    db.refresh(incident)

    # Synchronize with real-time multimodal event pipeline for live SSE broadcasting
    try:
        norm_event = UnifiedEvent(
            event_id=f"evt-{incident.id}",
            timestamp=incident.created_at.isoformat(),
            resident_id=incident.user_id,
            room_id=incident.location,
            source="camera_pose",
            event_type=incident.event_type,
            payload={
                "movement_after_event": incident.movement_after_event,
                "confidence": incident.confidence,
                "risk_level": risk_eval.risk_level,
                "reasons": risk_eval.reasons
            },
            confidence=incident.confidence,
            correlation_id=incident.correlation_id or incident.id
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(global_pipeline.ingest_event(norm_event, db=None))
        except RuntimeError:
            pass
    except Exception:
        pass

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
    Returns current active incidents for the React safety dashboard.
    """
    incidents = (
        db.query(IncidentModel)
        .filter(IncidentModel.status.in_(["ACTIVE", "ESCALATED_CAREGIVER", "ESCALATED_CAD"]))
        .order_by(IncidentModel.updated_at.desc(), IncidentModel.created_at.desc())
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
            workflow_state=inc.workflow_state or "DETECTED",
            correlation_id=inc.correlation_id,
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
    Returns full chronological timeline for an incident with all transition audit fields.
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
            previous_state=getattr(item, "previous_state", None),
            new_state=getattr(item, "new_state", None),
            reason=getattr(item, "reason", None),
            evidence=getattr(item, "evidence", None),
            correlation_id=getattr(item, "correlation_id", None),
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
    Updates incident status, generates emergency packet dynamically, and logs timeline.
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
        # Generate CAD Emergency Packet dynamically from actual incident state
        packet = EmergencyService.generate_packet_from_incident(incident_id=incident_id, db=db)

        # Persist Emergency Packet
        existing_pkt = db.query(EmergencyPacketModel).filter(EmergencyPacketModel.incident_id == incident_id).first()
        if not existing_pkt:
            packet_model = EmergencyPacketModel(
                incident_id=incident_id,
                packet_id=packet.packet_id,
                triage_priority=packet.triage_priority,
                formatted_summary=packet.formatted_ems_summary,
                packet_json=packet.model_dump(),
                created_at=now
            )
            db.add(packet_model)
        else:
            existing_pkt.formatted_summary = packet.formatted_ems_summary
            existing_pkt.packet_json = packet.model_dump()

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
        incident.workflow_state = EmergencyWorkflowState.DISPATCH_READY.value
        incident.current_risk_level = RiskLevel.CRITICAL.value
        incident.updated_at = now

        # Add Timeline Log
        t = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="CAD_DISPATCHED",
            actor="EMS_CAD",
            previous_state=EmergencyWorkflowState.EMERGENCY_ESCALATION.value,
            new_state=EmergencyWorkflowState.DISPATCH_READY.value,
            reason=f"Direct 911 CAD emergency escalation dispatched to EMS-CAD-MA-02108. Dispatch ID: {cad_resp.dispatch_id}. Units: {', '.join(cad_resp.units_dispatched)}.",
            evidence={"dispatch_id": cad_resp.dispatch_id, "units": cad_resp.units_dispatched},
            correlation_id=incident.correlation_id or incident.id,
            description=f"Direct 911 CAD emergency escalation dispatched to EMS-CAD-MA-02108. Dispatch ID: {cad_resp.dispatch_id}. Units: {', '.join(cad_resp.units_dispatched)}.",
            metadata_json=cad_resp.model_dump()
        )
        db.add(t)
        db.commit()

        return {
            "incident_id": incident_id,
            "escalation_type": "emergency_cad",
            "status": incident.status,
            "workflow_state": incident.workflow_state,
            "dispatch_id": cad_resp.dispatch_id,
            "emergency_packet_id": packet.packet_id,
            "units_dispatched": cad_resp.units_dispatched,
            "door_lock_unlocked": cad_resp.door_lock_unlocked,
            "smart_lock_pin": cad_resp.smart_lock_pin,
            "integration_type": cad_resp.integration_type,
            "disclaimer": cad_resp.disclaimer,
            "timestamp": now_iso
        }

    else:
        # Caregiver multi-channel notification via simulated adapters
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
        incident.workflow_state = EmergencyWorkflowState.CAREGIVER_ESCALATION.value
        incident.updated_at = now

        t = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="CAREGIVER_NOTIFIED",
            actor="CAREGIVER_HUB",
            previous_state=incident.workflow_state or EmergencyWorkflowState.WAITING_FOR_RESPONSE.value,
            new_state=EmergencyWorkflowState.CAREGIVER_ESCALATION.value,
            reason=f"Caregiver notified across {len(care_resp.channels_delivered)} channels (Alexa Drop-In, Push, SMS). Notification ID: {care_resp.notification_id}.",
            evidence={"notification_id": care_resp.notification_id, "channels": [c.channel for c in care_resp.channels_delivered]},
            correlation_id=incident.correlation_id or incident.id,
            description=f"Caregiver notified across {len(care_resp.channels_delivered)} channels (Alexa Drop-In, Push, SMS). Notification ID: {care_resp.notification_id}.",
            metadata_json=care_resp.model_dump()
        )
        db.add(t)
        db.commit()

        return {
            "incident_id": incident_id,
            "escalation_type": "caregiver",
            "status": incident.status,
            "workflow_state": incident.workflow_state,
            "notification_id": care_resp.notification_id,
            "channels_delivered": [c.model_dump() for c in care_resp.channels_delivered],
            "integration_type": care_resp.integration_type,
            "disclaimer": care_resp.disclaimer,
            "timestamp": now_iso
        }


@router.post("/incidents/{incident_id}/respond-voice")
async def respond_voice_incident(
    incident_id: str,
    payload: VoiceReplyIncidentRequest,
    db: Session = Depends(get_db)
):
    """
    Conversational verification hook supporting Scenarios A through E:
      - A: Safe verbal confirmation ("I'm okay") -> RESOLVED
      - B: Distress / Help ("Help me") -> CAREGIVER_ESCALATION
      - C: Physical incapacitation ("I cannot move") -> EMERGENCY_ESCALATION -> DISPATCH_READY
      - D: Silent timeout (No response) -> EMERGENCY_ESCALATION -> DISPATCH_READY
      - E: Ambiguous verbal reply -> CAREGIVER_ESCALATION
    """
    incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    result = await EmergencyWorkflowEngine.handle_voice_interaction(
        db=db,
        incident_id=incident_id,
        transcript=payload.transcript,
        is_timeout=payload.is_timeout
    )
    return result


@router.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident(
    incident_id: str,
    payload: Optional[CaregiverAckRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Caregiver acknowledgement hook (Scenario G).
    Stops automated escalations and marks caregiver acknowledgement.
    """
    req = payload or CaregiverAckRequest()
    return EmergencyWorkflowEngine.handle_caregiver_acknowledgement(
        db=db,
        incident_id=incident_id,
        caregiver_actor=req.caregiver_actor,
        notes=req.notes
    )


@router.post("/incidents/{incident_id}/sensor-update")
async def update_sensor_evidence(
    incident_id: str,
    payload: SensorUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Sensor evidence worsening hook during wellness check (Scenario F).
    Bypasses remaining timeout and triggers immediate emergency CAD escalation.
    """
    return await EmergencyWorkflowEngine.handle_sensor_worsening(
        db=db,
        incident_id=incident_id,
        worsening_evidence=payload.evidence
    )


@router.post("/incidents/{incident_id}/caregiver-timeout")
async def timeout_caregiver(
    incident_id: str,
    timeout_seconds: int = 120,
    db: Session = Depends(get_db)
):
    """
    Caregiver non-acknowledgement timeout hook (Scenario H).
    Auto-escalates from CAREGIVER_ESCALATION to EMERGENCY_ESCALATION -> DISPATCH_READY.
    """
    return await EmergencyWorkflowEngine.handle_caregiver_timeout(
        db=db,
        incident_id=incident_id,
        timeout_seconds=timeout_seconds
    )


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident(
    incident_id: str,
    payload: Optional[ResolveIncidentRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Explicit incident resolution hook (Scenario I).
    """
    req = payload or ResolveIncidentRequest()
    return EmergencyWorkflowEngine.handle_resolution(
        db=db,
        incident_id=incident_id,
        actor=req.actor,
        reason=req.reason,
        evidence=req.evidence
    )


@router.post("/incidents/{incident_id}/false-alarm")
def false_alarm_incident(
    incident_id: str,
    reason: str = "Resident upright and normal gait velocity restored",
    evidence: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Multimodal false alarm resolution hook (Scenario J).
    """
    return EmergencyWorkflowEngine.handle_false_alarm(
        db=db,
        incident_id=incident_id,
        reason=reason,
        evidence=evidence
    )


@router.get("/incidents/{incident_id}/packet")
def get_incident_packet(
    incident_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns the CAD Emergency Packet dynamically compiled from actual incident state.
    """
    incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    packet = EmergencyService.generate_packet_from_incident(incident_id=incident_id, db=db)
    return packet.model_dump()
