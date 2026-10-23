"""
Unit and Integration Tests for Aegis Fall Detection & Mock Event Emitter.
Amazon Developer Hackathon 2026.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
import numpy as np

from app.vision.fall_detector import AegisFallDetector, FallEvent
from fall_detector import generate_synthetic_frame
from mock_event_emitter import SCENARIOS, build_payload


# ---------------------------------------------------------------------------
# 1. FallEvent Contract Tests
# ---------------------------------------------------------------------------

def test_fall_event_contract_serialization():
    event = FallEvent(
        event_type="possible_fall",
        confidence=0.94,
        location="living_room",
        movement_after_event="none"
    )
    data = event.to_dict()

    assert data["event_type"] == "possible_fall"
    assert data["confidence"] == 0.94
    assert data["location"] == "living_room"
    assert data["movement_after_event"] == "none"
    assert "timestamp" in data

    json_str = event.to_json()
    parsed = json.loads(json_str)
    assert parsed["event_type"] == "possible_fall"
    assert parsed["movement_after_event"] == "none"


# ---------------------------------------------------------------------------
# 2. Biomechanical Analysis Calculations
# ---------------------------------------------------------------------------

def test_torso_angle_calculation_vertical_vs_horizontal():
    detector = AegisFallDetector(location="bedroom", use_yolo=False)

    # Synthetic standing upright keypoints (vertical)
    standing_kpts = np.zeros((17, 3), dtype=np.float32)
    standing_kpts[detector.LEFT_SHOULDER] = [200, 100, 0.9]
    standing_kpts[detector.RIGHT_SHOULDER] = [250, 100, 0.9]
    standing_kpts[detector.LEFT_HIP] = [205, 250, 0.9]
    standing_kpts[detector.RIGHT_HIP] = [245, 250, 0.9]

    standing_angle = detector._calculate_torso_angle(standing_kpts)
    assert standing_angle > 75.0, f"Standing angle should be ~90 deg, got {standing_angle}"

    # Synthetic fallen horizontal keypoints (lying flat on floor)
    fallen_kpts = np.zeros((17, 3), dtype=np.float32)
    fallen_kpts[detector.LEFT_SHOULDER] = [100, 380, 0.9]
    fallen_kpts[detector.RIGHT_SHOULDER] = [100, 410, 0.9]
    fallen_kpts[detector.LEFT_HIP] = [280, 385, 0.9]
    fallen_kpts[detector.RIGHT_HIP] = [280, 415, 0.9]

    fallen_angle = detector._calculate_torso_angle(fallen_kpts)
    assert fallen_angle < 30.0, f"Fallen angle should be < 30 deg, got {fallen_angle}"


def test_vertical_velocity_calculation():
    detector = AegisFallDetector(location="kitchen", use_yolo=False)

    # Seed history: person at y=150, height=200
    t0 = 1000.0
    detector.history.append((t0, 150.0, 200.0, np.zeros((17, 3))))

    # Rapid downward descent: drops to y=350 in 0.35 seconds
    t1 = t0 + 0.35
    vel = detector._calculate_vertical_velocity(current_time=t1, current_y=350.0, person_h=200.0)

    # dy = 200px / (0.35s * 200px) = ~2.85 body_heights/sec
    assert vel > 1.5, f"Expected rapid descent velocity > 1.5 body_h/s, got {vel}"


# ---------------------------------------------------------------------------
# 3. Full Synthetic Fall Pipeline Run
# ---------------------------------------------------------------------------

def test_synthetic_fall_detection_sequence():
    detector = AegisFallDetector(
        location="living_room",
        immobility_window_sec=1.0,
        use_yolo=True
    )

    confirmed_event = None
    # Simulate 100 frames of standing -> falling -> immobile
    for idx in range(100):
        frame = generate_synthetic_frame(idx, total_frames=100)
        sim_time = 1000.0 + (idx * 0.033)
        event, diag = detector.process_frame(frame, current_time=sim_time)
        if event:
            confirmed_event = event
            break

    assert confirmed_event is not None, "Pipeline must confirm fall in synthetic test sequence"
    assert confirmed_event.event_type == "possible_fall"
    assert confirmed_event.location == "living_room"
    assert confirmed_event.movement_after_event in ["none", "crawling", "slight_twitch"]


# ---------------------------------------------------------------------------
# 4. Mock Event Emitter Payload Verification
# ---------------------------------------------------------------------------

def test_mock_event_emitter_scenarios():
    for name, scen in SCENARIOS.items():
        payload = build_payload(name)
        assert "event" in payload
        assert "context" in payload
        assert payload["event"]["event_type"] in ["possible_fall", "prolonged_inactivity"]
        assert 0.0 <= payload["event"]["confidence"] <= 1.0
        assert payload["event"]["movement_after_event"] in ["none", "normal", "slight_twitch", "crawling"]


if __name__ == "__main__":
    pytest.main([__file__])
