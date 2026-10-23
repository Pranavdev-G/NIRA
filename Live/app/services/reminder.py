"""
Live Medical Reminder & Pill Adherence Verification Service.
Amazon Developer Hackathon 2026.

Features:
- Scheduled daily medication dosages
- Speech prompt generation ("Have you taken your medicine on specific dose?")
- Speech-to-text adherence verification ("Yes" / "No" / Reasons)
- Automatic SMS escalation to Caretaker via TextBEE on missed doses
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from Live.app.services.textbee import LiveTextBeeService
from Live.app.services.session import LiveSessionManager

logger = logging.getLogger("NIRA.LiveReminder")

DEFAULT_MEDICATIONS: List[Dict[str, Any]] = [
    {
        "id": "med_lisinopril",
        "name": "Lisinopril",
        "dose": "10 mg (1 tablet)",
        "condition": "Hypertension / Blood Pressure",
        "schedule_time": "14:00",
        "instructions": "Take with full glass of water. Do not skip.",
        "status": "PENDING",
        "last_taken": None
    },
    {
        "id": "med_metformin",
        "name": "Metformin",
        "dose": "500 mg (1 tablet)",
        "condition": "Glycemic Control / Blood Sugar",
        "schedule_time": "12:30",
        "instructions": "Take immediately with or after meals.",
        "status": "TAKEN",
        "last_taken": "2026-10-23T12:35:00Z"
    },
    {
        "id": "med_aspirin",
        "name": "Aspirin",
        "dose": "81 mg (1 chewable)",
        "condition": "Cardiovascular Defense",
        "schedule_time": "19:00",
        "instructions": "Evening cardiovascular prevention.",
        "status": "UPCOMING",
        "last_taken": None
    },
    {
        "id": "med_atorvastatin",
        "name": "Atorvastatin",
        "dose": "20 mg (1 tablet)",
        "condition": "Cholesterol Management",
        "schedule_time": "21:00",
        "instructions": "Take at bedtime.",
        "status": "UPCOMING",
        "last_taken": None
    }
]

_medications_list: List[Dict[str, Any]] = [dict(m) for m in DEFAULT_MEDICATIONS]


class LiveReminderService:
    """Manages medication adherence, vocal prompts, and caretaker alerts."""

    @classmethod
    def get_medications(cls) -> List[Dict[str, Any]]:
        global _medications_list
        return [dict(m) for m in _medications_list]

    @classmethod
    def get_active_reminder_prompt(cls, med_id: Optional[str] = None) -> Dict[str, Any]:
        global _medications_list
        target = None
        if med_id:
            target = next((m for m in _medications_list if m["id"] == med_id), None)
        if not target:
            target = next((m for m in _medications_list if m["status"] == "PENDING"), _medications_list[0])

        patient = LiveSessionManager.get_active_patient_info()
        prompt_text = (
            f"Hello {patient.get('name', 'Eleanor')}, it is time for your scheduled medicine: "
            f"{target['name']} {target['dose']} for {target['condition']}. "
            f"Have you taken your medication?"
        )

        return {
            "medication": target,
            "spoken_prompt": prompt_text,
            "question": f"Have you taken your {target['name']} ({target['dose']})?",
            "expected_responses": ["Yes, I took it", "No, not yet", "I forgot", "Taking it now"]
        }

    @classmethod
    async def process_user_adherence_response(
        cls,
        med_id: str,
        user_spoken_response: str,
        mongo_db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Analyzes resident's voice answer, updates pill status, and alerts caretaker if missed."""
        global _medications_list
        med = next((m for m in _medications_list if m["id"] == med_id), None)
        if not med:
            return {"success": False, "error": f"Medication {med_id} not found"}

        resp_lower = user_spoken_response.lower().strip()
        is_taken = any(affirm in resp_lower for affirm in [
            "yes", "yeah", "yep", "taken", "took it", "swallowed", "done", "already"
        ]) and not any(neg in resp_lower for neg in ["not", "no", "haven't", "havent", "forgot"])

        is_missed = any(neg in resp_lower for neg in [
            "no", "not yet", "forgot", "haven't", "havent", "didn't", "didnt", "refuse", "later"
        ]) or not is_taken

        caretaker = LiveSessionManager.get_active_caregiver()
        patient = LiveSessionManager.get_active_patient_info()
        now_iso = datetime.now(timezone.utc).isoformat()

        if is_taken:
            med["status"] = "TAKEN"
            med["last_taken"] = now_iso
            system_response = f"Thank you {patient.get('name', 'Eleanor')}. I have logged that you took {med['name']} {med['dose']}."
            alert_sent = False
        else:
            med["status"] = "MISSED"
            system_response = f"Please remember to take your {med['name']} {med['dose']} right away. I am sending an update to your caretaker {caretaker.get('caretaker_name', 'David Vance')}."

            # Dispatch TextBEE notification to caretaker
            sms_text = (
                f"💊 [NIRA MEDICATION ALERT] 💊\n\n"
                f"PATIENT: {patient.get('name')}\n"
                f"MISSED DOSE: {med['name']} {med['dose']}\n"
                f"SCHEDULED TIME: {med['schedule_time']}\n"
                f"RESIDENT RESPONSE: \"{user_spoken_response}\"\n\n"
                f"STATUS: Medication NOT confirmed taken.\n"
                f"ACTION: Caretaker verification requested."
            )
            try:
                await LiveTextBeeService.send_emergency_alert(
                    incident_id=f"INC-MED-{uuid.uuid4().hex[:6].upper()}",
                    patient_name=patient.get("name"),
                    severity="MEDICATION NON-ADHERENCE",
                    state_description=f"Senior reported: \"{user_spoken_response}\" when prompted for {med['name']} {med['dose']}",
                    needed_actions="Caretaker medication check-in & reminder call",
                    recipient_phone=caretaker.get("mobile_number"),
                    caretaker_name=caretaker.get("caretaker_name")
                )
                alert_sent = True
            except Exception as se:
                logger.error(f"[LiveReminder] SMS send note: {se}")
                alert_sent = False

        result = {
            "success": True,
            "medication": dict(med),
            "is_taken": is_taken,
            "user_response": user_spoken_response,
            "system_voice_reply": system_response,
            "caretaker_notified": not is_taken,
            "timestamp": now_iso
        }

        # Log adherence in MongoDB
        if mongo_db is not None:
            try:
                mongo_db.medication_logs.insert_one({
                    "id": f"log-med-{uuid.uuid4().hex[:8]}",
                    "medication_id": med["id"],
                    "medication_name": med["name"],
                    "dose": med["dose"],
                    "timestamp": now_iso,
                    "is_taken": is_taken,
                    "user_response": user_spoken_response
                })
            except Exception as me:
                logger.debug(f"[LiveReminder] Mongo log error: {me}")

        return result
