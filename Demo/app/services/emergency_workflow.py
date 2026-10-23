"""
Stateful Emergency Workflow Orchestration Engine.
Amazon Developer Hackathon 2026.

Workflow States:
  DETECTED
  → VERIFYING
  → WELLNESS_CHECK
  → WAITING_FOR_RESPONSE
  → RESPONSIVE
  → CAREGIVER_ESCALATION
  → EMERGENCY_ESCALATION
  → DISPATCH_READY
  → RESOLVED

Supported Scenarios (A - J):
  A. Elder says "I'm okay" (Safe confirmation -> RESOLVED)
  B. Elder asks for help (Distress -> CAREGIVER_ESCALATION)
  C. Elder says they cannot move (Critical immobility -> EMERGENCY_ESCALATION -> DISPATCH_READY)
  D. Elder does not respond (Timeout/Silence -> EMERGENCY_ESCALATION -> DISPATCH_READY)
  E. Elder responds ambiguously (Uncertainty -> CAREGIVER_ESCALATION)
  F. Sensor evidence worsens during wellness check (Vital deterioration -> EMERGENCY_ESCALATION)
  G. Caregiver acknowledges (Caregiver takes responsibility)
  H. Caregiver does not acknowledge (Caregiver timeout -> EMERGENCY_ESCALATION -> DISPATCH_READY)
  I. Emergency is resolved (Resolution confirmed -> RESOLVED)
  J. Event becomes false alarm (Normal mobility restored -> RESOLVED)

Every transition persistently captures:
  - timestamp (ISO-8601 UTC)
  - previous_state
  - new_state
  - reason
  - evidence
  - actor
  - correlation_id

Enforces Idempotency & Active Incident Deduplication:
  The same emergency does not create multiple duplicate incidents accidentally.
"""

import uuid
import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.models import IncidentModel, IncidentTimelineModel, EmergencyPacketModel
from app.models.schemas import (
    Event, Context, Risk,
    NotifyCaregiverRequest, EscalateEmergencyRequest
)
from app.models.enums import RiskLevel
from app.services.emergency_service import EmergencyService
from app.services.caregiver_service import CaregiverService

logger = logging.getLogger("aegis.emergency_workflow")


class EmergencyWorkflowState(str, Enum):
    """The 9 canonical states of the NIRA Emergency Orchestration Workflow."""
    DETECTED = "DETECTED"
    VERIFYING = "VERIFYING"
    WELLNESS_CHECK = "WELLNESS_CHECK"
    WAITING_FOR_RESPONSE = "WAITING_FOR_RESPONSE"
    RESPONSIVE = "RESPONSIVE"
    CAREGIVER_ESCALATION = "CAREGIVER_ESCALATION"
    EMERGENCY_ESCALATION = "EMERGENCY_ESCALATION"
    DISPATCH_READY = "DISPATCH_READY"
    RESOLVED = "RESOLVED"


class StateTransitionRecord(BaseModel):
    """Formal audit envelope for every state transition in the emergency lifecycle."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    previous_state: str
    new_state: str
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    actor: str
    correlation_id: str


# Permitted transition graph
VALID_TRANSITIONS: Dict[EmergencyWorkflowState, List[EmergencyWorkflowState]] = {
    EmergencyWorkflowState.DETECTED: [
        EmergencyWorkflowState.VERIFYING,
        EmergencyWorkflowState.WELLNESS_CHECK,
        EmergencyWorkflowState.CAREGIVER_ESCALATION,
        EmergencyWorkflowState.EMERGENCY_ESCALATION,
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.VERIFYING: [
        EmergencyWorkflowState.WELLNESS_CHECK,
        EmergencyWorkflowState.CAREGIVER_ESCALATION,
        EmergencyWorkflowState.EMERGENCY_ESCALATION,
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.WELLNESS_CHECK: [
        EmergencyWorkflowState.WAITING_FOR_RESPONSE,
        EmergencyWorkflowState.EMERGENCY_ESCALATION,
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.WAITING_FOR_RESPONSE: [
        EmergencyWorkflowState.RESPONSIVE,
        EmergencyWorkflowState.CAREGIVER_ESCALATION,
        EmergencyWorkflowState.EMERGENCY_ESCALATION,
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.RESPONSIVE: [
        EmergencyWorkflowState.CAREGIVER_ESCALATION,
        EmergencyWorkflowState.EMERGENCY_ESCALATION,
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.CAREGIVER_ESCALATION: [
        EmergencyWorkflowState.EMERGENCY_ESCALATION,
        EmergencyWorkflowState.DISPATCH_READY,
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.EMERGENCY_ESCALATION: [
        EmergencyWorkflowState.DISPATCH_READY,
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.DISPATCH_READY: [
        EmergencyWorkflowState.RESOLVED
    ],
    EmergencyWorkflowState.RESOLVED: [
        # Terminal state; can reopen to DETECTED if a new distinct emergency occurs
        EmergencyWorkflowState.DETECTED
    ]
}


class EmergencyWorkflowEngine:
    """Stateful Emergency Workflow Manager."""

    @classmethod
    def get_or_create_incident(
        cls,
        db: Session,
        resident_id: str,
        location: str,
        event_type: str,
        confidence: float,
        initial_risk_level: str,
        risk_confidence: float,
        risk_reasons: List[str],
        recommended_action: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None,
        movement_after_event: str = "none",
        correlation_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        dedup_window_seconds: int = 10
    ) -> Tuple[IncidentModel, bool]:
        """
        Idempotent incident creation.
        Ensures the same emergency does not create multiple emergency incidents accidentally.
        
        Returns:
            (IncidentModel, is_new: bool)
        """
        now = datetime.now(timezone.utc)
        corr_id = correlation_id or f"CORR-{uuid.uuid4().hex[:8].upper()}"
        idem_key = idempotency_key or f"IDEM-{resident_id}-{location}-{event_type}-{int(now.timestamp() // 60)}"

        # 1. Check exact idempotency_key match
        if idempotency_key:
            existing_by_key = db.query(IncidentModel).filter(
                IncidentModel.idempotency_key == idempotency_key
            ).first()
            if existing_by_key:
                logger.info(f"Idempotent hit: Reusing incident {existing_by_key.id} matching key {idempotency_key}")
                return existing_by_key, False

        # 2. Check active emergency incident for same resident & location within deduplication window
        # Ongoing fall emergencies attach subsequent sensor pulses rather than creating duplicate dispatches.
        if dedup_window_seconds > 0 and (idempotency_key or event_type in ["possible_fall", "fall"]):
            window_start = now - timedelta(seconds=dedup_window_seconds)
            active_incident = (
                db.query(IncidentModel)
                .filter(
                    IncidentModel.user_id == resident_id,
                    IncidentModel.location == location,
                    IncidentModel.event_type == event_type,
                    IncidentModel.status == "ACTIVE",
                    IncidentModel.created_at >= window_start
                )
                .order_by(IncidentModel.created_at.desc())
                .first()
            )

            if active_incident:
                logger.info(f"Deduplication hit: Attaching to active incident {active_incident.id} in {location}")
                # Update with fresh telemetry evidence without creating duplicate incident
                active_incident.confidence = max(active_incident.confidence, confidence)
                active_incident.updated_at = now
                if context_snapshot:
                    merged_ctx = active_incident.context_snapshot or {}
                    merged_ctx.update(context_snapshot)
                    active_incident.context_snapshot = merged_ctx
                db.commit()
                db.refresh(active_incident)
                return active_incident, False

        # 3. Create new incident starting at DETECTED
        incident_id = f"INC-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        new_incident = IncidentModel(
            id=incident_id,
            user_id=resident_id,
            event_type=event_type,
            confidence=confidence,
            location=location,
            movement_after_event=movement_after_event,
            initial_risk_level=initial_risk_level,
            current_risk_level=initial_risk_level,
            risk_confidence=risk_confidence,
            risk_reasons=risk_reasons,
            status="ACTIVE",
            workflow_state=EmergencyWorkflowState.DETECTED.value,
            correlation_id=corr_id,
            idempotency_key=idem_key,
            recommended_action=recommended_action,
            context_snapshot=context_snapshot or {},
            created_at=now,
            updated_at=now
        )
        db.add(new_incident)

        # Record initial timeline transition
        initial_transition = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="STATE_TRANSITION_DETECTED",
            actor="AEGIS_DETECTION_PIPELINE",
            previous_state="NONE",
            new_state=EmergencyWorkflowState.DETECTED.value,
            reason=f"Incident initially detected: {event_type} in {location} with {confidence:.0%} confidence.",
            evidence={
                "event_type": event_type,
                "location": location,
                "confidence": confidence,
                "initial_risk_level": initial_risk_level,
                "reasons": risk_reasons
            },
            correlation_id=corr_id,
            description=f"Emergency state initialized to DETECTED. Trigger: {event_type} in {location}.",
            metadata_json={
                "correlation_id": corr_id,
                "idempotency_key": idem_key,
                "initial_risk_level": initial_risk_level
            }
        )
        db.add(initial_transition)
        db.commit()
        db.refresh(new_incident)

        return new_incident, True

    @classmethod
    def transition(
        cls,
        db: Session,
        incident_id: str,
        target_state: EmergencyWorkflowState,
        reason: str,
        evidence: Dict[str, Any],
        actor: str,
        correlation_id: Optional[str] = None
    ) -> IncidentModel:
        """
        Executes and records a formal state transition for an incident.
        Guarantees all 7 transition audit fields are persistently logged.
        """
        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident '{incident_id}' not found.")

        current_state_str = incident.workflow_state or EmergencyWorkflowState.DETECTED.value
        try:
            current_state = EmergencyWorkflowState(current_state_str)
        except ValueError:
            current_state = EmergencyWorkflowState.DETECTED

        now = datetime.now(timezone.utc)
        corr_id = correlation_id or incident.correlation_id or incident.id

        # Validate transition
        allowed_targets = VALID_TRANSITIONS.get(current_state, [])
        if target_state not in allowed_targets and current_state != target_state:
            logger.warning(
                f"Transition warning: {current_state.value} -> {target_state.value} "
                f"is unusual for incident {incident_id}. Forcing transition with audit note."
            )

        # Update IncidentModel state & synchronize legacy status
        previous_state_str = current_state.value
        incident.workflow_state = target_state.value
        incident.updated_at = now

        if target_state == EmergencyWorkflowState.RESOLVED:
            incident.status = "RESOLVED"
            incident.resolved_at = now
        elif target_state == EmergencyWorkflowState.CAREGIVER_ESCALATION:
            incident.status = "ESCALATED_CAREGIVER"
        elif target_state in (EmergencyWorkflowState.EMERGENCY_ESCALATION, EmergencyWorkflowState.DISPATCH_READY):
            incident.status = "ESCALATED_CAD"
            incident.current_risk_level = RiskLevel.CRITICAL.value
        else:
            incident.status = "ACTIVE"

        # Persist full transition audit record in IncidentTimelineModel
        transition_record = IncidentTimelineModel(
            incident_id=incident.id,
            timestamp=now,
            action_type=f"STATE_TRANSITION_{target_state.value}",
            actor=actor,
            previous_state=previous_state_str,
            new_state=target_state.value,
            reason=reason,
            evidence=evidence,
            correlation_id=corr_id,
            description=f"State transitioned from {previous_state_str} to {target_state.value}. Reason: {reason}",
            metadata_json={
                "previous_state": previous_state_str,
                "new_state": target_state.value,
                "reason": reason,
                "evidence": evidence,
                "actor": actor,
                "correlation_id": corr_id,
                "timestamp": now.isoformat()
            }
        )
        db.add(transition_record)
        db.commit()
        db.refresh(incident)

        # Synchronize with global pipeline and broadcast SSE
        try:
            from app.services.event_pipeline import global_pipeline
            if target_state == EmergencyWorkflowState.RESOLVED:
                global_pipeline.reset_to_normal()
            elif target_state in (EmergencyWorkflowState.EMERGENCY_ESCALATION, EmergencyWorkflowState.DISPATCH_READY):
                global_pipeline.current_state.safety_state = "CRITICAL"
                global_pipeline.current_state.risk_level = "CRITICAL"
                global_pipeline.current_state.active_incident_id = incident.id
            elif target_state == EmergencyWorkflowState.CAREGIVER_ESCALATION:
                global_pipeline.current_state.safety_state = "HIGH"
                global_pipeline.current_state.active_incident_id = incident.id
            elif target_state in (EmergencyWorkflowState.WELLNESS_CHECK, EmergencyWorkflowState.WAITING_FOR_RESPONSE):
                global_pipeline.current_state.active_incident_id = incident.id

            loop = asyncio.get_running_loop()
            loop.create_task(global_pipeline.broadcast({
                "type": "NIRA_WORKFLOW_STATE_TRANSITION",
                "incident_id": incident.id,
                "previous_state": previous_state_str,
                "new_state": target_state.value,
                "reason": reason,
                "actor": actor,
                "correlation_id": corr_id,
                "timestamp": now.isoformat()
            }))
        except Exception:
            pass

        return incident

    # ---------------------------------------------------------------------------
    # Scenario Handlers (A - J)
    # ---------------------------------------------------------------------------

    @classmethod
    async def handle_voice_interaction(
        cls,
        db: Session,
        incident_id: str,
        transcript: Optional[str] = None,
        is_timeout: bool = False
    ) -> Dict[str, Any]:
        """
        Handles Scenarios A, B, C, D, E via resident voice check:
          - A: Elder says "I'm okay" -> RESOLVED
          - B: Elder asks for help -> CAREGIVER_ESCALATION
          - C: Elder says they cannot move -> EMERGENCY_ESCALATION -> DISPATCH_READY
          - D: Elder does not respond (timeout) -> EMERGENCY_ESCALATION -> DISPATCH_READY
          - E: Elder responds ambiguously -> CAREGIVER_ESCALATION
        """
        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident '{incident_id}' not found.")

        # Ensure we are at least in WAITING_FOR_RESPONSE
        current_state = incident.workflow_state or EmergencyWorkflowState.DETECTED.value
        if current_state in (EmergencyWorkflowState.DETECTED.value, EmergencyWorkflowState.VERIFYING.value):
            cls.transition(
                db=db,
                incident_id=incident_id,
                target_state=EmergencyWorkflowState.WELLNESS_CHECK,
                reason="Wellness check initiated for voice verification.",
                evidence={"prompt": "Are you okay?"},
                actor="ALEXA_VOICE_AGENT"
            )
            cls.transition(
                db=db,
                incident_id=incident_id,
                target_state=EmergencyWorkflowState.WAITING_FOR_RESPONSE,
                reason="Waiting for elder verbal reply or prompt timeout window.",
                evidence={"timeout_seconds": 20},
                actor="ALEXA_VOICE_AGENT"
            )

        # Log voice interaction for audit
        t_now = datetime.now(timezone.utc)
        t_voice = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=t_now,
            action_type="VOICE_RESPONSE_RECEIVED",
            actor="PATIENT",
            previous_state=current_state,
            new_state=EmergencyWorkflowState.RESPONSIVE.value if not is_timeout and transcript else EmergencyWorkflowState.EMERGENCY_ESCALATION.value,
            reason="Received voice reply" if not is_timeout and transcript else "No voice response received during prompt window (TIMEOUT).",
            evidence={"transcript": transcript, "is_timeout": is_timeout},
            correlation_id=incident.correlation_id or incident.id,
            description=f"Received voice reply: \"{transcript}\"" if not is_timeout and transcript else "No voice response received during prompt window (TIMEOUT).",
            metadata_json={"transcript": transcript, "is_timeout": is_timeout}
        )
        db.add(t_voice)
        db.commit()

        # SCENARIO D: Elder does not respond (Timeout / Silence)
        if is_timeout or not transcript or not transcript.strip():
            cls.transition(
                db=db,
                incident_id=incident_id,
                target_state=EmergencyWorkflowState.EMERGENCY_ESCALATION,
                reason="Elder did not respond within prompt window (Silent emergency protocol engaged).",
                evidence={"is_timeout": True, "prompt_window_seconds": 20},
                actor="AEGIS_SYSTEM"
            )
            # Progress to DISPATCH_READY
            return await cls._execute_cad_dispatch(db, incident_id, reason="Elder silent / unresponsive")

        clean_text = transcript.strip().lower()

        # SCENARIO A: Elder says "I'm okay"
        safe_keywords = [
            "i'm okay", "i am okay", "i'm fine", "i am fine", "false alarm",
            "all good", "no help", "just dropped", "i slipped but okay",
            "everything is fine", "fine here", "all is fine"
        ]
        is_safe = any(kw in clean_text for kw in safe_keywords)

        # SCENARIO C: Elder says they cannot move
        immobile_keywords = ["cannot move", "can't move", "can not move", "unable to move", "stuck on the floor", "broken", "cannot get up", "can't get up"]
        is_immobile = any(kw in clean_text for kw in immobile_keywords)

        # SCENARIO B: Elder asks for help
        help_keywords = ["help", "help me", "need help", "please help", "call someone", "call daughter", "call my son"]
        is_asking_help = any(kw in clean_text for kw in help_keywords)

        # 1. Elder is RESPONSIVE
        cls.transition(
            db=db,
            incident_id=incident_id,
            target_state=EmergencyWorkflowState.RESPONSIVE,
            reason="Elder verbally answered ambient wellness check prompt.",
            evidence={"transcript": transcript},
            actor="ELDER"
        )

        if is_safe:
            # SCENARIO A: Safe confirmation -> RESOLVED
            incident.current_risk_level = RiskLevel.LOW.value
            cls.transition(
                db=db,
                incident_id=incident_id,
                target_state=EmergencyWorkflowState.RESOLVED,
                reason="Elder verbally confirmed safety ('I'm okay'). Incident resolved and passive monitoring resumed.",
                evidence={"transcript": transcript, "intent": "CONFIRMED_SAFE"},
                actor="AEGIS_SYSTEM"
            )
            t_resolve = IncidentTimelineModel(
                incident_id=incident_id,
                timestamp=datetime.now(timezone.utc),
                action_type="RESOLVED_SAFE",
                actor="AEGIS_SYSTEM",
                previous_state=EmergencyWorkflowState.RESPONSIVE.value,
                new_state=EmergencyWorkflowState.RESOLVED.value,
                reason="Senior verbally confirmed safety. Incident resolved and passive monitoring resumed.",
                evidence={"transcript": transcript},
                correlation_id=incident.correlation_id or incident.id,
                description="Senior verbally confirmed safety. Incident resolved and passive monitoring resumed.",
                metadata_json={"resolved_at": datetime.now(timezone.utc).isoformat()}
            )
            db.add(t_resolve)
            db.commit()

            return {
                "incident_id": incident_id,
                "status": "RESOLVED",
                "risk_level": "LOW",
                "workflow_state": EmergencyWorkflowState.RESOLVED.value,
                "voice_intent": "safe",
                "scenario": "A_SAFE_CONFIRMATION",
                "action_taken": "RESOLVED_SAFE_CANCELLED",
                "transcript": transcript
            }

        elif is_immobile:
            # SCENARIO C: Elder cannot move -> EMERGENCY_ESCALATION -> DISPATCH_READY
            cls.transition(
                db=db,
                incident_id=incident_id,
                target_state=EmergencyWorkflowState.EMERGENCY_ESCALATION,
                reason="Elder reported severe incapacitation / inability to move.",
                evidence={"transcript": transcript, "intent": "SEVERE_IMMOBILITY"},
                actor="AEGIS_SYSTEM"
            )
            return await cls._execute_cad_dispatch(db, incident_id, reason=f"Elder immobilized: '{transcript}'")

        elif is_asking_help:
            # SCENARIO B: Elder asks for help -> CAREGIVER_ESCALATION
            cls.transition(
                db=db,
                incident_id=incident_id,
                target_state=EmergencyWorkflowState.CAREGIVER_ESCALATION,
                reason=f"Elder called for help: '{transcript}'. Triggering caregiver alerts.",
                evidence={"transcript": transcript, "intent": "REQUEST_ASSISTANCE"},
                actor="AEGIS_SYSTEM"
            )
            care_res = await cls._execute_caregiver_dispatch(db, incident_id, custom_message=f"Resident called for help: \"{transcript}\"")
            return {
                "incident_id": incident_id,
                "status": "ESCALATED_CAREGIVER",
                "workflow_state": EmergencyWorkflowState.CAREGIVER_ESCALATION.value,
                "scenario": "B_ELDER_ASKS_FOR_HELP",
                "action": "CAREGIVER_NOTIFIED",
                "caregiver_details": care_res,
                "caregiver_result": care_res
            }

        else:
            # SCENARIO E: Ambiguous response -> CAREGIVER_ESCALATION for human verification
            cls.transition(
                db=db,
                incident_id=incident_id,
                target_state=EmergencyWorkflowState.CAREGIVER_ESCALATION,
                reason=f"Elder responded ambiguously ('{transcript}') without confirming safety. Escalating to caregiver for secondary verification.",
                evidence={"transcript": transcript, "intent": "AMBIGUOUS_RESPONSE"},
                actor="AEGIS_SYSTEM"
            )
            care_res = await cls._execute_caregiver_dispatch(db, incident_id, custom_message=f"Unclear voice check reply: \"{transcript}\". Caregiver review required.")
            return {
                "incident_id": incident_id,
                "status": "ESCALATED_CAREGIVER",
                "workflow_state": EmergencyWorkflowState.CAREGIVER_ESCALATION.value,
                "scenario": "E_AMBIGUOUS_RESPONSE",
                "action": "CAREGIVER_ESCALATION_AMBIGUITY",
                "transcript": transcript,
                "caregiver_details": care_res,
                "caregiver_result": care_res
            }

    @classmethod
    async def handle_sensor_worsening(
        cls,
        db: Session,
        incident_id: str,
        worsening_evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        SCENARIO F: Sensor evidence worsens during wellness check or verification.
        e.g. Heart rate spike, radar confirmed collapse, floor wetness + zero motion > 60s.
        Bypasses remaining wait time and transitions directly to EMERGENCY_ESCALATION -> DISPATCH_READY.
        """
        cls.transition(
            db=db,
            incident_id=incident_id,
            target_state=EmergencyWorkflowState.EMERGENCY_ESCALATION,
            reason="Multimodal sensor evidence worsened during active monitoring (vital deterioration or prolonged collapse confirmed).",
            evidence=worsening_evidence,
            actor="SENSOR_FUSION"
        )
        return await cls._execute_cad_dispatch(db, incident_id, reason="Sensor evidence worsened during wellness check")

    @classmethod
    def handle_caregiver_acknowledgement(
        cls,
        db: Session,
        incident_id: str,
        caregiver_actor: str = "Sarah Vance (Caregiver)",
        notes: str = "Caregiver acknowledged alert and confirmed personal intervention."
    ) -> Dict[str, Any]:
        """
        SCENARIO G: Caregiver acknowledges emergency alert.
        Stops automated escalations, logs caregiver action, transitions to RESOLVED (or standby).
        """
        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident '{incident_id}' not found.")

        # Record caregiver acknowledgement
        cls.transition(
            db=db,
            incident_id=incident_id,
            target_state=EmergencyWorkflowState.RESOLVED,
            reason=f"Caregiver acknowledged incident and assumed primary care. {notes}",
            evidence={"caregiver": caregiver_actor, "notes": notes},
            actor=caregiver_actor
        )

        return {
            "incident_id": incident_id,
            "workflow_state": EmergencyWorkflowState.RESOLVED.value,
            "scenario": "G_CAREGIVER_ACKNOWLEDGED",
            "actor": caregiver_actor,
            "status": incident.status
        }

    @classmethod
    async def handle_caregiver_timeout(
        cls,
        db: Session,
        incident_id: str,
        timeout_seconds: int = 120
    ) -> Dict[str, Any]:
        """
        SCENARIO H: Caregiver does not acknowledge alert within timeout window.
        Auto-escalates from CAREGIVER_ESCALATION -> EMERGENCY_ESCALATION -> DISPATCH_READY.
        """
        cls.transition(
            db=db,
            incident_id=incident_id,
            target_state=EmergencyWorkflowState.EMERGENCY_ESCALATION,
            reason=f"Caregiver failed to acknowledge emergency notification within {timeout_seconds}s timeout window. Auto-escalating to emergency dispatch.",
            evidence={"timeout_seconds": timeout_seconds},
            actor="AEGIS_SYSTEM"
        )
        return await cls._execute_cad_dispatch(db, incident_id, reason="Caregiver non-acknowledgement timeout")

    @classmethod
    def handle_resolution(
        cls,
        db: Session,
        incident_id: str,
        actor: str = "AEGIS_SYSTEM",
        reason: str = "Incident manually resolved by care team.",
        evidence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        SCENARIO I: Emergency is fully resolved.
        Marks incident RESOLVED, restores smart lock / normal pipeline state.
        """
        cls.transition(
            db=db,
            incident_id=incident_id,
            target_state=EmergencyWorkflowState.RESOLVED,
            reason=reason,
            evidence=evidence or {},
            actor=actor
        )
        return {
            "incident_id": incident_id,
            "workflow_state": EmergencyWorkflowState.RESOLVED.value,
            "scenario": "I_EMERGENCY_RESOLVED",
            "actor": actor
        }

    @classmethod
    def handle_false_alarm(
        cls,
        db: Session,
        incident_id: str,
        reason: str = "Resident upright and normal gait velocity restored; acoustic signature resolved to dropped item.",
        evidence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        SCENARIO J: Event becomes false alarm through multimodal verification or recovery.
        Transitions safely to RESOLVED.
        """
        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if incident:
            incident.current_risk_level = RiskLevel.LOW.value

        cls.transition(
            db=db,
            incident_id=incident_id,
            target_state=EmergencyWorkflowState.RESOLVED,
            reason=f"Event verified as false alarm: {reason}",
            evidence=evidence or {"verification": "MULTIMODAL_FALSE_ALARM_FILTER"},
            actor="SENSOR_FUSION"
        )
        return {
            "incident_id": incident_id,
            "workflow_state": EmergencyWorkflowState.RESOLVED.value,
            "scenario": "J_FALSE_ALARM",
            "action": "RESOLVED_FALSE_ALARM"
        }

    # ---------------------------------------------------------------------------
    # Internal Execution Helpers
    # ---------------------------------------------------------------------------

    @classmethod
    async def _execute_cad_dispatch(
        cls,
        db: Session,
        incident_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Generates dynamic emergency packet from actual state, triggers simulated CAD adapter
        and smart lock, and transitions to DISPATCH_READY.
        """
        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        now = datetime.now(timezone.utc)

        # 1. Dynamically compile Emergency Packet from real incident and user state
        packet = EmergencyService.generate_packet_from_incident(incident_id=incident_id, db=db)

        # 2. Persist Emergency Packet in DB
        existing_pkt = db.query(EmergencyPacketModel).filter(EmergencyPacketModel.incident_id == incident_id).first()
        if not existing_pkt:
            pkt_model = EmergencyPacketModel(
                incident_id=incident_id,
                packet_id=packet.packet_id,
                triage_priority=packet.triage_priority,
                formatted_summary=packet.formatted_ems_summary,
                packet_json=packet.model_dump(),
                created_at=now
            )
            db.add(pkt_model)
        else:
            existing_pkt.formatted_summary = packet.formatted_ems_summary
            existing_pkt.packet_json = packet.model_dump()

        # 3. Escalate to Simulated CAD & unlock smart lock
        cad_res = await EmergencyService.escalate_to_cad(
            EscalateEmergencyRequest(
                emergency_packet=packet,
                cad_agency_code="EMS-CAD-MA-02108"
            )
        )

        # 4. Transition to DISPATCH_READY
        cls.transition(
            db=db,
            incident_id=incident_id,
            target_state=EmergencyWorkflowState.DISPATCH_READY,
            reason=f"Emergency packet compiled and simulated CAD dispatch confirmed ({reason}).",
            evidence={
                "packet_id": packet.packet_id,
                "dispatch_id": cad_res.dispatch_id,
                "units": cad_res.units_dispatched,
                "smart_lock_pin": cad_res.smart_lock_pin,
                "integration_type": cad_res.integration_type
            },
            actor="EMS_CAD"
        )

        t_cad = IncidentTimelineModel(
            incident_id=incident_id,
            timestamp=now,
            action_type="CAD_DISPATCHED",
            actor="EMS_CAD",
            previous_state=EmergencyWorkflowState.EMERGENCY_ESCALATION.value,
            new_state=EmergencyWorkflowState.DISPATCH_READY.value,
            reason=f"Direct 911 CAD emergency escalation dispatched to EMS-CAD-MA-02108. Dispatch ID: {cad_res.dispatch_id}. Units: {', '.join(cad_res.units_dispatched)}.",
            evidence={"dispatch_id": cad_res.dispatch_id, "units": cad_res.units_dispatched},
            correlation_id=incident.correlation_id or incident.id,
            description=f"Direct 911 CAD emergency escalation dispatched to EMS-CAD-MA-02108. Dispatch ID: {cad_res.dispatch_id}. Units: {', '.join(cad_res.units_dispatched)}.",
            metadata_json=cad_res.model_dump()
        )
        db.add(t_cad)
        db.commit()

        cad_info = {
            "dispatch_id": cad_res.dispatch_id,
            "emergency_packet_id": packet.packet_id,
            "units_dispatched": cad_res.units_dispatched,
            "door_lock_unlocked": cad_res.door_lock_unlocked,
            "smart_lock_pin": cad_res.smart_lock_pin,
            "integration_type": cad_res.integration_type,
            "disclaimer": cad_res.disclaimer
        }

        return {
            "incident_id": incident_id,
            "status": "ESCALATED_CAD",
            "risk_level": RiskLevel.CRITICAL.value,
            "action_taken": "SILENT_EMERGENCY_CAD_DISPATCH",
            "workflow_state": EmergencyWorkflowState.DISPATCH_READY.value,
            "cad_details": cad_info,
            "dispatch_id": cad_res.dispatch_id,
            "emergency_packet_id": packet.packet_id,
            "units_dispatched": cad_res.units_dispatched,
            "door_lock_unlocked": cad_res.door_lock_unlocked,
            "smart_lock_pin": cad_res.smart_lock_pin,
            "integration_type": cad_res.integration_type,
            "disclaimer": cad_res.disclaimer
        }

    @classmethod
    async def _execute_caregiver_dispatch(
        cls,
        db: Session,
        incident_id: str,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatches multi-channel caregiver notification via simulated adapters."""
        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        event = Event(
            event_type=incident.event_type,
            confidence=incident.confidence,
            location=incident.location,
            timestamp=incident.created_at.isoformat(),
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
            reasons=incident.risk_reasons or ["Risk escalation"]
        )

        care_resp = await CaregiverService.dispatch_notification(
            NotifyCaregiverRequest(
                risk=risk,
                event=event,
                context=context,
                custom_message=custom_message
            )
        )

        now = datetime.now(timezone.utc)
        t_care = IncidentTimelineModel(
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
        db.add(t_care)
        db.commit()

        return {
            "notification_id": care_resp.notification_id,
            "channels_delivered": [c.model_dump() for c in care_resp.channels_delivered],
            "integration_type": care_resp.integration_type,
            "disclaimer": care_resp.disclaimer
        }
