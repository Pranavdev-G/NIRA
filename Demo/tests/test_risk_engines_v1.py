"""
Comprehensive Unit and Integration Tests for Aegis CARE Core Engines (v1).
Amazon Developer Hackathon 2026.

Tests:
  - ContextEngine
  - PersonalBaselineEngine
  - AegisRiskEngine (LOW, MODERATE, HIGH, CRITICAL rules)
  - REST endpoints: /api/v1/assess-risk and /api/v1/reassess-risk
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Event, Context, VoiceResponse
from app.models.enums import RiskLevel
from app.services.context_engine import ContextEngine
from app.services.baseline_engine import PersonalBaselineEngine
from app.services.aegis_risk_engine import AegisRiskEngine


client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. ContextEngine Tests
# ---------------------------------------------------------------------------

def test_context_engine_location_hazards():
    # Bathroom & Shower should have high hazard multipliers
    bath_mult, bath_reason = ContextEngine.get_location_hazard("bathroom")
    assert bath_mult >= 1.5
    assert "bathroom" in bath_reason.lower()

    stairs_mult, stairs_reason = ContextEngine.get_location_hazard("stairs")
    assert stairs_mult >= 1.6

    living_mult, living_reason = ContextEngine.get_location_hazard("living_room")
    assert living_mult == 1.0


def test_context_engine_environmental_hazards():
    score, reasons = ContextEngine.get_environmental_hazards("dark_room_wet_floor")
    assert score >= 15.0  # Combined moisture and darkness
    assert any("wet" in r.lower() or "slippery" in r.lower() for r in reasons)
    assert any("lighting" in r.lower() or "dark" in r.lower() for r in reasons)


def test_context_engine_temporal_vulnerability():
    score_night, reason_night = ContextEngine.evaluate_temporal_vulnerability("night_time")
    assert score_night >= 10.0
    assert "nocturnal" in reason_night.lower()

    score_day, reason_day = ContextEngine.evaluate_temporal_vulnerability("afternoon")
    assert score_day == 0.0


# ---------------------------------------------------------------------------
# 2. PersonalBaselineEngine Tests
# ---------------------------------------------------------------------------

def test_baseline_engine_expected_nocturnal_routine():
    # Senior sleeping in bedroom at 2 AM -> Expected baseline -> Low deviation
    dev, reasons, meta = PersonalBaselineEngine.calculate_deviation(
        location="bedroom",
        activity="sleeping",
        timestamp_str="2026-10-17T02:30:00Z"
    )
    assert dev <= 0.40
    assert meta["circadian_slot"] == "Nocturnal Rest"


def test_baseline_engine_unexpected_nocturnal_anomaly():
    # Senior detected in bathroom with abnormal activity at 3 AM -> High deviation
    dev, reasons, meta = PersonalBaselineEngine.calculate_deviation(
        location="bathroom",
        activity="fall_detected",
        timestamp_str="2026-10-17T03:15:00Z"
    )
    assert dev >= 0.70
    assert any("nocturnal" in r.lower() or "anomaly" in r.lower() for r in reasons)


# ---------------------------------------------------------------------------
# 3. AegisRiskEngine Threshold Rules (LOW, MODERATE, HIGH, CRITICAL)
# ---------------------------------------------------------------------------

def test_risk_rule_low_verified_safe():
    """
    LOW Rule: Routine deviation minimal, normal sensor signals, verified safe.
    """
    event = Event(
        event_type="loud_thud",
        confidence=0.45,
        location="living_room",
        timestamp="2026-10-17T14:30:00Z",
        movement_after_event="normal"
    )
    context = Context(
        activity="reading",
        time_context="afternoon",
        baseline_deviation=0.08,
        wearable_status="worn_normal",
        environment="well_lit"
    )
    voice = VoiceResponse(transcript="I am completely okay, I just dropped my book", is_timeout=False)

    assessment = AegisRiskEngine.evaluate(event, context, voice_response=voice)
    assert assessment.risk_level == RiskLevel.LOW.value
    assert assessment.requires_caregiver_alert is False
    assert assessment.requires_emergency_escalation is False
    assert any("confirmed safety" in r.lower() for r in assessment.reasons)


def test_risk_rule_moderate_unverified_voice_check():
    """
    MODERATE Rule: Mild anomaly or unverified event requiring voice check.
    """
    event = Event(
        event_type="abnormal_inactivity",
        confidence=0.60,
        location="kitchen",
        timestamp="2026-10-17T11:00:00Z",
        movement_after_event="none"
    )
    context = Context(
        activity="cooking",
        time_context="morning",
        baseline_deviation=0.45,
        wearable_status="worn_normal",
        environment="well_lit"
    )
    # Voice response not received yet
    assessment = AegisRiskEngine.evaluate(event, context, voice_response=None)
    assert assessment.risk_level == RiskLevel.MODERATE.value
    assert assessment.requires_wellness_check is True
    assert assessment.requires_emergency_escalation is False
    assert "WELLNESS_CHECK" in assessment.recommended_action


def test_risk_rule_high_fall_with_help_me_response():
    """
    HIGH Rule: Confirmed fall or abnormal vitals + explicit 'Help me' response -> Caregiver alert.
    """
    event = Event(
        event_type="fall_detected",
        confidence=0.88,
        location="living_room",
        timestamp="2026-10-17T10:15:00Z",
        movement_after_event="crawling"
    )
    context = Context(
        activity="walking",
        time_context="morning",
        baseline_deviation=0.65,
        wearable_status="worn_normal",
        environment="well_lit"
    )
    voice = VoiceResponse(transcript="Help me please, I fell down and my hip hurts!", is_timeout=False)

    assessment = AegisRiskEngine.evaluate(event, context, voice_response=voice)
    assert assessment.risk_level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
    assert assessment.requires_caregiver_alert is True
    assert any("help" in r.lower() or "distress" in r.lower() for r in assessment.reasons)


def test_risk_rule_critical_silent_emergency():
    """
    CRITICAL Rule: Confirmed fall + abnormal vitals + NO response (silent emergency) -> Immediate CAD escalation.
    """
    event = Event(
        event_type="fall_detected",
        confidence=0.96,
        location="bathroom",
        timestamp="2026-10-17T02:45:00Z",
        movement_after_event="none"
    )
    context = Context(
        activity="showering",
        time_context="night_time",
        baseline_deviation=0.92,
        wearable_status="high_heart_rate",
        environment="dark_room_wet_floor"
    )
    voice = VoiceResponse(transcript=None, is_timeout=True)

    assessment = AegisRiskEngine.evaluate(event, context, voice_response=voice)
    assert assessment.risk_level == RiskLevel.CRITICAL.value
    assert assessment.confidence >= 0.95
    assert assessment.requires_emergency_escalation is True
    assert assessment.requires_caregiver_alert is True
    assert any("silent emergency" in r.lower() or "no response" in r.lower() for r in assessment.reasons)


# ---------------------------------------------------------------------------
# 4. REST Endpoints Tests (/api/v1/assess-risk, /api/v1/reassess-risk)
# ---------------------------------------------------------------------------

def test_api_v1_assess_risk_endpoint():
    payload = {
        "event": {
            "event_type": "fall_detected",
            "confidence": 0.92,
            "location": "bathroom",
            "timestamp": "2026-10-17T03:00:00Z",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "walking",
            "time_context": "night_time",
            "baseline_deviation": 0.88,
            "wearable_status": "high_heart_rate",
            "environment": "dark_room_wet_floor"
        }
    }
    response = client.post("/api/v1/assess-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "risk_level" in data
    assert "confidence" in data
    assert "reasons" in data
    assert len(data["reasons"]) >= 3
    assert data["risk_level"] in ["HIGH", "CRITICAL"]
    assert float(response.headers["X-Response-Time-Ms"]) < 50.0


def test_api_v1_reassess_risk_endpoint_silent_emergency():
    payload = {
        "event": {
            "event_type": "fall_detected",
            "confidence": 0.95,
            "location": "bathroom",
            "timestamp": "2026-10-17T03:00:00Z",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "walking",
            "time_context": "night_time",
            "baseline_deviation": 0.90,
            "wearable_status": "high_heart_rate",
            "environment": "dark_room_wet_floor"
        },
        "voice_response": {
            "transcript": None,
            "is_timeout": True
        }
    }
    response = client.post("/api/v1/reassess-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "CRITICAL"
    assert data["requires_emergency_escalation"] is True
    assert any("silent emergency" in r.lower() for r in data["reasons"])


def test_api_v1_reassess_risk_endpoint_safe_verbal_confirmation():
    payload = {
        "event": {
            "event_type": "fall_detected",
            "confidence": 0.75,
            "location": "living_room",
            "timestamp": "2026-10-17T15:00:00Z",
            "movement_after_event": "normal"
        },
        "context": {
            "activity": "reading",
            "time_context": "afternoon",
            "baseline_deviation": 0.20,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        },
        "voice_response": {
            "transcript": "I am fine, false alarm, just dropped my phone.",
            "is_timeout": False
        }
    }
    response = client.post("/api/v1/reassess-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "LOW"
    assert data["requires_emergency_escalation"] is False
    assert any("confirmed safety" in r.lower() for r in data["reasons"])


if __name__ == "__main__":
    pytest.main([__file__])
