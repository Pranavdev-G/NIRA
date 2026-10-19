"""
Aegis CARE Risk Engine.
Amazon Developer Hackathon 2026.

Integrates:
  1. Vision events & post-event motion telemetry
  2. ContextEngine environmental & location hazards
  3. PersonalBaselineEngine circadian routine deviations
  4. Wearable vitals & arrhythmia telemetry
  5. Conversational Alexa+ voice verification state machine

Implements strict risk level threshold rules:
  - LOW: Routine deviation minimal, normal sensor signals, verified safe.
  - MODERATE: Mild anomaly or unverified event requiring voice check.
  - HIGH: Confirmed fall or abnormal vitals + explicit 'Help me' -> Caregiver alert.
  - CRITICAL: Confirmed fall + abnormal vitals + NO response (silent emergency) -> Immediate CAD escalation.
"""

import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.models.enums import RiskLevel
from app.models.schemas import (
    Event, Context, Risk, VoiceResponse,
    RiskAssessmentResponse
)
from app.services.context_engine import ContextEngine
from app.services.baseline_engine import PersonalBaselineEngine
from app.services.risk_intelligence import MultimodalRiskIntelligence, ExplainableRiskResult


class AegisRiskEngine:
    """
    Central clinical & situational risk intelligence engine.
    """

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
    def _parse_voice_intent(cls, voice_response: Optional[VoiceResponse]) -> str:
        """Determines intent from voice response: 'safe', 'distress', 'timeout', or 'none'."""
        if not voice_response:
            return "none"

        if voice_response.is_timeout or not voice_response.transcript:
            return "timeout"

        if voice_response.intent:
            return voice_response.intent.lower()

        clean = re.sub(r"[^\w\s]", "", voice_response.transcript.lower())
        if any(kw in clean for kw in cls.SAFE_KEYWORDS) and not any(kw in clean for kw in cls.DISTRESS_KEYWORDS):
            return "safe"
        if any(kw in clean for kw in cls.DISTRESS_KEYWORDS):
            return "distress"

        # Ambiguous response defaults to distress for elderly safety
        return "distress"

    @classmethod
    def evaluate(
        cls,
        event: Event,
        context: Context,
        voice_response: Optional[VoiceResponse] = None
    ) -> RiskAssessmentResponse:
        """
        Synthesizes multimodal streams into an explainable risk assessment.
        """
        start_time = time.perf_counter()
        reasons: List[str] = []

        # 1. Context Synthesis
        context_enrichment = ContextEngine.merge_and_enrich(event, context)
        loc_mult = context_enrichment["location_multiplier"]
        reasons.extend(context_enrichment["context_reasons"])

        # 2. Personal Baseline Routine Deviation
        dev_score, dev_reasons, baseline_meta = PersonalBaselineEngine.calculate_deviation(
            location=event.location,
            activity=context.activity,
            timestamp_str=event.timestamp,
            provided_baseline_deviation=context.baseline_deviation
        )
        reasons.extend(dev_reasons)

        # 3. Biomechanical & Vision Signal Scoring
        base_score = 0.0
        event_lower = event.event_type.lower()
        movement_lower = event.movement_after_event.lower()

        is_confirmed_fall = False
        if "fall" in event_lower:
            is_confirmed_fall = event.confidence >= 0.70
            base_score += 48.0 * event.confidence
            reasons.append(f"Vision event '{event.event_type}' detected with {event.confidence:.0%} confidence")
        elif "thud" in event_lower or "impact" in event_lower:
            base_score += 32.0 * event.confidence
            reasons.append(f"Acoustic impact event '{event.event_type}' ({event.confidence:.0%})")
        elif "inactivity" in event_lower:
            base_score += 26.0 * event.confidence
            reasons.append(f"Prolonged immobility anomaly detected ({event.confidence:.0%})")
        else:
            base_score += 15.0 * event.confidence
            reasons.append(f"Ambient anomaly '{event.event_type}' ({event.confidence:.0%})")

        # Post-event movement scoring
        has_zero_movement = (movement_lower == "none")
        if has_zero_movement:
            base_score += 36.0
            reasons.append("Zero post-impact movement detected (prolonged motionless hazard)")
        elif "twitch" in movement_lower:
            base_score += 22.0
            reasons.append("Involuntary movement / slight twitching detected post-event")
        elif "crawling" in movement_lower:
            base_score += 15.0
            reasons.append("Post-event crawling detected (person unable to stand upright)")
        elif movement_lower == "normal":
            base_score -= 25.0
            reasons.append("Normal post-event movement detected (attenuating factor)")

        # 4. Wearable Telemetry & Vitals
        wear_lower = context.wearable_status.lower()
        has_abnormal_vitals = False
        if "high_heart_rate" in wear_lower or "tachycardia" in wear_lower:
            has_abnormal_vitals = True
            base_score += 18.0
            reasons.append("Wearable telemetry: Acute elevated heart rate (tachycardia)")
        elif "arrhythmia" in wear_lower:
            has_abnormal_vitals = True
            base_score += 25.0
            reasons.append("Wearable telemetry: Cardiac arrhythmia alert detected")
        elif "low_heart_rate" in wear_lower or "bradycardia" in wear_lower:
            has_abnormal_vitals = True
            base_score += 15.0
            reasons.append("Wearable telemetry: Abnormally depressed heart rate")

        # Apply location multiplier and environmental hazards
        adjusted_score = (base_score * loc_mult) + context_enrichment["environmental_hazard_score"] + (dev_score * 20.0)
        bounded_score = max(0.0, min(100.0, adjusted_score))

        # 5. Conversational Verification State Machine Rules
        voice_intent = cls._parse_voice_intent(voice_response)

        # -------------------------------------------------------------------
        # RULE SET EVALUATION
        # -------------------------------------------------------------------
        if voice_intent == "safe":
            # LOW: Routine deviation minimal, normal sensor signals, verified safe.
            risk_level = RiskLevel.LOW.value
            confidence = 0.94
            reasons.insert(0, f"User verbally confirmed safety ('{voice_response.transcript}'). Escalation sequence cancelled.")
            rec_action = "MONITOR_PASSIVELY"
            req_wellness = False
            req_caregiver = False
            req_emergency = False

        elif voice_intent == "timeout":
            # CRITICAL: Confirmed fall + abnormal vitals/zero movement + NO response (silent emergency) -> Immediate emergency escalation.
            risk_level = RiskLevel.CRITICAL.value
            confidence = 0.98
            reasons.insert(0, "SILENT EMERGENCY: No response received during wellness check window (presumed loss of consciousness)")
            rec_action = "IMMEDIATE_CAD_EMERGENCY_DISPATCH"
            req_wellness = False
            req_caregiver = True
            req_emergency = True

        elif voice_intent == "distress":
            # HIGH: Confirmed fall or abnormal vitals + explicit "Help me" response -> Trigger caregiver alert.
            # If both severe fall + abnormal vitals + distress -> Escalates to CRITICAL
            if (is_confirmed_fall and has_zero_movement) or has_abnormal_vitals:
                risk_level = RiskLevel.CRITICAL.value
                confidence = 0.96
                reasons.insert(0, f"Critical distress: User requested help ('{voice_response.transcript}') with compounding trauma/vital indicators")
                rec_action = "DISPATCH_EMERGENCY_SERVICES_AND_ALERT_CAREGIVER"
                req_wellness = False
                req_caregiver = True
                req_emergency = True
            else:
                risk_level = RiskLevel.HIGH.value
                confidence = 0.92
                reasons.insert(0, f"Distress confirmed: User requested assistance during wellness check ('{voice_response.transcript}')")
                rec_action = "ALERT_CAREGIVER_AND_PREPARE_CAD_PACKET"
                req_wellness = False
                req_caregiver = True
                req_emergency = False

        else:
            # Voice check has NOT occurred yet (Initial Assessment)
            if is_confirmed_fall and (has_zero_movement or has_abnormal_vitals or loc_mult >= 1.5):
                # Severe physical event requires immediate vocal re-check while queuing emergency
                risk_level = RiskLevel.CRITICAL.value if has_zero_movement and has_abnormal_vitals else RiskLevel.HIGH.value
                confidence = min(0.96, 0.70 + (event.confidence * 0.20))
                rec_action = "INITIATE_IMMEDIATE_WELLNESS_CHECK_AND_PREPARE_CAD"
                req_wellness = True
                req_caregiver = True
                req_emergency = (risk_level == RiskLevel.CRITICAL.value)

            elif bounded_score >= 35.0 or dev_score >= 0.50:
                # MODERATE: Mild anomaly or unverified event requiring a voice re-check / wellness check.
                risk_level = RiskLevel.MODERATE.value
                confidence = 0.82
                rec_action = "TRIGGER_ALEXA_WELLNESS_CHECK"
                req_wellness = True
                req_caregiver = False
                req_emergency = False

            else:
                # LOW: Routine deviation minimal, normal sensor signals.
                risk_level = RiskLevel.LOW.value
                confidence = 0.88
                rec_action = "PASSIVE_MONITORING"
                req_wellness = False
                req_caregiver = False
                req_emergency = False

        now_iso = datetime.now(timezone.utc).isoformat()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Compute rich explainable factors across all 14 dimensions
        explainable = MultimodalRiskIntelligence.evaluate(
            event=event,
            context=context,
            voice_response=voice_response
        )

        telemetry = {
            "composite_score": round(bounded_score, 1),
            "baseline_deviation": dev_score,
            "circadian_slot": baseline_meta["circadian_slot"],
            "location_multiplier": loc_mult,
            "voice_intent": voice_intent,
            "is_confirmed_fall": is_confirmed_fall,
            "has_zero_movement": has_zero_movement,
            "has_abnormal_vitals": has_abnormal_vitals,
            "contributing_factors": [f.model_dump() for f in explainable.contributing_factors],
            "suppressed_factors": [f.model_dump() for f in explainable.suppressed_factors],
            "sensor_conflict_detected": explainable.sensor_conflict_detected,
            "explainable_risk": explainable.model_dump()
        }

        return RiskAssessmentResponse(
            risk_level=risk_level,
            confidence=round(confidence, 2),
            reasons=reasons,
            recommended_action=rec_action,
            requires_wellness_check=req_wellness,
            requires_caregiver_alert=req_caregiver,
            requires_emergency_escalation=req_emergency,
            telemetry_breakdown=telemetry,
            evaluated_at=now_iso,
            latency_ms=round(elapsed_ms, 2)
        )

    @classmethod
    def evaluate_explainable(
        cls,
        event: Event,
        context: Context,
        voice_response: Optional[VoiceResponse] = None,
        correlation_id: Optional[str] = None
    ) -> ExplainableRiskResult:
        """Direct access to full multimodal explainable risk result."""
        return MultimodalRiskIntelligence.evaluate(
            event=event,
            context=context,
            voice_response=voice_response,
            correlation_id=correlation_id
        )
