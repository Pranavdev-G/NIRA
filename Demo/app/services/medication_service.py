"""
Medication Reminder & Adherence Service for NIRA Ambient Care.
Amazon Developer Hackathon 2026.

Supports:
- Scheduled prescriptions tracking
- Marking doses as taken, missed, or delayed
- Adherence rate calculation & chronological history
- Emitting events into the central event pipeline (UnifiedEvent)
- Caregiver notification trigger for prolonged missed doses (without creating emergency CAD dispatch)
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.database.models import MedicationModel, UserModel
from app.services.event_pipeline import global_pipeline
from app.services.caregiver_service import CaregiverService
from app.models.schemas import NotifyCaregiverRequest
from app.models.event_contracts import UnifiedEvent, EventSource, EventType

logger = logging.getLogger("aegis.medication_service")


class MedicationService:
    """Manages scheduled medications, adherence, and caregiver reminder escalations."""

    DEFAULT_RESIDENT_ID = "user_eleanor_vance"

    @classmethod
    def get_schedule(cls, db: Session, resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns the daily medication schedule and current adherence state."""
        res_id = resident_id or cls.DEFAULT_RESIDENT_ID
        meds = db.query(MedicationModel).filter(MedicationModel.resident_id == res_id).all()
        if not meds:
            cls.seed_default_medications(db, res_id)
            meds = db.query(MedicationModel).filter(MedicationModel.resident_id == res_id).all()

        return [
            {
                "id": m.id,
                "resident_id": m.resident_id,
                "medication_name": m.medication_name,
                "dosage": m.dosage,
                "scheduled_time": m.scheduled_time,
                "instructions": m.instructions,
                "status": m.status,
                "taken_at": m.taken_at.isoformat() if m.taken_at else None,
                "delay_minutes": m.delay_minutes,
                "adherence_rate": m.adherence_rate,
                "caregiver_alerted": m.caregiver_alerted
            }
            for m in meds
        ]

    @classmethod
    def seed_default_medications(cls, db: Session, resident_id: str):
        """Seeds standard daily prescriptions for Eleanor Vance."""
        default_prescriptions = [
            {
                "id": "med-lisinopril-01",
                "medication_name": "Lisinopril",
                "dosage": "10mg",
                "scheduled_time": "08:00",
                "instructions": "Take 1 tablet with breakfast for hypertension",
                "status": "TAKEN",
                "taken_at": datetime.now(timezone.utc),
                "delay_minutes": 15,
                "adherence_rate": 0.95
            },
            {
                "id": "med-calcium-02",
                "medication_name": "Calcium Citrate",
                "dosage": "500mg",
                "scheduled_time": "13:00",
                "instructions": "Take with midday meal for bone density",
                "status": "TAKEN",
                "taken_at": datetime.now(timezone.utc),
                "delay_minutes": 10,
                "adherence_rate": 0.92
            },
            {
                "id": "med-coq10-03",
                "medication_name": "CoQ10",
                "dosage": "100mg",
                "scheduled_time": "18:00",
                "instructions": "Evening dose with water for cardiovascular support",
                "status": "SCHEDULED",
                "taken_at": None,
                "delay_minutes": 0,
                "adherence_rate": 0.90
            }
        ]

        for p in default_prescriptions:
            exists = db.query(MedicationModel).filter(MedicationModel.id == p["id"]).first()
            if not exists:
                med = MedicationModel(
                    id=p["id"],
                    resident_id=resident_id,
                    medication_name=p["medication_name"],
                    dosage=p["dosage"],
                    scheduled_time=p["scheduled_time"],
                    instructions=p["instructions"],
                    status=p["status"],
                    taken_at=p["taken_at"],
                    delay_minutes=p["delay_minutes"],
                    adherence_rate=p["adherence_rate"],
                    caregiver_alerted=False
                )
                db.add(med)
        db.commit()

    @classmethod
    async def record_dose_action(
        cls,
        medication_id: str,
        action: str,  # 'TAKEN', 'MISSED', 'DELAYED'
        db: Session,
        delay_minutes: int = 0
    ) -> Dict[str, Any]:
        """
        Records adherence action on a medication dose.
        Emits a UnifiedEvent into the central event pipeline.
        If missed > 60m, triggers caregiver reminder without creating emergency CAD dispatch.
        """
        med = db.query(MedicationModel).filter(MedicationModel.id == medication_id).first()
        if not med:
            cls.seed_default_medications(db, cls.DEFAULT_RESIDENT_ID)
            med = db.query(MedicationModel).filter(MedicationModel.id == medication_id).first()
        if not med:
            raise ValueError(f"Medication with ID '{medication_id}' not found.")

        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.isoformat()
        act_upper = action.upper()

        if act_upper == "TAKEN":
            med.status = "TAKEN"
            med.taken_at = now_utc
            med.delay_minutes = delay_minutes
            med.adherence_rate = min(1.0, med.adherence_rate + 0.02)
            event_type = EventType.MEDICATION_TAKEN.value
            event_desc = f"{med.medication_name} {med.dosage} recorded as TAKEN."
        elif act_upper == "MISSED":
            med.status = "MISSED"
            med.delay_minutes = max(delay_minutes, 120)
            med.adherence_rate = max(0.5, med.adherence_rate - 0.05)
            event_type = EventType.MEDICATION_MISSED.value
            event_desc = f"{med.medication_name} {med.dosage} scheduled for {med.scheduled_time} was MISSED."
        else:
            med.status = "DELAYED"
            med.delay_minutes = max(delay_minutes, 30)
            event_type = EventType.MEDICATION_DELAYED.value
            event_desc = f"{med.medication_name} {med.dosage} delayed by {med.delay_minutes} minutes."

        # Emit event to central pipeline
        corr_id = f"corr-med-{uuid.uuid4().hex[:6]}"
        event = UnifiedEvent(
            event_id=f"evt-med-{uuid.uuid4().hex[:8]}",
            timestamp=now_iso,
            resident_id=med.resident_id,
            room_id="kitchen",
            source=EventSource.MEDICATION.value,
            event_type=event_type,
            payload={
                "medication_id": med.id,
                "medication_name": med.medication_name,
                "dosage": med.dosage,
                "scheduled_time": med.scheduled_time,
                "status": med.status,
                "delay_minutes": med.delay_minutes,
                "adherence_rate": med.adherence_rate,
                "description": event_desc
            },
            confidence=0.95,
            correlation_id=corr_id
        )
        await global_pipeline.ingest_event(event, db=db)

        # Caregiver notification if missed or significantly delayed
        caregiver_notified = False
        if act_upper in ["MISSED", "DELAYED"] and med.delay_minutes >= 60 and not med.caregiver_alerted:
            med.caregiver_alerted = True
            from app.models.schemas import Risk
            caregiver_req = NotifyCaregiverRequest(
                risk=Risk(
                    risk_level="MODERATE",
                    confidence=0.90,
                    reasons=[f"Prescription {med.medication_name} ({med.dosage}) delayed {med.delay_minutes} minutes"]
                ),
                custom_message=f"Eleanor has not taken her {med.scheduled_time} dose of {med.medication_name} {med.dosage} (Delayed {med.delay_minutes} min).",
                target_channels=["sms", "mobile_push"]
            )
            await CaregiverService.dispatch_notification(caregiver_req, db=db)
            caregiver_notified = True

        db.commit()

        return {
            "success": True,
            "medication_id": med.id,
            "medication_name": med.medication_name,
            "status": med.status,
            "delay_minutes": med.delay_minutes,
            "adherence_rate": med.adherence_rate,
            "caregiver_alerted": med.caregiver_alerted or caregiver_notified,
            "timestamp": now_iso
        }

    @classmethod
    def get_adherence_summary(cls, db: Session, resident_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates 7-day adherence percentage and compliance history."""
        res_id = resident_id or cls.DEFAULT_RESIDENT_ID
        meds = db.query(MedicationModel).filter(MedicationModel.resident_id == res_id).all()
        if not meds:
            cls.seed_default_medications(db, res_id)
            meds = db.query(MedicationModel).filter(MedicationModel.resident_id == res_id).all()

        total = len(meds)
        taken_count = sum(1 for m in meds if m.status == "TAKEN")
        missed_count = sum(1 for m in meds if m.status == "MISSED")
        delayed_count = sum(1 for m in meds if m.status == "DELAYED")
        avg_rate = round(sum(m.adherence_rate for m in meds) / max(1, total), 2)

        return {
            "resident_id": res_id,
            "total_prescriptions": total,
            "doses_taken": taken_count,
            "doses_missed": missed_count,
            "doses_delayed": delayed_count,
            "overall_adherence_rate": avg_rate,
            "adherence_percentage": f"{int(avg_rate * 100)}%",
            "status": "EXCELLENT" if avg_rate >= 0.90 else ("GOOD" if avg_rate >= 0.75 else "ATTENTION_NEEDED")
        }
