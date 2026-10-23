"""
NIRA — Comprehensive Operator Simulation & Command Console Test Suite
Amazon Developer Hackathon 2026

Deterministic integration tests covering:
1. Demo Login & Authentication Experience
2. Operator Console assets & HTML elements delivery
3. All 13 Operator Simulation Actions (/api/v1/demo/simulate/{action})
4. All 6 Predefined End-to-End Scenarios (/api/v1/demo/scenario/{scenario_name})
5. Smart Lock Authoritative Unlock & Location Security Contracts
6. Emergency Ambulance CAD Dispatch Contracts
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login_page_contract():
    """Verify demo login page serves credentials guide, error alerts, and session logic."""
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "loginErrorAlert" in resp.text
    assert "David Vance" in resp.text
    assert "Eleanor" in resp.text
    assert "Medic 14" in resp.text
    assert "demo" in resp.text.lower()


def test_operator_console_asset_contract():
    """Verify operator_console.js and index.html integration."""
    # Check operator script asset
    resp_script = client.get("/static/operator_console.js")
    assert resp_script.status_code == 200
    assert "OperatorConsoleEngine" in resp_script.text
    assert "DEMO_FLOW_STEPS" in resp_script.text
    assert "PREDEFINED_SCENARIOS" in resp_script.text

    # Check dashboard markup contains operator controls
    resp_dash = client.get("/")
    assert resp_dash.status_code == 200
    assert "operator-control-hub" in resp_dash.text
    assert "flowStepCounter" in resp_dash.text
    assert "flowProgressTrack" in resp_dash.text
    assert "scenarioProgressionBanner" in resp_dash.text
    assert "operator_console.js" in resp_dash.text


def test_all_13_simulation_actions():
    """Verify all 13 operator simulation actions execute and return authoritative states."""
    actions = [
        ("normal", "NORMAL"),
        ("fall", "FALL_DETECTED"),
        ("inactivity", "INACTIVITY"),
        ("high_heart_rate", "TACHYCARDIA"),
        ("low_movement", "LOW_MOVEMENT"),
        ("voice_safe", "VOICE_SAFE"),
        ("voice_risk", "VOICE_RISK"),
        ("voice_help", "VOICE_HELP"),
        ("voice_silence", "VOICE_TIMEOUT"),
        ("environment_hazard", "HAZARD_DETECTED"),
        ("device_disconnect", "SENSOR_OFFLINE"),
        ("medication_missed", "MEDICATION_MISSED"),
        ("recovery", "NORMAL")
    ]

    for action_key, _ in actions:
        resp = client.post(f"/api/v1/demo/simulate/{action_key}")
        assert resp.status_code == 200, f"Action '{action_key}' failed with status {resp.status_code}"
        data = resp.json()
        assert data["status"].upper() == "SUCCESS"
        assert data["action"].lower() == action_key
        assert "safety_state" in data and data["safety_state"] is not None
        assert "risk_level" in data
        assert "current_state" in data


def test_invalid_simulation_action():
    """Verify invalid simulation action returns 400 Bad Request."""
    resp = client.post("/api/v1/demo/simulate/invalid_action_xyz")
    assert resp.status_code == 400
    assert "Unknown simulation action" in resp.json()["detail"]


def test_all_6_demo_scenarios():
    """Verify all 6 predefined end-to-end scenarios are accepted by backend dispatcher."""
    scenarios = [
        "false_alarm",
        "responsive_emergency",
        "silent_emergency",
        "worsening_condition",
        "environmental_hazard",
        "medication_miss"
    ]

    for scenario_name in scenarios:
        resp = client.post(f"/api/v1/demo/scenario/{scenario_name}")
        assert resp.status_code == 200, f"Scenario '{scenario_name}' failed with {resp.status_code}"
        data = resp.json()
        assert data["status"] in ["triggered", "success"]
        assert data["scenario"] == scenario_name


def test_invalid_demo_scenario():
    """Verify invalid scenario returns 404 Not Found."""
    resp = client.post("/api/v1/demo/scenario/nonexistent_scenario_123")
    assert resp.status_code == 404
    assert "Unknown scenario" in resp.json()["detail"]


def test_smart_lock_authoritative_unlock_contract():
    """Verify smart lock authoritative unlock flow for emergency responders."""
    # 1. Advance responder to residence arrival (verified within geofence)
    step_resp = client.post("/api/v1/security/responder/step", json={"target_status": "ARRIVED"})
    assert step_resp.status_code == 200
    assert step_resp.json()["responder"]["arrival_confirmed"] is True

    # 2. Test valid authenticated unlock
    payload = {
        "responder_badge": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026",
        "reason": "Emergency 911 dispatch unit arrival"
    }
    resp = client.post("/api/v1/security/lock/unlock", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["smart_lock"]["state"] == "UNLOCKED"
    assert "8492" in str(data["smart_lock"])

    # 3. Test lock status reflection in security status endpoint
    status_resp = client.get("/api/v1/security/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["smart_lock"]["state"] == "UNLOCKED"


def test_ambulance_dispatch_contract():
    """Verify ambulance CAD dispatch flow and tracking contract."""
    payload = {
        "room": "bathroom",
        "severity": "CRITICAL",
        "reason": "Nocturnal bathroom fall detected with silence timeout"
    }
    resp = client.post("/api/v1/security/emergency/trigger", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["responder"]["status"] == "DISPATCHED"
    assert data["responder"]["unit_id"] == "MEDIC-42"
    assert data["residence"]["location_status"] == "EMERGENCY_AT_RESIDENCE"
