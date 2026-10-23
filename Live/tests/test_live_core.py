"""
Unit and Integration Tests for Authoritative NIRA Live Safety Core.
Covers:
1. Event validation, normalization, deduplication, and pipeline ingestion
2. Context Engine and Baseline Adaptation
3. Multimodal Risk Intelligence (14 signals), Contradictory Resolution, and Hysteresis
4. Deterministic Emergency Workflow (10-state FSM)
5. Incident Manager and Audit Timelines
6. Authoritative CAD Emergency Packet Generator
7. Real-time Pub/Sub Event Bus
8. CoreService Orchestrator (Fall, Immobility, Vocal Safe Confirmation, Distress, Silence Timeout)
9. FastAPI Core Router Endpoints
"""

import time
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from Live.core.models import (
    EventType, EventSource, ZoneType, SafetyState, SeverityLevel,
    RecommendedAction, LiveEvent, SignalEvidence, ContextState, IncidentRecord
)
from Live.core.event_contracts import (
    normalize_raw_event,
    validate_event_freshness,
    normalize_zone,
    normalize_event_type,
    normalize_event_source,
    create_event_fingerprint
)
from Live.core.event_pipeline import EventPipeline
from Live.core.context_engine import ContextEngine
from Live.core.baseline_engine import BaselineEngineAdapter
from Live.core.risk_intelligence import SignalExtractor
from Live.core.risk_engine import RiskEngine
from Live.core.emergency_workflow import EmergencyWorkflowFSM, VALID_TRANSITIONS
from Live.core.incident_manager import IncidentManager
from Live.core.emergency_packet import EmergencyPacketBuilder
from Live.core.realtime_bus import RealtimeBus
from Live.core.core_service import CoreService, get_live_core
from Live.app.main import app


# ---------------------------------------------------------------------------
# 1. Event Validation & Contracts
# ---------------------------------------------------------------------------
def test_normalize_raw_event_accepts_valid_payload():
    raw = {
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "Living_Room",
        "confidence": 0.95,
        "payload": {"posture": "ground_impact"}
    }
    event, err = normalize_raw_event(raw)
    assert err is None
    assert event is not None
    assert event.event_type == EventType.FALL_DETECTED
    assert event.source == EventSource.CAMERA_VISION
    assert event.location.zone == ZoneType.LIVING_ROOM
    assert event.confidence == 0.95

    fp = create_event_fingerprint(event)
    assert fp is not None and len(fp) == 64


def test_validate_event_freshness_rejects_stale_and_future():
    # Stale event (> 300 seconds)
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=350)).isoformat()
    is_fresh, reason = validate_event_freshness(stale_time)
    assert is_fresh is False
    assert "Stale event" in reason

    # Impossibly in the future (> 60 seconds)
    future_time = (datetime.now(timezone.utc) + timedelta(seconds=120)).isoformat()
    is_fresh_fut, reason_fut = validate_event_freshness(future_time)
    assert is_fresh_fut is False
    assert "Clock skew" in reason_fut


def test_normalization_heuristics():
    assert normalize_zone("master_bathroom") == ZoneType.BATHROOM
    assert normalize_zone("living room") == ZoneType.LIVING_ROOM
    assert normalize_zone("unknown_area") == ZoneType.UNKNOWN

    assert normalize_event_type("slip_fall") == EventType.FALL_DETECTED
    assert normalize_event_type("stillness_inactivity") == EventType.INACTIVITY_WARNING
    assert normalize_event_source("front_camera") == EventSource.CAMERA_VISION
    assert normalize_event_source("mic_whisper") == EventSource.VOICE_ASSISTANT


# ---------------------------------------------------------------------------
# 2. Ingestion Pipeline & Sliding Window Deduplication
# ---------------------------------------------------------------------------
def test_pipeline_deduplication():
    pipeline = EventPipeline(dedup_window_seconds=10.0)
    raw = {
        "event_id": "test-fixed-id-12345",
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "bedroom",
        "confidence": 0.9
    }
    ev1, status1 = pipeline.ingest(raw)
    assert ev1 is not None
    assert status1 == "SUCCESS"

    # Immediate identical event is suppressed as duplicate
    ev2, status2 = pipeline.ingest(raw)
    assert ev2 is None
    assert status2 == "DUPLICATE_EVENT_DROPPED"

    stats = pipeline.get_stats()
    assert stats["total_ingested"] == 2
    assert stats["duplicates_dropped"] == 1
    assert stats["valid_processed"] == 1


def test_pipeline_stale_rejection():
    pipeline = EventPipeline()
    stale_time = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
    raw = {
        "event_type": "fall_detected",
        "source": "camera_vision",
        "timestamp": stale_time
    }
    ev, status = pipeline.ingest(raw)
    assert ev is None
    assert "Stale" in status
    stats = pipeline.get_stats()
    assert stats["stale_rejected"] == 1


# ---------------------------------------------------------------------------
# 3. Context Engine & Baseline Adaptation
# ---------------------------------------------------------------------------
def test_context_engine_zone_and_environmental_multipliers():
    engine = ContextEngine()
    # Bathroom base hazard weight is 1.45
    ctx_bath = engine.get_context(ZoneType.BATHROOM)
    assert ctx_bath.zone_risk_tier == "CRITICAL_ZONE"
    assert ctx_bath.hazard_multiplier >= 1.45

    # Update environmental hazards: wet floor, dark, extreme cold
    updated = engine.update_environment(
        zone=ZoneType.BATHROOM,
        is_dark=True,
        is_wet_floor=True,
        temperature_c=12.0
    )
    assert updated.is_wet_floor is True
    assert updated.is_dark is True
    assert updated.hazard_multiplier >= 2.0  # Amplified by environmental hazards


def test_baseline_engine_adapter():
    adapter = BaselineEngineAdapter()
    threshold = adapter.get_dynamic_threshold_seconds(ZoneType.LIVING_ROOM)
    assert threshold >= 180.0

    eval_normal = adapter.evaluate_motionless_risk(ZoneType.LIVING_ROOM, motionless_seconds=60.0)
    assert eval_normal["is_anomaly"] is False

    eval_excessive = adapter.evaluate_motionless_risk(ZoneType.LIVING_ROOM, motionless_seconds=900.0)
    assert eval_excessive["is_anomaly"] is True

    # Reinforce safe confirmation
    adapter.reinforce_safe_confirmation(ZoneType.LIVING_ROOM, duration_sec=700.0)


# ---------------------------------------------------------------------------
# 4. Multimodal Risk Intelligence (14 Signals)
# ---------------------------------------------------------------------------
def test_signal_extractor_evaluates_all_14_signals():
    ctx_engine = ContextEngine()
    base_engine = BaselineEngineAdapter()
    extractor = SignalExtractor(ctx_engine, base_engine)

    trigger_event, _ = normalize_raw_event({
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "living_room",
        "confidence": 0.95,
        "payload": {"posture": "ground_horizontal", "velocity": 4.2}
    })

    signals = extractor.extract_signals(
        trigger_event=trigger_event,
        recent_events=[trigger_event],
        active_zone=ZoneType.LIVING_ROOM,
        voice_state={"distress": True, "unresponsive": False},
        vitals_state={"heart_rate_bpm": 145, "status": "TACHYCARDIA"},
        hardware_health={"camera_vision": True, "wearable_sensor": True}
    )

    assert len(signals) == 14
    sig_map = {s.signal_name: s for s in signals}
    assert sig_map["fall_probability"].is_abnormal is True
    assert sig_map["voice_distress"].is_abnormal is True
    assert sig_map["heart_rate"].is_abnormal is True


def test_risk_engine_contradictory_sensor_resolution():
    """
    Contradictory evidence: Vision camera might see partial upright, but resident
    screams for help. The voice distress + fall flag triggers Critical override.
    """
    ctx_engine = ContextEngine()
    base_engine = BaselineEngineAdapter()
    risk_engine = RiskEngine(ctx_engine, base_engine)

    trigger_event, _ = normalize_raw_event({
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "living_room",
        "confidence": 0.85,
        "payload": {"posture": "ground_horizontal"}
    })

    assessment = risk_engine.assess_risk(
        trigger_event=trigger_event,
        recent_events=[trigger_event],
        active_zone=ZoneType.LIVING_ROOM,
        voice_state={"distress": True, "unresponsive": False},
        vitals_state={"heart_rate_bpm": 80}
    )

    assert assessment.overall_score >= 0.85
    assert assessment.risk_level == SeverityLevel.CRITICAL
    assert assessment.recommended_action in [RecommendedAction.DISPATCH_EMERGENCY_CAD, RecommendedAction.ESCALATE_CAREGIVER]


def test_risk_engine_hysteresis():
    """
    High risk state must not abruptly plunge to zero on a single noisy empty frame.
    """
    ctx_engine = ContextEngine()
    base_engine = BaselineEngineAdapter()
    risk_engine = RiskEngine(ctx_engine, base_engine)

    trigger_event, _ = normalize_raw_event({
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "bathroom",
        "confidence": 0.95,
        "payload": {"posture": "ground_horizontal"}
    })

    assessment1 = risk_engine.assess_risk(
        trigger_event=trigger_event,
        recent_events=[trigger_event],
        active_zone=ZoneType.BATHROOM,
        voice_state={"distress": True}
    )
    assert assessment1.risk_level == SeverityLevel.CRITICAL

    # Next frame: empty input (e.g. sensor dropout)
    assessment2 = risk_engine.assess_risk(
        trigger_event=None,
        recent_events=[],
        active_zone=ZoneType.BATHROOM
    )
    # Hysteresis dampening preserves risk above reset floor
    assert assessment2.overall_score >= 0.20


# ---------------------------------------------------------------------------
# 5. Deterministic Emergency Workflow (FSM)
# ---------------------------------------------------------------------------
def test_emergency_workflow_fsm_valid_and_invalid_transitions():
    fsm = EmergencyWorkflowFSM()
    assert fsm.current_state == SafetyState.NORMAL

    # NORMAL -> DETECTED (valid)
    ok1, entry1 = fsm.transition(SafetyState.DETECTED, "FALL_NOTICED", "Fall impact observed")
    assert ok1 is True
    assert fsm.current_state == SafetyState.DETECTED

    # DETECTED -> WELLNESS_CHECK (valid)
    ok2, entry2 = fsm.transition(SafetyState.WELLNESS_CHECK, "START_PROMPT", "Asking resident")
    assert ok2 is True
    assert fsm.current_state == SafetyState.WELLNESS_CHECK

    # WELLNESS_CHECK -> WAITING_FOR_RESPONSE (valid)
    ok3, entry3 = fsm.transition(SafetyState.WAITING_FOR_RESPONSE, "MIC_OPENED", "Listening to resident")
    assert ok3 is True
    assert fsm.current_state == SafetyState.WAITING_FOR_RESPONSE

    # Invalid jump: WAITING_FOR_RESPONSE directly to NORMAL is forbidden by strict graph!
    ok_inv, entry_inv = fsm.transition(SafetyState.NORMAL, "JUMP_FORBIDDEN", "Premature jump")
    assert ok_inv is False
    assert fsm.current_state == SafetyState.WAITING_FOR_RESPONSE

    # WAITING_FOR_RESPONSE -> RESPONSIVE -> RESOLVED -> NORMAL (valid path)
    ok4, _ = fsm.transition(SafetyState.RESPONSIVE, "RESIDENT_ANSWERED", "I am okay")
    assert ok4 is True
    ok5, _ = fsm.transition(SafetyState.RESOLVED, "CONFIRMED_SAFE", "Resolved as safe")
    assert ok5 is True
    ok6, _ = fsm.transition(SafetyState.NORMAL, "RESUME_MONITORING", "Back to normal")
    assert ok6 is True
    assert fsm.current_state == SafetyState.NORMAL


# ---------------------------------------------------------------------------
# 6. Incident Manager & Audit Timelines
# ---------------------------------------------------------------------------
def test_incident_manager_lifecycle():
    manager = IncidentManager()
    event, _ = normalize_raw_event({
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "living_room",
        "confidence": 0.94
    })

    inc = manager.create_incident(
        trigger_event=event,
        severity=SeverityLevel.HIGH,
        risk_score=0.78
    )
    assert inc is not None
    assert inc.incident_id.startswith("INC-")
    assert manager.get_active_incident() is not None

    # Step: start wellness check
    manager.start_wellness_check(inc.incident_id, "Are you okay Eleanor?")
    assert manager.current_state == SafetyState.WAITING_FOR_RESPONSE

    # Step: record voice response
    manager.record_voice_response(inc.incident_id, "I'm okay, no problem", classification="SAFE")
    # Verified SAFE voice response auto-resolves incident and returns workflow to NORMAL
    assert inc.state == SafetyState.RESOLVED
    assert manager.current_state == SafetyState.NORMAL
    assert manager.get_active_incident() is None

    # Verify audit timeline
    timeline = manager.get_timeline(inc.incident_id)
    assert len(timeline) >= 4


# ---------------------------------------------------------------------------
# 7. CAD Emergency Packet Generator (Zero Hallucination)
# ---------------------------------------------------------------------------
def test_emergency_packet_generator_structure():
    manager = IncidentManager()
    event, _ = normalize_raw_event({
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "bathroom",
        "confidence": 0.98
    })
    inc = manager.create_incident(event, severity=SeverityLevel.CRITICAL, risk_score=0.92)

    packet = EmergencyPacketBuilder.build(
        incident=inc,
        patient_profile={
            "name": "Eleanor Vance",
            "age": 78,
            "conditions": ["Hypertension", "History of falls"],
            "allergies": ["Penicillin"]
        },
        caregiver_info={
            "name": "Dharaneesh N",
            "phone": "9489240892"
        },
        smart_home_state={
            "door_lock_status": "UNLOCKED",
            "front_door_pin": "8492"
        }
    )

    assert packet.incident_id == inc.incident_id
    assert packet.resident["full_name"] == "Eleanor Vance"
    assert packet.caregiver_contact["phone"] == "9489240892"
    assert packet.smart_home_state["front_door_pin"] == "8492"
    assert packet.location["zone"] == "bathroom"


# ---------------------------------------------------------------------------
# 8. Real-time Pub/Sub Bus
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_realtime_bus_publish_and_subscribe():
    bus = RealtimeBus()
    q = await bus.subscribe()

    await bus.publish("incident_created", {"incident_id": "INC-TEST-99"})
    msg = await q.get()
    assert msg["topic"] == "incident_created"
    assert msg["data"]["incident_id"] == "INC-TEST-99"

    await bus.unsubscribe(q)


# ---------------------------------------------------------------------------
# 9. CoreService End-to-End Orchestrator
# ---------------------------------------------------------------------------
def test_core_service_fall_then_safe_confirmation():
    core = CoreService()

    # 1. Ingest Fall Event
    event, risk, inc = core.ingest_event({
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "living_room",
        "confidence": 0.95,
        "payload": {"posture": "ground_impact"}
    })
    assert event is not None
    assert inc is not None
    state_snap = core.get_current_state()
    assert state_snap["safety_state"] in ["WELLNESS_CHECK", "WAITING_FOR_RESPONSE"]

    # 2. Resident Responds "I'm okay, just dropped my book"
    res = core.process_wellness_response("I am completely fine and okay, thank you")
    assert res["success"] is True
    assert res["classification"] == "SAFE"
    assert res["state"] in ["NORMAL", "RESOLVED"]


def test_core_service_inactivity_then_silence_timeout():
    core = CoreService()

    # 1. Ingest Immobility Alert (5-10 min)
    event, risk, inc = core.ingest_event({
        "event_type": "inactivity_critical",
        "source": "camera_vision",
        "zone": "living_room",
        "confidence": 0.90,
        "payload": {"duration_seconds": 360}
    })
    assert inc is not None

    # 2. Start Wellness Check (idempotent if already in progress)
    state = core.get_current_state()["safety_state"]
    if state != "WAITING_FOR_RESPONSE":
        core.start_wellness_check(inc.incident_id, "Eleanor, are you feeling alright?")
    assert core.get_current_state()["safety_state"] == "WAITING_FOR_RESPONSE"

    # 3. 15s Silence Timeout triggers emergency escalation
    silence_res = core.handle_silence_timeout(inc.incident_id)
    assert silence_res["success"] is True
    assert silence_res["state"] in ["EMERGENCY_ESCALATION", "DISPATCH_READY"]
    assert silence_res["escalated"] is True


# ---------------------------------------------------------------------------
# 10. FastAPI Core API Router Tests
# ---------------------------------------------------------------------------
client = TestClient(app)


def test_core_api_get_state():
    resp = client.get("/api/v1/live/core/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "safety_state" in data["state"]


def test_core_api_ingest_event_and_packet():
    # Ingest fall
    resp = client.post("/api/v1/live/core/events", json={
        "event_type": "fall_detected",
        "source": "camera_vision",
        "zone": "bathroom",
        "confidence": 0.97
    })
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    inc_id = res_data["active_incident_id"]
    assert inc_id is not None

    # Retrieve emergency packet
    pkt_resp = client.get(f"/api/v1/live/core/incidents/{inc_id}/packet")
    assert pkt_resp.status_code == 200
    pkt_data = pkt_resp.json()
    assert pkt_data["success"] is True
    assert pkt_data["emergency_packet"]["resident"]["full_name"] == "Eleanor Vance"

    # Resolve incident
    resolve_resp = client.post(f"/api/v1/live/core/incidents/{inc_id}/resolve", json={
        "outcome": "SAFE_CONFIRMED",
        "resolved_by": "CARE_TEAM",
        "notes": "Verified by phone call"
    })
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["incident"]["state"] == "RESOLVED"
