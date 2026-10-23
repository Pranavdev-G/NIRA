"""
Pytest Suite for NIRA Location & Residence Security.
Validates live location tracking, EMS arrival tracking, and automated smart-lock security:
  1. Live GPS tracking of Eleanor Vance with geofence perimeter.
  2. Separate emergency response team tracking and stage progression (Dispatched -> En Route -> Arriving -> Arrived).
  3. Strict arrival confirmation (arrival cannot be declared purely from resident location).
  4. Smart lock state transitions (LOCKED -> UNLOCKING -> UNLOCKED / ERROR).
  5. Security guardrails:
     - Geofence enforcement (never unlock solely on GPS entering without authorization).
     - Unauthorized responder rejection (403 Forbidden).
     - Out-of-geofence unlock rejection (400 Bad Request).
     - Lock offline / connectivity failure handling (503 Service Unavailable).
  6. Manual key override capabilities.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.security_api import security_manager

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_security_fixture():
    """Ensure clean simulator state before and after every test."""
    client.post("/api/v1/security/reset")
    yield
    client.post("/api/v1/security/reset")


def test_get_security_status_initial():
    """Test initial state returns valid resident, responder, lock, and audit properties."""
    resp = client.get("/api/v1/security/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    # Resident / Residence
    assert data["residence"]["name"] == "Eleanor Vance"
    assert data["residence"]["latitude"] == pytest.approx(42.3588, abs=0.001)
    assert data["residence"]["longitude"] == pytest.approx(-71.0638, abs=0.001)
    assert data["resident"]["is_in_residence"] is True

    # Responder
    assert data["responder"]["unit_id"].upper() == "MEDIC-42"
    assert data["responder"]["status"] == "DISPATCHED"
    assert data["responder"]["is_authorized"] is True
    assert data["responder"]["arrival_confirmed"] is False
    assert data["distance_meters"] > 35

    # Smart Lock
    assert data["smart_lock"]["state"] == "LOCKED"
    assert data["smart_lock"]["is_online"] is True
    assert "Waiting for authorized" in data["smart_lock"]["explanation"]

    # Audit Trail
    assert isinstance(data["audit_log"], list)
    assert len(data["audit_log"]) > 0


def test_responder_step_simulation_progression():
    """Test emergency team progresses through Dispatched -> En Route -> Arriving -> Arrived."""
    # Step 1: Advance to EN_ROUTE
    r1 = client.post("/api/v1/security/responder/step", json={"target_status": "EN_ROUTE"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["responder"]["status"] == "EN_ROUTE"
    assert d1["responder"]["arrival_confirmed"] is False
    assert d1["distance_meters"] < 1000

    # Step 2: Advance to ARRIVING
    r2 = client.post("/api/v1/security/responder/step", json={"target_status": "ARRIVING"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["responder"]["status"] == "ARRIVING"
    assert d2["responder"]["arrival_confirmed"] is False
    assert d2["distance_meters"] < 200

    # Step 3: Advance to ARRIVED
    r3 = client.post("/api/v1/security/responder/step", json={"target_status": "ARRIVED"})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["responder"]["status"] == "ARRIVED"
    assert d3["responder"]["arrival_confirmed"] is True
    assert d3["distance_meters"] <= 35.0
    assert d3["is_within_geofence"] is True


def test_responder_checkin_success_and_failures():
    """Test explicit check-in verification with geofence and authorized badge checks."""
    # 1. Failure: Unauthorized badge
    r_unauth = client.post("/api/v1/security/responder/checkin", json={
        "badge_id": "IMPOSTER-007",
        "auth_token": "AUTH-TOKEN-INVALID"
    })
    assert r_unauth.status_code == 403
    assert "Unauthorized" in r_unauth.json()["detail"]

    # 2. Failure: Authorized badge but outside residence geofence (e.g. 500m away)
    r_far = client.post("/api/v1/security/responder/checkin", json={
        "badge_id": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026",
        "latitude": 42.3650,
        "longitude": -71.0720
    })
    assert r_far.status_code == 400
    assert "not at registered residence" in r_far.json()["detail"]

    # 3. Success: Authorized badge and inside 35m perimeter
    r_ok = client.post("/api/v1/security/responder/checkin", json={
        "badge_id": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026",
        "latitude": 42.35882,
        "longitude": -71.06381,
        "override_stage": "ARRIVED"
    })
    assert r_ok.status_code == 200
    d_ok = r_ok.json()
    assert d_ok["responder"]["status"] == "ARRIVED"
    assert d_ok["responder"]["arrival_confirmed"] is True
    assert d_ok["is_within_geofence"] is True


def test_door_unlock_security_guardrails():
    """Verify security rules: never unlock for unauthorized badge, distant unit, or offline lock."""
    # Attempt 1: Reject unlock when responder is still dispatched at station
    r_early = client.post("/api/v1/security/lock/unlock", json={
        "responder_badge": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026"
    })
    assert r_early.status_code == 400
    assert "has not arrived" in r_early.json()["detail"]

    # Move responder to curb outside residence
    client.post("/api/v1/security/responder/step", json={"target_status": "ARRIVED"})

    # Attempt 2: Reject unlock when responder credentials are unauthorized
    r_unauth = client.post("/api/v1/security/lock/unlock", json={
        "responder_badge": "BOGUS-999",
        "auth_token": "BAD-TOKEN"
    })
    assert r_unauth.status_code == 403

    # Status should reflect ERROR state with explanatory message
    status_unauth = client.get("/api/v1/security/status").json()
    assert status_unauth["smart_lock"]["state"] == "ERROR"

    # Attempt 3: Reject unlock when smart lock device is offline
    client.post("/api/v1/security/lock/manual-override", json={"action": "SIMULATE_OFFLINE"})
    r_offline = client.post("/api/v1/security/lock/unlock", json={
        "responder_badge": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026"
    })
    assert r_offline.status_code == 503
    assert "manual access required" in r_offline.json()["detail"]


def test_full_verified_unlock_flow():
    """
    Test complete end-to-end verified workflow:
    Dispatched -> Arrived at Residence -> Verified Check-In -> Authenticated Unlock -> Audit Log Updated
    """
    # 1. Advance to arrived
    step_res = client.post("/api/v1/security/responder/step", json={"target_status": "ARRIVED"})
    assert step_res.status_code == 200
    assert step_res.json()["responder"]["arrival_confirmed"] is True

    # 2. Execute authenticated unlock command
    unlock_res = client.post("/api/v1/security/lock/unlock", json={
        "responder_badge": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026"
    })
    assert unlock_res.status_code == 200
    data = unlock_res.json()

    assert data["smart_lock"]["state"] == "UNLOCKED"
    assert "Door unlocked for authorized responders" in data["smart_lock"]["explanation"]
    assert "8492" in data["smart_lock"]["explanation"]

    # 3. Verify audit log contains entry
    audit = data["audit_log"]
    unlocked_entries = [e for e in audit if "unlocked" in e["message"].lower()]
    assert len(unlocked_entries) > 0


def test_manual_override_lock_toggle():
    """Test guardian/responder manual override functions."""
    # Test manual unlock
    r_unlock = client.post("/api/v1/security/lock/manual-override", json={
        "action": "UNLOCK",
        "actor": "Family Guardian (David Vance)"
    })
    assert r_unlock.status_code == 200
    assert r_unlock.json()["smart_lock"]["state"] == "UNLOCKED"

    # Test manual lock
    r_lock = client.post("/api/v1/security/lock/manual-override", json={
        "action": "LOCK",
        "actor": "David Vance"
    })
    assert r_lock.status_code == 200
    assert r_lock.json()["smart_lock"]["state"] == "LOCKED"


def test_emergency_trigger_and_team_dispatch():
    """Test emergency triggering dispatches response team and sets resident status."""
    resp = client.post("/api/v1/security/emergency/trigger", json={
        "resident_id": "user_eleanor_vance",
        "room": "bathroom",
        "severity": "HIGH",
        "reason": "Fall detected on bathroom tile"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert data["resident"]["location_status"] == "EMERGENCY_AT_RESIDENCE"
    assert "Bathroom" in data["resident"]["status"]
    assert data["responder"]["status"] == "DISPATCHED"
    assert data["responder"]["arrival_confirmed"] is False
    assert data["smart_lock"]["state"] == "LOCKED"
    assert "Waiting for authorized" in data["smart_lock"]["explanation"]

    # Verify audit log contains emergency alert
    logs = data["activity_log"]
    assert any("EMERGENCY" in l["message"].upper() for l in logs)


def test_failed_unlock_command_hardware_jam():
    """Test lock hardware motor retraction jam (500 error & ERROR state)."""
    # 1. Bring responder to scene and verify arrival
    client.post("/api/v1/security/responder/step", json={"target_status": "ARRIVED"})

    # 2. Attempt unlock with simulate_hardware_failure = True
    r_fail = client.post("/api/v1/security/lock/unlock", json={
        "responder_badge": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026",
        "simulate_hardware_failure": True
    })
    assert r_fail.status_code == 500
    assert "manual access required" in r_fail.json()["detail"]

    # Verify lock state transitioned to ERROR
    st = client.get("/api/v1/security/status").json()
    assert st["smart_lock"]["state"] == "ERROR"
    assert "manual access required" in st["smart_lock"]["explanation"]


def test_complete_demo_flow_end_to_end():
    """
    Test complete demo flow requested by user:
    Emergency triggered → Team dispatched → Team en route → Arrival verified → Simulated door unlock → Unlock confirmation → Incident history updated
    """
    # Step 1: Emergency triggered
    r1 = client.post("/api/v1/security/emergency/trigger", json={
        "room": "bathroom",
        "reason": "Sudden drop & lack of movement on wet tile"
    })
    assert r1.status_code == 200
    d1 = r1.json()
    assert "Bathroom" in d1["resident"]["status"]
    assert d1["responder"]["status"] == "DISPATCHED"
    assert d1["smart_lock"]["state"] == "LOCKED"

    # Step 2: Team dispatched & progressing to en route
    r2 = client.post("/api/v1/security/responder/step", json={"target_status": "EN_ROUTE"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["responder"]["status"] == "EN_ROUTE"
    assert d2["responder"]["arrival_confirmed"] is False

    # Step 3: Team en route & arriving at perimeter
    r3 = client.post("/api/v1/security/responder/step", json={"target_status": "ARRIVING"})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["responder"]["status"] == "ARRIVING"
    assert d3["responder"]["arrival_confirmed"] is False

    # Step 4: Arrival verified via check-in
    r4 = client.post("/api/v1/security/responder/checkin", json={
        "badge_id": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026",
        "latitude": 42.358810,
        "longitude": -71.063810,
        "override_stage": "ARRIVED"
    })
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["responder"]["status"] == "ARRIVED"
    assert d4["responder"]["arrival_confirmed"] is True
    assert d4["is_within_geofence"] is True

    # Step 5: Simulated authenticated door unlock
    r5 = client.post("/api/v1/security/lock/unlock", json={
        "responder_badge": "BEMS-8821",
        "auth_token": "AUTH-TOKEN-BEMS-8821-EXP2026"
    })
    assert r5.status_code == 200
    d5 = r5.json()

    # Step 6: Unlock confirmation & Incident history updated
    assert d5["smart_lock"]["state"] == "UNLOCKED"
    assert "Door unlocked for authorized responders" in d5["smart_lock"]["explanation"]
    assert d5["smart_lock"]["temporary_pin"] == "8492"

    # Verify incident history contains unlock record
    audit_msgs = [e["message"] for e in d5["audit_log"]]
    assert any("unlocked" in m.lower() for m in audit_msgs)


def test_resident_presence_does_not_declare_responder_arrived():
    """Do not mark response team as arrived merely because the elderly person is at residence."""
    st = client.get("/api/v1/security/status").json()
    assert st["resident"]["is_in_residence"] is True
    assert st["responder"]["status"] == "DISPATCHED"
    assert st["responder"]["arrival_confirmed"] is False
    assert st["is_within_geofence"] is False
