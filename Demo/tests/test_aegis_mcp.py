"""
Comprehensive test suite for Aegis Ambient Care MCP Server.
Amazon Developer Hackathon 2026.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import time
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import Event, Context, Risk
from app.models.enums import RiskLevel, WellnessState
from app.services.risk_engine import RiskEngine
from app.services.state_machine import WellnessStateMachine


client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Pydantic Models & Data Contract Tests
# ---------------------------------------------------------------------------

def test_event_schema_contract():
    event_data = {
        "event_type": "fall_detected",
        "confidence": 0.94,
        "location": "living_room",
        "timestamp": "2026-10-17T08:15:30Z",
        "movement_after_event": "none"
    }
    event = Event(**event_data)
    assert event.event_type == "fall_detected"
    assert event.confidence == 0.94
    assert event.location == "living_room"
    assert event.movement_after_event == "none"


def test_context_schema_contract():
    context_data = {
        "activity": "walking_to_kitchen",
        "time_context": "night_time",
        "baseline_deviation": 0.85,
        "wearable_status": "high_heart_rate",
        "environment": "dark_room_wet_floor"
    }
    context = Context(**context_data)
    assert context.activity == "walking_to_kitchen"
    assert context.time_context == "night_time"
    assert context.baseline_deviation == 0.85
    assert context.wearable_status == "high_heart_rate"
    assert context.environment == "dark_room_wet_floor"


def test_risk_schema_contract():
    risk_data = {
        "risk_level": "CRITICAL",
        "confidence": 0.95,
        "reasons": ["Severe fall impact", "Zero post-fall movement detected"]
    }
    risk = Risk(**risk_data)
    assert risk.risk_level == "CRITICAL"
    assert risk.confidence == 0.95
    assert len(risk.reasons) == 2


# ---------------------------------------------------------------------------
# 2. Risk Engine Evaluation & Latency Tests
# ---------------------------------------------------------------------------

def test_risk_engine_critical_fall():
    event = Event(
        event_type="fall_detected",
        confidence=0.96,
        location="bathroom",
        timestamp="2026-10-17T08:15:30Z",
        movement_after_event="none"
    )
    context = Context(
        activity="showering",
        time_context="night_time",
        baseline_deviation=0.9,
        wearable_status="high_heart_rate",
        environment="dark_room_wet_floor"
    )
    risk = RiskEngine.evaluate(event, context)
    assert risk.risk_level == RiskLevel.CRITICAL.value
    assert risk.confidence >= 0.8
    assert any("bathroom" in r.lower() or "moisture" in r.lower() for r in risk.reasons)


def test_risk_engine_low_risk_normal_movement():
    event = Event(
        event_type="loud_thud",
        confidence=0.4,
        location="living_room",
        timestamp="2026-10-17T14:15:30Z",
        movement_after_event="normal"
    )
    context = Context(
        activity="reading",
        time_context="afternoon",
        baseline_deviation=0.1,
        wearable_status="worn_normal",
        environment="well_lit"
    )
    risk = RiskEngine.evaluate(event, context)
    assert risk.risk_level in [RiskLevel.LOW.value, RiskLevel.MODERATE.value]


# ---------------------------------------------------------------------------
# 3. Conversational State Machine Tests (Task 4)
# ---------------------------------------------------------------------------

import asyncio

def test_state_machine_safe_reply_downgrades_risk():
    """
    Scenario: 'I'm okay' -> Downgrade risk -> Cancel escalation.
    """
    from app.models.schemas import WellnessCheckReplyRequest

    # Start session
    init_resp = WellnessStateMachine.start_wellness_check(session_id="test_safe_session")
    assert init_resp.state == WellnessState.PENDING_CHECK.value

    # Process safe user reply
    reply = WellnessCheckReplyRequest(
        session_id="test_safe_session",
        user_speech_transcript="I'm okay, I just dropped a book",
        is_timeout=False
    )
    resolution = asyncio.run(WellnessStateMachine.process_reply(reply))

    assert resolution.new_state == WellnessState.SAFE_RESOLVED.value
    assert resolution.updated_risk.risk_level == RiskLevel.LOW.value
    assert resolution.triggered_caregiver_notification is False
    assert resolution.triggered_emergency_escalation is False
    assert "CANCEL" in resolution.action_taken


def test_state_machine_distress_reply_elevates_risk():
    """
    Scenario: 'Help me' -> Elevate risk -> Trigger notify_caregiver & generate_emergency_packet.
    """
    from app.models.schemas import WellnessCheckReplyRequest

    init_resp = WellnessStateMachine.start_wellness_check(session_id="test_distress_session")
    assert init_resp.state == WellnessState.PENDING_CHECK.value

    # Process distress user reply
    reply = WellnessCheckReplyRequest(
        session_id="test_distress_session",
        user_speech_transcript="Help me, I fell down and my hip hurts!",
        is_timeout=False
    )
    resolution = asyncio.run(WellnessStateMachine.process_reply(reply))

    assert resolution.new_state == WellnessState.DISTRESS_ELEVATED.value
    assert resolution.updated_risk.risk_level in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]
    assert resolution.triggered_caregiver_notification is True
    assert "ELEVATE" in resolution.action_taken

    # Verify session has stored emergency packet
    session = WellnessStateMachine.get_session("test_distress_session")
    assert session.emergency_packet is not None
    assert session.caregiver_notification_id is not None


def test_state_machine_timeout_escalates_to_critical_cad():
    """
    Scenario: No response / Timeout -> Set risk to CRITICAL -> Trigger escalate_emergency.
    """
    from app.models.schemas import WellnessCheckReplyRequest

    init_resp = WellnessStateMachine.start_wellness_check(session_id="test_timeout_session")
    assert init_resp.state == WellnessState.PENDING_CHECK.value

    # Process timeout (silence / no speech)
    reply = WellnessCheckReplyRequest(
        session_id="test_timeout_session",
        user_speech_transcript="",
        is_timeout=True
    )
    resolution = asyncio.run(WellnessStateMachine.process_reply(reply))

    assert resolution.new_state == WellnessState.TIMEOUT_ESCALATED.value
    assert resolution.updated_risk.risk_level == RiskLevel.CRITICAL.value
    assert resolution.triggered_emergency_escalation is True
    assert "ESCALATE_TO_EMERGENCY_CAD" in resolution.action_taken

    session = WellnessStateMachine.get_session("test_timeout_session")
    assert session.emergency_dispatch_id is not None


# ---------------------------------------------------------------------------
# 4. HTTP Direct Tool Endpoints Tests
# ---------------------------------------------------------------------------

def test_endpoint_assess_risk():
    payload = {
        "event": {
            "event_type": "fall_detected",
            "confidence": 0.95,
            "location": "bathroom",
            "timestamp": "2026-10-17T08:15:30Z",
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
    response = client.post("/tools/assess_risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk"]["risk_level"] == "CRITICAL"
    assert data["requires_wellness_check"] is True
    assert float(response.headers["X-Response-Time-Ms"]) < 500.0


def test_endpoint_start_wellness_check():
    payload = {
        "session_id": "api_test_sess_01",
        "event": {
            "event_type": "loud_thud",
            "confidence": 0.8,
            "location": "kitchen",
            "timestamp": "2026-10-17T08:15:30Z",
            "movement_after_event": "slight_twitch"
        }
    }
    response = client.post("/tools/start_wellness_check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "api_test_sess_01"
    assert data["state"] == "PENDING_CHECK"
    assert "Eleanor" in data["prompt_text"]
    assert "speak" in data["prompt_ssml"]


def test_endpoint_notify_caregiver():
    payload = {
        "risk": {
            "risk_level": "HIGH",
            "confidence": 0.9,
            "reasons": ["Unusual prolonged stillness in hallway"]
        },
        "event": {
            "event_type": "prolonged_inactivity",
            "confidence": 0.85,
            "location": "hallway",
            "timestamp": "2026-10-17T08:15:30Z",
            "movement_after_event": "none"
        }
    }
    response = client.post("/tools/notify_caregiver", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "HIGH"
    assert len(data["channels_delivered"]) >= 3
    assert any(c["channel"] == "alexa_drop_in" for c in data["channels_delivered"])


def test_endpoint_generate_emergency_packet():
    payload = {
        "event": {
            "event_type": "fall_detected",
            "confidence": 0.97,
            "location": "bathroom",
            "timestamp": "2026-10-17T08:15:30Z",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "bathing",
            "time_context": "night_time",
            "baseline_deviation": 0.95,
            "wearable_status": "high_heart_rate",
            "environment": "dark_room_wet_floor"
        },
        "risk": {
            "risk_level": "CRITICAL",
            "confidence": 0.98,
            "reasons": ["Severe impact", "Zero movement"]
        }
    }
    response = client.post("/tools/generate_emergency_packet", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["packet_id"].startswith("EPK-")
    assert data["patient_profile"]["name"] == "Eleanor Vance"
    assert "Penicillin" in str(data["patient_profile"]["medical_history"])
    assert "EMERGENCY CAD TRANSMISSION" in data["formatted_ems_summary"]


def test_endpoint_escalate_emergency():
    payload = {
        "cad_agency_code": "EMS-CAD-MA-02108"
    }
    response = client.post("/tools/escalate_emergency", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DISPATCHED"
    assert data["door_lock_unlocked"] is True
    assert data["audio_stream_active"] is True
    assert len(data["units_dispatched"]) >= 1


# ---------------------------------------------------------------------------
# 5. MCP Streamable HTTP JSON-RPC Protocol Tests
# ---------------------------------------------------------------------------

def test_mcp_initialize():
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["result"]["serverInfo"]["name"] == "Aegis Ambient Care MCP Server"
    assert data["result"]["capabilities"]["tools"]["listChanged"] is False


def test_mcp_tools_list():
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    
    # Assert all 5 core tools are present
    assert "assess_risk" in tool_names
    assert "start_wellness_check" in tool_names
    assert "notify_caregiver" in tool_names
    assert "generate_emergency_packet" in tool_names
    assert "escalate_emergency" in tool_names


def test_endpoint_respond_wellness_check_safe():
    init_res = client.post("/tools/start_wellness_check", json={"session_id": "api_resp_sess_safe"})
    assert init_res.status_code == 200

    reply_payload = {
        "session_id": "api_resp_sess_safe",
        "user_speech_transcript": "I am fine, everything is okay",
        "is_timeout": False
    }
    resp = client.post("/tools/respond_wellness_check", json=reply_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_state"] == "SAFE_RESOLVED"
    assert data["updated_risk"]["risk_level"] == "LOW"
    assert data["triggered_emergency_escalation"] is False


def test_endpoint_respond_wellness_check_distress():
    init_res = client.post("/tools/start_wellness_check", json={"session_id": "api_resp_sess_distress"})
    assert init_res.status_code == 200

    reply_payload = {
        "session_id": "api_resp_sess_distress",
        "user_speech_transcript": "Help me please, I cannot get up",
        "is_timeout": False
    }
    resp = client.post("/tools/respond_wellness_check", json=reply_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_state"] == "DISTRESS_ELEVATED"
    assert data["triggered_caregiver_notification"] is True


def test_endpoint_respond_wellness_check_timeout():
    init_res = client.post("/tools/start_wellness_check", json={"session_id": "api_resp_sess_timeout"})
    assert init_res.status_code == 200

    reply_payload = {
        "session_id": "api_resp_sess_timeout",
        "user_speech_transcript": None,
        "is_timeout": True
    }
    resp = client.post("/tools/respond_wellness_check", json=reply_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_state"] == "TIMEOUT_ESCALATED"
    assert data["updated_risk"]["risk_level"] == "CRITICAL"
    assert data["triggered_emergency_escalation"] is True


def test_health_check_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["latency_sla"]["compliant"] is True
    assert data["latency_sla"]["engine_self_test_ms"] < 500.0


def test_mcp_tools_call_start_wellness_check():
    payload = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "start_wellness_check",
            "arguments": {
                "session_id": "mcp_rpc_wellness_01"
            }
        }
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    res = response.json()["result"]
    assert res["isError"] is False
    assert "PENDING_CHECK" in res["content"][0]["text"]


def test_mcp_tools_call_assess_risk():
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "assess_risk",
            "arguments": {
                "event": {
                    "event_type": "fall_detected",
                    "confidence": 0.95,
                    "location": "kitchen",
                    "timestamp": "2026-10-17T08:15:30Z",
                    "movement_after_event": "none"
                },
                "context": {
                    "activity": "cooking",
                    "time_context": "afternoon",
                    "baseline_deviation": 0.85,
                    "wearable_status": "high_heart_rate",
                    "environment": "well_lit"
                }
            }
        }
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["isError"] is False
    content_text = result["content"][0]["text"]
    assert "CRITICAL" in content_text or "HIGH" in content_text


def test_mcp_tools_call_escalate_emergency():
    payload = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "escalate_emergency",
            "arguments": {
                "cad_agency_code": "EMS-CAD-MA-02108"
            }
        }
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 200
    res = response.json()["result"]
    assert res["isError"] is False
    assert "DISPATCHED" in res["content"][0]["text"]



# ---------------------------------------------------------------------------
# 6. Latency Budget Verification (< 500ms)
# ---------------------------------------------------------------------------

def test_latency_budget_compliance():
    """
    Validates Amazon's strict <500ms voice round-trip latency requirement.
    """
    payload = {
        "event": {
            "event_type": "fall_detected",
            "confidence": 0.9,
            "location": "living_room",
            "timestamp": "2026-10-17T08:15:30Z",
            "movement_after_event": "slight_twitch"
        },
        "context": {
            "activity": "walking",
            "time_context": "night_time",
            "baseline_deviation": 0.7,
            "wearable_status": "worn_normal",
            "environment": "dark_room"
        }
    }

    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        resp = client.post("/tools/assess_risk", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert resp.status_code == 200
        times.append(elapsed_ms)

    avg_ms = sum(times) / len(times)
    assert avg_ms < 500.0, f"Latency breached: {avg_ms}ms exceeds 500ms SLA"
    # In practice it is < 15ms
    assert avg_ms < 50.0


if __name__ == "__main__":
    pytest.main([__file__])
