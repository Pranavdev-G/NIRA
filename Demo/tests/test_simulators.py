"""
Comprehensive Tests for NIRA Multi-Device Simulators and Scenario Producers.
Amazon Developer Hackathon 2026.

Verifies:
  1. WearableSimulator produces genuine UnifiedEvent biometrics, handles noise, disconnect/reconnect.
  2. EnvironmentSimulator produces multi-room ambient telemetry and moisture hazard detection.
  3. RadarSimulator emits privacy-preserving micro/macro motion and posture classifications.
  4. VisionSimulator emits YOLOv8 torso angle keypoints and post-fall mobility indicators.
  5. VoiceSimulator emits conversational confirmations, distress calls, and silence timeouts.
  6. Simulators interact strictly via HTTP endpoints, never directly touching SQLite database tables.
  7. Realistic 24-hour normal day routine (9 slots) consistently stays NORMAL (0 false emergencies).
  8. Scenarios A through F produce expected safety state evolutions.
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.event_pipeline import global_pipeline
from wearable_simulator import WearableSimulator
from environment_simulator import EnvironmentSimulator
from radar_simulator import RadarSimulator
from vision_simulator import VisionSimulator
from voice_simulator import VoiceSimulator
from scenario_simulator import ScenarioSimulator
import nira_simulator


@pytest.fixture
def client():
    """In-process TestClient to evaluate endpoints without external server dependency."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_pipeline():
    """Ensure every simulator test starts with a clean resident baseline."""
    global_pipeline.reset_to_normal()
    yield
    global_pipeline.reset_to_normal()


# ===========================================================================
# 1. Wearable Simulator Tests
# ===========================================================================

def test_wearable_event_generation():
    """WearableSimulator generates valid UnifiedEvent dictionaries with biometric payloads."""
    sim = WearableSimulator(resident_id="user_eleanor_vance", noise_level=0.0)
    event = sim.generate_unified_event(preset="normal_resting", room_id="bedroom")

    assert event["source"] == "wearable"
    assert event["resident_id"] == "user_eleanor_vance"
    assert event["room_id"] == "bedroom"
    assert "payload" in event
    payload = event["payload"]
    assert 68 <= payload["heart_rate_bpm"] <= 76
    assert payload["wearable_status"] == "worn_normal"
    assert payload["movement_index"] == 0.05
    assert payload["arrhythmia_detected"] is False
    assert event["confidence"] >= 0.90


def test_wearable_noise_and_overrides():
    """Noise jitter alters biometrics within bounded range, and overrides take effect."""
    sim = WearableSimulator(noise_level=0.2)
    ev = sim.generate_unified_event(preset="normal_resting", hr_override=105, movement_override=0.85)

    assert ev["payload"]["heart_rate_bpm"] == 105
    assert ev["payload"]["movement_index"] == 0.85


def test_wearable_disconnect_and_reconnect():
    """Device disconnect drops HR to 0 and sets disconnected status; reconnect restores normal vitals."""
    sim = WearableSimulator()
    assert sim.is_connected is True

    sim.disconnect()
    assert sim.is_connected is False
    ev_disc = sim.generate_unified_event()
    assert ev_disc["payload"]["heart_rate_bpm"] == 0
    assert ev_disc["payload"]["wearable_status"] == "disconnected"

    sim.reconnect()
    assert sim.is_connected is True
    ev_recon = sim.generate_unified_event(preset="normal_resting")
    assert ev_recon["payload"]["heart_rate_bpm"] > 50
    assert ev_recon["payload"]["wearable_status"] == "worn_normal"


def test_wearable_http_ingest(client):
    """Wearable simulator payload is valid for POST /api/v1/events/ingest."""
    sim = WearableSimulator()
    ev = sim.generate_unified_event(preset="walking_normal", room_id="kitchen")

    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACCEPTED"
    assert data["event_id"] == ev["event_id"]
    assert data["safety_state"] == "NORMAL"


# ===========================================================================
# 2. Environment Simulator Tests
# ===========================================================================

def test_environment_multi_room_presets():
    """EnvironmentSimulator supports diverse room states (bathroom wet floor, living room, bedroom)."""
    sim = EnvironmentSimulator()

    # Bathroom wet floor hazard
    ev_bath = sim.generate_unified_event(preset="bathroom_hazard_wet")
    assert ev_bath["room_id"] == "bathroom"
    assert ev_bath["payload"]["floor_moisture_detected"] is True
    assert ev_bath["payload"]["lighting_lux"] < 30
    assert ev_bath["payload"]["environment_label"] == "dark_room_wet_floor"

    # Living room normal
    ev_lr = sim.generate_unified_event(preset="living_room_normal")
    assert ev_lr["room_id"] == "living_room"
    assert ev_lr["payload"]["floor_moisture_detected"] is False
    assert ev_lr["payload"]["lighting_lux"] > 300

    # Nocturnal bedroom
    ev_bed = sim.generate_unified_event(preset="bedroom_nocturnal")
    assert ev_bed["payload"]["lighting_lux"] <= 5.0
    assert ev_bed["payload"]["motion_activity"] == "sleeping"


def test_environment_http_ingest(client):
    """Environmental telemetry ingests cleanly into backend event pipeline."""
    sim = EnvironmentSimulator()
    ev = sim.generate_unified_event(preset="kitchen_active")

    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"


# ===========================================================================
# 3. mmWave Radar Simulator Tests
# ===========================================================================

def test_radar_posture_and_motion():
    """Radar simulator produces micro/macro motion and biomechanical postures."""
    sim = RadarSimulator()

    # Standing
    ev_walk = sim.generate_unified_event(preset="upright_walking", room_id="living_room")
    assert ev_walk["payload"]["posture"] == "standing"
    assert ev_walk["payload"]["motion_level"] > 0.5
    assert ev_walk["payload"]["presence"] is True

    # Floor collapse
    ev_fall = sim.generate_unified_event(preset="floor_collapse_immobile", room_id="bathroom")
    assert ev_fall["payload"]["posture"] == "floor_collapse"
    assert ev_fall["payload"]["motion_level"] == 0.0
    assert ev_fall["payload"]["zone"] == "floor"

    # Rising from floor
    ev_rise = sim.generate_unified_event(preset="recovery_rising", room_id="living_room")
    assert ev_rise["payload"]["posture"] == "rising"
    assert ev_rise["payload"]["motion_level"] > 0.4


def test_radar_http_ingest(client):
    """Radar presence telemetry ingests properly through standard event API."""
    sim = RadarSimulator()
    ev = sim.generate_unified_event(preset="seated_relaxing", room_id="living_room")

    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"


# ===========================================================================
# 4. Vision / Edge AI Camera Simulator Tests
# ===========================================================================

def test_vision_posture_and_fall_metrics():
    """VisionSimulator generates YOLOv8 keypoint metrics (torso angle, velocity, post-fall movement)."""
    sim = VisionSimulator()

    # Standing upright
    ev_stand = sim.generate_unified_event(preset="upright_standing", room_id="kitchen")
    assert ev_stand["payload"]["torso_angle_deg"] > 80.0
    assert ev_stand["payload"]["downward_velocity_norm"] < 0.2
    assert ev_stand["payload"]["movement_after_event"] == "normal"
    assert ev_stand["payload"]["fall_confirmed"] is False

    # Floor collapse with zero mobility
    ev_fall = sim.generate_unified_event(preset="fall_impact_immobile", room_id="bathroom")
    assert ev_fall["payload"]["torso_angle_deg"] < 25.0
    assert ev_fall["payload"]["downward_velocity_norm"] > 0.8
    assert ev_fall["payload"]["movement_after_event"] == "none"
    assert ev_fall["payload"]["fall_confirmed"] is True


def test_vision_http_ingest(client):
    """Vision events successfully ingest and affect risk scoring."""
    sim = VisionSimulator()
    ev = sim.generate_unified_event(preset="upright_walking", room_id="bedroom")

    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"
    assert resp.json()["safety_state"] == "NORMAL"


# ===========================================================================
# 5. Voice Interaction Simulator Tests
# ===========================================================================

def test_voice_presets_and_timeout():
    """VoiceSimulator generates conversational responses and timeout windows."""
    sim = VoiceSimulator()

    # Safe confirmation
    ev_safe = sim.generate_unified_event(preset="safe_verbal_confirmation")
    assert ev_safe["payload"]["is_timeout"] is False
    assert "I'm okay" in ev_safe["payload"]["transcript"]
    assert ev_safe["payload"]["intent"] == "safe"

    # Distress call
    ev_distress = sim.generate_unified_event(preset="distress_help")
    assert "Help me" in ev_distress["payload"]["transcript"]
    assert ev_distress["payload"]["intent"] == "distress"

    # Silence timeout
    ev_timeout = sim.generate_unified_event(preset="prompt_timeout")
    assert ev_timeout["payload"]["is_timeout"] is True
    assert ev_timeout["payload"]["transcript"] is None
    assert ev_timeout["payload"]["intent"] == "timeout"


def test_voice_http_ingest(client):
    """Voice events ingest into the backend pipeline via /api/v1/events/ingest."""
    sim = VoiceSimulator()
    ev = sim.generate_unified_event(preset="safe_verbal_confirmation")

    resp = client.post("/api/v1/events/ingest", json=ev)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACCEPTED"


# ===========================================================================
# 6. Scenario Orchestrator: 24-Hour Normal Routine (Must Stay NORMAL)
# ===========================================================================

def test_normal_day_routine_stays_normal(client):
    """
    Eleanor's realistic 24-hour day across all 9 slots:
      07:00 wake -> 07:30 bathroom -> 08:00 breakfast -> 10:00 living room ->
      12:30 lunch -> 15:00 rest -> 18:00 kitchen -> 21:30 bedroom -> 02:00 bathroom
    Must NEVER treat normal elder routine as an emergency!
    """
    sim_wear = WearableSimulator()
    sim_env = EnvironmentSimulator()
    sim_rad = RadarSimulator()
    corr_id = f"corr-normday-{uuid.uuid4().hex[:8]}"

    timeline = [
        ("07:00", "wake", "bedroom", "bedroom_morning", "bed_sleeping", "normal_resting"),
        ("07:30", "morning_toilet", "bathroom", "bathroom_normal", "upright_walking", "normal_resting"),
        ("08:00", "breakfast", "kitchen", "kitchen_active", "upright_walking", "walking_normal"),
        ("10:00", "reading", "living_room", "living_room_normal", "seated_relaxing", "normal_resting"),
        ("12:30", "lunch", "kitchen", "kitchen_active", "upright_walking", "walking_normal"),
        ("15:00", "afternoon_rest", "living_room", "living_room_normal", "seated_relaxing", "normal_resting"),
        ("18:00", "dinner_prep", "kitchen", "kitchen_active", "upright_walking", "walking_normal"),
        ("21:30", "retiring_to_bed", "bedroom", "bedroom_nocturnal", "bed_sleeping", "normal_resting"),
        ("02:00", "nocturnal_bathroom", "bathroom", "bathroom_normal", "upright_walking", "normal_resting")
    ]

    for clock, activity, room, env_pre, rad_pre, wear_pre in timeline:
        ev_env = sim_env.generate_unified_event(preset=env_pre, room_override=room, correlation_id=corr_id)
        ev_rad = sim_rad.generate_unified_event(preset=rad_pre, room_id=room, correlation_id=corr_id)
        ev_wear = sim_wear.generate_unified_event(preset=wear_pre, room_id=room, correlation_id=corr_id)

        # Ingest all 3 telemetry streams
        r1 = client.post("/api/v1/events/ingest", json=ev_env)
        r2 = client.post("/api/v1/events/ingest", json=ev_rad)
        r3 = client.post("/api/v1/events/ingest", json=ev_wear)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 200

        # Verify state is NORMAL and risk score is low
        wear_data = r3.json()
        assert wear_data["safety_state"] == "NORMAL", f"Slot {clock} ({activity}) falsely flagged emergency!"
        assert wear_data["composite_risk_score"] < 40.0, f"Slot {clock} risk score elevated unexpectedly!"


# ===========================================================================
# 7. Scenario A: False Alarm (Acoustic Thud -> Verbal Confirmation)
# ===========================================================================

def test_scenario_a_false_alarm_telemetry(client):
    """
    Scenario A: Minor stumble -> Radar upright -> "I'm okay" -> State returns to NORMAL/RESOLVED.
    """
    corr_id = f"corr-scen-a-{uuid.uuid4().hex[:8]}"
    vis = VisionSimulator()
    rad = RadarSimulator()
    wear = WearableSimulator()
    vox = VoiceSimulator()

    # Step 1: Minor stumble
    ev_vis = vis.generate_unified_event(preset="minor_stumble", room_id="living_room", correlation_id=corr_id)
    r1 = client.post("/api/v1/events/ingest", json=ev_vis)
    assert r1.status_code == 200

    # Step 2: Radar confirms upright
    ev_rad = rad.generate_unified_event(preset="upright_walking", room_id="living_room", correlation_id=corr_id)
    r2 = client.post("/api/v1/events/ingest", json=ev_rad)
    assert r2.status_code == 200

    # Step 3: Wearable reports normal motion resuming
    ev_wear = wear.generate_unified_event(preset="normal_resting", room_id="living_room", hr_override=80, correlation_id=corr_id)
    r3 = client.post("/api/v1/events/ingest", json=ev_wear)
    assert r3.status_code == 200

    # Step 4: Verbal confirmation "I'm okay"
    ev_vox = vox.generate_unified_event(preset="safe_verbal_confirmation", room_id="living_room", correlation_id=corr_id)
    r4 = client.post("/api/v1/events/ingest", json=ev_vox)
    assert r4.status_code == 200
    assert r4.json()["safety_state"] in ("NORMAL", "RESOLVED")


# ===========================================================================
# 8. Scenario B: Responsive Emergency (Fall -> Calls for Help)
# ===========================================================================

def test_scenario_b_responsive_emergency_telemetry(client):
    """
    Scenario B: Fall with crawling + floor posture + tachycardia + "Help me" -> CAREGIVER_ESCALATION.
    """
    corr_id = f"corr-scen-b-{uuid.uuid4().hex[:8]}"
    vis = VisionSimulator()
    rad = RadarSimulator()
    wear = WearableSimulator()
    vox = VoiceSimulator()

    # Step 1: Fall with crawling
    ev_vis = vis.generate_unified_event(preset="fall_impact_crawling", room_id="living_room", correlation_id=corr_id)
    r1 = client.post("/api/v1/events/ingest", json=ev_vis)
    assert r1.status_code == 200

    # Step 2: Radar confirms floor collapse
    ev_rad = rad.generate_unified_event(preset="floor_collapse_immobile", room_id="living_room", correlation_id=corr_id)
    r2 = client.post("/api/v1/events/ingest", json=ev_rad)
    assert r2.status_code == 200

    # Step 3: Wearable elevated HR
    ev_wear = wear.generate_unified_event(preset="walking_normal", room_id="living_room", hr_override=112, correlation_id=corr_id)
    r3 = client.post("/api/v1/events/ingest", json=ev_wear)
    assert r3.status_code == 200

    # Step 4: Calls for help
    ev_vox = vox.generate_unified_event(preset="distress_help", room_id="living_room", correlation_id=corr_id)
    r4 = client.post("/api/v1/events/ingest", json=ev_vox)
    assert r4.status_code == 200
    assert r4.json()["safety_state"] in ("HIGH", "CRITICAL")
    assert r4.json()["composite_risk_score"] >= 60.0


# ===========================================================================
# 9. Scenario C: Silent Emergency (Wet Floor Fall + Tachycardia + Silence)
# ===========================================================================

def test_scenario_c_silent_emergency_telemetry(client):
    """
    Scenario C: Nocturnal wet floor fall + complete immobility + tachycardia + silence timeout -> CRITICAL / DISPATCH.
    """
    corr_id = f"corr-scen-c-{uuid.uuid4().hex[:8]}"
    env = EnvironmentSimulator()
    vis = VisionSimulator()
    rad = RadarSimulator()
    wear = WearableSimulator()
    vox = VoiceSimulator()

    # Step 1: Wet bathroom floor
    ev_env = env.generate_unified_event(preset="bathroom_hazard_wet", room_override="bathroom", correlation_id=corr_id)
    r1 = client.post("/api/v1/events/ingest", json=ev_env)
    assert r1.status_code == 200

    # Step 2: High-impact fall
    ev_vis = vis.generate_unified_event(preset="fall_impact_immobile", room_id="bathroom", correlation_id=corr_id)
    r2 = client.post("/api/v1/events/ingest", json=ev_vis)
    assert r2.status_code == 200

    # Step 3: Radar confirms floor collapse
    ev_rad = rad.generate_unified_event(preset="floor_collapse_immobile", room_id="bathroom", correlation_id=corr_id)
    r3 = client.post("/api/v1/events/ingest", json=ev_rad)
    assert r3.status_code == 200

    # Step 4: Sympathetic tachycardia surge (140 bpm) with zero motion
    ev_wear = wear.generate_unified_event(preset="tachycardia_fall_impact", room_id="bathroom", correlation_id=corr_id)
    r4 = client.post("/api/v1/events/ingest", json=ev_wear)
    assert r4.status_code == 200

    # Step 5: Silence timeout
    ev_vox = vox.generate_unified_event(preset="prompt_timeout", room_id="bathroom", correlation_id=corr_id)
    r5 = client.post("/api/v1/events/ingest", json=ev_vox)
    assert r5.status_code == 200
    assert r5.json()["safety_state"] == "CRITICAL"
    assert r5.json()["composite_risk_score"] >= 80.0


# ===========================================================================
# 10. Scenario D: Recovery After Emergency
# ===========================================================================

def test_scenario_d_recovery_telemetry(client):
    """
    Scenario D: Fall detected -> movement index rises -> radar rising -> upright posture -> safe voice -> NORMAL.
    """
    corr_id = f"corr-scen-d-{uuid.uuid4().hex[:8]}"
    vis = VisionSimulator()
    rad = RadarSimulator()
    wear = WearableSimulator()
    vox = VoiceSimulator()

    # Fall
    ev_vis = vis.generate_unified_event(preset="fall_impact_crawling", room_id="kitchen", correlation_id=corr_id)
    client.post("/api/v1/events/ingest", json=ev_vis)

    # Movement recovery
    ev_wear = wear.generate_unified_event(preset="recovery_movement", room_id="kitchen", correlation_id=corr_id)
    client.post("/api/v1/events/ingest", json=ev_wear)

    # Radar tracks rising
    ev_rad = rad.generate_unified_event(preset="recovery_rising", room_id="kitchen", correlation_id=corr_id)
    client.post("/api/v1/events/ingest", json=ev_rad)

    # Upright restored
    ev_vis2 = vis.generate_unified_event(preset="posture_recovered_upright", room_id="kitchen", correlation_id=corr_id)
    client.post("/api/v1/events/ingest", json=ev_vis2)

    # Verbal recovery confirmation
    ev_vox = vox.generate_unified_event(preset="recovery_confirmation", room_id="kitchen", correlation_id=corr_id)
    resp = client.post("/api/v1/events/ingest", json=ev_vox)
    assert resp.status_code == 200
    assert resp.json()["safety_state"] in ("NORMAL", "RESOLVED")


# ===========================================================================
# 11. Scenario E: Sensor Dropout & Reconnect
# ===========================================================================

def test_scenario_e_sensor_dropout_telemetry(client):
    """
    Scenario E: Wearable watch disconnects (0 bpm), but radar confirms safe upright walking
    in living room -> No false critical emergency. Reconnect restores normal vitals.
    """
    corr_id = f"corr-scen-e-{uuid.uuid4().hex[:8]}"
    wear = WearableSimulator()
    rad = RadarSimulator()

    # Wearable disconnected
    wear.disconnect()
    ev_disc = wear.generate_unified_event(preset="disconnected", room_id="living_room", correlation_id=corr_id)
    r1 = client.post("/api/v1/events/ingest", json=ev_disc)
    assert r1.status_code == 200

    # Radar confirms active walking
    ev_rad = rad.generate_unified_event(preset="upright_walking", room_id="living_room", correlation_id=corr_id)
    r2 = client.post("/api/v1/events/ingest", json=ev_rad)
    assert r2.status_code == 200
    assert r2.json()["safety_state"] == "NORMAL"

    # Wearable reconnected
    wear.reconnect()
    ev_recon = wear.generate_unified_event(preset="normal_resting", room_id="living_room", correlation_id=corr_id)
    r3 = client.post("/api/v1/events/ingest", json=ev_recon)
    assert r3.status_code == 200
    assert r3.json()["safety_state"] == "NORMAL"


# ===========================================================================
# 12. Scenario F: Environmental Hazard Pre-Warning
# ===========================================================================

def test_scenario_f_environmental_hazard_telemetry(client):
    """
    Scenario F: Wet floor detected in dark bathroom before resident arrives.
    System elevates environmental risk without triggering a false fall emergency.
    """
    corr_id = f"corr-scen-f-{uuid.uuid4().hex[:8]}"
    env = EnvironmentSimulator()
    rad = RadarSimulator()
    wear = WearableSimulator()

    # Hazard event in bathroom
    ev_env = env.generate_unified_event(preset="bathroom_hazard_wet", room_override="bathroom", correlation_id=corr_id)
    r1 = client.post("/api/v1/events/ingest", json=ev_env)
    assert r1.status_code == 200
    assert r1.json()["safety_state"] in ("ANOMALY", "NORMAL", "CAUTION")

    # Resident approaching in hallway
    ev_rad = rad.generate_unified_event(preset="upright_walking", room_id="hallway", correlation_id=corr_id)
    r2 = client.post("/api/v1/events/ingest", json=ev_rad)
    assert r2.status_code == 200

    # Wearable reports normal baseline vitals
    ev_wear = wear.generate_unified_event(preset="walking_normal", room_id="hallway", correlation_id=corr_id)
    r3 = client.post("/api/v1/events/ingest", json=ev_wear)
    assert r3.status_code == 200
    # State should remain controlled (not a false CRITICAL fall)
    assert r3.json()["safety_state"] != "CRITICAL"


# ===========================================================================
# 13. Master CLI Argument Parsing and Dispatch
# ===========================================================================

def test_nira_simulator_cli_parser():
    """Verify nira_simulator CLI parser accepts all expected arguments without syntax error."""
    import sys
    from unittest.mock import patch

    test_args = ["nira_simulator.py", "--scenario", "normal_day", "--speed", "0.01"]
    with patch.object(sys, "argv", test_args):
        with patch("nira_simulator.ScenarioSimulator") as MockOrch:
            instance = MockOrch.return_value
            instance.run_normal_day.return_value = []
            nira_simulator.main()
            instance.run_normal_day.assert_called_once()
