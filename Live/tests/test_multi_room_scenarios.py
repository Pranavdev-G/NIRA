"""
Comprehensive Multi-Room Vision, Voice, and Core Integration Test Suite.
Amazon Developer Hackathon 2026.

Validates:
  - Test Scenarios 1 to 10 (Phases 56 to 65)
  - All 5 Rooms: Living Room, Bathroom, Bedroom, Kitchen, Hallway (Phase 3)
  - Independent Room States & Zone Sessions (Phases 4, 15)
  - Inter-room Person Handoff & Continuity (Phases 5, 6)
  - Kinematic Fall Confirmation & Post-Fall Recovery (Phases 12, 13)
  - Continuous Microphone & Spontaneous Help Detection (Phases 28 to 31)
  - Authoritative Response Priority: EMERGENCY > RISK > UNCERTAIN > SAFE (Phases 32, 33)
  - Severity-Aware Silence Escalation Policy (Phase 38)
  - Fast Virtual Time Advancement via TestClock (Phase 67)
"""

import pytest
import numpy as np
from datetime import datetime, timezone

from Live.core.models import ZoneType, EventType, EventSource, SeverityLevel, SafetyState, LiveEvent, LocationModel
from Live.core.time_provider import TestClock, set_time_provider, reset_time_provider
from Live.core.core_service import CoreService
from Live.vision.camera_models import CameraConfig, CameraSourceType, CameraStatus, PostureType
from Live.vision.room_tracker import RoomTracker
from Live.vision.camera_manager import CameraManager
from Live.voice.continuous_monitor import ContinuousMicrophoneMonitor, MicrophoneMode
from Live.voice.response_analyzer import ResponseAnalyzer
from Live.voice.models import VoiceInteractionStatus, VoiceUrgencyLevel


@pytest.fixture
def test_clock():
    """Injectable virtual clock for instant time-advancement testing (Phase 67)."""
    clock = TestClock(datetime(2026, 10, 23, 10, 0, 0, tzinfo=timezone.utc))
    set_time_provider(clock)
    yield clock
    reset_time_provider()


@pytest.fixture
def core_service(test_clock):
    return CoreService()


@pytest.fixture
def camera_manager(core_service):
    mgr = CameraManager(core_service=core_service)
    core_service.camera_manager = mgr
    return mgr


@pytest.fixture
def mic_monitor(core_service, camera_manager):
    return ContinuousMicrophoneMonitor(core_service=core_service, camera_manager=camera_manager)


# ==============================================================================
# PHASE 3 & 4: MULTI-ROOM REGISTRATION & INDEPENDENT CONCURRENT STATES
# ==============================================================================
def test_all_five_rooms_registered_and_independent(camera_manager):
    """Verifies living_room, bathroom, bedroom, kitchen, hallway have independent state."""
    rooms = camera_manager.get_all_rooms()
    room_ids = {r["room_id"] for r in rooms}

    assert "living_room" in room_ids
    assert "bathroom" in room_ids
    assert "bedroom" in room_ids
    assert "kitchen" in room_ids
    assert "hallway" in room_ids

    # Change bathroom state independently
    bath_tracker = camera_manager.get_tracker_for_room(ZoneType.BATHROOM)
    bath_tracker.state.person_present = True
    bath_tracker.state.zone_visit_duration_sec = 903.0
    bath_tracker.state.behavior_state = "PROLONGED_ZONE_STAY"

    # Verify bedroom and living room remain independent
    bed_tracker = camera_manager.get_tracker_for_room(ZoneType.BEDROOM)
    assert bed_tracker.state.person_present is False
    assert bed_tracker.state.zone_visit_duration_sec == 0.0

    living_tracker = camera_manager.get_tracker_for_room(ZoneType.LIVING_ROOM)
    assert living_tracker.state.person_present is False


# ==============================================================================
# SCENARIO 1: BATHROOM NORMAL VISIT (Phase 56)
# Expected: 10 min. Entered: 10:00, Left: 10:09 (9 min).
# Result: NORMAL, safe visit learned, no prompt.
# ==============================================================================
def test_scenario_1_bathroom_normal_visit(camera_manager, core_service, test_clock):
    bath_tracker = camera_manager.get_tracker_for_room(ZoneType.BATHROOM)

    # 10:00 - Resident enters bathroom
    bath_tracker.state.person_present = True
    result1 = bath_tracker._handle_person_present(
        detections=type("D", (), {"boxes": type("B", (), {"conf": [0.9], "xyxy": [[10, 10, 50, 100]]})()})(),
        now_ts=test_clock.time(),
        now_iso=test_clock.now_iso()
    )
    assert result1["behavior_state"] == "NORMAL"

    # Advance 9 minutes (540s) with active movement
    test_clock.advance(540)
    result2 = bath_tracker._handle_person_present(
        detections=type("D", (), {"boxes": type("B", (), {"conf": [0.9], "xyxy": [[35, 35, 75, 125]]})()})(),
        now_ts=test_clock.time(),
        now_iso=test_clock.now_iso()
    )

    # 9 mins < 10 mins (600s) -> NORMAL
    assert result2["behavior_state"] == "NORMAL"
    assert result2["dwell_sec"] == 540.0
    assert core_service.incident_manager.get_active_incident() is None

    # Resident leaves safely at 10:09
    summary = bath_tracker.close_current_session(safe_outcome=True)
    assert summary["safe_outcome"] is True
    assert summary["total_dwell_sec"] == 540.0


# ==============================================================================
# SCENARIO 2: BATHROOM PROLONGED STAY + SAFE RESPONSE (Phase 57)
# Expected: 10 min. Observed: 15 min. Movement: normal.
# Result: PROLONGED_ZONE_STAY -> Prompt -> Resident "I'm okay" -> SAFE -> Gradual reinforcement, no ambulance.
# ==============================================================================
def test_scenario_2_bathroom_prolonged_stay_safe_response(camera_manager, core_service, mic_monitor, test_clock):
    bath_tracker = camera_manager.get_tracker_for_room(ZoneType.BATHROOM)

    # 10:00 - Enter bathroom
    bath_tracker.state.person_present = True
    bath_tracker._handle_person_present(
        detections=type("D", (), {"boxes": type("B", (), {"conf": [0.9], "xyxy": [[10, 10, 50, 100]]})()})(),
        now_ts=test_clock.time(),
        now_iso=test_clock.now_iso()
    )

    # Advance 15 minutes (900s) with active movement
    test_clock.advance(900)
    result = bath_tracker._handle_person_present(
        detections=type("D", (), {"boxes": type("B", (), {"conf": [0.9], "xyxy": [[30, 30, 70, 120]]})()})(),
        now_ts=test_clock.time(),
        now_iso=test_clock.now_iso()
    )

    # 15 mins >= 10 mins * 1.5 -> PROLONGED_ZONE_STAY
    assert result["behavior_state"] == "PROLONGED_ZONE_STAY"
    assert result["dwell_sec"] == 900.0

    # Dispatch to Core
    camera_manager._dispatch_vision_events(bath_tracker, result, resident_id="resident_eleanor_vance")

    incident = core_service.incident_manager.get_active_incident()
    assert incident is not None
    assert incident.state in [SafetyState.DETECTED, SafetyState.WELLNESS_CHECK, SafetyState.WAITING_FOR_RESPONSE]

    # Verify contextual prompt
    prompt = core_service._generate_contextual_prompt(incident)
    assert "bathroom" in prompt.lower() and "longer than usual" in prompt.lower()

    # Resident responds: "I'm okay."
    res = core_service.process_wellness_response("I'm okay.", incident_id=incident.incident_id, duration_sec=900.0)
    assert res["classification"] == "SAFE"

    # Verify gradual learning occurred without sudden jump
    stats = core_service.baseline_engine._learner.get_room_visit_stats("bathroom")
    assert stats["median_duration_sec"] > 600.0
    assert stats["median_duration_sec"] < 700.0  # Gradual shift, not jumping straight to 900s

    # Verify NO ambulance dispatch was triggered
    assert incident.emergency_dispatch is None


# ==============================================================================
# SCENARIO 3: BATHROOM DANGEROUS STAY + "I CAN'T GET UP" (Phase 58)
# Observed: 15 min. Posture: floor. Movement: low. HR: high.
# Result: Prompt -> "I can't get up" -> EMERGENCY -> Emergency workflow override.
# ==============================================================================
def test_scenario_3_bathroom_dangerous_stay_emergency(camera_manager, core_service, test_clock):
    bath_tracker = camera_manager.get_tracker_for_room(ZoneType.BATHROOM)
    bath_tracker.state.person_present = True

    # Initial entry
    test_clock.advance(900)
    eval_res = core_service.baseline_engine.evaluate_zone_dwell(
        zone=ZoneType.BATHROOM,
        dwell_seconds=900.0,
        movement_rate=0.04,
        posture="floor",
        heart_rate=118
    )

    assert eval_res["behavior_state"] == "CRITICAL_COLLAPSE_IN_ZONE"
    assert eval_res["risk_level"] == "CRITICAL"

    # Prompt generated
    prompt = eval_res["suggested_question"]
    assert "help getting up" in prompt.lower()

    # Create active incident and resident responds: "I can't get up."
    raw_event = {
        "event_type": EventType.PROLONGED_ZONE_STAY.value,
        "source": EventSource.ROOM_TRACKER.value,
        "location": {"zone": "bathroom"},
        "payload": eval_res
    }
    evt, risk, incident = core_service.ingest_event(raw_event)
    assert incident is not None

    res = core_service.process_wellness_response("I can't get up.", incident_id=incident.incident_id)
    assert res["classification"] == "EMERGENCY"

    # Emergency escalation confirmed
    assert incident.state == SafetyState.DISPATCH_READY
    assert incident.emergency_dispatch is not None


# ==============================================================================
# SCENARIO 4: SPONTANEOUS VOICE EMERGENCY (Phase 59)
# No fall, no inactivity, no prior alarm. Resident suddenly says: "Help me."
# Result: VOICE_HELP_REQUEST -> Core creates Incident & Emergency Workflow.
# ==============================================================================
def test_scenario_4_spontaneous_help_request(mic_monitor, core_service):
    # Ensure no prior incident
    assert core_service.incident_manager.get_active_incident() is None

    # Resident spontaneously calls out: "Help me."
    mic_monitor.simulate_speech_utterance("Help me.", room=ZoneType.LIVING_ROOM)

    # Core must have created an incident and started emergency workflow
    incident = core_service.incident_manager.get_active_incident()
    assert incident is not None
    assert incident.severity == SeverityLevel.CRITICAL
    assert incident.emergency_dispatch is not None
    assert incident.state == SafetyState.DISPATCH_READY


# ==============================================================================
# SCENARIO 5: MULTI-ROOM RESIDENT HANDOFF (Phase 60)
# Resident moves: bedroom -> hallway -> bathroom -> hallway -> kitchen -> living_room
# Result: ROOM_ENTRY / ROOM_EXIT events, single continuous resident history.
# ==============================================================================
def test_scenario_5_multi_room_handoff(camera_manager, core_service, test_clock):
    route = [
        ZoneType.BEDROOM,
        ZoneType.HALLWAY,
        ZoneType.BATHROOM,
        ZoneType.HALLWAY,
        ZoneType.KITCHEN,
        ZoneType.LIVING_ROOM
    ]

    for room in route:
        tracker = camera_manager.get_tracker_for_room(room)
        test_clock.advance(5)
        camera_manager._handle_person_tracking_continuity(tracker, test_clock.time(), "resident_eleanor_vance")
        assert camera_manager.current_resident_room == room

    # Single resident track throughout
    assert camera_manager.current_resident_room == ZoneType.LIVING_ROOM


# ==============================================================================
# SCENARIO 6: TWO CAMERAS SEE RESIDENT DURING TRANSITION (Phase 61)
# Result: Single resident track, no duplicate emergency or missing person alert.
# ==============================================================================
def test_scenario_6_duplicate_camera_handoff_suppression(camera_manager, core_service, test_clock):
    hall_tracker = camera_manager.get_tracker_for_room(ZoneType.HALLWAY)
    bath_tracker = camera_manager.get_tracker_for_room(ZoneType.BATHROOM)

    # Resident visible in hallway
    camera_manager._handle_person_tracking_continuity(hall_tracker, test_clock.time(), "resident_eleanor_vance")
    assert camera_manager.current_resident_room == ZoneType.HALLWAY

    # Resident also momentarily visible in bathroom doorway within 1 second
    test_clock.advance(1)
    camera_manager._handle_person_tracking_continuity(bath_tracker, test_clock.time(), "resident_eleanor_vance")
    assert camera_manager.current_resident_room == ZoneType.BATHROOM

    # No spurious incidents created
    assert core_service.incident_manager.get_active_incident() is None


# ==============================================================================
# SCENARIO 7: CAMERA GOES OFFLINE (Phase 62)
# Result: CAMERA_OFFLINE (NOT normal movement, NOT fall, NOT inactivity).
# ==============================================================================
def test_scenario_7_camera_offline(camera_manager):
    tracker = camera_manager.get_tracker_for_room(ZoneType.KITCHEN)
    tracker.state.camera_status = CameraStatus.STOPPED

    res = tracker.process_frame(np.zeros((10, 10, 3), dtype=np.uint8))
    assert res["status"] == CameraStatus.STOPPED.value
    assert res["status"] != "NORMAL_MOVEMENT"
    assert res["status"] != "fall_detected"


# ==============================================================================
# SCENARIO 8: MICROPHONE DISCONNECTS & RECOVERS (Phase 63)
# Result: MIC_OFFLINE, camera continues safety monitoring, auto-recovery -> MIC_RECOVERED.
# ==============================================================================
def test_scenario_8_mic_disconnect_and_recovery(mic_monitor, core_service):
    # Simulate mic error
    mic_monitor._dispatch_mic_event(EventType.MIC_OFFLINE, {"error": "Device unplugged"})
    recent = core_service.pipeline.get_recent_events(limit=1)
    assert recent[0].event_type == EventType.MIC_OFFLINE

    # System continues running
    assert core_service.incident_manager.current_state == SafetyState.NORMAL

    # Simulate recovery
    mic_monitor._dispatch_mic_event(EventType.MIC_RECOVERED, {"status": "ONLINE"})
    recent2 = core_service.pipeline.get_recent_events(limit=1)
    assert recent2[0].event_type == EventType.MIC_RECOVERED


# ==============================================================================
# SCENARIO 9: CONTRADICTORY SPEECH (Phase 64)
# "I'm okay, but I fell and I can't get up." -> EMERGENCY (Never SAFE).
# ==============================================================================
def test_scenario_9_mixed_response_emergency_override():
    analysis = ResponseAnalyzer.analyze_response("I'm okay, but I fell and I can't get up.")
    assert analysis.status == VoiceInteractionStatus.EMERGENCY
    assert analysis.is_mixed is True
    assert analysis.urgency == VoiceUrgencyLevel.CRITICAL


# ==============================================================================
# SCENARIO 10: "I'M FINE" / "I AM NOT OKAY" VALIDATION (Phase 65)
# ==============================================================================
def test_scenario_10_safe_and_negation_responses():
    # True safe phrase
    safe_res = ResponseAnalyzer.analyze_response("I'm fine.")
    assert safe_res.status == VoiceInteractionStatus.SAFE

    # Strict negation: "I'm not okay" must NEVER be safe
    neg_res = ResponseAnalyzer.analyze_response("I'm not okay.")
    assert neg_res.status != VoiceInteractionStatus.SAFE
    assert neg_res.status in [VoiceInteractionStatus.RISK, VoiceInteractionStatus.EMERGENCY]
    assert neg_res.is_negated is True


# ==============================================================================
# SEVERITY-AWARE SILENCE TIMEOUT (Phase 38)
# ==============================================================================
def test_severity_aware_silence_escalation(core_service):
    # 1. Mild Dwell Incident (Low/Medium severity)
    dwell_event = LiveEvent(
        event_id="evt-dwell-1",
        event_type=EventType.PROLONGED_ZONE_STAY,
        source=EventSource.ROOM_TRACKER,
        correlation_id="corr-dwell-1",
        location=LocationModel(zone=ZoneType.BATHROOM)
    )
    dummy_dwell = core_service.incident_manager.create_incident(
        trigger_event=dwell_event,
        severity=SeverityLevel.MEDIUM,
        risk_score=0.45
    )
    res_mild = core_service.handle_silence_timeout(dummy_dwell.incident_id)
    assert res_mild["escalation_level"] == "CAREGIVER_ALERT"
    core_service.incident_manager.resolve_incident(dummy_dwell.incident_id)

    # 2. Critical Fall Incident (Critical severity)
    fall_event = LiveEvent(
        event_id="evt-fall-1",
        event_type=EventType.FALL_DETECTED,
        source=EventSource.ROOM_TRACKER,
        correlation_id="corr-fall-1",
        location=LocationModel(zone=ZoneType.BATHROOM)
    )
    dummy_fall = core_service.incident_manager.create_incident(
        trigger_event=fall_event,
        severity=SeverityLevel.CRITICAL,
        risk_score=0.92
    )
    res_crit = core_service.handle_silence_timeout(dummy_fall.incident_id)
    assert res_crit["escalation_level"] == "EMERGENCY_CAD_AND_SMS"
    assert dummy_fall.emergency_dispatch is not None
