"""
Authoritative Multimodal Risk Engine for NIRA Live Core.
Amazon Developer Hackathon 2026.

Integrates:
- 14 multimodal signals from SignalExtractor
- Dynamic context hazard multipliers (ContextEngine)
- Dynamic baseline immobility tolerances (BaselineEngineAdapter)
- Contradictory sensor resolution & missing sensor re-weighting
- Risk hysteresis to prevent alert flapping
- Authoritative action recommendation (WELLNESS_CHECK, ESCALATE, CAD_DISPATCH, RESOLVE)
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from Live.core.models import (
    LiveEvent,
    EventType,
    ZoneType,
    SeverityLevel,
    RecommendedAction,
    RiskAssessment,
    SignalEvidence
)
from Live.core.context_engine import ContextEngine
from Live.core.baseline_engine import BaselineEngineAdapter
from Live.core.risk_intelligence import SignalExtractor

logger = logging.getLogger("NIRA.LiveCore.RiskEngine")

# Risk Level Score Thresholds
THRESH_LOW = 0.25
THRESH_MEDIUM = 0.50
THRESH_HIGH = 0.70
THRESH_CRITICAL = 0.85

# Hysteresis Reset Floor
HYSTERESIS_NORMAL_CEILING = 0.22


class RiskEngine:
    """
    Authoritative Multimodal Risk Engine for NIRA Live.
    Computes composite clinical and environmental risk.
    """

    def __init__(self, context_engine: ContextEngine, baseline_engine: BaselineEngineAdapter):
        self.context_engine = context_engine
        self.baseline_engine = baseline_engine
        self.extractor = SignalExtractor(context_engine, baseline_engine)

        # Previous assessment for hysteresis tracking
        self._last_assessment: Optional[RiskAssessment] = None

    def assess_risk(
        self,
        trigger_event: Optional[LiveEvent],
        recent_events: List[LiveEvent],
        active_zone: ZoneType = ZoneType.LIVING_ROOM,
        voice_state: Optional[Dict[str, Any]] = None,
        vitals_state: Optional[Dict[str, Any]] = None,
        hardware_health: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """
        Evaluates current resident state across all multimodal signals.
        Returns authoritative RiskAssessment. Never marks safe if critical hazards present.
        """
        assessment_id = f"risk-{uuid.uuid4().hex[:10]}"
        hour = datetime.now().hour
        ctx = self.context_engine.get_context(active_zone, hour)

        # 1. Extract all 14 signals
        signals = self.extractor.extract_signals(
            trigger_event=trigger_event,
            recent_events=recent_events,
            active_zone=active_zone,
            voice_state=voice_state,
            vitals_state=vitals_state,
            hardware_health=hardware_health
        )

        # 2. Contradictory Sensor Resolution & Critical Overrides
        voice_distress_active = any(s.signal_name == "voice_distress" and s.is_abnormal for s in signals)
        silence_active = any(s.signal_name == "silence_no_response" and s.is_abnormal for s in signals)
        fall_active = any(s.signal_name == "fall_probability" and s.is_abnormal for s in signals)
        collapse_posture = any(s.signal_name == "posture" and s.is_abnormal for s in signals)
        safe_response_active = any(s.signal_name == "recovery_movement" and s.raw_value is True for s in signals)

        # Calculate base weighted sum
        positive_weight_sum = 0.0
        weighted_score_accum = 0.0

        for sig in signals:
            if sig.signal_name == "recovery_movement":
                # Attenuator applied at the end
                continue
            positive_weight_sum += sig.weight
            weighted_score_accum += sig.risk_contribution

        # Re-normalize if missing sensors reduced weights
        base_score = (weighted_score_accum / positive_weight_sum) if positive_weight_sum > 0 else 0.1

        # Apply Environmental Hazard Multiplier
        composite_score = base_score * ctx.hazard_multiplier

        # Apply Recovery Attenuator if confirmed safe
        if safe_response_active and not (voice_distress_active or silence_active):
            composite_score = max(0.08, composite_score - 0.35)

        # Critical Overrides: If voice distress or unresponsiveness confirmed with fall/collapse
        if voice_distress_active and (fall_active or collapse_posture):
            composite_score = max(0.88, composite_score)  # Direct Critical
        elif silence_active and (fall_active or collapse_posture):
            composite_score = max(0.92, composite_score)  # Unconscious collapse = Emergency CAD
        elif fall_active and collapse_posture:
            composite_score = max(0.72, composite_score)  # Confirmed fall = High risk verification

        # 3. Apply Risk Hysteresis
        # If currently in High/Critical, do not drop back to Normal on minor noise
        if self._last_assessment and self._last_assessment.risk_level in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            if not safe_response_active:
                composite_score = max(composite_score, self._last_assessment.overall_score * 0.85)

        composite_score = round(min(1.0, max(0.0, composite_score)), 3)

        # 4. Map Score to Severity Level
        if composite_score >= THRESH_CRITICAL:
            risk_level = SeverityLevel.CRITICAL
            recommended_action = RecommendedAction.DISPATCH_EMERGENCY_CAD
        elif composite_score >= THRESH_HIGH:
            risk_level = SeverityLevel.HIGH
            recommended_action = RecommendedAction.ESCALATE_CAREGIVER
        elif composite_score >= THRESH_MEDIUM:
            risk_level = SeverityLevel.MEDIUM
            recommended_action = RecommendedAction.TRIGGER_WELLNESS_CHECK
        elif composite_score >= THRESH_LOW:
            risk_level = SeverityLevel.LOW
            recommended_action = RecommendedAction.CONTINUE_MONITORING
        else:
            risk_level = SeverityLevel.LOW
            recommended_action = RecommendedAction.CONTINUE_MONITORING

        # 5. Dynamic baseline tolerance for immobility
        tolerance_sec = self.baseline_engine.get_dynamic_threshold_seconds(active_zone, hour)

        assessment = RiskAssessment(
            assessment_id=assessment_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            resident_id="resident_eleanor_vance",
            risk_level=risk_level,
            overall_score=composite_score,
            confidence=0.94 if (fall_active or voice_distress_active or silence_active) else 0.82,
            contributing_signals=signals,
            context_modifiers={
                "zone": active_zone.value,
                "zone_risk_tier": ctx.zone_risk_tier,
                "circadian_phase": ctx.circadian_phase,
                "hazard_multiplier": ctx.hazard_multiplier,
                "is_wet_floor": ctx.is_wet_floor,
                "is_dark": ctx.is_dark
            },
            baseline_tolerance_sec=tolerance_sec,
            recommended_action=recommended_action
        )

        self._last_assessment = assessment
        return assessment

    def reset_hysteresis(self):
        """Clears previous assessment memory."""
        self._last_assessment = None
