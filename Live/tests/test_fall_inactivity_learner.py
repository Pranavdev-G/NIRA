"""
Comprehensive Test Suite for NIRA Refined Fall Detector,
Prolonged Inactivity (3-5 mins), Alarm Inquiry, and Self-Learning Daily Activity Routine.
Amazon Developer Hackathon 2026.
"""

import time
import pytest
import numpy as np
from pathlib import Path

from Live.activity_routine_learner import DailyActivityRoutineLearner, ZONE_RISK_PROFILES
from Live.live_vision_tracker import (
    LiveVisionTracker,
    STATE_NORMAL,
    STATE_FALL,
    STATE_PROLONGED_INACTIVITY,
    STATE_UNRESPONSIVE
)


@pytest.fixture
def temp_learner(tmp_path):
    json_path = tmp_path / "test_baseline.json"
    learner = DailyActivityRoutineLearner(data_path=str(json_path))
    return learner


@pytest.fixture
def mock_tracker(tmp_path):
    json_path = tmp_path / "test_baseline_tracker.json"
    tracker = LiveVisionTracker(
        unresponsive_threshold_sec=180.0,
        simulation_speedup_factor=1.0,
        zone="living_room"
    )
    # Point learner to isolated temp path
    tracker.activity_learner = DailyActivityRoutineLearner(data_path=str(json_path))
    return tracker


# ============================================================================
# 1. Activity Routine Learner Tests
# ============================================================================

def test_learner_default_circadian_priors(temp_learner):
    """Verifies that daytime vs nighttime thresholds are initialized safely."""
    # Nighttime (e.g. 23:00) in bedroom allows extended sleep
    night_thresh = temp_learner.get_tolerated_inactivity_threshold("bedroom", hour=23)
    assert night_thresh >= 1800.0, "Night bedroom threshold should be at least 30 mins"

    # Bathroom must always have strict threshold (180s - 300s) even at night
    bath_thresh = temp_learner.get_tolerated_inactivity_threshold("bathroom", hour=23)
    assert 180.0 <= bath_thresh <= 300.0, "Bathroom threshold must remain strict"


def test_learner_anomaly_detection_under_and_over_threshold(temp_learner):
    """Verifies that inactivity below threshold is safe, and above is anomaly."""
    # Daytime living room (14:00) with 60s stillness -> Normal
    diag_safe = temp_learner.evaluate_inactivity_anomaly("living_room", motionless_seconds=60.0, hour=14)
    assert diag_safe["is_anomaly"] is False

    # Bathroom with 200s stillness -> Anomaly!
    diag_risk = temp_learner.evaluate_inactivity_anomaly("bathroom", motionless_seconds=200.0, hour=14)
    assert diag_risk["is_anomaly"] is True
    assert "Are you okay" in diag_risk["suggested_question"]


def test_learner_self_training_on_safe_feedback(temp_learner):
    """
    CRITICAL TEST: Verifies that when resident responds 'I am okay' to an alarm,
    the model trains itself to expand tolerance for that zone/hour,
    preventing future false alarms for that user activity!
    """
    hour = 16
    initial_thresh = temp_learner.get_tolerated_inactivity_threshold("living_room", hour=hour)
    assert initial_thresh in [180.0, 300.0]  # 3-5 mins base

    # Resident was motionless for 360s (6 mins), alarm fired, resident says "I'm okay, just watching TV"
    update = temp_learner.reinforce_dismissed_alarm(
        zone="living_room",
        inactivity_duration_sec=360.0,
        hour=hour,
        feedback="User confirmed safe watching TV"
    )

    new_thresh = update["new_threshold_sec"]
    assert new_thresh > initial_thresh, "Tolerated threshold must adapt upward"
    assert new_thresh >= 360.0 * 1.15, "New threshold should include 15% safety buffer"
    assert temp_learner.profile["suppressed_false_alarms"] == 1

    # Now re-evaluating 360s stillness in the living room at 16:00 MUST BE NORMAL (not an anomaly)!
    diag_recheck = temp_learner.evaluate_inactivity_anomaly("living_room", motionless_seconds=360.0, hour=hour)
    assert diag_recheck["is_anomaly"] is False, "Learned daily routine must eliminate the false alarm!"


def test_learner_strict_floor_posture_protection(temp_learner):
    """
    Verifies that if the resident is horizontal on the FLOOR (not bed),
    extended sleep/rest tolerances are bypassed to protect from long lies!
    """
    hour = 14
    # On sofa/bed: 400s might be normal
    # On floor: MUST trigger anomaly
    diag_floor = temp_learner.evaluate_inactivity_anomaly(
        zone="living_room",
        motionless_seconds=190.0,
        posture="floor_collapse",
        hour=hour
    )
    assert diag_floor["is_anomaly"] is True
    assert "floor" in diag_floor["reason"].lower()


# ============================================================================
# 2. Refined LiveVisionTracker: Inactivity, Alarms & Voice Response Tests
# ============================================================================

def test_tracker_prolonged_inactivity_triggers_alarm(mock_tracker):
    """
    Verifies that motionless resident exceeding threshold triggers
    PROLONGED_INACTIVITY state and activates the spoken alarm prompt.
    """
    mock_tracker.zone = "bathroom"
    # Bathroom has 180s threshold
    mock_tracker.simulate_inactivity(185.0)

    frame = np.zeros((416, 416, 3), dtype=np.uint8)
    res = mock_tracker.evaluate_frame(frame, location="bathroom")

    assert res["state"] == STATE_PROLONGED_INACTIVITY
    assert res["alarm_active"] is True
    assert "Are you okay" in res["alarm_prompt"]
    assert res["unresponsive_seconds"] >= 185.0


def test_tracker_voice_response_safe_clears_alarm_and_trains(mock_tracker):
    """
    Verifies full closed-loop:
      1. Alarm triggered by inactivity.
      2. User responds verbally: 'I am okay, no problem.'
      3. System dismisses alarm, transitions to NORMAL, and trains daily routine!
    """
    mock_tracker.zone = "kitchen"
    mock_tracker.simulate_inactivity(260.0)

    # Frame triggers alarm
    frame = np.zeros((416, 416, 3), dtype=np.uint8)
    eval_res = mock_tracker.evaluate_frame(frame, location="kitchen")
    assert eval_res["alarm_active"] is True

    # User speaks "I am okay."
    voice_res = mock_tracker.handle_voice_response("Yes, I am okay, just cooking.", location="kitchen")

    assert voice_res["status"] == "SAFE"
    assert voice_res["action"] == "ALARM_DISMISSED"
    assert mock_tracker.current_state == STATE_NORMAL
    assert mock_tracker.alarm_active is False
    assert mock_tracker.accumulated_motionless_sec == 0.0
    assert voice_res["learned_update"]["suppressed_false_alarms_total"] >= 1


def test_tracker_voice_response_emergency_escalates(mock_tracker):
    """
    Verifies that when resident responds with distress ('Help me, I fell down'),
    the system transitions to UNRESPONSIVENESS / EMERGENCY and alerts CAD/caregivers.
    """
    mock_tracker.zone = "hallway"
    mock_tracker.simulate_inactivity(190.0)

    # Frame triggers alarm
    frame = np.zeros((416, 416, 3), dtype=np.uint8)
    mock_tracker.evaluate_frame(frame, location="hallway")

    # User cries for help
    voice_res = mock_tracker.handle_voice_response("Help me, I fell down and cannot get up!", location="hallway")

    assert voice_res["status"] == "EMERGENCY"
    assert voice_res["action"] == "ESCALATE_EMERGENCY_CAD"
    assert mock_tracker.current_state == STATE_UNRESPONSIVE
    assert mock_tracker.alarm_active is True


def test_tracker_negated_positives_never_become_safe(mock_tracker):
    """
    Verifies clinical safety guarantee: 'I am NOT okay' or 'I am not fine'
    MUST NEVER be classified as SAFE.
    """
    mock_tracker.simulate_inactivity(200.0)
    voice_res = mock_tracker.handle_voice_response("No, I am not okay, I feel terrible.")

    assert voice_res["status"] != "SAFE"
    assert voice_res["status"] in ["RISK", "EMERGENCY"]
    assert mock_tracker.current_state != STATE_NORMAL


def test_tracker_motion_resumption_clears_benign_stillness(mock_tracker):
    """
    Verifies that when normal movement resumes (e.g. resident shifts or walks),
    the stillness accumulator resets.
    """
    mock_tracker.accumulated_motionless_sec = 45.0

    # Simulate moving frames (nonzero difference)
    f1 = np.zeros((416, 416, 3), dtype=np.uint8)
    f2 = np.ones((416, 416, 3), dtype=np.uint8) * 180

    mock_tracker.evaluate_frame(f1)
    res = mock_tracker.evaluate_frame(f2)

    assert res["motion_displacement"] >= 14.0
    assert mock_tracker.accumulated_motionless_sec == 0.0
    assert mock_tracker.current_state == STATE_NORMAL
