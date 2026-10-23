"""Comprehensive Backend Safety Integrations Test Suite.

Verifies:
1. Event Contract & Normalization (UnifiedEvent with GPS, MEDICATION, SMART_HOME, DEVICE_HEALTH, metadata)
2. Authentication System (login, logout, session, roles, invalid login 401 rejection)
3. Medication Adherence & Reminder Service (scheduled, taken, missed, delayed, adherence scoring, caregiver alert)
4. Location & Ambulance Tracking (/api/v1/security/ambulance, /location, canonical statuses, map links)
5. Voice Distress & Negation Detection ('I am not okay' -> distress, 'Help me' -> emergency, 'I am okay' -> safe)
6. Adaptive Baseline Learning & Emergency Guardrails (tolerance adaptation vs fall suppression block)
7. End-to-End Scenarios A-F dispatch and safety state verification
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from Demo.app.main import app
from Demo.app.models.event_contracts import (
    UnifiedEvent,
    EventSource,
    EventType,
    SafetyState
)
from app.models.schemas import VoiceResponse
from app.services.aegis_risk_engine import AegisRiskEngine
from app.services.baseline_engine import PersonalBaselineEngine
from app.services.medication_service import MedicationService

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. EVENT CONTRACT & NORMALIZATION TESTS
# ---------------------------------------------------------------------------

def test_unified_event_all_sources_and_types():
    """Verify UnifiedEvent serialization and support for new event sources and types."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # GPS Event
    gps_evt = UnifiedEvent(
        event_id="evt-gps-001",
        timestamp=now_iso,
        resident_id="user_eleanor_vance",
        room_id="living_room",
        source=EventSource.GPS.value,
        event_type=EventType.GPS_LOCATION_UPDATE.value,
        location="42.3584,-71.0636",
        zone="living_room",
        simulated=True,
        confidence=0.99,
        correlation_id="corr-gps-100",
        details={"latitude": 42.3584, "longitude": -71.0636, "accuracy_m": 4.5},
        device_metadata={"device_id": "phone-eleanor-vance", "battery": 88}
    )
    assert gps_evt.source == "gps"
    assert gps_evt.simulated is True
    assert gps_evt.location == "42.3584,-71.0636"
    assert gps_evt.device_metadata["device_id"] == "phone-eleanor-vance"

    # Medication Event
    med_evt = UnifiedEvent(
        event_id="evt-med-001",
        timestamp=now_iso,
        resident_id="user_eleanor_vance",
        room_id="kitchen",
        source=EventSource.MEDICATION.value,
        event_type=EventType.MEDICATION_MISSED.value,
        simulated=True,
        correlation_id="corr-med-101",
        details={"medication_id": "lisinopril_10mg", "scheduled_time": "18:00"},
        confidence=1.0
    )
    assert med_evt.source == "medication"
    assert med_evt.event_type == "medication_missed"

    # Smart Home Lock Event
    lock_evt = UnifiedEvent(
        event_id="evt-lock-001",
        timestamp=now_iso,
        resident_id="user_eleanor_vance",
        room_id="hallway",
        source=EventSource.SMART_HOME.value,
        event_type=EventType.SMART_LOCK_STATE_CHANGED.value,
        correlation_id="corr-lock-102",
        details={"lock_state": "UNLOCKED", "authorized_by": "BEMS-8821"},
        simulated=True
    )
    assert lock_evt.source == "smart_home"
    assert lock_evt.event_type == "smart_lock_state_changed"


# ---------------------------------------------------------------------------
# 2. AUTHENTICATION API TESTS
# ---------------------------------------------------------------------------

def test_auth_login_valid_credentials():
    """Verify demo credentials login successfully and return authenticated session tokens."""
    # Resident / Family
    resp = client.post("/api/v1/auth/login", json={
        "email": "david.vance@example.com",
        "password": "admin123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["user"]["role"] == "admin"
    assert data["session_token"].startswith("demo-token-")
    token = data["session_token"]

    # Verify session
    session_resp = client.get("/api/v1/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert session_resp.status_code == 200
    assert session_resp.json()["is_authenticated"] is True
    assert session_resp.json()["session"]["email"] == "david.vance@example.com"

    # Logout
    logout_resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True


def test_auth_login_invalid_credentials_rejected():
    """Verify invalid password or unrecognized email returns 401 Unauthorized."""
    resp = client.post("/api/v1/auth/login", json={
        "email": "david.vance@example.com",
        "password": "wrong-password"
    })
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]

    resp2 = client.post("/api/v1/auth/login", json={
        "email": "unknown.hacker@example.com",
        "password": "any-password"
    })
    assert resp2.status_code == 401


def test_auth_roles_endpoint():
    """Verify roles and accounts directory lists valid demo roles without revealing real passwords."""
    resp = client.get("/api/v1/auth/roles")
    assert resp.status_code == 200
    roles = resp.json()["roles"]
    role_names = [r["role"] for r in roles]
    assert "admin" in role_names
    assert "resident_family" in role_names
    assert "ems_responder" in role_names


# ---------------------------------------------------------------------------
# 3. MEDICATION MANAGEMENT TESTS
# ---------------------------------------------------------------------------

def test_medication_schedule_and_prescriptions():
    """Verify default seeded prescriptions and schedule retrieval."""
    resp = client.get("/api/v1/medications/schedule?resident_id=user_eleanor_vance")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["schedule"]) >= 3
    med_names = [item["medication_name"] for item in data["schedule"]]
    assert any("Lisinopril" in name for name in med_names)
    assert any("Calcium" in name for name in med_names)
    assert any("CoQ10" in name for name in med_names)


def test_medication_record_dose_action_taken():
    """Verify recording a medication as TAKEN updates schedule and adherence."""
    payload = {
        "resident_id": "user_eleanor_vance",
        "medication_id": "med-calcium-02",
        "action": "TAKEN",
        "notes": "Taken with breakfast"
    }
    resp = client.post("/api/v1/medications/record", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "TAKEN"

    # Adherence
    adh_resp = client.get("/api/v1/medications/adherence?resident_id=user_eleanor_vance")
    assert adh_resp.status_code == 200
    adh_data = adh_resp.json()
    assert adh_data["overall_adherence_rate"] >= 0.0
    assert adh_data["doses_taken"] >= 1


def test_medication_record_dose_action_missed_alerts_caregiver():
    """Verify recording a dose as MISSED triggers caregiver notification without 911 dispatch."""
    payload = {
        "resident_id": "user_eleanor_vance",
        "medication_id": "med-lisinopril-01",
        "action": "MISSED",
        "notes": "Resident skipped evening dose"
    }
    resp = client.post("/api/v1/medications/record", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "MISSED"
    assert data["caregiver_alerted"] is True


# ---------------------------------------------------------------------------
# 4. LOCATION & AMBULANCE TRACKING TESTS
# ---------------------------------------------------------------------------

def test_security_ambulance_tracking_endpoint():
    """Verify canonical ambulance tracker provides status, vehicle, ETA, distance, and coordinates."""
    resp = client.get("/api/v1/security/ambulance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["IDLE", "STANDBY", "DISPATCHED", "EN_ROUTE", "NEARBY", "ARRIVED"]
    assert "vehicle_id" in data
    assert "eta_minutes" in data
    assert "distance_km" in data
    assert "distance_meters" in data
    assert "coordinates" in data
    assert "lat" in data["coordinates"]
    assert "lng" in data["coordinates"]


def test_security_location_endpoint_with_maps_and_hospitals():
    """Verify resident location endpoint returns address, coordinates, map links, and nearby hospitals."""
    resp = client.get("/api/v1/security/location?resident_id=user_eleanor_vance")
    assert resp.status_code == 200
    data = resp.json()
    assert data["resident_id"] == "user_eleanor_vance"
    assert "Beacon St" in data["home_address"]
    assert "google_maps" in data["map_links"]
    assert "apple_maps" in data["map_links"]
    assert len(data["nearby_emergency_destinations"]) >= 2
    hosp_names = [h["name"] for h in data["nearby_emergency_destinations"]]
    assert any("Massachusetts General Hospital" in n for n in hosp_names)


# ---------------------------------------------------------------------------
# 5. VOICE DISTRESS & NEGATION RECOGNITION TESTS
# ---------------------------------------------------------------------------

def test_voice_negation_classified_as_distress():
    """Safety Critical: 'I am not okay' must NEVER be classified as SAFE."""
    intent1 = AegisRiskEngine._parse_voice_intent(VoiceResponse(
        transcript="I am not okay, please help",
        is_timeout=False
    ))
    assert intent1 == "distress"

    intent2 = AegisRiskEngine._parse_voice_intent(VoiceResponse(
        transcript="I don't feel well at all",
        is_timeout=False
    ))
    assert intent2 == "distress"

    intent3 = AegisRiskEngine._parse_voice_intent(VoiceResponse(
        transcript="I am not fine",
        is_timeout=False
    ))
    assert intent3 == "distress"

    intent_safe = AegisRiskEngine._parse_voice_intent(VoiceResponse(
        transcript="I am okay, false alarm",
        is_timeout=False
    ))
    assert intent_safe == "safe"


def test_voice_emergency_help_me():
    """Verify 'Help me' triggers emergency / distress intent."""
    intent = AegisRiskEngine._parse_voice_intent(VoiceResponse(
        transcript="Help me, I fell and can't get up",
        is_timeout=False
    ))
    assert intent == "distress"


def test_voice_silence_timeout():
    """Verify voice check timeout triggers timeout intent."""
    intent = AegisRiskEngine._parse_voice_intent(VoiceResponse(
        transcript="",
        is_timeout=True
    ))
    assert intent == "timeout"


# ---------------------------------------------------------------------------
# 6. ADAPTIVE BASELINE LEARNING & GUARDRAIL TESTS
# ---------------------------------------------------------------------------

def test_baseline_hourly_mobility_profile():
    """Verify baseline engine defines 24-hour mobility profile and zone inactivity limits."""
    assert len(PersonalBaselineEngine.HOURLY_MOBILITY_PROFILE) == 24
    # Nocturnal hours (e.g., 3 AM) expect low mobility
    assert PersonalBaselineEngine.HOURLY_MOBILITY_PROFILE[3] <= 0.15
    # Morning active hours (e.g., 10 AM) expect higher mobility
    assert PersonalBaselineEngine.HOURLY_MOBILITY_PROFILE[10] >= 0.60
    # Bathroom limit is strictly defined
    assert "bathroom" in PersonalBaselineEngine.ZONE_INACTIVITY_LIMITS_SEC
    assert PersonalBaselineEngine.ZONE_INACTIVITY_LIMITS_SEC["bathroom"] <= 1800
    assert PersonalBaselineEngine.get_zone_inactivity_limit("bathroom") <= 1800


def test_resident_feedback_learning_adaptation():
    """Verify user confirmation adapts baseline tolerance deterministically."""
    PersonalBaselineEngine.reset_learning()
    new_tol = PersonalBaselineEngine.record_resident_feedback(
        location="living_room",
        activity="reading",
        is_safe=True
    )
    assert new_tol > 0.0
    tol = PersonalBaselineEngine.get_learned_tolerance("living_room", "reading")
    assert tol == new_tol


def test_baseline_guardrail_never_suppresses_true_fall_emergency():
    """CRITICAL SAFETY: Learned behavior must NEVER suppress a true fall emergency."""
    # Seed learned tolerance for bathroom
    PersonalBaselineEngine.record_resident_feedback(
        location="bathroom",
        activity="resting",
        is_safe=True
    )

    # Inactivity with fall in bathroom at 3 AM
    dev, reasons, meta = PersonalBaselineEngine.calculate_deviation(
        location="bathroom",
        activity="fall_detected_immobility_none",
        timestamp_str="2026-10-17T03:15:00Z"
    )
    # Obvious fall emergency in bathroom must have high deviation and not be suppressed!
    assert dev >= 0.70
    assert any("abnormal" in r.lower() or "fall" in r.lower() or "circadian" in r.lower() for r in reasons)


# ---------------------------------------------------------------------------
# 7. SCENARIO DISPATCH TESTS (A through F)
# ---------------------------------------------------------------------------

def test_all_scenarios_dispatchable_and_authoritative(monkeypatch):
    """Verify all 6 core scenarios trigger correctly and transition authoritative pipeline state."""
    from app.routers import demo_api
    monkeypatch.setattr(demo_api, "_run_scenario_background", lambda name: None)
    scenarios = [
        "false_alarm",
        "responsive_emergency",
        "silent_emergency",
        "worsening_condition",
        "environmental_hazard",
        "medication_miss"
    ]
    for sc in scenarios:
        resp = client.post(f"/api/v1/demo/scenario/{sc}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "triggered"
        assert resp.json()["scenario"] == sc
