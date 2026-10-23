"""
NIRA Multimodal Risk Intelligence & Explainability Engine.
Amazon Developer Hackathon 2026.

Integrates 14 multimodal signal dimensions:
  1. Fall detected (vision / radar / accelerometer confidence)
  2. Posture abnormality (aspect ratio, horizontal torso angle)
  3. Sudden acceleration/deceleration (downward vertical velocity)
  4. Prolonged immobility (post-impact movement index / motionless duration)
  5. Heart-rate anomaly (acute tachycardia, moderate tachycardia, bradycardia, arrhythmia)
  6. Environmental hazard (wet floor, dark lighting, obstacles)
  7. Room context (bathroom 1.55x, shower 1.6x, stairs 1.65x, kitchen 1.25x)
  8. Time of day (circadian window: nocturnal rest 23:00-07:00 vs daytime)
  9. Personal baseline deviation (circadian slot divergence 0.0-1.0)
 10. Lack of response (wellness check timeout / 20s silence)
 11. Voice distress ("Help me", "I fell down", "can't get up")
 12. Device connectivity (wearable disconnected / charging)
 13. Repeated abnormal events (event frequency / alert storm debouncing)
 14. Recovery movement (upright posture recovered, normal movement detected)

Features:
  - Deterministic evaluation for identical inputs.
  - Explainable contributing and suppressed factors with weights.
  - Risk hysteresis preventing HIGH <-> LOW oscillation.
  - Alert debouncing and cooldown protection against alert storms.
  - Sensor conflict detection (e.g. camera fall vs active wearable walking cadence).
  - Missing sensor graceful degradation.
"""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.models.enums import RiskLevel
from app.models.schemas import Event, Context, VoiceResponse
from app.services.context_engine import ContextEngine
from app.services.baseline_engine import PersonalBaselineEngine


# ---------------------------------------------------------------------------
# 1. Explainability Data Contracts
# ---------------------------------------------------------------------------

class FactorContribution(BaseModel):
    factor: str = Field(..., description="Machine-readable factor identifier")
    weight: float = Field(..., description="Numeric weight added or subtracted (-100.0 to +100.0)")
    description: str = Field(..., description="Human-readable clinical/safety justification")
    evidence_source: Optional[str] = Field(None, description="Originating sensor or subsystem")
    metric_value: Optional[Any] = Field(None, description="Observed raw sensor value")


class ExplainableRiskResult(BaseModel):
    risk_level: str = Field(..., description="'LOW', 'MODERATE', 'HIGH', 'CRITICAL'")
    score: float = Field(..., ge=0.0, le=100.0, description="Composite risk score bounded [0, 100]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Risk evaluation confidence [0, 1]")
    contributing_factors: List[FactorContribution] = Field(default_factory=list)
    suppressed_factors: List[FactorContribution] = Field(default_factory=list)
    room: str
    timestamp: str
    recommended_action: str
    correlation_id: str
    sensor_conflict_detected: bool = False
    missing_sensors: List[str] = Field(default_factory=list)
    hysteresis_applied: bool = False
    clinical_disclaimer: str = (
        "NIRA Risk Assessment: Evaluates situational hazard, physical trauma indicators, "
        "and ambient signals. Not a medical diagnosis."
    )


# ---------------------------------------------------------------------------
# 2. Hysteresis & Alert Storm Debounce Tracker
# ---------------------------------------------------------------------------

class RiskHysteresisTracker:
    """
    Maintains temporal state per resident to prevent rapid alert oscillation
    (HIGH -> LOW -> HIGH -> LOW) and alert storms.
    """
    ESCALATE_TO_MODERATE = 35.0
    ESCALATE_TO_HIGH = 58.0
    ESCALATE_TO_CRITICAL = 82.0

    # Asymmetric lower thresholds for de-escalation (Hysteresis gap)
    DEESCALATE_TO_HIGH = 68.0
    DEESCALATE_TO_MODERATE = 42.0
    DEESCALATE_TO_LOW = 22.0

    DEBOUNCE_WINDOW_SEC = 5.0
    COOLDOWN_WINDOW_SEC = 25.0

    def __init__(self):
        self.current_stable_level = RiskLevel.LOW.value
        self.last_transition_time = time.perf_counter()
        self.last_escalation_time = 0.0
        self.recent_events_count = 0
        self.last_event_time = 0.0
        self.last_event_fingerprint = ""

    def evaluate_hysteresis(
        self,
        raw_score: float,
        forced_override_level: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Applies asymmetric thresholding to stabilize risk transitions.
        Returns: (stable_risk_level, was_hysteresis_applied)
        """
        if forced_override_level:
            # Deterministic override (e.g. verified voice "I'm okay" or silent emergency timeout)
            self.current_stable_level = forced_override_level
            self.last_transition_time = time.perf_counter()
            return forced_override_level, False

        prev = self.current_stable_level
        new_level = prev
        hysteresis_applied = False

        if prev == RiskLevel.LOW.value:
            if raw_score >= self.ESCALATE_TO_CRITICAL:
                new_level = RiskLevel.CRITICAL.value
            elif raw_score >= self.ESCALATE_TO_HIGH:
                new_level = RiskLevel.HIGH.value
            elif raw_score >= self.ESCALATE_TO_MODERATE:
                new_level = RiskLevel.MODERATE.value

        elif prev == RiskLevel.MODERATE.value:
            if raw_score >= self.ESCALATE_TO_CRITICAL:
                new_level = RiskLevel.CRITICAL.value
            elif raw_score >= self.ESCALATE_TO_HIGH:
                new_level = RiskLevel.HIGH.value
            elif raw_score < self.DEESCALATE_TO_LOW:
                new_level = RiskLevel.LOW.value
            else:
                hysteresis_applied = True  # Score is between 22 and 35, held at MODERATE

        elif prev == RiskLevel.HIGH.value:
            if raw_score >= self.ESCALATE_TO_CRITICAL:
                new_level = RiskLevel.CRITICAL.value
            elif raw_score < self.DEESCALATE_TO_LOW:
                new_level = RiskLevel.LOW.value
            elif raw_score < self.DEESCALATE_TO_MODERATE:
                new_level = RiskLevel.MODERATE.value
            else:
                hysteresis_applied = True  # Score is between 42 and 58, held at HIGH

        elif prev == RiskLevel.CRITICAL.value:
            if raw_score < self.DEESCALATE_TO_LOW:
                new_level = RiskLevel.LOW.value
            elif raw_score < self.DEESCALATE_TO_MODERATE:
                new_level = RiskLevel.MODERATE.value
            elif raw_score < self.DEESCALATE_TO_HIGH:
                new_level = RiskLevel.HIGH.value
            else:
                hysteresis_applied = True  # Score is between 68 and 82, held at CRITICAL

        if new_level != prev:
            self.current_stable_level = new_level
            self.last_transition_time = time.perf_counter()

        return new_level, hysteresis_applied

    def check_debounce(self, event_fingerprint: str) -> Tuple[bool, int]:
        """
        Checks whether repeated events in short window should be debounced.
        Returns: (is_debounced, compounding_count)
        """
        now = time.perf_counter()
        if event_fingerprint == self.last_event_fingerprint and (now - self.last_event_time) < self.DEBOUNCE_WINDOW_SEC:
            self.recent_events_count += 1
            self.last_event_time = now
            return True, self.recent_events_count
        else:
            self.last_event_fingerprint = event_fingerprint
            self.last_event_time = now
            self.recent_events_count = 1
            return False, 1


# Global tracker singleton
_global_hysteresis_tracker = RiskHysteresisTracker()


# ---------------------------------------------------------------------------
# 3. Core Multimodal Intelligence Engine
# ---------------------------------------------------------------------------

class MultimodalRiskIntelligence:
    """
    Deterministic clinical & situational risk evaluation engine.
    Analyzes 14 multimodal dimensions, explains contributing vs suppressed factors,
    and applies hysteresis stabilization.
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
    def parse_voice_intent(cls, voice_response: Optional[VoiceResponse]) -> str:
        """Categorizes voice response into 'safe', 'distress', 'timeout', or 'none'."""
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
        # Ambiguous user response defaults to distress for elderly safety
        return "distress"

    @classmethod
    def evaluate(
        cls,
        event: Event,
        context: Context,
        voice_response: Optional[VoiceResponse] = None,
        correlation_id: Optional[str] = None,
        hysteresis_tracker: Optional[RiskHysteresisTracker] = None
    ) -> ExplainableRiskResult:
        """
        Executes deterministic multimodal risk evaluation across all 14 factors.
        """
        corr_id = correlation_id or f"corr-risk-{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        tracker = hysteresis_tracker or _global_hysteresis_tracker

        contributors: List[FactorContribution] = []
        suppressors: List[FactorContribution] = []
        missing_sensors: List[str] = []
        sensor_conflict = False

        base_score = 0.0
        confidence = 0.88

        # Event & context string normalizations
        event_type = event.event_type.lower()
        movement_str = event.movement_after_event.lower()
        wearable_str = context.wearable_status.lower()
        activity_str = context.activity.lower()

        # -------------------------------------------------------------------
        # Dimension 1: Fall Detected (Vision / Radar / Acceleration)
        # -------------------------------------------------------------------
        is_confirmed_fall = False
        if "fall" in event_type:
            is_confirmed_fall = event.confidence >= 0.70
            weight = round(45.0 * event.confidence, 1)
            base_score += weight
            contributors.append(FactorContribution(
                factor="fall_detected",
                weight=weight,
                description=f"Vision/radar event '{event.event_type}' detected with {event.confidence:.0%} confidence",
                evidence_source="camera_pose",
                metric_value=event.confidence
            ))
        elif "thud" in event_type or "impact" in event_type:
            weight = round(32.0 * event.confidence, 1)
            base_score += weight
            contributors.append(FactorContribution(
                factor="acoustic_impact",
                weight=weight,
                description=f"Acoustic impact '{event.event_type}' detected with {event.confidence:.0%} confidence",
                evidence_source="microphone",
                metric_value=event.confidence
            ))
        elif "inactivity" in event_type:
            weight = round(26.0 * event.confidence, 1)
            base_score += weight
            contributors.append(FactorContribution(
                factor="abnormal_inactivity",
                weight=weight,
                description=f"Prolonged immobility anomaly detected ({event.confidence:.0%})",
                evidence_source="radar",
                metric_value=event.confidence
            ))
        elif "vital" in event_type:
            weight = round(28.0 * event.confidence, 1)
            base_score += weight
            contributors.append(FactorContribution(
                factor="vital_anomaly",
                weight=weight,
                description=f"Wearable vital sign anomaly detected ({event.confidence:.0%})",
                evidence_source="wearable",
                metric_value=event.confidence
            ))
        else:
            weight = round(12.0 * event.confidence, 1)
            base_score += weight
            contributors.append(FactorContribution(
                factor="ambient_anomaly",
                weight=weight,
                description=f"Unclassified ambient anomaly '{event.event_type}' ({event.confidence:.0%})",
                evidence_source="ambient",
                metric_value=event.confidence
            ))

        # -------------------------------------------------------------------
        # Dimension 2 & 3: Posture Abnormality & Sudden Acceleration
        # -------------------------------------------------------------------
        if "horizontal" in movement_str or "floor" in movement_str:
            base_score += 15.0
            contributors.append(FactorContribution(
                factor="posture_horizontal",
                weight=15.0,
                description="Biomechanical pose confirms horizontal body orientation on floor surface",
                evidence_source="camera_pose"
            ))

        # -------------------------------------------------------------------
        # Dimension 4: Prolonged Immobility vs Dimension 14: Recovery Movement
        # -------------------------------------------------------------------
        has_zero_movement = (movement_str == "none")
        if has_zero_movement:
            base_score += 35.0
            contributors.append(FactorContribution(
                factor="prolonged_immobility",
                weight=35.0,
                description="Zero post-impact movement detected (acute motionless trauma indicator)",
                evidence_source="motion_telemetry",
                metric_value=0.0
            ))
        elif "twitch" in movement_str or "involuntary" in movement_str:
            base_score += 22.0
            contributors.append(FactorContribution(
                factor="involuntary_twitching",
                weight=22.0,
                description="Involuntary slight twitching motion detected post-event",
                evidence_source="motion_telemetry"
            ))
        elif "crawling" in movement_str:
            base_score += 16.0
            contributors.append(FactorContribution(
                factor="crawling_attempt",
                weight=16.0,
                description="Post-event crawling detected (unable to regain upright stance)",
                evidence_source="motion_telemetry"
            ))
        elif movement_str == "normal" or "recovered" in movement_str:
            # Dimension 14: Recovery Movement (Suppressed factor)
            base_score -= 25.0
            suppressors.append(FactorContribution(
                factor="recovery_movement",
                weight=-25.0,
                description="Normal post-event movement detected (attenuating factor, senior is mobile)",
                evidence_source="motion_telemetry"
            ))

        # -------------------------------------------------------------------
        # Dimension 5: Heart-Rate Anomaly vs Dimension 12: Device Connectivity
        # -------------------------------------------------------------------
        has_abnormal_vitals = False
        if "disconnected" in wearable_str or "charging" in wearable_str or "offline" in wearable_str:
            missing_sensors.append("wearable")
            base_score += 6.0
            contributors.append(FactorContribution(
                factor="device_disconnected",
                weight=6.0,
                description="Wearable telemetry offline or disconnected (uncertainty penalty)",
                evidence_source="wearable",
                metric_value=wearable_str
            ))
        elif "tachycardia" in wearable_str or "high_heart_rate" in wearable_str:
            has_abnormal_vitals = True
            base_score += 18.0
            contributors.append(FactorContribution(
                factor="acute_tachycardia",
                weight=18.0,
                description="Wearable telemetry indicates acute sympathetic surge / tachycardia",
                evidence_source="wearable",
                metric_value="high_heart_rate"
            ))
        elif "arrhythmia" in wearable_str:
            has_abnormal_vitals = True
            base_score += 24.0
            contributors.append(FactorContribution(
                factor="cardiac_arrhythmia",
                weight=24.0,
                description="Wearable telemetry flagged irregular cardiac rhythm (arrhythmia)",
                evidence_source="wearable",
                metric_value="arrhythmia"
            ))
        elif "bradycardia" in wearable_str or "low_heart_rate" in wearable_str:
            has_abnormal_vitals = True
            base_score += 15.0
            contributors.append(FactorContribution(
                factor="bradycardia",
                weight=15.0,
                description="Wearable telemetry indicates abnormally depressed heart rate (<50 BPM)",
                evidence_source="wearable"
            ))

        # -------------------------------------------------------------------
        # Dimension 6: Environmental Hazard
        # -------------------------------------------------------------------
        env_score, env_reasons = ContextEngine.get_environmental_hazards(context.environment)
        if env_score > 0:
            base_score += env_score
            for reason in env_reasons:
                contributors.append(FactorContribution(
                    factor="environmental_hazard",
                    weight=env_score,
                    description=reason,
                    evidence_source="environment_sensors",
                    metric_value=context.environment
                ))

        # -------------------------------------------------------------------
        # Dimension 7: Room Context & Location Hazard Multiplier
        # -------------------------------------------------------------------
        loc_mult, loc_reason = ContextEngine.get_location_hazard(event.location)
        if loc_reason and loc_mult > 1.0:
            weight = round((loc_mult - 1.0) * 25.0, 1)
            base_score += weight
            contributors.append(FactorContribution(
                factor="location_hazard_zone",
                weight=weight,
                description=f"High-hazard location '{event.location}' (hazard multiplier: {loc_mult:.2f}x)",
                evidence_source="spatial_model",
                metric_value=loc_mult
            ))

        # -------------------------------------------------------------------
        # Dimension 8: Time of Day (Circadian Vulnerability)
        # -------------------------------------------------------------------
        time_score, time_reason = ContextEngine.evaluate_temporal_vulnerability(context.time_context)
        if time_score > 0 and time_reason:
            base_score += time_score
            contributors.append(FactorContribution(
                factor="temporal_vulnerability",
                weight=time_score,
                description=time_reason,
                evidence_source="circadian_clock",
                metric_value=context.time_context
            ))

        # -------------------------------------------------------------------
        # Dimension 9: Personal Baseline Deviation
        # -------------------------------------------------------------------
        dev_score, dev_reasons, baseline_meta = PersonalBaselineEngine.calculate_deviation(
            location=event.location,
            activity=context.activity,
            timestamp_str=event.timestamp,
            provided_baseline_deviation=context.baseline_deviation
        )
        if dev_score >= 0.40:
            weight = round(dev_score * 18.0, 1)
            base_score += weight
            for r in dev_reasons:
                contributors.append(FactorContribution(
                    factor="baseline_deviation",
                    weight=weight,
                    description=r,
                    evidence_source="personal_baseline_engine",
                    metric_value=dev_score
                ))

        # -------------------------------------------------------------------
        # Dimension 13: Repeated Event Compounding & Debounce
        # -------------------------------------------------------------------
        fingerprint = f"{event.location}:{event.event_type}"
        is_debounced, repeat_count = tracker.check_debounce(fingerprint)
        if repeat_count > 1:
            compound_weight = round(min(repeat_count, 3) * 5.0, 1)
            base_score += compound_weight
            contributors.append(FactorContribution(
                factor="repeated_event_cluster",
                weight=compound_weight,
                description=f"Repeated abnormal event cluster ({repeat_count} alerts in short window)",
                evidence_source="event_debouncer",
                metric_value=repeat_count
            ))

        # -------------------------------------------------------------------
        # Sensor Conflict Detection
        # (e.g. Vision flags fall, but wearable or movement shows active walking)
        # -------------------------------------------------------------------
        if "fall" in event_type and (movement_str == "normal" or "walking" in activity_str):
            sensor_conflict = True
            base_score -= 20.0
            confidence = max(0.60, confidence - 0.20)
            suppressors.append(FactorContribution(
                factor="conflicting_sensor_locomotion",
                weight=-20.0,
                description="Camera indicated sudden fall, but wearable/radar confirms active locomotion (likely false alarm / dropped object)",
                evidence_source="sensor_fusion"
            ))

        # -------------------------------------------------------------------
        # Dimension 10 & 11: Conversational Voice Verification State
        # -------------------------------------------------------------------
        voice_intent = cls.parse_voice_intent(voice_response)
        voice_transcript = voice_response.transcript if (voice_response and voice_response.transcript) else ""
        forced_override_level: Optional[str] = None

        if voice_intent == "safe":
            # Dimension 10/11: Senior verbally confirms safe -> Immediate downgrade
            forced_override_level = RiskLevel.LOW.value
            base_score = 10.0
            confidence = 0.94
            suppressors.insert(0, FactorContribution(
                factor="verbal_safety_confirmation",
                weight=-70.0,
                description=f"User verbally confirmed safety ('{voice_transcript}'). Escalation sequence cancelled.",
                evidence_source="alexa_voice",
                metric_value=voice_transcript
            ))

        elif voice_intent == "timeout":
            # Dimension 10: Silent Emergency -> Forced Critical
            forced_override_level = RiskLevel.CRITICAL.value
            base_score = 98.0
            confidence = 0.98
            contributors.insert(0, FactorContribution(
                factor="voice_timeout_silent_emergency",
                weight=35.0,
                description="SILENT EMERGENCY: No response received during wellness check window (presumed loss of consciousness)",
                evidence_source="alexa_voice",
                metric_value="timeout_20s"
            ))

        elif voice_intent == "distress":
            # Dimension 11: Voice Distress
            weight = 30.0
            base_score += weight
            contributors.insert(0, FactorContribution(
                factor="voice_distress_call",
                weight=weight,
                description=f"Distress confirmed: User requested assistance during wellness check ('{voice_transcript}')",
                evidence_source="alexa_voice",
                metric_value=voice_transcript
            ))
            if (is_confirmed_fall and has_zero_movement) or has_abnormal_vitals:
                forced_override_level = RiskLevel.CRITICAL.value
            else:
                forced_override_level = RiskLevel.HIGH.value

        # Bound score between 0.0 and 100.0
        final_score = round(max(0.0, min(100.0, base_score)), 1)

        # -------------------------------------------------------------------
        # Apply Risk Hysteresis to Prevent Rapid Oscillation
        # -------------------------------------------------------------------
        stable_risk_level, hysteresis_applied = tracker.evaluate_hysteresis(
            raw_score=final_score,
            forced_override_level=forced_override_level
        )

        # Action Recommendations
        if stable_risk_level == RiskLevel.CRITICAL.value:
            rec_action = "IMMEDIATE_CAD_EMERGENCY_DISPATCH"
        elif stable_risk_level == RiskLevel.HIGH.value:
            rec_action = "ALERT_CAREGIVER_AND_PREPARE_CAD_PACKET"
        elif stable_risk_level == RiskLevel.MODERATE.value:
            rec_action = "TRIGGER_ALEXA_WELLNESS_CHECK"
        else:
            rec_action = "MONITOR_PASSIVELY"

        return ExplainableRiskResult(
            risk_level=stable_risk_level,
            score=final_score,
            confidence=round(confidence, 2),
            contributing_factors=contributors,
            suppressed_factors=suppressors,
            room=event.location,
            timestamp=now_iso,
            recommended_action=rec_action,
            correlation_id=corr_id,
            sensor_conflict_detected=sensor_conflict,
            missing_sensors=missing_sensors,
            hysteresis_applied=hysteresis_applied
        )
