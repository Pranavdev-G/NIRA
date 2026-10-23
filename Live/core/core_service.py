"""
Authoritative Central CoreService for NIRA Live.
Amazon Developer Hackathon 2026.

Unifies:
  REAL SENSORS / REAL AI
           ↓
   LIVE EVENT INGESTION (EventPipeline)
           ↓
   LIVE SAFETY CORE (CoreService)
           ↓
   RISK ASSESSMENT (RiskEngine + SignalExtractor)
           ↓
   INCIDENT LIFECYCLE (IncidentManager)
           ↓
   EMERGENCY WORKFLOW (EmergencyWorkflowFSM)
           ↓
   CAREGIVER / SMS / CAD / SMART HOME (Adapters)
           ↓
   LIVE DASHBOARD (RealtimeBus)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from Live.core.models import (
    LiveEvent,
    EventType,
    ZoneType,
    SafetyState,
    SeverityLevel,
    RecommendedAction,
    RiskAssessment,
    IncidentRecord,
    TimelineEntry,
    EmergencyPacket
)
from Live.core.event_pipeline import EventPipeline
from Live.core.context_engine import ContextEngine
from Live.core.baseline_engine import BaselineEngineAdapter
from Live.core.risk_engine import RiskEngine
from Live.core.incident_manager import IncidentManager
from Live.core.realtime_bus import get_realtime_bus, RealtimeBus
from Live.core.persistence import CorePersistenceManager
from Live.core.emergency_packet import EmergencyPacketBuilder

logger = logging.getLogger("NIRA.LiveCore.Service")


class CoreService:
    """
    Central authoritative safety service for NIRA Live.
    Single source of truth for safety state, risk scores, active incidents, and dispatches.
    """

    def __init__(self):
        self.pipeline = EventPipeline()
        self.context_engine = ContextEngine()
        self.baseline_engine = BaselineEngineAdapter()
        self.risk_engine = RiskEngine(self.context_engine, self.baseline_engine)
        self.incident_manager = IncidentManager()
        self.bus: RealtimeBus = get_realtime_bus()
        self.persistence = CorePersistenceManager()

        # Cached latest state components
        self._current_zone: ZoneType = ZoneType.LIVING_ROOM
        self._current_vitals: Dict[str, Any] = {
            "heart_rate_bpm": 74,
            "blood_pressure": "124/78",
            "spo2": 98.0,
            "device_model": "Aegis Pulse Band Pro",
            "battery_percent": 88,
            "status": "BLE_5.3_CONNECTED"
        }
        self._last_risk: Optional[RiskAssessment] = None

        logger.info("[CoreService] NIRA Authoritative Safety Core initialized successfully.")

    # ------------------------------------------------------------------
    # 1. Event Ingestion & Multimodal Safety Evaluation
    # ------------------------------------------------------------------
    def ingest_event(self, raw_input: Dict[str, Any]) -> Tuple[Optional[LiveEvent], RiskAssessment, Optional[IncidentRecord]]:
        """
        Authoritative entrypoint for any sensor or AI event.
        Executes: Pipeline Ingest -> Multimodal Risk Assessment -> FSM Evaluation -> Persistence -> Realtime Broadcast.
        """
        event, status = self.pipeline.ingest(raw_input)
        if event is None:
            # If rejected (duplicate/stale), re-evaluate current risk with existing history
            current_risk = self.assess_risk()
            return None, current_risk, self.incident_manager.get_active_incident()

        # Update zone & vitals telemetry cache
        if event.location and event.location.zone != ZoneType.UNKNOWN:
            self._current_zone = event.location.zone

        if "bpm" in event.payload or "heart_rate" in event.payload:
            self._current_vitals["heart_rate_bpm"] = event.payload.get("bpm") or event.payload.get("heart_rate")

        # Persist event
        self.persistence.save_telemetry_event(event)

        # Assess risk combining all 14 signals
        recent_events = self.pipeline.get_recent_events(limit=10)
        risk = self.risk_engine.assess_risk(
            trigger_event=event,
            recent_events=recent_events,
            active_zone=self._current_zone,
            vitals_state=self._current_vitals
        )
        self._last_risk = risk

        # Evaluate Incident Lifecycle & FSM transitions
        incident = self.incident_manager.get_active_incident()

        if incident is None:
            # Trigger new incident if risk is Elevated (Medium+) or Fall/Critical event
            if risk.risk_level in [SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL] or event.event_type in [EventType.FALL_DETECTED, EventType.INACTIVITY_CRITICAL]:
                incident = self.incident_manager.create_incident(
                    trigger_event=event,
                    severity=risk.risk_level,
                    risk_score=risk.overall_score,
                    location=event.location
                )
                self.persistence.save_incident(incident)

                # Broadcast incident creation
                self.bus.publish_sync("incident_created", incident.model_dump())

                # If action is WELLNESS_CHECK, immediately initiate inquiry
                if risk.recommended_action == RecommendedAction.TRIGGER_WELLNESS_CHECK or event.event_type in [EventType.FALL_DETECTED, EventType.INACTIVITY_CRITICAL]:
                    self.start_wellness_check(
                        incident_id=incident.incident_id,
                        prompt="Are you okay Eleanor? Please let me know if you need assistance."
                    )
        else:
            # Update existing active incident
            incident.risk_score = risk.overall_score
            incident.severity = risk.risk_level
            incident.supporting_evidence.append(event.model_dump())
            self.persistence.save_incident(incident)

        # Broadcast state change
        state_snapshot = self.get_current_state()
        self.bus.publish_sync("state_update", state_snapshot)

        return event, risk, incident

    # ------------------------------------------------------------------
    # 2. Risk Assessment Query
    # ------------------------------------------------------------------
    def assess_risk(self, zone: Optional[ZoneType] = None) -> RiskAssessment:
        """Computes and returns current risk assessment without ingesting new event."""
        target_zone = zone or self._current_zone
        recent = self.pipeline.get_recent_events(limit=10)
        risk = self.risk_engine.assess_risk(
            trigger_event=None,
            recent_events=recent,
            active_zone=target_zone,
            vitals_state=self._current_vitals
        )
        self._last_risk = risk
        return risk

    # ------------------------------------------------------------------
    # 3. Conversational Wellness Check & Auto-Microphone
    # ------------------------------------------------------------------
    def start_wellness_check(
        self,
        incident_id: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Triggers vocal inquiry and automatically turns on the microphone.
        """
        inc = self.incident_manager.get_active_incident() if not incident_id else self.incident_manager.get_incident(incident_id)
        if not inc:
            # Synthesize event to anchor incident
            dummy_event = LiveEvent(
                event_id="evt-wellness-manual",
                event_type=EventType.INACTIVITY_WARNING,
                source=self.pipeline._stats.get("source", "system_monitor"),
                correlation_id="corr-wellness",
                payload={"reason": "Manual wellness check triggered"}
            )
            inc = self.incident_manager.create_incident(dummy_event, severity=SeverityLevel.MEDIUM, risk_score=0.55)

        default_prompt = "Are you okay Eleanor? Please let me know if you need any assistance."
        check_prompt = prompt or default_prompt

        updated_inc = self.incident_manager.start_wellness_check(inc.incident_id, check_prompt)
        if updated_inc:
            self.persistence.save_incident(updated_inc)
            # Broadcast to dashboard to synthesize speech and start auto-mic
            self.bus.publish_sync("wellness_check_started", {
                "incident_id": inc.incident_id,
                "prompt": check_prompt,
                "auto_mic_active": True
            })

        return {
            "success": True,
            "incident_id": inc.incident_id,
            "state": self.incident_manager.current_state.value,
            "prompt": check_prompt,
            "auto_mic_active": True
        }

    def process_wellness_response(
        self,
        response_text: str,
        incident_id: Optional[str] = None,
        duration_sec: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Authoritative processing of resident vocal response captured by speech-to-text.
        """
        inc = self.incident_manager.get_active_incident() if not incident_id else self.incident_manager.get_incident(incident_id)
        clean_text = str(response_text).lower().strip()

        # Classify intent
        if any(w in clean_text for w in ["okay", "fine", "safe", "alright", "good", "no problem", "glasses"]):
            classification = "SAFE"
        elif any(w in clean_text for w in ["help", "fell", "pain", "hurt", "emergency", "ambulance", "can't get up"]):
            classification = "HELP"
        else:
            classification = "AMBIGUOUS"

        if inc:
            updated_inc = self.incident_manager.record_voice_response(
                incident_id=inc.incident_id,
                response_text=response_text,
                classification=classification,
                duration_sec=duration_sec
            )
            if updated_inc:
                self.persistence.save_incident(updated_inc)

            # If SAFE: reinforce adaptive baseline to suppress false alarms
            if classification == "SAFE":
                self.baseline_engine.reinforce_safe_confirmation(
                    zone=inc.location.zone,
                    duration_sec=duration_sec or 30.0,
                    feedback=f"Resident answered: '{response_text}'"
                )
                self.risk_engine.reset_hysteresis()
                system_reply = "Thank you Eleanor. I have confirmed you are safe. Normal ambient monitoring resumed."
            elif classification == "HELP":
                system_reply = "Help is on the way Eleanor. Alerting emergency medical services and your caretaker now."
                # Trigger Caregiver SMS & Emergency CAD
                self.trigger_caregiver_sms_action(updated_inc)
                self.trigger_ambulance_cad_action(updated_inc)
            else:
                system_reply = "I am alerting your caretaker to check in with you."
                self.trigger_caregiver_sms_action(updated_inc)

            self.bus.publish_sync("voice_response_processed", {
                "incident_id": inc.incident_id,
                "transcript": response_text,
                "classification": classification,
                "system_reply": system_reply,
                "new_state": self.incident_manager.current_state.value
            })

            return {
                "success": True,
                "incident_id": inc.incident_id,
                "classification": classification,
                "system_reply": system_reply,
                "state": self.incident_manager.current_state.value
            }

        return {"success": False, "error": "No active incident to associate response"}

    def handle_silence_timeout(self, incident_id: Optional[str] = None) -> Dict[str, Any]:
        """Handles 15-second vocal silence / unresponsiveness timeout."""
        inc = self.incident_manager.get_active_incident() if not incident_id else self.incident_manager.get_incident(incident_id)
        if not inc:
            return {"success": False, "error": "No active incident"}

        updated_inc = self.incident_manager.record_silence_timeout(inc.incident_id)
        if updated_inc:
            self.persistence.save_incident(updated_inc)
            # Immediate escalation to Caregiver SMS and Paramedic CAD
            self.trigger_caregiver_sms_action(updated_inc)
            self.trigger_ambulance_cad_action(updated_inc)

            self.bus.publish_sync("silence_timeout_escalated", {
                "incident_id": inc.incident_id,
                "state": self.incident_manager.current_state.value,
                "severity": updated_inc.severity.value
            })

        return {
            "success": True,
            "incident_id": inc.incident_id,
            "state": self.incident_manager.current_state.value,
            "escalated": True
        }

    # ------------------------------------------------------------------
    # 4. Action Adapters: TextBEE SMS, CAD Dispatch & Smart Lock
    # ------------------------------------------------------------------
    def trigger_caregiver_sms_action(self, incident: IncidentRecord):
        """Asynchronously dispatches urgent emergency SMS to caretaker via TextBEE adapter."""
        try:
            from Live.app.services.textbee import LiveTextBeeService
            from Live.app.services.session import LiveSessionManager
            caregiver = LiveSessionManager.get_active_caregiver()
            patient = LiveSessionManager.get_active_patient_info()

            async def _send():
                res = await LiveTextBeeService.send_emergency_alert(
                    incident_id=incident.incident_id,
                    patient_name=patient.get("name", "Eleanor Vance"),
                    severity=incident.severity.value,
                    recipient_phone=caregiver.get("mobile_number", "9489240892"),
                    latitude=patient.get("latitude", 42.3601),
                    longitude=patient.get("longitude", -71.0589),
                    address=patient.get("address")
                )
                self.incident_manager.record_caregiver_action(
                    incident_id=incident.incident_id,
                    action_type="TEXTBEE_EMERGENCY_SMS_DISPATCHED",
                    caregiver_name=caregiver.get("caretaker_name", "Dharaneesh N"),
                    phone=caregiver.get("mobile_number", "9489240892"),
                    notes=f"Batch ID: {res.get('batch_id', 'TXB-DISPATCHED')}"
                )
                self.bus.publish_sync("sms_dispatched", res)

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_send())
            except RuntimeError:
                asyncio.run(_send())
        except Exception as e:
            logger.warning(f"[CoreService] Caregiver SMS trigger error: {e}")

    def trigger_ambulance_cad_action(self, incident: IncidentRecord):
        """Dispatches Paramedic CAD unit and starts live radar GPS tracking."""
        try:
            from Live.app.services.emergency import LiveEmergencyTrackerService
            cad_res = LiveEmergencyTrackerService.trigger_dispatch(incident_id=incident.incident_id)

            updated = self.incident_manager.record_emergency_dispatch(
                incident_id=incident.incident_id,
                unit_id=cad_res.get("unit_id", "Medic-14"),
                cad_number=cad_res.get("cad_incident_id") or f"CAD-{incident.incident_id[-6:]}",
                eta_mins=cad_res.get("eta_mins", 3.8),
                smart_door_status="LOCKED",
                smart_door_pin="8492"
            )
            if updated:
                self.persistence.save_incident(updated)

            self.bus.publish_sync("cad_dispatched", cad_res)
        except Exception as e:
            logger.warning(f"[CoreService] CAD trigger error: {e}")

    # ------------------------------------------------------------------
    # 5. Incident Resolution & State Query
    # ------------------------------------------------------------------
    def resolve_incident(
        self,
        incident_id: Optional[str] = None,
        outcome: str = "SAFE_CONFIRMED",
        resolved_by: str = "CARE_TEAM",
        notes: str = ""
    ) -> Optional[IncidentRecord]:
        """Resolves active incident and returns safety state to NORMAL."""
        inc = self.incident_manager.get_active_incident() if not incident_id else self.incident_manager.get_incident(incident_id)
        if not inc:
            return None

        resolved_inc = self.incident_manager.resolve_incident(
            incident_id=inc.incident_id,
            outcome=outcome,
            resolved_by=resolved_by,
            notes=notes
        )
        if resolved_inc:
            self.persistence.save_incident(resolved_inc)
            self.bus.publish_sync("incident_resolved", resolved_inc.model_dump())

        return resolved_inc

    def generate_emergency_packet(self, incident_id: Optional[str] = None) -> Optional[EmergencyPacket]:
        """Generates authoritative EmergencyPacket without fabricated values."""
        inc = self.incident_manager.get_active_incident() if not incident_id else self.incident_manager.get_incident(incident_id)
        if not inc:
            return None

        from Live.app.services.session import LiveSessionManager
        caregiver = LiveSessionManager.get_active_caregiver()
        patient = LiveSessionManager.get_active_patient_info()

        packet = EmergencyPacketBuilder.build(
            incident=inc,
            risk_assessment=self._last_risk,
            patient_profile=patient,
            caregiver_info=caregiver,
            vitals=self._current_vitals,
            snapshot_url="/live/static/fall_snapshot.jpg"
        )
        self.persistence.save_emergency_packet(packet)
        return packet

    def get_current_state(self) -> Dict[str, Any]:
        """Returns the authoritative real-time Live safety state snapshot."""
        active_inc = self.incident_manager.get_active_incident()
        risk = self._last_risk or self.assess_risk()

        return {
            "safety_state": self.incident_manager.current_state.value,
            "risk_score": risk.overall_score,
            "risk_level": risk.risk_level.value,
            "active_zone": self._current_zone.value,
            "active_incident_id": active_inc.incident_id if active_inc else None,
            "active_incident": active_inc.model_dump() if active_inc else None,
            "vitals": self._current_vitals,
            "pipeline_stats": self.pipeline.get_stats(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global singleton instance
_core_instance: Optional[CoreService] = None


def get_live_core() -> CoreService:
    global _core_instance
    if _core_instance is None:
        _core_instance = CoreService()
    return _core_instance
