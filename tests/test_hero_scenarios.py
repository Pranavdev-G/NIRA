"""
End-to-End Pytest Suite for the 3 Aegis CARE Hero Scenarios.
Amazon Developer Hackathon 2026.

Hero Scenarios:
  1. False Alarm: Slip / impact -> Voice check -> "I'm okay" -> LOW -> RESOLVED
  2. Responsive Emergency: Fall -> Voice check -> "Help me" -> Caregiver Multi-Channel Alert -> ESCALATED_CAREGIVER
  3. Silent Emergency: Nocturnal bathroom fall + tachycardia -> Voice check -> Timeout/Silence -> CAD 911 Dispatch -> ESCALATED_CAD
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import init_db

# Initialize database schema and default patient profile
init_db()

client = TestClient(app)


# ---------------------------------------------------------------------------
# HERO SCENARIO 1: False Alarm (Safe Verbal Confirmation)
# ---------------------------------------------------------------------------

def test_hero_scenario_false_alarm():
    """
    Scenario 1:
      - Senior drops a heavy book in the living room (acoustic impact / minor slip).
      - Ingest event -> Status ACTIVE.
      - Alexa asks: "Are you okay?"
      - Senior replies: "I'm okay, false alarm, just dropped my book."
      - Risk downgraded to LOW, incident marked RESOLVED, escalation cancelled.
    """
    # 1. Ingest Event
    event_payload = {
        "event": {
            "event_type": "loud_thud",
            "confidence": 0.65,
            "location": "living_room",
            "timestamp": "2026-10-17T14:15:00Z",
            "movement_after_event": "normal"
        },
        "context": {
            "activity": "reading",
            "time_context": "afternoon",
            "baseline_deviation": 0.15,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        },
        "user_id": "user_eleanor_vance"
    }

    ingest_resp = client.post("/api/v1/events", json=event_payload)
    assert ingest_resp.status_code == 201
    data = ingest_resp.json()
    incident_id = data["incident_id"]
    assert incident_id.startswith("INC-")
    assert data["status"] == "ACTIVE"

    # 2. Check active incidents feed
    active_resp = client.get("/api/v1/incidents/active")
    assert active_resp.status_code == 200
    active_ids = [inc["id"] for inc in active_resp.json()]
    assert incident_id in active_ids

    # 3. Simulate Senior's Safe Voice Response
    voice_payload = {
        "transcript": "I'm okay, false alarm, just dropped my book.",
        "is_timeout": False
    }
    voice_resp = client.post(f"/api/v1/incidents/{incident_id}/respond-voice", json=voice_payload)
    assert voice_resp.status_code == 200
    voice_data = voice_resp.json()
    assert voice_data["status"] == "RESOLVED"
    assert voice_data["risk_level"] == "LOW"
    assert "RESOLVED_SAFE" in voice_data["action_taken"]

    # 4. Verify Timeline Audit Sequence
    timeline_resp = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert timeline_resp.status_code == 200
    actions = [item["action_type"] for item in timeline_resp.json()]
    assert "VISION_EVENT_INGESTED" in actions
    assert "RISK_ASSESSED" in actions
    assert "VOICE_RESPONSE_RECEIVED" in actions
    assert "RESOLVED_SAFE" in actions

    # 5. Confirm no longer in active incidents
    active_resp_after = client.get("/api/v1/incidents/active")
    active_ids_after = [inc["id"] for inc in active_resp_after.json()]
    assert incident_id not in active_ids_after


# ---------------------------------------------------------------------------
# HERO SCENARIO 2: Responsive Emergency ("Help Me")
# ---------------------------------------------------------------------------

def test_hero_scenario_responsive_emergency():
    """
    Scenario 2:
      - Senior falls in the living room and crawls on floor.
      - Ingest event -> Initial Risk HIGH -> Wellness Check initiated.
      - Senior verbally calls for help: "Help me, I fell down and my hip hurts!"
      - Caregiver notified across Alexa Drop-In, Push, and SMS.
      - Status updated to ESCALATED_CAREGIVER.
    """
    event_payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.88,
            "location": "living_room",
            "timestamp": "2026-10-17T11:20:00Z",
            "movement_after_event": "crawling"
        },
        "context": {
            "activity": "walking",
            "time_context": "morning",
            "baseline_deviation": 0.65,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        },
        "user_id": "user_eleanor_vance"
    }

    ingest_resp = client.post("/api/v1/events", json=event_payload)
    assert ingest_resp.status_code == 201
    incident_id = ingest_resp.json()["incident_id"]

    # Senior calls for help
    voice_payload = {
        "transcript": "Help me, I fell down and my hip hurts!",
        "is_timeout": False
    }
    voice_resp = client.post(f"/api/v1/incidents/{incident_id}/respond-voice", json=voice_payload)
    assert voice_resp.status_code == 200
    voice_data = voice_resp.json()
    assert voice_data["status"] == "ESCALATED_CAREGIVER"
    assert "caregiver_details" in voice_data
    assert voice_data["caregiver_details"]["notification_id"].startswith("notif_")

    # Verify Timeline
    timeline_resp = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert timeline_resp.status_code == 200
    actions = [item["action_type"] for item in timeline_resp.json()]
    assert "VOICE_RESPONSE_RECEIVED" in actions
    assert "CAREGIVER_NOTIFIED" in actions


# ---------------------------------------------------------------------------
# HERO SCENARIO 3: Silent Emergency (Unresponsive Fall + CAD Dispatch)
# ---------------------------------------------------------------------------

def test_hero_scenario_silent_emergency():
    """
    Scenario 3:
      - Severe fall in bathroom at 2:45 AM, zero post-impact movement, tachycardia vitals.
      - Ingest event -> Initial Risk CRITICAL.
      - Alexa wellness check prompt times out (20 seconds of complete silence).
      - Silent emergency triggered -> CAD 911 dispatch, entry door unlocked, emergency packet generated.
      - Status updated to ESCALATED_CAD.
    """
    event_payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.96,
            "location": "bathroom",
            "timestamp": "2026-10-17T02:45:00Z",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "showering",
            "time_context": "night_time",
            "baseline_deviation": 0.92,
            "wearable_status": "high_heart_rate",
            "environment": "dark_room_wet_floor"
        },
        "user_id": "user_eleanor_vance"
    }

    ingest_resp = client.post("/api/v1/events", json=event_payload)
    assert ingest_resp.status_code == 201
    incident_id = ingest_resp.json()["incident_id"]

    # Senior does not answer (Timeout / silence)
    voice_payload = {
        "transcript": None,
        "is_timeout": True
    }
    voice_resp = client.post(f"/api/v1/incidents/{incident_id}/respond-voice", json=voice_payload)
    assert voice_resp.status_code == 200
    voice_data = voice_resp.json()
    assert voice_data["status"] == "ESCALATED_CAD"
    assert voice_data["risk_level"] == "CRITICAL"
    assert "cad_details" in voice_data
    assert voice_data["cad_details"]["dispatch_id"].startswith("CAD-DISP-")
    assert voice_data["cad_details"]["door_lock_unlocked"] is True

    # Verify Timeline contains CAD dispatch
    timeline_resp = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    actions = [item["action_type"] for item in timeline_resp.json()]
    assert "VOICE_RESPONSE_RECEIVED" in actions
    assert "CAD_DISPATCHED" in actions


if __name__ == "__main__":
    pytest.main([__file__])
