"""
Comprehensive Test Suite for NIRA Multimodal Risk Intelligence Layer.
Amazon Developer Hackathon 2026.

Tests all 10 required clinical and ambient edge cases:
  1. False Alarm (Dropped object + Verbal safety confirmation)
  2. Responsive Emergency (Kitchen fall + Explicit 'Help me' distress call)
  3. Silent Emergency (Nocturnal bathroom fall + Immobility + Voice Timeout)
  4. Recovery (Sudden drop followed by upright mobility recovery)
  5. Noisy Sensor (Solitary sensor spike without multimodal corroboration)
  6. Missing Sensor (Wearable offline/charging, graceful radar fallback)
  7. Conflicting Sensor (Vision fall false flag vs Wearable active walking cadence)
  8. Delayed Event (Historical timestamp handling without state disruption)
  9. Repeated Event & Alert Storm Debounce (Event cluster compounding & Hysteresis)
 10. Normal Elderly Activity (Baseline daytime reading / cooking)
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import datetime, timezone

from app.models.enums import RiskLevel
from app.models.schemas import Event, Context, VoiceResponse
from app.services.risk_intelligence import (
    MultimodalRiskIntelligence, RiskHysteresisTracker, ExplainableRiskResult
)


# ---------------------------------------------------------------------------
# 1. False Alarm Scenario
# ---------------------------------------------------------------------------

def test_scenario_false_alarm():
    """
    False Alarm:
      - Senior drops a heavy book in the living room (acoustic thud).
      - Senior verbally answers: "I'm okay, Alexa! I just dropped my reading glasses."
      - Risk must resolve to LOW, with verbal confirmation recorded in suppressed_factors.
    """
    event = Event(
        event_type="loud_thud",
        confidence=0.60,
        location="living_room",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    context = Context(
        activity="reading",
        time_context="afternoon",
        baseline_deviation=0.10,
        wearable_status="worn_normal",
        environment="well_lit"
    )
    voice = VoiceResponse(transcript="I'm okay, Alexa! I just dropped my reading glasses.", is_timeout=False)

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=voice)

    assert result.risk_level == RiskLevel.LOW.value
    assert result.score <= 20.0
    assert any("verbal_safety_confirmation" in f.factor for f in result.suppressed_factors)
    assert any("confirmed safety" in f.description.lower() for f in result.suppressed_factors)
    assert result.recommended_action == "MONITOR_PASSIVELY"


# ---------------------------------------------------------------------------
# 2. Responsive Emergency Scenario
# ---------------------------------------------------------------------------

def test_scenario_responsive_emergency():
    """
    Responsive Emergency:
      - Fall in kitchen, crawling post-event posture, heart rate elevated.
      - Senior answers: "Help me, Alexa! I slipped and hurt my wrist, I can't get up!"
      - Risk must elevate to HIGH or CRITICAL with explicit voice distress contributor.
    """
    event = Event(
        event_type="fall_detected",
        confidence=0.88,
        location="kitchen",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="crawling"
    )
    context = Context(
        activity="cooking",
        time_context="morning",
        baseline_deviation=0.60,
        wearable_status="high_heart_rate",
        environment="well_lit"
    )
    voice = VoiceResponse(transcript="Help me, Alexa! I slipped and hurt my wrist, I can't get up!", is_timeout=False)

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=voice)

    assert result.risk_level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
    assert result.score >= 65.0
    factors = [f.factor for f in result.contributing_factors]
    assert "voice_distress_call" in factors
    assert "fall_detected" in factors
    assert "crawling_attempt" in factors


# ---------------------------------------------------------------------------
# 3. Silent Emergency Scenario
# ---------------------------------------------------------------------------

def test_scenario_silent_emergency():
    """
    Silent Emergency:
      - Nocturnal fall on wet bathroom floor at 2:15 AM, zero post-fall movement, tachycardia.
      - 20s voice timeout elapsed with zero verbal response (presumed unconscious).
      - Must force CRITICAL risk with CAD dispatch action recommendation.
    """
    event = Event(
        event_type="fall_detected",
        confidence=0.96,
        location="bathroom",
        timestamp="2026-10-19T02:15:00Z",
        movement_after_event="none"
    )
    context = Context(
        activity="bathing",
        time_context="night_time",
        baseline_deviation=0.92,
        wearable_status="high_heart_rate",
        environment="dark_room_wet_floor"
    )
    voice = VoiceResponse(transcript=None, is_timeout=True)

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=voice)

    assert result.risk_level == RiskLevel.CRITICAL.value
    assert result.score >= 90.0
    assert result.confidence >= 0.95
    assert result.recommended_action == "IMMEDIATE_CAD_EMERGENCY_DISPATCH"
    factors = [f.factor for f in result.contributing_factors]
    assert "voice_timeout_silent_emergency" in factors
    assert "prolonged_immobility" in factors
    assert "location_hazard_zone" in factors


# ---------------------------------------------------------------------------
# 4. Recovery Scenario
# ---------------------------------------------------------------------------

def test_scenario_recovery():
    """
    Recovery:
      - Sudden drop / slip occurs, but posture recovers and post-event movement is normal.
      - Suppressed factor 'recovery_movement' attenuates score by -25.0.
    """
    event = Event(
        event_type="possible_fall",
        confidence=0.65,
        location="bedroom",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    context = Context(
        activity="walking",
        time_context="afternoon",
        baseline_deviation=0.20,
        wearable_status="worn_normal",
        environment="well_lit"
    )

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=None)

    assert any(f.factor == "recovery_movement" for f in result.suppressed_factors)
    # Recovery movement suppresses score, keeping it below critical/high
    assert result.risk_level in [RiskLevel.LOW.value, RiskLevel.MODERATE.value]
    assert result.score < 50.0


# ---------------------------------------------------------------------------
# 5. Noisy Sensor Anti-False Alarm Scenario
# ---------------------------------------------------------------------------

def test_scenario_noisy_sensor():
    """
    Noisy Sensor:
      - Solitary sensor spike (e.g. heart rate blip or single uncorroborated camera anomaly).
      - No post-event immobility, dry environment, expected time of day.
      - Anti-noise protection: Must NOT trigger emergency alert.
    """
    event = Event(
        event_type="possible_fall",
        confidence=0.55,
        location="living_room",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    context = Context(
        activity="sitting",
        time_context="afternoon",
        baseline_deviation=0.05,
        wearable_status="worn_normal",
        environment="well_lit"
    )

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=None)

    assert result.risk_level != RiskLevel.CRITICAL.value
    assert result.risk_level != RiskLevel.HIGH.value
    assert result.score < 50.0


# ---------------------------------------------------------------------------
# 6. Missing Sensor Scenario
# ---------------------------------------------------------------------------

def test_scenario_missing_sensor():
    """
    Missing Sensor:
      - Wearable is taken off to charge (status: 'disconnected').
      - System degrades gracefully: records missing_sensors=['wearable'] and uncertainty penalty.
    """
    event = Event(
        event_type="motion_detected",
        confidence=0.85,
        location="hallway",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    context = Context(
        activity="walking",
        time_context="afternoon",
        baseline_deviation=0.15,
        wearable_status="disconnected",
        environment="well_lit"
    )

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=None)

    assert "wearable" in result.missing_sensors
    assert any(f.factor == "device_disconnected" for f in result.contributing_factors)
    assert result.risk_level in [RiskLevel.LOW.value, RiskLevel.MODERATE.value]


# ---------------------------------------------------------------------------
# 7. Conflicting Sensor Scenario
# ---------------------------------------------------------------------------

def test_scenario_conflicting_sensor():
    """
    Conflicting Sensor:
      - Camera pose flags a potential fall (occlusion or dropped jacket),
        but movement after event is normal / active locomotion.
      - System flags sensor_conflict_detected=True, appends suppressed factor,
        and prevents false positive alert escalation.
    """
    event = Event(
        event_type="fall_detected",
        confidence=0.75,
        location="living_room",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    context = Context(
        activity="walking",
        time_context="afternoon",
        baseline_deviation=0.10,
        wearable_status="worn_normal",
        environment="well_lit"
    )

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=None)

    assert result.sensor_conflict_detected is True
    assert any(f.factor == "conflicting_sensor_locomotion" for f in result.suppressed_factors)
    assert result.risk_level != RiskLevel.CRITICAL.value


# ---------------------------------------------------------------------------
# 8. Delayed Event Scenario
# ---------------------------------------------------------------------------

def test_scenario_delayed_event():
    """
    Delayed Event:
      - Historical timestamp from earlier activity is ingested.
      - System processes deterministically without crashing or state corruption.
    """
    event = Event(
        event_type="loud_thud",
        confidence=0.50,
        location="kitchen",
        timestamp="2026-10-18T12:00:00Z",
        movement_after_event="normal"
    )
    context = Context(
        activity="cooking",
        time_context="afternoon",
        baseline_deviation=0.12,
        wearable_status="worn_normal",
        environment="well_lit"
    )

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=None)
    assert isinstance(result, ExplainableRiskResult)
    assert result.risk_level in [RiskLevel.LOW.value, RiskLevel.MODERATE.value]


# ---------------------------------------------------------------------------
# 9. Repeated Event & Hysteresis Scenario
# ---------------------------------------------------------------------------

def test_scenario_repeated_event_debouncing_and_hysteresis():
    """
    Repeated Events & Hysteresis:
      - Rapid succession of identical events in short window is debounced to prevent alert storms.
      - Repeated event compounding records cluster count in contributing factors.
      - Hysteresis prevents rapid HIGH <-> LOW oscillation.
    """
    tracker = RiskHysteresisTracker()
    event = Event(
        event_type="loud_thud",
        confidence=0.65,
        location="living_room",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    context = Context(
        activity="resting",
        time_context="afternoon",
        baseline_deviation=0.15,
        wearable_status="worn_normal",
        environment="well_lit"
    )

    # First event
    res1 = MultimodalRiskIntelligence.evaluate(event, context, hysteresis_tracker=tracker)
    assert res1.risk_level == RiskLevel.LOW.value

    # Immediate second and third events (rapid cluster)
    _ = MultimodalRiskIntelligence.evaluate(event, context, hysteresis_tracker=tracker)
    res3 = MultimodalRiskIntelligence.evaluate(event, context, hysteresis_tracker=tracker)

    # Cluster compounding is recorded
    assert any(f.factor == "repeated_event_cluster" for f in res3.contributing_factors)

    # Test Hysteresis stabilization:
    # Once elevated to HIGH, score must drop significantly below 42.0 to de-escalate to MODERATE
    tracker.current_stable_level = RiskLevel.HIGH.value
    # A borderline score of 50.0 is held at HIGH by hysteresis (does not drop to MODERATE/LOW)
    level, was_held = tracker.evaluate_hysteresis(raw_score=50.0)
    assert level == RiskLevel.HIGH.value
    assert was_held is True


# ---------------------------------------------------------------------------
# 10. Normal Elderly Activity Scenario
# ---------------------------------------------------------------------------

def test_scenario_normal_elderly_activity():
    """
    Normal Elderly Activity:
      - Eleanor reading in chair at 2:30 PM, heart rate 72 BPM, well lit, dry floor.
      - Risk must evaluate to LOW with minimal score (<15.0) and zero false alerts.
    """
    event = Event(
        event_type="ambient_heartbeat",
        confidence=0.99,
        location="living_room",
        timestamp="2026-10-19T14:30:00Z",
        movement_after_event="normal"
    )
    context = Context(
        activity="reading",
        time_context="afternoon",
        baseline_deviation=0.04,
        wearable_status="worn_normal",
        environment="well_lit"
    )

    result = MultimodalRiskIntelligence.evaluate(event, context, voice_response=None)

    assert result.risk_level == RiskLevel.LOW.value
    assert result.score < 15.0
    assert result.recommended_action == "MONITOR_PASSIVELY"
    assert result.sensor_conflict_detected is False
    assert len(result.missing_sensors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
