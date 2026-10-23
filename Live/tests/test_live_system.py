"""
Unit & Integration Tests for NIRA Live System.
Amazon Developer Hackathon 2026.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from Live.app.main import app as live_app
from main import app as root_app
from Live.app.services.session import LiveSessionManager
from Live.app.services.textbee import LiveTextBeeService
from Live.app.services.reminder import LiveReminderService
from Live.app.services.heartbeat import LiveHeartbeatService
from Live.app.services.emergency import LiveEmergencyTrackerService

client = TestClient(root_app)


def test_gateway_and_login_page_renders():
    """Verify entry routes serve gateway and login portals."""
    login_resp = client.get("/login")
    assert login_resp.status_code == 200
    assert "Caretaker" in login_resp.text
    assert "Sign In" in login_resp.text
    assert "Register Caretaker" in login_resp.text

    gateway_resp = client.get("/")
    assert gateway_resp.status_code == 200
    assert "NIRA" in gateway_resp.text
    assert "HACKATHON" in gateway_resp.text
    assert "REAL-TIME" in gateway_resp.text

    live_resp = client.get("/live")
    assert live_resp.status_code == 200
    assert "NIRA LIVE AMBIENT CARE" in live_resp.text


def test_caretaker_registration_and_login_flow():
    """Verify registration with all 9 fields and signin with username/mobile/email."""
    payload = {
        "caretaker_name": "David Vance",
        "mobile_number": "+15550184421",
        "email": "david.vance@example.com",
        "caring_person_name": "Eleanor Vance",
        "address": "Residence Unit 4B - Beacon Hill, Boston MA",
        "latitude": 42.3601,
        "longitude": -71.0589,
        "maps_link": "https://maps.google.com/?q=42.3601,-71.0589",
        "age": 79,
        "disabilities": "Mild cognitive impairment, evening mobility limitation",
        "health_issues": "Hypertension, documented bathroom fall history",
        "password": "SecurePassword!2026"
    }

    # Register
    reg_resp = client.post("/api/v1/live/auth/register", json=payload)
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["success"] is True
    assert reg_data["caregiver"]["name"] == "David Vance"
    assert reg_data["caregiver"]["mobile"] == "+15550184421"

    # Sign in via mobile
    login_mobile = client.post(
        "/api/v1/live/auth/login",
        json={"identifier": "+15550184421", "password": "SecurePassword!2026"}
    )
    assert login_mobile.status_code == 200
    assert login_mobile.json()["success"] is True

    # Sign in via email
    login_email = client.post(
        "/api/v1/live/auth/login",
        json={"identifier": "david.vance@example.com", "password": "SecurePassword!2026"}
    )
    assert login_email.status_code == 200
    assert login_email.json()["success"] is True


def test_live_gps_location_endpoints():
    """Verify live location fetching and updates with Google Maps link."""
    get_resp = client.get("/api/v1/live/location/live")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["success"] is True
    assert "latitude" in data
    assert "longitude" in data
    assert "maps_link" in data

    post_resp = client.post(
        "/api/v1/live/location/live",
        json={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "MG Road, Bengaluru",
            "source": "browser_gps"
        }
    )
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    assert post_data["success"] is True
    assert post_data["latitude"] == 12.9716


def test_medical_pill_reminder_system():
    """Verify pill reminder schedule, active voice prompt, and voice adherence."""
    # 1. Get medications
    meds_resp = client.get("/api/v1/live/reminders")
    assert meds_resp.status_code == 200
    meds = meds_resp.json()["medications"]
    assert len(meds) >= 4
    assert any("Lisinopril" in m["name"] for m in meds)

    # 2. Get active voice prompt
    prompt_resp = client.get("/api/v1/live/reminders/active-prompt")
    assert prompt_resp.status_code == 200
    prompt_data = prompt_resp.json()
    assert "spoken_prompt" in prompt_data
    assert "question" in prompt_data

    # 3. Respond with "Yes" (Taken)
    resp_taken = client.post(
        "/api/v1/live/reminders/respond",
        json={"medication_id": "med_lisinopril", "user_spoken_response": "Yes, I took it with water"}
    )
    assert resp_taken.status_code == 200
    assert resp_taken.json()["is_taken"] is True
    assert resp_taken.json()["caretaker_notified"] is False


def test_wearable_heartbeat_and_device_telemetry():
    """Verify wearable device specs and continuous heartbeat telemetry."""
    # Wearable device specs
    wearable_resp = client.get("/api/v1/live/heartbeat/wearable")
    assert wearable_resp.status_code == 200
    w = wearable_resp.json()["wearable"]
    assert "Aegis Pulse Band Pro" in w["device_name"]
    assert w["battery_percent"] > 0
    assert "Bluetooth" in w["connection_type"]

    # Live BPM
    bpm_resp = client.get("/api/v1/live/heartbeat/live")
    assert bpm_resp.status_code == 200
    bpm_data = bpm_resp.json()
    assert 50 <= bpm_data["bpm"] <= 180
    assert "blood_pressure" in bpm_data
    assert len(bpm_data["ecg_waveform_sample"]) > 10


def test_emergency_cad_tracking_and_auto_door_unlock():
    """Verify ambulance dispatch, GPS tracking progression, and door unlock."""
    dispatch_resp = client.post("/api/v1/live/emergency/trigger-cad", json={})
    assert dispatch_resp.status_code == 200
    disp = dispatch_resp.json()["dispatch"]
    assert disp["is_active"] is True
    assert disp["unit_id"] == "MEDIC-14-PARAMEDIC"

    tracking_resp = client.get("/api/v1/live/emergency/tracking")
    assert tracking_resp.status_code == 200
    tr = tracking_resp.json()["tracking"]
    assert "eta_mins" in tr
    assert "distance_km" in tr
    assert "door_status" in tr
    assert "8492" in tr["door_pin"]


def test_vision_multi_room_and_routine_baseline():
    """Verify multi-room cameras, room switching, and self-learning baseline."""
    rooms_resp = client.get("/api/v1/live/vision/rooms")
    assert rooms_resp.status_code == 200
    rooms = rooms_resp.json()["rooms"]
    assert "living_room" in rooms
    assert "bathroom" in rooms

    switch_resp = client.post("/api/v1/live/vision/switch-room", json={"room_id": "bathroom"})
    assert switch_resp.status_code == 200
    assert switch_resp.json()["active_room"] == "bathroom"

    baseline_resp = client.get("/api/v1/live/vision/routine-baseline")
    assert baseline_resp.status_code == 200
    assert "routine" in baseline_resp.json()
