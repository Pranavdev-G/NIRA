"""
Risk Assessment Engine for Aegis Ambient Care.
Optimized for ultra-low latency (<20ms execution) within Alexa+ budget.
"""

from datetime import datetime, timezone
from typing import List
from app.models.enums import RiskLevel
from app.models.schemas import Event, Context, Risk, AssessRiskResponse


class RiskEngine:
    """
    Deterministic rule-assisted scoring engine incorporating ambient vision,
    motion telemetry, wearable vitals, and circadian deviation.
    """

    @classmethod
    def evaluate(cls, event: Event, context: Context) -> Risk:
        reasons: List[str] = []
        score = 0.0

        # 1. Event Type & Confidence Weighting
        event_lower = event.event_type.lower()
        if "fall" in event_lower:
            score += 45.0 * event.confidence
            reasons.append(f"Event type '{event.event_type}' detected with {event.confidence:.0%} confidence")
        elif "thud" in event_lower or "impact" in event_lower:
            score += 35.0 * event.confidence
            reasons.append(f"Acoustic impact '{event.event_type}' detected ({event.confidence:.0%})")
        elif "inactivity" in event_lower:
            score += 25.0 * event.confidence
            reasons.append(f"Prolonged inactivity detected ({event.confidence:.0%})")
        elif "vital" in event_lower:
            score += 30.0 * event.confidence
            reasons.append(f"Vital sign anomaly detected ({event.confidence:.0%})")
        else:
            score += 15.0 * event.confidence
            reasons.append(f"Unclassified anomaly '{event.event_type}' ({event.confidence:.0%})")

        # 2. Movement After Event (Critical Prognostic Indicator)
        movement_lower = event.movement_after_event.lower()
        if movement_lower == "none":
            score += 35.0
            reasons.append("Zero post-impact movement detected (acute immobilization hazard)")
        elif "twitch" in movement_lower or "involuntary" in movement_lower:
            score += 25.0
            reasons.append("Involuntary or slight twitching motion detected post-event")
        elif "crawling" in movement_lower:
            score += 18.0
            reasons.append("Post-event crawling movement detected (attempting recovery)")
        elif movement_lower == "normal":
            score -= 20.0
            reasons.append("Normal post-event movement detected (attenuating factor)")

        # 3. Location Hazard Multiplier
        loc_lower = event.location.lower()
        if "bath" in loc_lower or "shower" in loc_lower or "toilet" in loc_lower:
            score += 15.0
            reasons.append(f"High-hazard moisture location: '{event.location}'")
        elif "stair" in loc_lower:
            score += 20.0
            reasons.append(f"High-hazard vertical incline: '{event.location}'")
        elif "kitchen" in loc_lower:
            score += 8.0
            reasons.append(f"Hard surface zone: '{event.location}'")

        # 4. Environmental Multipliers
        env_lower = context.environment.lower()
        if "wet" in env_lower or "dark" in env_lower:
            score += 10.0
            reasons.append(f"Compounding environmental risk: '{context.environment}'")

        # 5. Baseline Deviation (Circadian / Behavioral Model)
        # baseline_deviation > 0.5 indicates significant divergence from historical norm
        if context.baseline_deviation >= 0.8:
            score += 20.0
            reasons.append(f"Severe baseline deviation ({context.baseline_deviation:.2f} > 0.80)")
        elif context.baseline_deviation >= 0.5:
            score += 10.0
            reasons.append(f"Moderate baseline deviation ({context.baseline_deviation:.2f})")

        # 6. Wearable Status / Vitals
        wear_lower = context.wearable_status.lower()
        if "high_heart_rate" in wear_lower or "tachycardia" in wear_lower:
            score += 15.0
            reasons.append("Wearable telemetry indicates acute elevated heart rate")
        elif "arrhythmia" in wear_lower:
            score += 22.0
            reasons.append("Wearable telemetry indicates cardiac arrhythmia warning")
        elif "disconnected" in wear_lower:
            score += 5.0
            reasons.append("Wearable telemetry offline or disconnected")

        # 7. Time Context
        time_lower = context.time_context.lower()
        if "night" in time_lower or "sleep" in time_lower:
            score += 8.0
            reasons.append(f"Off-peak temporal risk: '{context.time_context}'")

        # Bound score between 0.0 and 100.0
        bounded_score = max(0.0, min(100.0, score))
        confidence = min(0.98, max(0.55, 0.50 + (bounded_score / 200.0) + (event.confidence * 0.25)))

        # Categorize Risk Level
        if bounded_score >= 70.0:
            risk_level = RiskLevel.CRITICAL.value
        elif bounded_score >= 45.0:
            risk_level = RiskLevel.HIGH.value
        elif bounded_score >= 25.0:
            risk_level = RiskLevel.MODERATE.value
        else:
            risk_level = RiskLevel.LOW.value

        return Risk(
            risk_level=risk_level,
            confidence=round(confidence, 2),
            reasons=reasons
        )

    @classmethod
    def evaluate_and_respond(cls, event: Event, context: Context, start_time_ms: float = 0.0) -> AssessRiskResponse:
        risk = cls.evaluate(event, context)
        
        req_wellness = risk.risk_level in [RiskLevel.MODERATE.value, RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
        req_caregiver = risk.risk_level in [RiskLevel.MODERATE.value, RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
        req_emergency = risk.risk_level == RiskLevel.CRITICAL.value

        if risk.risk_level == RiskLevel.CRITICAL.value:
            rec_action = "IMMEDIATE_WELLNESS_CHECK_AND_PREPARE_CAD_ESCALATION"
        elif risk.risk_level == RiskLevel.HIGH.value:
            rec_action = "INITIATE_WELLNESS_CHECK_AND_NOTIFY_CAREGIVER"
        elif risk.risk_level == RiskLevel.MODERATE.value:
            rec_action = "INITIATE_WELLNESS_CHECK"
        else:
            rec_action = "PASSIVE_MONITORING"

        now_iso = datetime.now(timezone.utc).isoformat()

        return AssessRiskResponse(
            risk=risk,
            requires_wellness_check=req_wellness,
            requires_caregiver_alert=req_caregiver,
            requires_emergency_escalation=req_emergency,
            recommended_action=rec_action,
            evaluated_at=now_iso,
            latency_ms=0.0  # Will be populated by caller
        )
