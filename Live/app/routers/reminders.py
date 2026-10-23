"""
Live Medical Pill Reminder API Router.
Amazon Developer Hackathon 2026.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from Live.app.database import get_mongo_db
from Live.app.services.reminder import LiveReminderService

router = APIRouter(prefix="/api/v1/live/reminders", tags=["Live Medical Reminder System"])


class VoiceAdherencePayload(BaseModel):
    medication_id: str = Field(..., description="Target medication ID (e.g. med_lisinopril)")
    user_spoken_response: str = Field(..., description="Resident speech transcript (e.g. 'Yes I took it' or 'No')")


@router.get("", summary="Get all scheduled daily medications")
def get_medications():
    return {
        "success": True,
        "medications": LiveReminderService.get_medications()
    }


@router.get("/active-prompt", summary="Get current active voice reminder prompt")
def get_active_prompt(med_id: Optional[str] = None):
    return LiveReminderService.get_active_reminder_prompt(med_id=med_id)


@router.post("/respond", summary="Submit resident voice adherence response")
async def respond_to_reminder(payload: VoiceAdherencePayload):
    mongo_db = get_mongo_db()
    result = await LiveReminderService.process_user_adherence_response(
        med_id=payload.medication_id,
        user_spoken_response=payload.user_spoken_response,
        mongo_db=mongo_db
    )
    return result
