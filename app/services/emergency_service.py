"""
Emergency Services and Packet Generator.
Generates structured CAD-compliant packets and escalates CRITICAL alerts to emergency endpoints.
"""

import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.config import settings
from app.models.enums import RiskLevel, EmergencyDispatchStatus
from app.models.schemas import (
    Event, Context, Risk, EmergencyPacket, PatientSnapshot,
    GenerateEmergencyPacketRequest, EscalateEmergencyRequest, EscalateEmergencyResponse
)


class EmergencyService:
    """Manages emergency packet compilation and CAD (Computer Aided Dispatch) escalation."""

    @classmethod
    def generate_packet(
        cls,
        event: Event,
        context: Context,
        risk: Risk,
        patient_id: Optional[str] = None
    ) -> EmergencyPacket:
        packet_id = f"EPK-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        pid = patient_id or settings.DEFAULT_PATIENT_ID

        patient_profile = PatientSnapshot(
            patient_id=pid,
            name=settings.DEFAULT_PATIENT_NAME,
            age=79,
            residence_address=settings.DEFAULT_LOCATION_LABEL,
            medical_history=[
                "Mild cognitive impairment (early stage)",
                "Hypertension (managed with Lisinopril)",
                "Documented history of slip & fall in bathroom (Jan 2026)",
                "Penicillin allergy (Anaphylaxis risk)"
            ],
            emergency_contact=f"{settings.PRIMARY_CAREGIVER_NAME} ({settings.PRIMARY_CAREGIVER_PHONE})",
            dnr_order=False
        )

        # Telemetry aggregate summary
        telemetry: Dict[str, Any] = {
            "sensor_confidence": event.confidence,
            "post_event_movement": event.movement_after_event,
            "wearable_telemetry": {
                "status": context.wearable_status,
                "baseline_deviation_ratio": context.baseline_deviation,
            },
            "environment_factors": {
                "room": event.location,
                "conditions": context.environment,
                "circadian_slot": context.time_context
            },
            "smart_home_state": {
                "smart_lock_status": "AUTO_UNLOCKED_FOR_FIRST_RESPONDERS",
                "hallway_lights": "100%_PATHWAY_ILLUMINATION_ENGAGED",
                "hvac_fan": "LOW_ACOUSTIC_MODE"
            }
        }

        # Formatted CAD text summary for 911 / EMS dispatcher consoles
        reasons_bullet = "\n  - ".join(risk.reasons)
        ems_summary = (
            f"=== 911 / EMS EMERGENCY CAD TRANSMISSION ===\n"
            f"PACKET ID: {packet_id} | TIMESTAMP: {now_iso}\n"
            f"PATIENT: {patient_profile.name}, Age {patient_profile.age} | ID: {patient_profile.patient_id}\n"
            f"LOCATION: {patient_profile.residence_address} -> Room: {event.location.upper()}\n"
            f"INCIDENT TYPE: {event.event_type.upper()} | CONFIDENCE: {event.confidence:.0%}\n"
            f"POST-INCIDENT MOVEMENT: {event.movement_after_event.upper()}\n"
            f"RISK TRIAGE: {risk.risk_level} (Score Confidence: {risk.confidence:.0%})\n"
            f"CLINICAL / AMBIENT SIGNALS:\n  - {reasons_bullet}\n"
            f"CRITICAL MEDICAL NOTES: {'; '.join(patient_profile.medical_history)}\n"
            f"CONTACT: {patient_profile.emergency_contact}\n"
            f"SMART ACCESS: Entry smart lock unlocked; hallway lighting illuminated for paramedics.\n"
            f"============================================="
        )

        return EmergencyPacket(
            packet_id=packet_id,
            version="2026.1",
            generated_at=now_iso,
            patient_profile=patient_profile,
            triage_priority="DELTA_CRITICAL" if risk.risk_level == RiskLevel.CRITICAL.value else "CHARLIE_URGENT",
            risk_breakdown=risk,
            incident_metadata=event,
            temporal_signals=context,
            telemetry_summary=telemetry,
            formatted_ems_summary=ems_summary
        )

    @classmethod
    async def escalate_to_cad(
        cls,
        request: EscalateEmergencyRequest
    ) -> EscalateEmergencyResponse:
        start_time = time.perf_counter()
        dispatch_id = f"CAD-DISP-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # If no packet was provided, generate one from embedded event/context/risk
        packet = request.emergency_packet
        if not packet:
            # Fallback default event/context/risk if omitted
            event = request.event or Event(
                event_type="unresponsive_fall",
                confidence=0.95,
                location="living_room",
                timestamp=now_iso,
                movement_after_event="none"
            )
            context = request.context or Context(
                activity="walking",
                time_context="night_time",
                baseline_deviation=0.92,
                wearable_status="high_heart_rate",
                environment="dark_room"
            )
            risk = request.risk or Risk(
                risk_level=RiskLevel.CRITICAL.value,
                confidence=0.96,
                reasons=["Unresponsive after high-impact fall", "Zero movement detected"]
            )
            packet = cls.generate_packet(event, context, risk)

        # Simulated low-latency dispatch call (<15ms)
        elapsed_dispatch = (time.perf_counter() - start_time) * 1000.0

        notes = (
            f"Automated Alexa+ emergency dispatch transmitted to {request.cad_agency_code}. "
            f"Unit Medic-14 and Engine-4 assigned. Two-way ambient audio bridge active. "
            f"Building front entrance smart lock unlocked for first responders."
        )

        return EscalateEmergencyResponse(
            dispatch_id=dispatch_id,
            emergency_packet_id=packet.packet_id,
            status=EmergencyDispatchStatus.DISPATCHED.value,
            cad_agency_code=request.cad_agency_code,
            estimated_arrival_minutes=6,
            units_dispatched=["Medic-14", "Engine-4 (Paramedic RIT)"],
            audio_stream_active=True,
            door_lock_unlocked=True,
            transmitted_at=now_iso,
            dispatch_notes=notes
        )
