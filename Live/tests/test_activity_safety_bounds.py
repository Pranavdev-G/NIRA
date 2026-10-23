"""
Unit Tests for Adaptive Activity Routine Learner Safety Bounds & Quality Metrics.
Amazon Developer Hackathon 2026.

Verifies:
  - 24-hour circadian bins and all 6 required zones (bathroom, hallway, kitchen, living_room, bedroom, general)
  - Safety minimum threshold (at least 180s)
  - Strict floor collapse protection (floor falls never learned as normal)
  - Bounded adaptation ceilings
  - Baseline quality and confidence metrics
  - False alarm suppression with safe bounds
"""

import pytest
from Live.activity_routine_learner import (
    DailyActivityRoutineLearner,
    ZONE_RISK_PROFILES
)


@pytest.fixture
def learner(tmp_path):
    p = tmp_path / "test_safety_bounds.json"
    return DailyActivityRoutineLearner(data_path=str(p))


def test_all_six_zones_supported(learner):
    """Ensures all 6 zones specified in requirements are present."""
    expected_zones = ["bathroom", "hallway", "living_room", "bedroom", "kitchen", "general"]
    for z in expected_zones:
        cfg = learner.get_zone_config(z)
        assert cfg is not None
        assert cfg["base_inactivity_sec"] >= 180.0
        assert "risk_tier" in cfg


def test_safety_minimum_threshold_bounds(learner):
    """Tolerated inactivity must NEVER be less than 180 seconds in any zone."""
    for z in ZONE_RISK_PROFILES:
        for hour in range(24):
            thresh = learner.get_tolerated_inactivity_threshold(z, hour=hour)
            assert thresh >= 180.0, f"Threshold below safety minimum (180s) in {z} at {hour}:00: {thresh}"


def test_ceiling_caps_prevent_unbounded_learning(learner):
    """Learning must never exceed the clinical zone cap even after massive inactivity."""
    # Bathroom maximum cap is 300.0s (5 mins)
    bath_cfg = learner.get_zone_config("bathroom")
    max_cap = bath_cfg["max_cap_sec"]

    # Attempt to reinforce with 10,000s of inactivity
    update = learner.reinforce_dismissed_alarm(
        zone="bathroom",
        inactivity_duration_sec=10000.0,
        hour=10,
        feedback="Resident confirmed safe"
    )
    new_thresh = update["new_threshold_sec"]
    assert new_thresh <= max_cap, f"Learned threshold {new_thresh} exceeded max cap {max_cap}"


def test_floor_collapse_cannot_be_learned_as_normal_rest(learner):
    """
    CRITICAL SAFETY REQUIREMENT:
    A fall on the floor must NOT become 'normal behavior' just because
    a resident often rests.
    """
    initial_floor = learner.evaluate_inactivity_anomaly("living_room", motionless_seconds=190.0, posture="floor")
    assert initial_floor["is_anomaly"] is True

    # Attempt to train the learner with floor fall feedback
    update = learner.reinforce_dismissed_alarm(
        zone="living_room",
        inactivity_duration_sec=600.0,
        hour=14,
        feedback="Resident fell on floor but said okay"
    )

    # Floor posture check must STILL trigger anomaly at 190s!
    recheck_floor = learner.evaluate_inactivity_anomaly("living_room", motionless_seconds=190.0, posture="floor", hour=14)
    assert recheck_floor["is_anomaly"] is True, "Floor collapse must remain an anomaly!"
    assert recheck_floor["threshold_sec"] <= 180.0


def test_circadian_resting_windows(learner):
    """Bedroom sleep at night must have higher tolerance than active day."""
    night_bedroom = learner.get_tolerated_inactivity_threshold("bedroom", hour=2)
    day_bedroom = learner.get_tolerated_inactivity_threshold("bedroom", hour=11)
    assert night_bedroom >= 1800.0, "Night bedroom threshold should accommodate sleep"
    assert night_bedroom >= day_bedroom


def test_baseline_quality_metrics(learner):
    """Verifies structured baseline quality, sample count, and confidence score."""
    q = learner.get_baseline_quality("living_room", hour=15)
    assert "expected_activity" in q
    assert "tolerated_inactivity" in q
    assert "zone_risk_tier" in q
    assert "learned_sample_count" in q
    assert "false_alarms_prevented" in q
    assert "baseline_confidence" in q
    assert 0.0 <= q["baseline_confidence"] <= 1.0
    assert q["min_safety_bound_sec"] >= 180.0


def test_summary_reports_authentic_counts(learner):
    """Summary must report authentic counts rather than hardcoded minimums."""
    summary = learner.get_summary()
    assert summary["total_learned_events"] == learner.profile.get("total_learned_events", 0)
    assert summary["suppressed_false_alarms"] == learner.profile.get("suppressed_false_alarms", 0)
    assert "current_thresholds" in summary
    assert "baseline_quality" in summary
