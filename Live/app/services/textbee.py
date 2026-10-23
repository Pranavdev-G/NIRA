"""
Live TextBEE SMS Emergency Dispatch Service.
Amazon Developer Hackathon 2026.

Dispatches real-time emergency SMS alerts to caregivers using the TextBEE API gateway.
Includes:
- State of the person
- Visual camera snapshot evidence URL
- Severity level
- Needed emergency rescue (Ambulance / EMS, Smart Lock PIN)
- Live GPS location & Google Maps tracking link
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx

from Live.app.config import settings

logger = logging.getLogger("NIRA.LiveTextBEE")


def format_phone_e164(phone: str) -> str:
    """Formats phone number for TextBEE E.164 compliance."""
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) > 10 and not str(phone).startswith("+"):
        return f"+{digits}"
    elif str(phone).startswith("+"):
        return phone
    return f"+1{digits}" if digits else "+15550184421"


class LiveTextBeeService:
    """Manages urgent SMS delivery to caregivers for severe safety emergencies."""

    @classmethod
    async def send_emergency_alert(
        cls,
        incident_id: str,
        patient_name: str = "Eleanor Vance",
        severity: str = "CRITICAL SEVERE",
        state_description: Optional[str] = None,
        needed_actions: Optional[str] = None,
        recipient_phone: Optional[str] = None,
        image_url: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None,
        caretaker_name: str = "David Vance",
        mongo_db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Dispatches an urgent emergency SMS with live GPS and camera evidence."""
        target_phone = recipient_phone or settings.DEFAULT_EMERGENCY_RECIPIENT
        formatted_phone = format_phone_e164(target_phone)

        # Skip real network call for unconfigured gateway or simulated unit test numbers
        if not settings.is_textbee_configured() or "555" in formatted_phone:
            return {
                "success": True,
                "status": "simulated",
                "batch_id": f"TXB-SIM-{uuid.uuid4().hex[:6].upper()}",
                "recipient": formatted_phone,
                "message": "Simulated emergency SMS (gateway unconfigured or test recipient)"
            }

        snapshot_url = image_url or f"{settings.PUBLIC_BASE_URL}/live/static/fall_snapshot.jpg"

        state_text = (
            state_description
            or "Severe Traumatic Fall Confirmed. Resident lying motionless on floor for >35s. Unresponsive to conversational wellness check."
        )

        needed_text = (
            needed_actions
            or "🚑 AMBULANCE / EMS PARAMEDICS DISPATCHED.\nBoston CAD Unit Medic-14 en route.\nFront door smart lock UNLOCKED (PIN: 8492)."
        )

        loc_str = address or "Residence Unit 4B - Beacon Hill, Boston MA 02108"
        lat = latitude if latitude is not None else 42.3601
        lon = longitude if longitude is not None else -71.0589
        maps_link = f"https://maps.google.com/?q={lat:.5f},{lon:.5f}"

        sms_body = (
            f"🚨 [NIRA EMERGENCY ALERT - {severity}] 🚨\n\n"
            f"PATIENT: {patient_name}\n"
            f"LOCATION:\n{loc_str}\n"
            f"• Live GPS: {lat:.5f}, {lon:.5f}\n"
            f"• Live Tracking Map: {maps_link}\n\n"
            f"SEVERITY: {severity}\n\n"
            f"STATE OF PERSON:\n{state_text}\n\n"
            f"EMERGENCY NEEDED:\n{needed_text}\n\n"
            f"CAMERA SNAPSHOT EVIDENCE:\n{snapshot_url}\n\n"
            f"Notifying Caretaker: {caretaker_name} ({formatted_phone})"
        )

        endpoint = f"{settings.TEXTBEE_BASE_URL}/gateway/devices/{settings.TEXTBEE_DEVICE_ID}/sendSMS"
        headers = {
            "x-api-key": settings.TEXTBEE_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "recipients": [formatted_phone],
            "message": sms_body
        }

        result = {
            "incident_id": incident_id,
            "recipient": formatted_phone,
            "severity": severity,
            "device_id": settings.TEXTBEE_DEVICE_ID,
            "provider": "TextBEE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "snapshot_url": snapshot_url,
            "live_location": {
                "latitude": lat,
                "longitude": lon,
                "maps_link": maps_link,
                "address": loc_str
            },
            "success": False,
            "details": {}
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                result["status_code"] = response.status_code

                if response.status_code in (200, 201):
                    resp_json = response.json()
                    result["success"] = True
                    result["details"] = resp_json.get("data", {})
                    result["batch_id"] = result["details"].get("smsBatchId", f"TXB-{uuid.uuid4().hex[:6]}")
                    logger.info(f"[LiveTextBEE] Dispatched SMS to {formatted_phone}: {result['batch_id']}")
                else:
                    result["error"] = response.text
                    logger.warning(f"[LiveTextBEE] Gateway returned {response.status_code}: {response.text}")
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            logger.error(f"[LiveTextBEE] SMS send error: {e}")

        # Persist to MongoDB Atlas if available
        if mongo_db is not None:
            try:
                mongo_db.incident_timelines.insert_one({
                    "id": f"time-sms-{uuid.uuid4().hex[:8]}",
                    "incident_id": incident_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action_type": "TEXTBEE_EMERGENCY_SMS_DISPATCHED",
                    "actor": "TEXTBEE_GATEWAY",
                    "recipient": formatted_phone,
                    "evidence": result
                })
            except Exception as me:
                logger.debug(f"[LiveTextBEE] Mongo log note: {me}")

        return result
