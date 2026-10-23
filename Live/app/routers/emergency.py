"""
Live Emergency CAD Dispatch, Tracking, and TextBEE SMS Router.
Amazon Developer Hackathon 2026.
"""

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from Live.app.database import get_mongo_db
from Live.app.services.textbee import LiveTextBeeService
from Live.app.services.session import LiveSessionManager
from Live.app.services.emergency import LiveEmergencyTrackerService

router = APIRouter(prefix="/api/v1/live/emergency", tags=["Live Emergency CAD & SMS Gateway"])


class DispatchCADPayload(BaseModel):
    incident_id: Optional[str] = None
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None


class SendSMSPayload(BaseModel):
    incident_id: Optional[str] = None
    severity: str = Field("CRITICAL SEVERE", description="Severity level")
    state_description: Optional[str] = None
    needed_actions: Optional[str] = None
    recipient_phone: Optional[str] = None
    image_url: Optional[str] = None


@router.post("/trigger-cad", summary="Trigger live emergency ambulance CAD dispatch")
def trigger_ambulance_dispatch(payload: DispatchCADPayload):
    result = LiveEmergencyTrackerService.trigger_dispatch(
        incident_id=payload.incident_id,
        target_lat=payload.target_lat,
        target_lon=payload.target_lon
    )
    return {
        "success": True,
        "message": "Ambulance CAD Unit Medic-14 dispatched. Live tracking active.",
        "dispatch": result
    }


@router.get("/tracking", summary="Get live real-time ambulance tracking & door lock status")
def get_ambulance_tracking():
    status = LiveEmergencyTrackerService.get_tracking_status()
    return {
        "success": True,
        "tracking": status
    }


@router.post("/send-sms", summary="Dispatch severe emergency TextBEE SMS alert to caretaker")
async def send_emergency_sms(payload: SendSMSPayload):
    mongo_db = get_mongo_db()
    caretaker = LiveSessionManager.get_active_caregiver()
    patient = LiveSessionManager.get_active_patient_info()

    res = await LiveTextBeeService.send_emergency_alert(
        incident_id=payload.incident_id or "INC-LIVE-EMERGENCY",
        patient_name=patient.get("name", "Eleanor Vance"),
        severity=payload.severity,
        state_description=payload.state_description,
        needed_actions=payload.needed_actions,
        recipient_phone=payload.recipient_phone or caretaker.get("mobile_number"),
        image_url=payload.image_url,
        latitude=patient.get("latitude"),
        longitude=patient.get("longitude"),
        address=patient.get("address"),
        caretaker_name=caretaker.get("caretaker_name", "David Vance"),
        mongo_db=mongo_db
    )
    return res
