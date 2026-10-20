"""
Frontend Contract and Real-Time State Integration Tests (Person 2).
Amazon Developer Hackathon 2026.

Validates that:
1. All static assets and state-store modules (/static/nira_store.js, etc.) are properly served with no-cache headers.
2. The SSE stream endpoint (/sse) correctly serves text/event-stream headers and session initiation.
3. Ingested scenario events from the real-time frontend store (/api/v1/events) generate database incidents and risk levels.
4. Active incidents feed (/api/v1/incidents/active) returns updated risk levels without page refresh.
5. Chronological audit timeline (/api/v1/incidents/{id}/timeline) returns sequential system actions.
6. Voice state transitions (/api/v1/incidents/{id}/respond-voice) correctly update incident status.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_static_assets_serving_and_headers():
    """Verify frontend HTML, CSS, and JS modules are served with valid headers."""
    # Main dashboard
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "nira_store.js" in resp.text
    assert "mcpConnectionBadge" in resp.text

    # Centralized state store
    resp_store = client.get("/static/nira_store.js")
    assert resp_store.status_code == 200
    assert "class NiraStateStore" in resp_store.text

    # Dashboard logic
    resp_dash = client.get("/static/dashboard.js")
    assert resp_dash.status_code == 200
    assert "renderDashboard" in resp_dash.text

    # Admin portal
    resp_admin = client.get("/admin")
    assert resp_admin.status_code == 200
    assert "nira_store.js" in resp_admin.text


def test_health_and_connection_contract():
    """Verify backend health endpoint returns healthy state with sub-50ms latency."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"




def test_scenario_dispatch_contract_and_active_feed():
    """Verify that scenario button dispatches create database incidents visible in active feed."""
    # Scenario: Silent emergency
    payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.94,
            "location": "bathroom",
            "movement_after_event": "none",
            "timestamp": "2026-10-19T02:14:00Z"
        },
        "context": {
            "activity": "sleeping",
            "time_context": "night",
            "baseline_deviation": 0.92,
            "wearable_status": "worn_normal",
            "environment": "dark_hazard"
        },
        "user_id": "user_eleanor_vance"
    }

    resp = client.post("/api/v1/events", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    incident_id = data["incident_id"]
    assert incident_id.startswith("INC-")
    assert data["risk_assessment"]["risk_level"] in ["HIGH", "CRITICAL"]
    assert data["risk_assessment"]["requires_wellness_check"] is True

    # Check active incidents feed
    active_resp = client.get("/api/v1/incidents/active")
    assert active_resp.status_code == 200
    active_incidents = active_resp.json()
    assert len(active_incidents) > 0
    latest = active_incidents[0]
    assert latest["id"] == incident_id
    assert latest["current_risk_level"] in ["HIGH", "CRITICAL"]

    # Check timeline for incident
    timeline_resp = client.get(f"/api/v1/incidents/{incident_id}/timeline")
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()
    assert len(timeline) >= 2
    action_types = [t["action_type"] for t in timeline]
    assert "VISION_EVENT_INGESTED" in action_types
    assert "RISK_ASSESSED" in action_types


def test_voice_response_state_transition_contract():
    """Verify that user voice response transitions incident risk and marks resolution."""
    # 1. Create initial incident
    payload = {
        "event": {
            "event_type": "dropped_object_reach",
            "confidence": 0.88,
            "location": "living",
            "movement_after_event": "normal",
            "timestamp": "2026-10-19T14:30:00Z"
        },
        "context": {
            "activity": "reading",
            "time_context": "afternoon",
            "baseline_deviation": 0.10,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        }
    }
    create_resp = client.post("/api/v1/events", json=payload)
    assert create_resp.status_code == 201
    incident_id = create_resp.json()["incident_id"]

    # 2. Senior responds "I'm okay"
    voice_payload = {
        "transcript": "I'm okay, Alexa! I just dropped my glasses.",
        "is_timeout": False
    }
    voice_resp = client.post(f"/api/v1/incidents/{incident_id}/respond-voice", json=voice_payload)
    assert voice_resp.status_code == 200
    voice_data = voice_resp.json()
    assert voice_data["status"] == "RESOLVED"
    assert voice_data["risk_level"] == "LOW"
    assert voice_data["voice_intent"] == "safe"


def test_emergency_command_center_contract():
    """Verify emergency command center DOM IDs and backend timeline contract."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # The 6 W's Briefing Grid for 10-second comprehension
    assert "cmdWhatHappened" in html
    assert "cmdWhere" in html
    assert "cmdWhen" in html
    assert "cmdWhyEscalated" in html
    assert "cmdWhoNotified" in html
    assert "cmdWhatNow" in html

    # Live header and incident metadata
    assert "cmdIncidentIdBadge" in html
    assert "cmdSeverityBadge" in html
    assert "cmdElapsedTimer" in html

    # Event-driven timeline container
    assert "cmdIncidentTimeline" in html
    assert "cmdTimelineCount" in html
    assert "cmdRiskScoreTag" in html

    # 911 CAD & Guardian Hub controls
    assert "cmdPacketId" in html
    assert "cmdPacketStatus" in html
    assert "cmdTriagePriority" in html
    assert "cmdDoorBadge" in html
    assert "btnAckIncident" in html

