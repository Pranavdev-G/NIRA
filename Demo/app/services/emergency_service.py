"""
Emergency Services and Packet Generator.
Generates structured CAD-compliant packets and escalates CRITICAL alerts to emergency endpoints.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.config import settings
from app.models.enums import RiskLevel, EmergencyDispatchStatus
from app.models.schemas import (
    Event, Context, Risk, EmergencyPacket, PatientSnapshot,
    EscalateEmergencyRequest, EscalateEmergencyResponse
)


from sqlalchemy.orm import Session
from app.adapters.simulated_adapters import (
    default_cad_adapter,
    default_lock_adapter
)


class EmergencyService:
    """Manages emergency packet compilation and CAD (Computer Aided Dispatch) escalation via adapter layer."""

    @classmethod
    def generate_packet_from_incident(
        cls,
        incident_id: str,
        db: Session,
        packet_id: Optional[str] = None
    ) -> EmergencyPacket:
        """
        Dynamically compiles an emergency packet from actual database incident state,
        resident clinical profile, and live sensor snapshot.
        """
        from app.database.models import IncidentModel, UserModel

        incident = db.query(IncidentModel).filter(IncidentModel.id == incident_id).first()
        if not incident:
            raise ValueError(f"Cannot generate packet: Incident '{incident_id}' not found.")

        user = db.query(UserModel).filter(UserModel.id == incident.user_id).first()
        patient_id = user.patient_id if user else settings.DEFAULT_PATIENT_ID
        patient_name = user.name if user else settings.DEFAULT_PATIENT_NAME
        patient_age = user.age if user else 79
        residence_addr = user.residence_address if user else settings.DEFAULT_LOCATION_LABEL
        emergency_contact = user.emergency_contact if user else f"{settings.PRIMARY_CAREGIVER_NAME} ({settings.PRIMARY_CAREGIVER_PHONE})"
        medical_hist = user.medical_history if user and user.medical_history else [
            "Mild cognitive impairment (early stage)",
            "Hypertension (managed with Lisinopril)",
            "Documented history of slip & fall in bathroom (Jan 2026)",
            "Penicillin allergy (Anaphylaxis risk)"
        ]
        dnr = user.dnr_order if user else False

        patient_profile = PatientSnapshot(
            patient_id=patient_id,
            name=patient_name,
            age=patient_age,
            residence_address=residence_addr,
            medical_history=medical_hist,
            emergency_contact=emergency_contact,
            dnr_order=dnr
        )

        # Retrieve live sensor snapshot from event pipeline
        from app.services.event_pipeline import global_pipeline
        snapshot = global_pipeline.current_state
        wearable_hr = snapshot.vitals.get("heart_rate_bpm") if snapshot.vitals else 72
        hr_str = f"{wearable_hr} bpm" if wearable_hr else "telemetry active"
        room_env = snapshot.environment or {}

        context_dict = incident.context_snapshot or {}
        context = Context(
            activity=context_dict.get("activity", "resting"),
            time_context=context_dict.get("time_context", "ambient"),
            baseline_deviation=float(context_dict.get("baseline_deviation", 0.85)),
            wearable_status=f"{hr_str} ({context_dict.get('wearable_status', 'worn_normal')})",
            environment=context_dict.get("environment", "well_lit")
        )

        event = Event(
            event_type=incident.event_type,
            confidence=incident.confidence,
            location=incident.location,
            timestamp=incident.created_at.isoformat(),
            movement_after_event=incident.movement_after_event
        )

        risk = Risk(
            risk_level=incident.current_risk_level,
            confidence=incident.risk_confidence,
            reasons=incident.risk_reasons or ["Multimodal anomaly confirmed"]
        )

        pid = packet_id or f"EPK-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Telemetry aggregate summary from actual state
        telemetry: Dict[str, Any] = {
            "incident_id": incident.id,
            "correlation_id": incident.correlation_id or incident.id,
            "sensor_confidence": incident.confidence,
            "post_event_movement": incident.movement_after_event,
            "wearable_telemetry": {
                "heart_rate_bpm": wearable_hr,
                "status": context.wearable_status,
                "baseline_deviation_ratio": context.baseline_deviation,
            },
            "environment_factors": {
                "room": incident.location,
                "floor_hazard": room_env.get("floor_moisture_detected", False),
                "ambient_lux": room_env.get("lighting_lux", 380.0),
                "radar_occupancy": True,
                "circadian_slot": context.time_context
            },
            "smart_home_state": {
                "smart_lock_status": "AUTO_UNLOCKED_FOR_FIRST_RESPONDERS" if not default_lock_adapter.is_locked else "LOCKED",
                "smart_lock_pin": default_lock_adapter.temporary_pin or "EMG-2026",
                "hallway_lights": "100%_PATHWAY_ILLUMINATION_ENGAGED",
                "hvac_fan": "LOW_ACOUSTIC_MODE"
            }
        }

        reasons_bullet = "\n  - ".join(risk.reasons)
        ems_summary = (
            f"=== 911 / EMS EMERGENCY CAD TRANSMISSION ===\n"
            f"PACKET ID: {pid} | TIMESTAMP: {now_iso}\n"
            f"INCIDENT REF: {incident.id} | CORRELATION: {incident.correlation_id or incident.id}\n"
            f"PATIENT: {patient_profile.name}, Age {patient_profile.age} | ID: {patient_profile.patient_id}\n"
            f"LOCATION: {patient_profile.residence_address} -> Room: {incident.location.upper()}\n"
            f"INCIDENT TYPE: {incident.event_type.upper()} | CONFIDENCE: {incident.confidence:.0%}\n"
            f"POST-INCIDENT MOVEMENT: {incident.movement_after_event.upper()}\n"
            f"RISK TRIAGE: {risk.risk_level} (Score Confidence: {risk.confidence:.0%})\n"
            f"CURRENT VITALS: Heart Rate {hr_str} | Active Safety State: {snapshot.safety_state}\n"
            f"CLINICAL / AMBIENT SIGNALS:\n  - {reasons_bullet}\n"
            f"CRITICAL MEDICAL NOTES: {'; '.join(patient_profile.medical_history)}\n"
            f"DNR STATUS: {'YES (Do Not Resuscitate)' if patient_profile.dnr_order else 'NO (Full Resuscitation)'}\n"
            f"EMERGENCY CONTACT: {patient_profile.emergency_contact}\n"
            f"SMART ACCESS: Front lock PIN: {telemetry['smart_home_state']['smart_lock_pin']}; Pathway lights 100% illuminated.\n"
            f"NOTE: Simulation Mode active via adapter layer. Live dispatch unauthenticated.\n"
            f"============================================="
        )

        return EmergencyPacket(
            packet_id=pid,
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
    def generate_packet(
        cls,
        event: Event,
        context: Context,
        risk: Risk,
        patient_id: Optional[str] = None
    ) -> EmergencyPacket:
        """Standard packet compiler for direct event/context/risk inputs."""
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
        """
        Escalates critical alerts via Simulated CAD Adapter and Simulated Smart Lock Adapter.
        Strictly satisfies Principle 7: clearly marks response as SIMULATED.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # If no packet was provided, generate one
        packet = request.emergency_packet
        if not packet:
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

        # 1. Unlock entry door via Simulated Smart Lock Adapter
        lock_res = await default_lock_adapter.unlock_door(
            device_id="lock_front_door_01",
            actor="NIRA_EMERGENCY_DISPATCH",
            reason=f"Emergency dispatch for resident {packet.patient_profile.name} (Packet {packet.packet_id})"
        )

        # 2. Dispatch emergency via Simulated CAD Adapter
        cad_res = await default_cad_adapter.dispatch_emergency(
            emergency_packet_id=packet.packet_id,
            triage_priority=packet.triage_priority,
            cad_agency_code=request.cad_agency_code,
            location_address=packet.patient_profile.residence_address,
            formatted_summary=packet.formatted_ems_summary,
            resident_name=packet.patient_profile.name,
            medical_notes=packet.patient_profile.medical_history
        )

        units = cad_res.details.get("units_dispatched", ["Medic-14", "Engine-4 (Paramedic RIT)"])
        eta = cad_res.details.get("estimated_arrival_minutes", 6)
        notes = (
            f"Simulated Alexa+ emergency dispatch transmitted to {request.cad_agency_code}. "
            f"Transaction ID: {cad_res.transaction_id}. Units {', '.join(units)} assigned (ETA {eta}m). "
            f"Two-way ambient audio bridge active. Smart lock unlocked with emergency PIN: {lock_res.details.get('emergency_access_pin')}."
        )

        return EscalateEmergencyResponse(
            dispatch_id=cad_res.transaction_id,
            emergency_packet_id=packet.packet_id,
            status=EmergencyDispatchStatus.DISPATCHED.value,
            cad_agency_code=request.cad_agency_code,
            estimated_arrival_minutes=eta,
            units_dispatched=units,
            audio_stream_active=True,
            door_lock_unlocked=not default_lock_adapter.is_locked,
            transmitted_at=now_iso,
            dispatch_notes=notes,
            integration_type="SIMULATED",
            disclaimer=cad_res.disclaimer,
            smart_lock_pin=lock_res.details.get("emergency_access_pin")
        )

