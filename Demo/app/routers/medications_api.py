"""
Medications REST API for NIRA Ambient Care.
Amazon Developer Hackathon 2026.

Exposes endpoints for:
- Viewing scheduled prescriptions & today's compliance
- Recording doses (TAKEN, MISSED, DELAYED)
- Generating adherence reports & history
- Triggering gentle reminders
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.medication_service import MedicationService

router = APIRouter(prefix="/api/v1/medications", tags=["Medications & Adherence"])


class RecordDoseRequest(BaseModel):
    medication_id: str = Field(..., description="Unique ID of scheduled prescription e.g. med-coq10-03")
    action: str = Field(..., description="'TAKEN', 'MISSED', or 'DELAYED'")
    delay_minutes: int = Field(0, ge=0, description="Minutes delayed past scheduled administration time")


class MedicationRemindRequest(BaseModel):
    medication_id: str
    channel: str = Field("echo_show", description="'echo_show', 'sms', 'push'")


@router.get("/schedule", summary="Fetch daily medication schedule and status")
async def get_medication_schedule(
    resident_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns today's medication schedule and completion states for Eleanor Vance."""
    schedule = MedicationService.get_schedule(db=db, resident_id=resident_id)
    return {
        "status": "success",
        "resident_id": resident_id or MedicationService.DEFAULT_RESIDENT_ID,
        "count": len(schedule),
        "schedule": schedule
    }


@router.post("/record", summary="Record medication adherence action")
async def record_medication_action(
    req: RecordDoseRequest,
    db: Session = Depends(get_db)
):
    """
    Records dose action (TAKEN, MISSED, DELAYED).
    Emits UnifiedEvent to the central multimodal pipeline.
    If missed > 60m, notifies caregiver without creating a 911 CAD emergency.
    """
    try:
        result = await MedicationService.record_dose_action(
            medication_id=req.medication_id,
            action=req.action,
            db=db,
            delay_minutes=req.delay_minutes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/adherence", summary="Get medication compliance & adherence statistics")
async def get_medication_adherence(
    resident_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns adherence metrics, doses completed, and risk compliance status."""
    summary = MedicationService.get_adherence_summary(db=db, resident_id=resident_id)
    return summary


@router.post("/remind", summary="Trigger gentle ambient medication reminder")
async def trigger_medication_reminder(
    req: MedicationRemindRequest,
    db: Session = Depends(get_db)
):
    """Delivers an ambient audio/visual reminder to Echo Show 15 for upcoming or pending dose."""
    schedule = MedicationService.get_schedule(db=db)
    med = next((m for m in schedule if m["id"] == req.medication_id), None)
    if not med:
        raise HTTPException(status_code=404, detail=f"Medication '{req.medication_id}' not found.")

    return {
        "status": "delivered",
        "channel": req.channel,
        "medication": med["medication_name"],
        "scheduled_time": med["scheduled_time"],
        "prompt": f"Eleanor, it's time for your {med['scheduled_time']} dose of {med['medication_name']} {med['dosage']}.",
        "is_simulated": True
    }
