"""
Authoritative Incident Lifecycle Manager for NIRA Live Core.
Amazon Developer Hackathon 2026.

Manages complete incident lifecycles:
create → update → acknowledge → verify → escalate → resolve → false_alarm → recovery → timeout
Preserves immutable chronological audit timelines across all state transitions.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from Live.core.models import (
    LiveEvent,
    SafetyState,
    SeverityLevel,
    IncidentRecord,
    TimelineEntry,
    VoiceInteractionRecord,
    CaregiverActionRecord,
    EmergencyDispatchRecord,
    LocationModel
)
from Live.core.emergency_workflow import EmergencyWorkflowFSM

logger = logging.getLogger("NIRA.LiveCore.IncidentManager")


class IncidentManager:
    """
    Authoritative manager for Live safety incidents.
    Coordinates the EmergencyWorkflowFSM and maintains historical audit trails.
    """

    def __init__(self):
        self._active_incident: Optional[IncidentRecord] = None
        self._fsm: EmergencyWorkflowFSM = EmergencyWorkflowFSM()
        self._incident_history: Dict[str, IncidentRecord] = {}

    @property
    def current_state(self) -> SafetyState:
        return self._fsm.current_state

    def get_active_incident(self) -> Optional[IncidentRecord]:
        return self._active_incident

    def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        if self._active_incident and self._active_incident.incident_id == incident_id:
            return self._active_incident
        return self._incident_history.get(incident_id)

    def get_timeline(self, incident_id: str) -> List[TimelineEntry]:
        inc = self.get_incident(incident_id)
        if inc:
            return inc.timeline
        return self._fsm.get_history()

    def get_all_incidents(self, limit: int = 50) -> List[IncidentRecord]:
        all_inc = list(self._incident_history.values())
        if self._active_incident and self._active_incident.incident_id not in self._incident_history:
            all_inc.append(self._active_incident)
        all_inc.sort(key=lambda x: x.start_time, reverse=True)
        return all_inc[:limit]

    def create_incident(
        self,
        trigger_event: LiveEvent,
        severity: SeverityLevel = SeverityLevel.MEDIUM,
        risk_score: float = 0.5,
        location: Optional[LocationModel] = None
    ) -> IncidentRecord:
        """Creates a new authoritative safety incident and transitions workflow to DETECTED."""
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        loc = location or trigger_event.location

        # Transition FSM to DETECTED
        success, entry = self._fsm.transition(
            target_state=SafetyState.DETECTED,
            action="INCIDENT_TRIGGERED",
            description=f"Incident triggered by {trigger_event.event_type.value} from {trigger_event.source.value}",
            actor=trigger_event.source.value,
            metadata={"trigger_event_id": trigger_event.event_id, "confidence": trigger_event.confidence}
        )

        incident = IncidentRecord(
            incident_id=incident_id,
            resident_id=trigger_event.resident_id,
            state=SafetyState.DETECTED,
            severity=severity,
            risk_score=risk_score,
            start_time=now_iso,
            last_updated=now_iso,
            location=loc,
            trigger_event=trigger_event.model_dump(),
            supporting_evidence=[trigger_event.model_dump()],
            timeline=[entry]
        )

        self._active_incident = incident
        self._incident_history[incident_id] = incident
        logger.info(f"[IncidentManager] Created incident {incident_id} [{severity.value}] at {loc.zone.value}")
        return incident

    def start_wellness_check(self, incident_id: str, prompt: str) -> Optional[IncidentRecord]:
        """Transitions incident to WELLNESS_CHECK and logs voice inquiry."""
        inc = self.get_incident(incident_id)
        if not inc:
            return None

        success, entry = self._fsm.transition(
            target_state=SafetyState.WELLNESS_CHECK,
            action="START_WELLNESS_CHECK",
            description=f"Vocal check-in prompt: '{prompt}'",
            actor="VOICE_SYNTHESIS_ENGINE"
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        inc.state = self._fsm.current_state
        inc.last_updated = now_iso
        inc.voice_interaction = VoiceInteractionRecord(
            prompt=prompt,
            prompt_timestamp=now_iso
        )
        inc.timeline.append(entry)

        # Immediately transition to WAITING_FOR_RESPONSE (Auto-mic open)
        success2, entry2 = self._fsm.transition(
            target_state=SafetyState.WAITING_FOR_RESPONSE,
            action="ACTIVATE_AUTO_MIC",
            description="Microphone automatically activated for resident vocal response",
            actor="AUTOMATIC_MICROPHONE_GATEWAY"
        )
        inc.state = self._fsm.current_state
        inc.timeline.append(entry2)
        return inc

    def record_voice_response(
        self,
        incident_id: str,
        response_text: str,
        classification: str,
        duration_sec: Optional[float] = None
    ) -> Optional[IncidentRecord]:
        """Records the resident's vocal answer and advances FSM accordingly."""
        inc = self.get_incident(incident_id)
        if not inc:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        clean_cls = classification.upper().strip()

        if inc.voice_interaction:
            inc.voice_interaction.resident_response = response_text
            inc.voice_interaction.classification = clean_cls
            inc.voice_interaction.duration_sec = duration_sec

        inc.last_updated = now_iso

        if clean_cls in ["SAFE", "SAFE_VERIFIED", "FINE", "OKAY"]:
            # Resident confirmed safe
            success, entry = self._fsm.transition(
                target_state=SafetyState.RESPONSIVE,
                action="RESIDENT_CONFIRMED_SAFE",
                description=f"Resident verbally confirmed safe: '{response_text}'",
                actor="RESIDENT_VOICE"
            )
            inc.state = self._fsm.current_state
            inc.timeline.append(entry)

            # Auto-resolve incident
            self.resolve_incident(
                incident_id=incident_id,
                outcome="SAFE_CONFIRMED",
                resolved_by="RESIDENT_VOCAL_CONFIRMATION",
                notes=f"Resident answered: '{response_text}'"
            )

        elif clean_cls in ["HELP", "EMERGENCY", "PAIN", "FELL"]:
            # Resident asked for help
            success, entry = self._fsm.transition(
                target_state=SafetyState.EMERGENCY_ESCALATION,
                action="RESIDENT_REQUESTED_HELP",
                description=f"Resident verbally requested assistance: '{response_text}'",
                actor="RESIDENT_VOICE"
            )
            inc.state = self._fsm.current_state
            inc.severity = SeverityLevel.CRITICAL
            inc.timeline.append(entry)

        else:
            # Unclear or partial
            success, entry = self._fsm.transition(
                target_state=SafetyState.CAREGIVER_ESCALATION,
                action="AMBIGUOUS_VOICE_ESCALATION",
                description=f"Ambiguous response '{response_text}', alerting caregiver",
                actor="VOICE_ASR_ANALYZER"
            )
            inc.state = self._fsm.current_state
            inc.timeline.append(entry)

        return inc

    def record_silence_timeout(self, incident_id: str) -> Optional[IncidentRecord]:
        """Handles 15s silence / no vocal response after wellness check."""
        inc = self.get_incident(incident_id)
        if not inc:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        if inc.voice_interaction:
            inc.voice_interaction.resident_response = "[SILENCE - NO VOCAL RESPONSE]"
            inc.voice_interaction.classification = "UNRESPONSIVE"

        # Escalate directly to EMERGENCY_ESCALATION
        success, entry = self._fsm.transition(
            target_state=SafetyState.EMERGENCY_ESCALATION,
            action="SILENCE_TIMEOUT_ESCALATION",
            description="Resident failed to respond within timeout window. Potential unconscious collapse.",
            actor="SAFETY_TIMER"
        )
        inc.state = self._fsm.current_state
        inc.severity = SeverityLevel.CRITICAL
        inc.last_updated = now_iso
        inc.timeline.append(entry)
        return inc

    def record_caregiver_action(
        self,
        incident_id: str,
        action_type: str,
        caregiver_name: str,
        phone: str,
        notes: str = ""
    ) -> Optional[IncidentRecord]:
        """Records a caregiver action (e.g. TextBEE SMS dispatched, phone call, acknowledge)."""
        inc = self.get_incident(incident_id)
        if not inc:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        record = CaregiverActionRecord(
            action_type=action_type,
            caregiver_name=caregiver_name,
            phone=phone,
            timestamp=now_iso,
            notes=notes
        )
        inc.caregiver_actions.append(record)
        inc.last_updated = now_iso

        entry = TimelineEntry(
            timestamp=now_iso,
            state=inc.state,
            action=action_type,
            description=f"Caregiver {caregiver_name} ({phone}): {notes or action_type}",
            actor="CAREGIVER_SYSTEM",
            metadata={"phone": phone}
        )
        inc.timeline.append(entry)
        return inc

    def record_emergency_dispatch(
        self,
        incident_id: str,
        unit_id: str = "Medic-14",
        cad_number: Optional[str] = None,
        eta_mins: float = 3.5,
        smart_door_status: str = "LOCKED",
        smart_door_pin: str = "8492"
    ) -> Optional[IncidentRecord]:
        """Transitions to DISPATCH_READY and links Paramedic CAD Unit."""
        inc = self.get_incident(incident_id)
        if not inc:
            return None

        cad_id = cad_number or f"CAD-BOS-{uuid.uuid4().hex[:6].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        success, entry = self._fsm.transition(
            target_state=SafetyState.DISPATCH_READY,
            action="AMBULANCE_CAD_DISPATCHED",
            description=f"First responder CAD dispatched: {unit_id} (ETA: {eta_mins} mins). Smart door PIN {smart_door_pin}.",
            actor="EMERGENCY_DISPATCH_CAD",
            metadata={"cad_id": cad_id, "unit_id": unit_id, "eta_mins": eta_mins}
        )

        dispatch_rec = EmergencyDispatchRecord(
            service_type="AMBULANCE_CAD",
            unit_id=unit_id,
            cad_incident_number=cad_id,
            dispatched_at=now_iso,
            eta_mins=eta_mins,
            status="EN_ROUTE",
            smart_door_status=smart_door_status,
            smart_door_pin=smart_door_pin
        )
        inc.state = self._fsm.current_state
        inc.emergency_dispatch = dispatch_rec
        inc.last_updated = now_iso
        inc.timeline.append(entry)
        return inc

    def resolve_incident(
        self,
        incident_id: str,
        outcome: str = "SAFE_CONFIRMED",
        resolved_by: str = "CARE_TEAM",
        notes: str = ""
    ) -> Optional[IncidentRecord]:
        """Resolves incident and returns workflow to NORMAL."""
        inc = self.get_incident(incident_id)
        if not inc:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()

        success, entry = self._fsm.transition(
            target_state=SafetyState.RESOLVED,
            action="RESOLVE_INCIDENT",
            description=f"Incident resolved [{outcome}] by {resolved_by}: {notes}",
            actor=resolved_by,
            metadata={"outcome": outcome}
        )

        inc.state = SafetyState.RESOLVED
        inc.resolved_at = now_iso
        inc.last_updated = now_iso
        inc.resolution_summary = {
            "resolved_by": resolved_by,
            "outcome": outcome,
            "notes": notes,
            "resolved_at": now_iso
        }
        inc.timeline.append(entry)

        # Transition FSM back to NORMAL
        self._fsm.transition(
            target_state=SafetyState.NORMAL,
            action="WORKFLOW_RESET_NORMAL",
            description="Safety state returned to NORMAL ambient monitoring",
            actor="NIRA_SAFETY_CORE"
        )

        # Archive active incident
        self._incident_history[incident_id] = inc
        if self._active_incident and self._active_incident.incident_id == incident_id:
            self._active_incident = None

        logger.info(f"[IncidentManager] Resolved incident {incident_id} [{outcome}]")
        return inc
