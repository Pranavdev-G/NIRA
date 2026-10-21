"""
Production-Style Backend Hardening & Reliability Test Suite for NIRA.
Amazon Developer Hackathon 2026.

Validates:
  1. Event Ingestion (single, batch, edge cases)
  2. Concurrent Events & Lock Safety (async race conditions, state integrity)
  3. Duplicate Events & Idempotency (deduplication cache, no double-escalations)
  4. Delayed / Stale Events (max staleness window enforcement)
  5. Malformed Events & Schema Validation (HTTP 422 failure paths)
  6. Missing Telemetry & Partial Payload Resilience (empty dict, non-standard keys)
  7. Sensor Disconnect & Redundant Sensor Fusion (wearable off-wrist + radar verification)
  8. Emergency Escalation Workflow (DETECTED -> WELLNESS_CHECK -> CAREGIVER -> DISPATCH)
  9. Emergency Cancellation / False Alarm Resolution (voice "I'm okay" -> RESOLVED)
  10. Wellness Timeout (unresponsive timer window -> silent emergency)
  11. Caregiver Acknowledgement (caregiver ack -> halts escalation)
  12. Database Persistence & Transaction Rollback (telemetry, incidents, timeline)
  13. Restart Recovery (re-hydrating active incident & evidence from DB)
  14. SSE / WebSocket Streaming & Slow Consumer Protection (queue limit, disconnect cleanup)
  15. Deterministic Risk Calculations (exact score bounds and multi-factor mathematical weights)
  16. MCP Tools Integration (protocol compliance)
  17. Simulator Integration (multi-device telemetry driving backend state)
"""

import sys
import json
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database.session import SessionLocal
from app.database.models import IncidentModel, IncidentTimelineModel, TelemetryEventModel
from app.models.event_contracts import (
    UnifiedEvent, EventSource, EventType, SafetyState
)
from app.models.enums import RiskLevel
from app.services.event_pipeline import global_pipeline
from app.services.emergency_workflow import EmergencyWorkflowEngine, EmergencyWorkflowState
from wearable_simulator import WearableSimulator
from radar_simulator import RadarSimulator
from environment_simulator import EnvironmentSimulator
from voice_simulator import VoiceSimulator


@pytest.fixture
def client():
    """In-process TestClient to evaluate endpoints without external server dependency."""
    return TestClient(app)


@pytest.fixture
def db():
    """Database session for validating persistent state."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_clean_state():
    """Ensures each test begins with a pristine baseline."""
    global_pipeline.reset_to_normal()
    yield
    global_pipeline.reset_to_normal()


def make_valid_event(
    event_type: str = "wearable_telemetry",
    source: str = "wearable",
    room_id: str = "living_room",
    payload: Dict[str, Any] = None,
    confidence: float = 0.95,
    timestamp: str = None,
    correlation_id: str = None,
    event_id: str = None
) -> Dict[str, Any]:
    """Helper to generate a structurally valid UnifiedEvent dict."""
    now_iso = timestamp or datetime.now(timezone.utc).isoformat()
    return {
        "event_id": event_id or f"evt-test-{uuid.uuid4().hex[:8]}",
        "timestamp": now_iso,
        "resident_id": "user_eleanor_vance",
        "room_id": room_id,
        "source": source,
        "event_type": event_type,
        "payload": payload if payload is not None else {"heart_rate_bpm": 74, "movement_index": 0.5},
        "confidence": confidence,
        "correlation_id": correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
    }


# ===========================================================================
# 1. Event Ingestion & Batch Ingestion
# ===========================================================================

def test_event_ingestion_single(client):
    """Single valid UnifiedEvent is accepted, parsed, and logged."""
    ev = make_valid_event(event_type="wearable_telemetry", payload={"heart_rate_bpm": 72, "movement_index": 0.6})
    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACCEPTED"
    assert data["event_id"] == ev["event_id"]
    assert data["safety_state"] == "NORMAL"
    assert data["risk_level"] == "LOW"


def test_event_ingestion_batch(client):
    """Batch of sequential ordered events processed atomically."""
    corr = f"corr-batch-{uuid.uuid4().hex[:6]}"
    batch = [
        make_valid_event(event_type="radar_presence", source="radar", room_id="hallway", correlation_id=corr),
        make_valid_event(event_type="wearable_telemetry", source="wearable", room_id="hallway", correlation_id=corr),
        make_valid_event(event_type="environmental_reading", source="environment", room_id="hallway", correlation_id=corr)
    ]
    resp = client.post("/api/v1/events/batch", json=batch)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 3
    for r in results:
        assert r["status"] == "ACCEPTED"
        assert r["correlation_id"] == corr


# ===========================================================================
# 2. Concurrent Events & Lock Safety
# ===========================================================================

@pytest.mark.asyncio
async def test_concurrent_event_ingestion_lock_safety():
    """
    Submits 15 events simultaneously from multiple coroutines.
    Verifies that pipeline lock eliminates race conditions and preserves state integrity.
    """
    corr = f"corr-conc-{uuid.uuid4().hex[:6]}"
    events = [
        UnifiedEvent(**make_valid_event(
            event_id=f"evt-conc-{i:03d}",
            correlation_id=corr,
            payload={"heart_rate_bpm": 70 + (i % 5), "movement_index": 0.5}
        ))
        for i in range(15)
    ]

    async def ingest_task(ev):
        return await global_pipeline.ingest_event(ev)

    results = await asyncio.gather(*[ingest_task(ev) for ev in events])
    assert len(results) == 15
    for res in results:
        assert res.status == "ACCEPTED"

    # Verify authoritative state after all concurrent events
    assert global_pipeline.current_state.resident_id == "user_eleanor_vance"
    assert global_pipeline.current_state.safety_state == "NORMAL"
    # Ensure evidence history recorded all distinct events up to deque capacity
    assert len(global_pipeline.current_state.accumulated_evidence) >= 15


# ===========================================================================
# 3. Duplicate Events & Idempotency
# ===========================================================================

def test_duplicate_event_rejection(client):
    """Submitting the identical event_id twice returns DUPLICATE_IGNORED and does not alter state."""
    fixed_id = f"evt-dup-{uuid.uuid4().hex[:8]}"
    ev = make_valid_event(event_id=fixed_id)

    # First attempt: ACCEPTED
    r1 = client.post("/api/v1/events/ingest", json=ev)
    assert r1.status_code == 200
    assert r1.json()["status"] == "ACCEPTED"

    # Second attempt: DUPLICATE_IGNORED
    r2 = client.post("/api/v1/events/ingest", json=ev)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "DUPLICATE_IGNORED"
    assert data2["state_changed"] is False


# ===========================================================================
# 4. Delayed / Stale Events
# ===========================================================================

def test_stale_delayed_event_handling(client):
    """
    An event with a timestamp older than MAX_STALENESS_SECONDS (300s)
    is accepted as historical audit telemetry but flagged STALE_FLAGGED without changing safety state.
    """
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    ev = make_valid_event(
        event_type="possible_fall",
        source="camera_pose",
        timestamp=stale_time,
        payload={"fall_confirmed": True, "movement_after_event": "none"}
    )
    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "STALE_FLAGGED"
    assert data["state_changed"] is False
    assert data["safety_state"] == "NORMAL"  # Did NOT advance state


# ===========================================================================
# 5. Malformed Events & Schema Validation (Failure-Path Tests)
# ===========================================================================

def test_malformed_missing_required_fields(client):
    """Missing mandatory fields (e.g. event_id or source) returns HTTP 422 Unprocessable Entity."""
    # Missing source and room_id
    bad_payload = {
        "event_id": "evt-bad-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resident_id": "user_eleanor_vance"
    }
    resp = client.post("/api/v1/events/ingest", json=bad_payload)
    assert resp.status_code == 422
    errs = resp.json()["detail"]
    fields_missing = [e["loc"][-1] for e in errs]
    assert "room_id" in fields_missing or "source" in fields_missing


def test_malformed_confidence_out_of_bounds(client):
    """Confidence outside [0.0, 1.0] returns HTTP 422."""
    ev = make_valid_event()
    ev["confidence"] = 1.85  # Invalid > 1.0
    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 422

    ev["confidence"] = -0.5  # Invalid < 0.0
    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 422


def test_malformed_invalid_timestamp_format(client):
    """Non-ISO 8601 timestamp string returns HTTP 422."""
    ev = make_valid_event()
    ev["timestamp"] = "yesterday at 4pm"
    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 422


# ===========================================================================
# 6. Missing Telemetry & Partial Payload Resilience
# ===========================================================================

def test_missing_telemetry_partial_payload(client):
    """
    Events with empty payload dict, missing biometric keys, or unusual data types
    ingest without crashing the server or throwing unhandled 500 exceptions.
    """
    # Empty payload
    ev_empty = make_valid_event(payload={})
    r1 = client.post("/api/v1/events/ingest", json=ev_empty)
    assert r1.status_code == 200
    assert r1.json()["status"] == "ACCEPTED"

    # None values in payload
    ev_nulls = make_valid_event(payload={"heart_rate_bpm": None, "random_key": "unusual_string"})
    r2 = client.post("/api/v1/events/ingest", json=ev_nulls)
    assert r2.status_code == 200
    assert r2.json()["status"] == "ACCEPTED"


# ===========================================================================
# 7. Sensor Disconnect & Redundant Sensor Coverage
# ===========================================================================

def test_sensor_disconnect_with_redundant_radar_fusion(client):
    """
    When wearable is disconnected (0 bpm), radar verifies active walking in the room.
    The system gracefully flags ANOMALY/NORMAL without raising a false CRITICAL fall alarm.
    """
    corr = f"corr-disc-{uuid.uuid4().hex[:6]}"
    wear = WearableSimulator()
    rad = RadarSimulator()

    # 1. Disconnect event
    wear.disconnect()
    ev_disc = wear.generate_unified_event(preset="disconnected", room_id="living_room", correlation_id=corr)
    r1 = client.post("/api/v1/events/ingest", json=ev_disc)
    assert r1.status_code == 200

    # 2. Radar verifies upright motion
    ev_rad = rad.generate_unified_event(preset="upright_walking", room_id="living_room", correlation_id=corr)
    r2 = client.post("/api/v1/events/ingest", json=ev_rad)
    assert r2.status_code == 200
    # Must NOT panic into CRITICAL emergency
    assert r2.json()["safety_state"] != "CRITICAL"


# ===========================================================================
# 8. Emergency Escalation Workflow (Multi-Stage Lifecycle)
# ===========================================================================

def test_emergency_workflow_full_escalation(db):
    """
    Validates complete stateful progression:
      DETECTED -> VERIFYING -> WELLNESS_CHECK -> WAITING_FOR_RESPONSE ->
      CAREGIVER_ESCALATION -> EMERGENCY_ESCALATION -> DISPATCH_READY
    """
    corr_id = f"corr-esc-{uuid.uuid4().hex[:6]}"
    incident, _ = EmergencyWorkflowEngine.get_or_create_incident(
        db=db,
        resident_id="user_eleanor_vance",
        location=f"bathroom_{uuid.uuid4().hex[:4]}",
        event_type="possible_fall",
        confidence=0.95,
        initial_risk_level="HIGH",
        risk_confidence=0.95,
        risk_reasons=["Fall detected"],
        correlation_id=corr_id,
        idempotency_key=f"IDEM-{corr_id}"
    )
    inc_id = incident.id
    assert incident.workflow_state == EmergencyWorkflowState.DETECTED.value

    # DETECTED -> VERIFYING
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.VERIFYING,
        reason="Corroborating sensors", evidence={"radar_conf": 0.92}, actor="SYSTEM", correlation_id=corr_id
    )
    # VERIFYING -> WELLNESS_CHECK
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.WELLNESS_CHECK,
        reason="Sensors confirmed fall", evidence={"fall_confirmed": True}, actor="ALEXA", correlation_id=corr_id
    )
    # WELLNESS_CHECK -> WAITING_FOR_RESPONSE
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.WAITING_FOR_RESPONSE,
        reason="Waiting for answer", evidence={"prompt_sent": True}, actor="ALEXA", correlation_id=corr_id
    )
    # WAITING_FOR_RESPONSE -> CAREGIVER_ESCALATION
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.CAREGIVER_ESCALATION,
        reason="Unresponsive", evidence={"timeout": True}, actor="ORCHESTRATOR", correlation_id=corr_id
    )
    # CAREGIVER_ESCALATION -> EMERGENCY_ESCALATION
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.EMERGENCY_ESCALATION,
        reason="Escalating to 911", evidence={"caregiver_unreachable": True}, actor="ORCHESTRATOR", correlation_id=corr_id
    )
    # EMERGENCY_ESCALATION -> DISPATCH_READY
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.DISPATCH_READY,
        reason="CAD packet ready", evidence={"cad_packet_ready": True}, actor="CAD_ADAPTER", correlation_id=corr_id
    )
    inc = db.query(IncidentModel).filter(IncidentModel.id == inc_id).first()
    assert inc.workflow_state == EmergencyWorkflowState.DISPATCH_READY.value


# ===========================================================================
# 9. Emergency Cancellation / False Alarm Resolution
# ===========================================================================

def test_emergency_cancellation_by_resident_safe_confirmation(client, db):
    """Senior verbally confirming safety transitions active incident to RESOLVED."""
    corr_id = f"corr-cancel-{uuid.uuid4().hex[:6]}"
    incident, _ = EmergencyWorkflowEngine.get_or_create_incident(
        db=db, resident_id="user_eleanor_vance",
        location=f"living_{uuid.uuid4().hex[:4]}", event_type="stumble",
        confidence=0.70, initial_risk_level="MODERATE",
        risk_confidence=0.70, risk_reasons=["Deceleration"],
        correlation_id=corr_id, idempotency_key=f"IDEM-{corr_id}"
    )
    inc_id = incident.id
    resp = client.post(f"/api/v1/incidents/{inc_id}/respond-voice", json={
        "transcript": "I'm okay, false alarm, just dropped a book.",
        "is_timeout": False
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVED"
    assert resp.json()["workflow_state"] == "RESOLVED"


# ===========================================================================
# 10. Wellness Timeout Leading to Silent Emergency
# ===========================================================================

def test_wellness_timeout_triggers_escalation(client, db):
    """Complete silence during wellness check window escalates to CAD / EMERGENCY_ESCALATION."""
    corr_id = f"corr-to-{uuid.uuid4().hex[:6]}"
    incident, _ = EmergencyWorkflowEngine.get_or_create_incident(
        db=db, resident_id="user_eleanor_vance",
        location=f"bath_{uuid.uuid4().hex[:4]}", event_type="fall_detected",
        confidence=0.95, initial_risk_level="CRITICAL",
        risk_confidence=0.95, risk_reasons=["High impact"],
        correlation_id=corr_id, idempotency_key=f"IDEM-{corr_id}"
    )
    inc_id = incident.id
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.VERIFYING,
        reason="Verifying", evidence={"sensor": "ok"}, actor="SYSTEM", correlation_id=corr_id
    )
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.WELLNESS_CHECK,
        reason="Prompting", evidence={"alexa_prompt": True}, actor="ALEXA", correlation_id=corr_id
    )
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.WAITING_FOR_RESPONSE,
        reason="Awaiting reply", evidence={"awaiting_voice": True}, actor="ALEXA", correlation_id=corr_id
    )
    resp = client.post(f"/api/v1/incidents/{inc_id}/respond-voice", json={
        "transcript": None,
        "is_timeout": True
    })
    assert resp.status_code == 200
    assert resp.json()["workflow_state"] in ("EMERGENCY_ESCALATION", "DISPATCH_READY")


# ===========================================================================
# 11. Caregiver Acknowledgement Halts Escalation
# ===========================================================================

def test_caregiver_acknowledgement_halts_escalation(client, db):
    """Caregiver acknowledging the alert via REST API updates state and halts automated escalation."""
    corr_id = f"corr-cg-{uuid.uuid4().hex[:6]}"
    incident, _ = EmergencyWorkflowEngine.get_or_create_incident(
        db=db, resident_id="user_eleanor_vance",
        location=f"bed_{uuid.uuid4().hex[:4]}", event_type="fall_detected",
        confidence=0.90, initial_risk_level="HIGH",
        risk_confidence=0.90, risk_reasons=["Immobility"],
        correlation_id=corr_id, idempotency_key=f"IDEM-{corr_id}"
    )
    inc_id = incident.id
    EmergencyWorkflowEngine.transition(
        db=db, incident_id=inc_id, target_state=EmergencyWorkflowState.CAREGIVER_ESCALATION,
        reason="Alerting caregiver", evidence={"alert_sent": True}, actor="SYSTEM", correlation_id=corr_id
    )

    resp = client.post(f"/api/v1/incidents/{inc_id}/acknowledge", json={"caregiver_actor": "Sarah Vance (Caregiver)"})
    assert resp.status_code == 200
    assert resp.json()["scenario"] == "G_CAREGIVER_ACKNOWLEDGED"
    assert resp.json()["workflow_state"] == "RESOLVED"


# ===========================================================================
# 12. Database Persistence & Transaction Rollback
# ===========================================================================

def test_database_persistence_of_telemetry_and_timelines(client, db):
    """Every ingested event and state transition persists traceable records to SQLite tables."""
    test_event_id = f"evt-persist-{uuid.uuid4().hex[:8]}"
    ev = make_valid_event(event_id=test_event_id, event_type="wearable_telemetry", room_id="kitchen")

    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200

    # Query DB directly to verify persistence
    rec = db.query(TelemetryEventModel).filter(TelemetryEventModel.id == test_event_id).first()
    assert rec is not None
    assert rec.room_id == "kitchen"
    assert rec.source == "wearable"


def test_database_rollback_on_commit_error(client):
    """A simulated database failure triggers rollback and is safely handled without 500 crash."""
    ev = make_valid_event()
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Simulated SQLite Disk Error")):
        # Ingestion should catch exception, rollback, and still return result
        resp = client.post("/api/v1/events/ingest", json=ev)
        assert resp.status_code == 200


# ===========================================================================
# 13. Restart Recovery (Re-hydrating State from DB)
# ===========================================================================

def test_restart_recovery_from_database(db):
    """
    Simulates application restart while an incident was ACTIVE in the database.
    Verifies that recover_state_from_database reloads the active incident and safety state.
    """
    now = datetime.now(timezone.utc)
    inc_id = f"INC-REC-{uuid.uuid4().hex[:6].upper()}"

    # 1. Seed an active incident in DB
    seeded_inc = IncidentModel(
        id=inc_id,
        user_id="user_eleanor_vance",
        event_type="fall_detected",
        confidence=0.96,
        location="bathroom",
        movement_after_event="none",
        initial_risk_level="CRITICAL",
        current_risk_level="CRITICAL",
        risk_confidence=0.96,
        risk_reasons=["High-velocity fall impact", "Zero movement"],
        status="ACTIVE",
        recommended_action="STATE_CRITICAL",
        created_at=now,
        updated_at=now
    )
    db.add(seeded_inc)
    db.commit()

    # 2. Reset pipeline to clear in-memory state
    global_pipeline.reset_to_normal()
    assert global_pipeline.current_state.active_incident_id is None
    assert global_pipeline.current_state.safety_state == "NORMAL"

    # 3. Perform restart recovery
    rec_info = global_pipeline.recover_state_from_database(db)
    assert rec_info["recovered"] is True
    assert rec_info["active_incident"] == inc_id

    # 4. Verify authoritative in-memory state matches recovered DB record
    assert global_pipeline.current_state.active_incident_id == inc_id
    assert global_pipeline.current_state.safety_state == "CRITICAL"
    assert global_pipeline.current_state.smart_home["smart_lock_unlocked"] is True


def test_restart_recovery_endpoint(client, db):
    """POST /api/v1/events/recover triggers recovery and returns status."""
    resp = client.post("/api/v1/events/recover")
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"


# ===========================================================================
# 14. SSE / WebSocket Streaming & Slow Consumer Protection
# ===========================================================================

def test_sse_subscriber_queue_lifecycle():
    """Subscribing and unsubscribing queues cleans up cleanly without resource leaks."""
    initial_subscribers = len(global_pipeline._subscribers)
    q = global_pipeline.subscribe()
    assert len(global_pipeline._subscribers) == initial_subscribers + 1

    # Unsubscribe
    global_pipeline.unsubscribe(q)
    assert len(global_pipeline._subscribers) == initial_subscribers


@pytest.mark.asyncio
async def test_slow_consumer_queue_overflow_drop_oldest():
    """
    If a slow consumer queue fills past capacity (50 items),
    the oldest messages are dropped to prevent memory exhaustion and unblock other clients.
    """
    q = global_pipeline.subscribe()
    try:
        # Broadcast 55 items
        for i in range(55):
            await global_pipeline.broadcast({"index": i, "data": "telemetry"})
        
        # Queue should be bounded to at most 50 items
        assert q.qsize() <= 50
    finally:
        global_pipeline.unsubscribe(q)


# ===========================================================================
# 15. Deterministic Risk Calculations (Exact Bounds & Multi-Factor Weights)
# ===========================================================================

def test_deterministic_risk_calculation_baseline_normal():
    """Normal resting vitals and environmental reading evaluate strictly to LOW risk (score = 5.0)."""
    ev = make_valid_event(
        event_type="wearable_telemetry",
        payload={"heart_rate_bpm": 72, "movement_index": 0.8, "arrhythmia_detected": False}
    )
    state, risk, score = global_pipeline._evaluate_multimodal_state(
        UnifiedEvent(**ev),
        global_pipeline._evidence_history[0] if global_pipeline._evidence_history else None
    )
    assert state == "NORMAL"
    assert risk == "LOW"
    assert score == 5.0


def test_deterministic_risk_calculation_fall_with_immobility():
    """A fall corroborated with immobility evaluates strictly to HIGH risk (score = 78.0)."""
    from app.models.event_contracts import EvidenceItem
    ev = make_valid_event(
        event_type="possible_fall",
        payload={"movement_after_event": "none"}
    )
    evi = EvidenceItem(
        evidence_id="evi-test-fall",
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="camera_pose",
        event_type="possible_fall",
        room_id="living_room",
        confidence=0.95,
        description="Fall detected",
        weight=1.5
    )
    state, risk, score = global_pipeline._evaluate_multimodal_state(UnifiedEvent(**ev), evi)
    assert state == "HIGH"
    assert risk == "HIGH"
    assert score == 78.0


def test_deterministic_risk_calculation_critical_silent_emergency():
    """Voice timeout during wellness check deterministically evaluates to CRITICAL (score = 98.0)."""
    from app.models.event_contracts import EvidenceItem
    ev = make_valid_event(event_type="voice_timeout", source="audio_voice")
    evi = EvidenceItem(
        evidence_id="evi-test-timeout",
        timestamp=datetime.now(timezone.utc).isoformat(),
        source="audio_voice",
        event_type="voice_timeout",
        room_id="bathroom",
        confidence=1.0,
        description="Prompt timeout",
        weight=2.0
    )
    state, risk, score = global_pipeline._evaluate_multimodal_state(UnifiedEvent(**ev), evi)
    assert state == "CRITICAL"
    assert risk == "CRITICAL"
    assert score == 98.0


# ===========================================================================
# 16. MCP Tools Integration Tests
# ===========================================================================

def test_mcp_tools_protocol_endpoints(client):
    """MCP HTTP tools return valid structured responses."""
    # Assess risk tool
    req = {
        "event": {
            "event_type": "camera_activity",
            "confidence": 0.95,
            "location": "living_room",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "movement_after_event": "normal"
        },
        "context": {
            "activity": "walking",
            "time_context": "afternoon",
            "baseline_deviation": 0.0,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        }
    }
    r_risk = client.post("/tools/assess_risk", json=req)
    assert r_risk.status_code == 200
    assert "risk" in r_risk.json()
    assert r_risk.json()["risk"]["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")

    # Resident state query
    r_state = client.get("/api/v1/resident/state")
    assert r_state.status_code == 200
    assert r_state.json()["resident_id"] == "user_eleanor_vance"


# ===========================================================================
# 17. Simulator Integration Verification
# ===========================================================================

def test_simulator_integration_telemetry_flow(client):
    """All external simulators (Wearable, Radar, Environment, Voice) integrate seamlessly via HTTP."""
    wear = WearableSimulator()
    rad = RadarSimulator()
    env = EnvironmentSimulator()
    vox = VoiceSimulator()
    corr = f"corr-sim-{uuid.uuid4().hex[:6]}"

    # Ingest from each simulator
    r_w = client.post("/api/v1/events/ingest", json=wear.generate_unified_event(correlation_id=corr))
    r_r = client.post("/api/v1/events/ingest", json=rad.generate_unified_event(correlation_id=corr))
    r_e = client.post("/api/v1/events/ingest", json=env.generate_unified_event(correlation_id=corr))
    r_v = client.post("/api/v1/events/ingest", json=vox.generate_unified_event(correlation_id=corr))

    assert r_w.status_code == 200 and r_w.json()["status"] == "ACCEPTED"
    assert r_r.status_code == 200 and r_r.json()["status"] == "ACCEPTED"
    assert r_e.status_code == 200 and r_e.json()["status"] == "ACCEPTED"
    assert r_v.status_code == 200 and r_v.json()["status"] == "ACCEPTED"
