"""
Comprehensive Pytest Suite for NIRA Stateful Emergency Orchestration.
Amazon Developer Hackathon 2026.

Tests all requirements:
  - 9 Workflow States:
    DETECTED -> VERIFYING -> WELLNESS_CHECK -> WAITING_FOR_RESPONSE ->
    RESPONSIVE -> CAREGIVER_ESCALATION -> EMERGENCY_ESCALATION -> DISPATCH_READY -> RESOLVED
  - Scenarios A through J:
    A. Elder says "I'm okay"
    B. Elder asks for help
    C. Elder says they cannot move
    D. Elder does not respond (timeout)
    E. Elder responds ambiguously
    F. Sensor evidence worsens during wellness check
    G. Caregiver acknowledges
    H. Caregiver does not acknowledge (timeout escalation)
    I. Emergency is resolved
    J. Event becomes false alarm
  - Audit trail completeness:
    timestamp, previous_state, new_state, reason, evidence, actor, correlation ID
  - Idempotency & active incident deduplication
  - Dynamic emergency packet generation from real state
  - Simulated adapters (CAD, Smart Lock, SMS, Push, Alexa Drop-In) with clear disclaimers
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import init_db, SessionLocal
from app.database.models import IncidentModel, IncidentTimelineModel
from app.services.emergency_workflow import EmergencyWorkflowEngine, EmergencyWorkflowState
from app.adapters.simulated_adapters import (
    default_cad_adapter,
    default_lock_adapter,
    default_sms_adapter,
    default_push_adapter,
    default_alexa_adapter
)

init_db()
client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_test_incident(event_type: str = "possible_fall", location: str = "bathroom", confidence: float = 0.90) -> str:
    """Helper to ingest an event and return incident_id."""
    resp = client.post("/api/v1/events", json={
        "event": {
            "event_type": event_type,
            "confidence": confidence,
            "location": location,
            "timestamp": "2026-10-19T20:00:00Z",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "showering",
            "time_context": "night_time",
            "baseline_deviation": 0.85,
            "wearable_status": "high_heart_rate",
            "environment": "wet_floor"
        },
        "user_id": "user_eleanor_vance"
    })
    assert resp.status_code == 201
    return resp.json()["incident_id"]


# ---------------------------------------------------------------------------
# Test 1: Full 9-State Linear Transition Audit
# ---------------------------------------------------------------------------

def test_full_nine_state_workflow_transitions():
    """Validates the 9 canonical states and transition persistence."""
    import uuid
    with SessionLocal() as db:
        corr_id = f"CORR-TEST-9STATE-{uuid.uuid4().hex[:8]}"
        incident, _ = EmergencyWorkflowEngine.get_or_create_incident(
            db=db,
            resident_id="user_eleanor_vance",
            location=f"hallway_{uuid.uuid4().hex[:4]}",
            event_type="stumble",
            confidence=0.80,
            initial_risk_level="MODERATE",
            risk_confidence=0.85,
            risk_reasons=["Sudden deceleration"],
            correlation_id=corr_id,
            idempotency_key=f"IDEM-LINEAR-{corr_id}"
        )
        inc_id = incident.id
        assert incident.workflow_state == EmergencyWorkflowState.DETECTED.value

        # DETECTED -> VERIFYING
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.VERIFYING,
            reason="Verifying radar presence and wearable motion data.",
            evidence={"radar_confidence": 0.82},
            actor="SENSOR_FUSION", correlation_id=corr_id
        )

        # VERIFYING -> WELLNESS_CHECK
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.WELLNESS_CHECK,
            reason="Ambience requires voice prompt.",
            evidence={"prompt_tone": "gentle"},
            actor="ALEXA_VOICE_AGENT", correlation_id=corr_id
        )

        # WELLNESS_CHECK -> WAITING_FOR_RESPONSE
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.WAITING_FOR_RESPONSE,
            reason="Audio bridge opened for resident reply.",
            evidence={"window_sec": 20},
            actor="ALEXA_VOICE_AGENT", correlation_id=corr_id
        )

        # WAITING_FOR_RESPONSE -> RESPONSIVE
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.RESPONSIVE,
            reason="Resident spoke.",
            evidence={"audio_detected": True},
            actor="ELDER", correlation_id=corr_id
        )

        # RESPONSIVE -> CAREGIVER_ESCALATION
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.CAREGIVER_ESCALATION,
            reason="Elder requested assistance.",
            evidence={"need": "help"},
            actor="AEGIS_SYSTEM", correlation_id=corr_id
        )

        # CAREGIVER_ESCALATION -> EMERGENCY_ESCALATION
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.EMERGENCY_ESCALATION,
            reason="Condition worsening, first responders needed.",
            evidence={"tachycardia": 135},
            actor="AEGIS_SYSTEM", correlation_id=corr_id
        )

        # EMERGENCY_ESCALATION -> DISPATCH_READY
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.DISPATCH_READY,
            reason="Emergency packet generated and simulated CAD notified.",
            evidence={"packet_compiled": True},
            actor="EMS_CAD", correlation_id=corr_id
        )

        # DISPATCH_READY -> RESOLVED
        EmergencyWorkflowEngine.transition(
            db=db, incident_id=inc_id,
            target_state=EmergencyWorkflowState.RESOLVED,
            reason="Paramedics on scene; resident safe.",
            evidence={"paramedic_arrival": True},
            actor="FIRST_RESPONDER", correlation_id=corr_id
        )

        # Verify all 8 transitions logged with complete 7 fields
        timelines = db.query(IncidentTimelineModel).filter(
            IncidentTimelineModel.incident_id == inc_id
        ).order_by(IncidentTimelineModel.id.asc()).all()

        # Initial DETECTED transition + 8 progression transitions = 9
        assert len(timelines) >= 9

        for t in timelines:
            assert t.timestamp is not None
            assert t.previous_state is not None
            assert t.new_state is not None
            assert t.reason is not None
            assert t.evidence is not None
            assert t.actor is not None
            assert t.correlation_id is not None


# ---------------------------------------------------------------------------
# Test 2: Scenario A - Elder says "I'm okay"
# ---------------------------------------------------------------------------

def test_scenario_a_elder_says_im_okay():
    """Scenario A: Verbal confirmation of safety -> RESOLVED."""
    inc_id = create_test_incident(location="kitchen_a")
    resp = client.post(f"/api/v1/incidents/{inc_id}/respond-voice", json={
        "transcript": "I'm okay, just slipped a little bit but I am totally fine.",
        "is_timeout": False
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RESOLVED"
    assert data["risk_level"] == "LOW"
    assert data["workflow_state"] == "RESOLVED"

    # Verify timeline reflects resolution
    tl_resp = client.get(f"/api/v1/incidents/{inc_id}/timeline")
    assert tl_resp.status_code == 200
    actions = [item["action_type"] for item in tl_resp.json()]
    assert "RESOLVED_SAFE" in actions


# ---------------------------------------------------------------------------
# Test 3: Scenario B - Elder asks for help
# ---------------------------------------------------------------------------

def test_scenario_b_elder_asks_for_help():
    """Scenario B: Elder calls for help -> CAREGIVER_ESCALATION."""
    inc_id = create_test_incident(location="bedroom_b")
    resp = client.post(f"/api/v1/incidents/{inc_id}/respond-voice", json={
        "transcript": "Help me, I fell and I need someone to help me up please.",
        "is_timeout": False
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ESCALATED_CAREGIVER"
    assert data["workflow_state"] == "CAREGIVER_ESCALATION"
    assert "caregiver_details" in data
    assert len(data["caregiver_details"]["channels_delivered"]) > 0


# ---------------------------------------------------------------------------
# Test 4: Scenario C - Elder says they cannot move
# ---------------------------------------------------------------------------

def test_scenario_c_elder_cannot_move():
    """Scenario C: Elder says they cannot move -> EMERGENCY_ESCALATION -> DISPATCH_READY."""
    inc_id = create_test_incident(location="bathroom_c")
    resp = client.post(f"/api/v1/incidents/{inc_id}/respond-voice", json={
        "transcript": "I cannot move, my hip is broken and I can't move at all!",
        "is_timeout": False
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ESCALATED_CAD"
    assert data["workflow_state"] == "DISPATCH_READY"
    assert data["cad_details"]["door_lock_unlocked"] is True
    assert data["cad_details"]["smart_lock_pin"] is not None


# ---------------------------------------------------------------------------
# Test 5: Scenario D - Elder does not respond (timeout)
# ---------------------------------------------------------------------------

def test_scenario_d_elder_does_not_respond():
    """Scenario D: Complete silence / timeout -> EMERGENCY_ESCALATION -> DISPATCH_READY."""
    inc_id = create_test_incident(location="hallway_d")
    resp = client.post(f"/api/v1/incidents/{inc_id}/respond-voice", json={
        "transcript": None,
        "is_timeout": True
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ESCALATED_CAD"
    assert data["workflow_state"] == "DISPATCH_READY"
    assert "cad_details" in data
    assert data["cad_details"]["dispatch_id"].startswith("CAD-DISP-")


# ---------------------------------------------------------------------------
# Test 6: Scenario E - Elder responds ambiguously
# ---------------------------------------------------------------------------

def test_scenario_e_elder_responds_ambiguously():
    """Scenario E: Unclear response -> CAREGIVER_ESCALATION for human verification."""
    inc_id = create_test_incident(location="living_room_e")
    resp = client.post(f"/api/v1/incidents/{inc_id}/respond-voice", json={
        "transcript": "Uh... what... I don't know what is happening...",
        "is_timeout": False
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ESCALATED_CAREGIVER"
    assert data["workflow_state"] == "CAREGIVER_ESCALATION"
    assert data["scenario"] == "E_AMBIGUOUS_RESPONSE"


# ---------------------------------------------------------------------------
# Test 7: Scenario F - Sensor evidence worsens during wellness check
# ---------------------------------------------------------------------------

def test_scenario_f_sensor_evidence_worsens():
    """Scenario F: Vitals or immobility worsen during wellness check -> immediate CAD escalation."""
    inc_id = create_test_incident(location="bathroom_f")
    resp = client.post(f"/api/v1/incidents/{inc_id}/sensor-update", json={
        "evidence": {
            "heart_rate_bpm": 142,
            "prolonged_immobility_seconds": 90,
            "radar_respiration_rate": "irregular"
        },
        "reason": "Wearable detected severe tachycardia (142 bpm) during wellness check."
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ESCALATED_CAD"
    assert data["workflow_state"] == "DISPATCH_READY"
    assert data["door_lock_unlocked"] is True


# ---------------------------------------------------------------------------
# Test 8: Scenario G - Caregiver acknowledges
# ---------------------------------------------------------------------------

def test_scenario_g_caregiver_acknowledges():
    """Scenario G: Caregiver acknowledges alert and assumes primary care -> RESOLVED."""
    inc_id = create_test_incident(location="study_g")
    # First escalate to caregiver
    client.post(f"/api/v1/incidents/{inc_id}/escalate", json={"escalation_type": "caregiver"})

    # Caregiver acknowledges
    ack_resp = client.post(f"/api/v1/incidents/{inc_id}/acknowledge", json={
        "caregiver_actor": "Sarah Vance (Caregiver)",
        "notes": "I live 5 minutes away, driving over right now to check on mom."
    })
    assert ack_resp.status_code == 200
    data = ack_resp.json()
    assert data["status"] == "RESOLVED"
    assert data["workflow_state"] == "RESOLVED"
    assert data["actor"] == "Sarah Vance (Caregiver)"


# ---------------------------------------------------------------------------
# Test 9: Scenario H - Caregiver does not acknowledge (timeout)
# ---------------------------------------------------------------------------

def test_scenario_h_caregiver_timeout():
    """Scenario H: Caregiver non-acknowledgement timeout -> auto CAD escalation."""
    inc_id = create_test_incident(location="kitchen_h")
    client.post(f"/api/v1/incidents/{inc_id}/escalate", json={"escalation_type": "caregiver"})

    # Timeout occurs
    timeout_resp = client.post(f"/api/v1/incidents/{inc_id}/caregiver-timeout?timeout_seconds=120")
    assert timeout_resp.status_code == 200
    data = timeout_resp.json()
    assert data["status"] == "ESCALATED_CAD"
    assert data["workflow_state"] == "DISPATCH_READY"
    assert data["door_lock_unlocked"] is True


# ---------------------------------------------------------------------------
# Test 10: Scenario I - Emergency is resolved explicitly
# ---------------------------------------------------------------------------

def test_scenario_i_emergency_resolved():
    """Scenario I: Explicit resolution by care team."""
    inc_id = create_test_incident(location="hallway_i")
    client.post(f"/api/v1/incidents/{inc_id}/escalate", json={"escalation_type": "emergency"})

    resolve_resp = client.post(f"/api/v1/incidents/{inc_id}/resolve", json={
        "actor": "EMS_PARAMEDIC_LIEUTENANT",
        "reason": "Patient evaluated on scene. Vitals normalized, no acute trauma, resting in chair.",
        "evidence": {"bp": "120/80", "pulse": 72}
    })
    assert resolve_resp.status_code == 200
    data = resolve_resp.json()
    assert data["workflow_state"] == "RESOLVED"
    assert data["scenario"] == "I_EMERGENCY_RESOLVED"


# ---------------------------------------------------------------------------
# Test 11: Scenario J - Event becomes false alarm
# ---------------------------------------------------------------------------

def test_scenario_j_false_alarm():
    """Scenario J: Multimodal false alarm resolution."""
    inc_id = create_test_incident(location="dining_room_j")
    fa_resp = client.post(f"/api/v1/incidents/{inc_id}/false-alarm", params={
        "reason": "Resident upright with normal gait velocity verified by radar and camera."
    })
    assert fa_resp.status_code == 200
    data = fa_resp.json()
    assert data["workflow_state"] == "RESOLVED"
    assert data["scenario"] == "J_FALSE_ALARM"


# ---------------------------------------------------------------------------
# Test 12: Idempotency and Active Incident Deduplication
# ---------------------------------------------------------------------------

def test_idempotency_and_active_incident_deduplication():
    """Same emergency event submitted twice must attach to existing incident rather than duplicating."""
    import uuid
    loc = f"living_room_dedup_{uuid.uuid4().hex[:6]}"
    with SessionLocal() as db:
        initial_count = db.query(IncidentModel).count()

    event_payload = {
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.89,
            "location": loc,
            "timestamp": "2026-10-19T21:00:00Z",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "walking",
            "time_context": "evening",
            "baseline_deviation": 0.70,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        },
        "user_id": "user_eleanor_vance"
    }

    # First submission
    resp1 = client.post("/api/v1/events", json=event_payload)
    assert resp1.status_code == 201
    id1 = resp1.json()["incident_id"]

    # Immediate second submission (same resident, location, within dedup window)
    resp2 = client.post("/api/v1/events", json=event_payload)
    assert resp2.status_code == 201
    id2 = resp2.json()["incident_id"]

    # Must reuse the same incident ID
    assert id1 == id2

    with SessionLocal() as db:
        new_count = db.query(IncidentModel).count()
        assert new_count == initial_count + 1  # Only 1 incident created, not 2


# ---------------------------------------------------------------------------
# Test 13: Dynamic Emergency Packet Generation from Actual State
# ---------------------------------------------------------------------------

def test_dynamic_emergency_packet_generation():
    """Validates that emergency packets are dynamically compiled from DB state."""
    inc_id = create_test_incident(event_type="high_impact_fall", location="master_bathroom", confidence=0.97)

    packet_resp = client.get(f"/api/v1/incidents/{inc_id}/packet")
    assert packet_resp.status_code == 200
    packet_data = packet_resp.json()

    # Dynamic fields from actual UserModel and IncidentModel
    assert packet_data["patient_profile"]["name"] == "Eleanor Vance"
    assert packet_data["patient_profile"]["age"] == 79
    assert "bathroom" in packet_data["incident_metadata"]["location"].lower()
    assert packet_data["incident_metadata"]["confidence"] == 0.97
    assert "telemetry_summary" in packet_data
    assert packet_data["telemetry_summary"]["incident_id"] == inc_id

    # Formatted EMS summary contains actual values
    summary = packet_data["formatted_ems_summary"]
    assert "ELEANOR VANCE" in summary.upper()
    assert "MASTER_BATHROOM" in summary.upper()
    assert "HIGH_IMPACT_FALL" in summary.upper()
    assert "Simulation Mode active via adapter layer" in summary


# ---------------------------------------------------------------------------
# Test 14: Simulated Adapter Disclaimers and Integration Types
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulated_adapters_contract_and_disclaimers():
    """Validates that all external integrations return SIMULATED and have clear disclaimers."""
    # CAD Adapter
    cad_result = await default_cad_adapter.dispatch_emergency(
        emergency_packet_id="EPK-TEST-01",
        triage_priority="DELTA_CRITICAL",
        cad_agency_code="EMS-CAD-MA-02108",
        location_address="123 Test St",
        formatted_summary="Test Summary",
        resident_name="Eleanor Vance",
        medical_notes=["Hypertension"]
    )
    assert cad_result.integration_type == "SIMULATED"
    assert "Not connected to live external carrier/PSAP" in cad_result.disclaimer
    assert cad_result.transaction_id.startswith("CAD-DISP-")

    # Smart Lock Adapter
    lock_result = await default_lock_adapter.unlock_door(
        device_id="lock_test_01",
        actor="TEST_ACTOR",
        reason="Test emergency"
    )
    assert lock_result.integration_type == "SIMULATED"
    assert lock_result.status == "UNLOCKED"
    assert "emergency_access_pin" in lock_result.details

    # SMS Adapter
    sms_result = await default_sms_adapter.send_message(
        recipient="+15551234567",
        headline="Alert",
        body="Test alert",
        priority="HIGH"
    )
    assert sms_result.integration_type == "SIMULATED"
    assert "Simulated-Twilio-SMS" in sms_result.provider_name

    # Push Adapter
    push_result = await default_push_adapter.send_message(
        recipient="token_test_123",
        headline="Alert",
        body="Test push alert",
        priority="HIGH"
    )
    assert push_result.integration_type == "SIMULATED"
    assert "Simulated-Apple-APNS-FCM" in push_result.provider_name

    # Alexa Drop-In Adapter
    alexa_result = await default_alexa_adapter.send_message(
        recipient="echo_device_sarah",
        headline="Audio Bridge",
        body="Opening drop in",
        priority="CRITICAL"
    )
    assert alexa_result.integration_type == "SIMULATED"
    assert alexa_result.details["ambient_duplex_active"] is True
