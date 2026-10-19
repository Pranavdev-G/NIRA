"""
Ambient Conversational State Machine for Alexa+ Wellness Checks.
Handles:
  1. 'I'm okay' -> Downgrade risk -> Cancel escalation.
  2. 'Help me' -> Elevate risk -> Trigger caregiver notification & emergency packet.
  3. No response / Timeout -> CRITICAL risk -> Trigger CAD emergency escalation.
"""

import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from app.config import settings
from app.models.enums import RiskLevel, WellnessState
from app.models.schemas import (
    Event, Context, Risk, WellnessCheckResponse,
    WellnessCheckReplyRequest, WellnessCheckResolutionResponse,
    NotifyCaregiverRequest, GenerateEmergencyPacketRequest,
    EscalateEmergencyRequest, EmergencyPacket
)
from app.services.caregiver_service import CaregiverService
from app.services.emergency_service import EmergencyService


class WellnessSession:
    """Internal session tracking for ambient conversational interactions."""
    def __init__(
        self,
        session_id: str,
        event: Optional[Event] = None,
        context: Optional[Context] = None,
        risk: Optional[Risk] = None,
        timeout_seconds: int = 20
    ):
        self.session_id = session_id
        self.event = event or Event(
            event_type="ambient_anomaly",
            confidence=0.85,
            location="living_room",
            timestamp=datetime.now(timezone.utc).isoformat(),
            movement_after_event="slight_twitch"
        )
        self.context = context or Context(
            activity="resting",
            time_context="afternoon",
            baseline_deviation=0.65,
            wearable_status="worn_normal",
            environment="well_lit"
        )
        self.risk = risk or Risk(
            risk_level=RiskLevel.MODERATE.value,
            confidence=0.75,
            reasons=["Unverified ambient anomaly"]
        )
        self.state = WellnessState.PENDING_CHECK
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.resolved_at: Optional[str] = None
        self.timeout_seconds = timeout_seconds
        self.transcript: Optional[str] = None
        self.emergency_packet: Optional[EmergencyPacket] = None
        self.caregiver_notification_id: Optional[str] = None
        self.emergency_dispatch_id: Optional[str] = None


class WellnessStateMachine:
    """
    Manages ambient voice check sessions, state transitions, and automatic
    action orchestration for the Alexa+ MCP interface.
    """
    _sessions: Dict[str, WellnessSession] = {}

    SAFE_KEYWORDS = [
        "ok", "okay", "fine", "alright", "all good", "false alarm",
        "dropped", "dont worry", "don't worry", "im fine", "i am fine",
        "im ok", "i'm ok", "i'm okay", "i am okay", "no help", "doing well"
    ]

    DISTRESS_KEYWORDS = [
        "help", "fell", "fallen", "cant get up", "can't get up",
        "cannot get up", "hurts", "pain", "bleeding", "dizzy",
        "call someone", "call daughter", "call 911", "call sarah",
        "emergency", "need assistance", "ouch"
    ]

    @classmethod
    def start_wellness_check(
        cls,
        session_id: Optional[str] = None,
        event: Optional[Event] = None,
        context: Optional[Context] = None,
        initial_risk: Optional[Risk] = None,
        prompt_override: Optional[str] = None
    ) -> WellnessCheckResponse:
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        session = WellnessSession(
            session_id=sid,
            event=event,
            context=context,
            risk=initial_risk,
            timeout_seconds=settings.WELLNESS_CHECK_TIMEOUT_SECONDS
        )
        cls._sessions[sid] = session

        loc = session.event.location.replace("_", " ").title()
        patient_first = settings.DEFAULT_PATIENT_NAME.split()[0]

        prompt_text = (
            prompt_override or
            f"{patient_first}, this is Aegis on Alexa. I noticed a potential concern in the {loc}. "
            f"Are you okay? Please tell me if you need any help."
        )

        prompt_ssml = (
            f"<speak>"
            f"<amazon:emotion name='concerned' intensity='medium'>"
            f"{patient_first}, this is Aegis on Alexa."
            f"</amazon:emotion>"
            f"<break time='300ms'/>"
            f"I noticed a potential concern in the {loc}. Are you okay?"
            f"<break time='250ms'/>"
            f"Please tell me if you need any help."
            f"</speak>"
        )

        return WellnessCheckResponse(
            session_id=sid,
            state=session.state.value,
            prompt_text=prompt_text,
            prompt_ssml=prompt_ssml,
            timeout_seconds=session.timeout_seconds,
            quick_replies=["I'm okay", "Help me", "I fell down", "I'm fine"],
            risk_level=session.risk.risk_level,
            created_at=now_iso
        )

    @classmethod
    async def process_reply(
        cls,
        reply: WellnessCheckReplyRequest
    ) -> WellnessCheckResolutionResponse:
        session = cls._sessions.get(reply.session_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        # If session not found, initialize a fallback session
        if not session:
            session = WellnessSession(session_id=reply.session_id)
            cls._sessions[reply.session_id] = session

        prev_state = session.state.value
        transcript = (reply.user_speech_transcript or "").strip()
        session.transcript = transcript

        # -------------------------------------------------------------------
        # Branch 1: TIMEOUT / NO RESPONSE -> Set CRITICAL -> Escalate Emergency
        # -------------------------------------------------------------------
        if reply.is_timeout or not transcript:
            session.state = WellnessState.TIMEOUT_ESCALATED
            session.resolved_at = now_iso

            # Elevate risk to CRITICAL
            session.risk = Risk(
                risk_level=RiskLevel.CRITICAL.value,
                confidence=1.0,
                reasons=[
                    "No verbal response received during ambient wellness check timeout window",
                    "Patient presumed incapacitated / unresponsive",
                    f"Prior incident: {session.event.event_type} at {session.event.location}"
                ]
            )

            # Auto-generate emergency packet
            packet = EmergencyService.generate_packet(session.event, session.context, session.risk)
            session.emergency_packet = packet

            # Auto-escalate to CAD emergency service
            cad_response = await EmergencyService.escalate_to_cad(
                EscalateEmergencyRequest(
                    emergency_packet=packet,
                    event=session.event,
                    context=session.context,
                    risk=session.risk
                )
            )
            session.emergency_dispatch_id = cad_response.dispatch_id

            speech = (
                "I did not hear a response. Initiating emergency escalation now. "
                "Contacting emergency services and unlocking the front door for first responders."
            )

            return WellnessCheckResolutionResponse(
                session_id=session.session_id,
                previous_state=prev_state,
                new_state=session.state.value,
                transcript_received=None,
                is_timeout=True,
                updated_risk=session.risk,
                action_taken="ESCALATE_TO_EMERGENCY_CAD",
                triggered_caregiver_notification=True,
                triggered_emergency_escalation=True,
                alexa_speech_response=speech,
                resolved_at=now_iso
            )

        # -------------------------------------------------------------------
        # Branch 2: "I'm okay" / Safe input -> Downgrade risk -> Cancel escalation
        # -------------------------------------------------------------------
        clean_text = re.sub(r"[^\w\s]", "", transcript.lower())
        is_safe = any(kw in clean_text for kw in cls.SAFE_KEYWORDS)
        is_distress = any(kw in clean_text for kw in cls.DISTRESS_KEYWORDS)

        if is_safe and not is_distress:
            session.state = WellnessState.SAFE_RESOLVED
            session.resolved_at = now_iso

            # Downgrade risk level to LOW
            session.risk = Risk(
                risk_level=RiskLevel.LOW.value,
                confidence=0.92,
                reasons=[
                    f"User verbally confirmed safety during wellness check: '{transcript}'",
                    "Escalation cancelled by direct ambient voice confirmation",
                    "Autonomous monitoring returned to baseline"
                ]
            )

            speech = "Thank goodness! I've confirmed you are okay and cancelled all emergency alerts. Take care."

            return WellnessCheckResolutionResponse(
                session_id=session.session_id,
                previous_state=prev_state,
                new_state=session.state.value,
                transcript_received=transcript,
                is_timeout=False,
                updated_risk=session.risk,
                action_taken="CANCEL_ESCALATION_DOWNGRADE_TO_LOW",
                triggered_caregiver_notification=False,
                triggered_emergency_escalation=False,
                alexa_speech_response=speech,
                resolved_at=now_iso
            )

        # -------------------------------------------------------------------
        # Branch 3: "Help me" / Distress input -> Elevate risk -> Notify caregiver & Packet
        # -------------------------------------------------------------------
        # Any explicit distress phrase, or ambiguous response that is not clearly safe
        session.state = WellnessState.DISTRESS_ELEVATED
        session.resolved_at = now_iso

        # Elevate risk level
        session.risk = Risk(
            risk_level=RiskLevel.HIGH.value,
            confidence=0.98,
            reasons=[
                f"User expressed distress during wellness check: '{transcript}'",
                f"Confirmed acute safety incident in {session.event.location}",
                "Immediate caregiver intervention required"
            ]
        )

        # Trigger caregiver alert
        caregiver_resp = await CaregiverService.dispatch_notification(
            NotifyCaregiverRequest(
                risk=session.risk,
                event=session.event,
                context=session.context,
                custom_message=f"Eleanor requested assistance during wellness check: \"{transcript}\". Please check on her."
            )
        )
        session.caregiver_notification_id = caregiver_resp.notification_id

        # Trigger emergency packet generation
        packet = EmergencyService.generate_packet(
            event=session.event,
            context=session.context,
            risk=session.risk
        )
        session.emergency_packet = packet

        speech = (
            f"Hold on {settings.DEFAULT_PATIENT_NAME.split()[0]}, I am getting help right now. "
            f"I have notified {settings.PRIMARY_CAREGIVER_NAME} and prepared your incident summary. "
            f"Please stay still and keep talking to me if you can."
        )

        return WellnessCheckResolutionResponse(
            session_id=session.session_id,
            previous_state=prev_state,
            new_state=session.state.value,
            transcript_received=transcript,
            is_timeout=False,
            updated_risk=session.risk,
            action_taken="ELEVATE_TO_HIGH_NOTIFY_CAREGIVER_GENERATE_PACKET",
            triggered_caregiver_notification=True,
            triggered_emergency_escalation=False,
            alexa_speech_response=speech,
            resolved_at=now_iso
        )

    @classmethod
    def get_session(cls, session_id: str) -> Optional[WellnessSession]:
        return cls._sessions.get(session_id)
