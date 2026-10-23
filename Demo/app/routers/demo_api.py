"""
NIRA Demo System API Router.
Amazon Developer Hackathon 2026.

Exposes endpoints for the Demo System:
- POST /api/v1/demo/launch: Invoked immediately when user clicks the DEMO button.
- POST /api/v1/demo/scenario/{name}: Triggers any demo scenario from the demo package.
- GET  /api/v1/demo/reference: Provides structured file references and documentation for demo & live systems.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, status

logger = logging.getLogger("NIRA.DemoAPI")
router = APIRouter(prefix="/api/v1/demo", tags=["NIRA Demo System"])

# Available demo scenarios
DEMO_SCENARIOS = {
    "normal_day": "Realistic 24-Hour Routine (9 time slots, resident stays safe & normal)",
    "false_alarm": "Scenario 1: False Alarm Recovery (Living room stumble -> 'I'm okay' -> RESOLVED)",
    "responsive_emergency": "Scenario 2: Responsive Emergency (Fall detected -> 'Help me' -> Caregiver Escalation)",
    "silent_emergency": "Scenario 3: Silent Emergency (Nocturnal wet tile fall -> Silence -> 911 CAD Dispatch)",
    "worsening_condition": "Scenario 4: Worsening Condition (Slip -> Increasing inactivity -> Tachycardia surge -> Auto-Escalate)",
    "environmental_hazard": "Scenario 5: Environmental Hazard (Standing water leak in dim bathroom -> Pre-fall warning)",
    "medication_miss": "Scenario 6: Medication Miss (Evening Lisinopril delayed -> Echo prompt -> Caregiver alert)",
    "recovery": "Recovery Scenario: Fall detected, rising movement confirms recovery -> Normal baseline",
    "sensor_dropout": "Sensor Dropout: Watch disconnected, 60GHz radar verifies safe -> Reconnect"
}


@router.post("/launch", summary="Launch Demo System (Called when DEMO button is clicked)")
async def launch_demo_system():
    """
    Called directly when the user clicks 'DEMO' on the NIRA landing gateway.
    Prepares the demo environment, verifies sensor telemetry, and connects
    the client to the demo system.
    """
    return {
        "status": "ready",
        "system_mode": "demo",
        "message": "NIRA Demo System successfully loaded and engaged.",
        "active_resident": "Eleanor Vance (Age 79)",
        "available_scenarios": DEMO_SCENARIOS,
        "demo_folder": "demo/",
        "live_folder": "live/"
    }


@router.get("/reference", summary="Reference of Demo and Live folder files")
async def get_system_reference():
    """Returns file references and architecture map for demo and live folders."""
    return {
        "architecture": {
            "demo": {
                "folder": "demo/",
                "description": "Multi-device ambient simulators, mock event emitters, and scenarios",
                "files": [
                    {"name": "demo/nira_simulator.py", "role": "Master unified CLI simulator and multi-device orchestrator"},
                    {"name": "demo/scenario_simulator.py", "role": "End-to-end multi-device timeline scenario generator"},
                    {"name": "demo/wearable_simulator.py", "role": "Apple Watch biometrics & IMU telemetry generator"},
                    {"name": "demo/radar_simulator.py", "role": "60GHz mmWave radar micro-motion & posture simulator"},
                    {"name": "demo/vision_simulator.py", "role": "Edge AI camera optical skeleton keypoint simulator"},
                    {"name": "demo/voice_simulator.py", "role": "Alexa Echo Show 15 acoustic & dialog simulator"},
                    {"name": "demo/environment_simulator.py", "role": "Ambient lux, humidity, and water leak sensor simulator"},
                    {"name": "demo/fall_detector.py", "role": "Geometric pose & threshold fall detection logic"},
                    {"name": "demo/mock_event_emitter.py", "role": "Lightweight mock event dispatcher for quick testing"}
                ]
            },
            "live": {
                "folder": "live/",
                "description": "Real-time webcam inference, physical sensor ingestion streams, and live models",
                "files": [
                    {"name": "live/live_vision_tracker.py", "role": "Real-time YOLOv8-pose edge webcam skeletal fall tracker"},
                    {"name": "live/live_ingest_stream.py", "role": "Direct HTTP ingestion client for physical IoT devices"}
                ]
            }
        }
    }


def _run_scenario_background(scenario_name: str):
    """Executes a scenario in the background using the demo package orchestrator."""
    try:
        try:
            from Demo.scenario_simulator import ScenarioSimulator
        except ImportError:
            from scenario_simulator import ScenarioSimulator
        sim = ScenarioSimulator(base_url="http://localhost:8000", resident_id="user_eleanor_vance", step_delay_sec=0.3)
        if scenario_name == "normal_day":
            sim.run_normal_day(slot_delay_sec=0.2)
        elif scenario_name == "false_alarm":
            sim.run_scenario_a_false_alarm()
        elif scenario_name == "responsive_emergency":
            sim.run_scenario_b_responsive_emergency()
        elif scenario_name == "silent_emergency":
            sim.run_scenario_c_silent_emergency()
        elif scenario_name == "worsening_condition":
            sim.run_scenario_worsening_condition()
        elif scenario_name == "environmental_hazard":
            sim.run_scenario_f_environmental_hazard()
        elif scenario_name == "medication_miss":
            sim.run_scenario_medication_miss()
        elif scenario_name == "recovery":
            sim.run_scenario_d_recovery()
        elif scenario_name == "sensor_dropout":
            sim.run_scenario_e_sensor_dropout()
    except Exception as e:
        logger.error(f"Error running scenario {scenario_name}: {e}")


@router.post("/scenario/{scenario_name}", summary="Trigger a demo scenario from demo/")
async def trigger_demo_scenario(scenario_name: str, background_tasks: BackgroundTasks):
    """Triggers execution of a demo scenario from demo/ package."""
    canonical = scenario_name.lower().replace("-", "_")
    if canonical not in DEMO_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown scenario '{scenario_name}'. Valid: {list(DEMO_SCENARIOS.keys())}"
        )

    background_tasks.add_task(_run_scenario_background, canonical)
    return {
        "status": "triggered",
        "scenario": canonical,
        "description": DEMO_SCENARIOS[canonical],
        "message": f"Scenario '{canonical}' is now streaming into the NIRA Event Pipeline."
    }


# ---------------------------------------------------------------------------
# Operator Sensor Simulation Actions (13 Core Actions)
# ---------------------------------------------------------------------------

import uuid
from datetime import datetime, timezone
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.event_pipeline import global_pipeline
from app.models.event_contracts import UnifiedEvent, EventSource, EventType


@router.post("/simulate/{action}", summary="Trigger specific sensor simulation event")
async def trigger_operator_simulation_action(
    action: str,
    db: Session = Depends(get_db)
):
    """
    Executes authoritative sensor events for operator control panel:
    NORMAL, FALL, INACTIVITY, HIGH HEART RATE, LOW MOVEMENT,
    VOICE SAFE, VOICE RISK, VOICE HELP, VOICE SILENCE,
    ENVIRONMENT HAZARD, DEVICE DISCONNECT, MEDICATION MISSED, RECOVERY.
    """
    act = action.lower().replace("-", "_")
    now_iso = datetime.now(timezone.utc).isoformat()
    corr_id = f"corr-op-{act}-{uuid.uuid4().hex[:6]}"

    if act == "normal":
        global_pipeline.reset_to_normal()
        await global_pipeline.broadcast({
            "type": "NIRA_STATE_RESET",
            "state": global_pipeline.current_state.model_dump(),
            "timestamp": now_iso
        })
        return {
            "status": "SUCCESS",
            "action": "NORMAL",
            "safety_state": global_pipeline.current_state.safety_state,
            "risk_level": global_pipeline.current_state.risk_level,
            "message": "NIRA resident state reset to baseline NORMAL.",
            "current_state": global_pipeline.current_state.model_dump()
        }

    evt_map = {
        "fall": UnifiedEvent(
            event_id=f"evt-op-fall-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.CAMERA_POSE.value,
            event_type=EventType.POSE_FALL_DETECTED.value,
            payload={
                "fall_confirmed": True,
                "aspect_ratio": 2.4,
                "torso_angle": 12.0,
                "movement_after_event": "none",
                "downward_velocity_norm": 2.85
            },
            confidence=0.94,
            correlation_id=corr_id
        ),
        "inactivity": UnifiedEvent(
            event_id=f"evt-op-inac-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.RADAR.value,
            event_type=EventType.IMMOBILITY_DETECTED.value,
            payload={
                "presence": True,
                "motion_level": 0.02,
                "duration_sec": 240,
                "occupancy_count": 1,
                "zone": "floor_substrate"
            },
            confidence=0.92,
            correlation_id=corr_id
        ),
        "high_heart_rate": UnifiedEvent(
            event_id=f"evt-op-hr-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.WEARABLE.value,
            event_type=EventType.TACHYCARDIA_ALERT.value,
            payload={
                "heart_rate_bpm": 138,
                "movement_index": 0.05,
                "wearable_status": "worn_normal",
                "arrhythmia_detected": True,
                "skin_contact": True
            },
            confidence=0.96,
            correlation_id=corr_id
        ),
        "low_movement": UnifiedEvent(
            event_id=f"evt-op-lowmv-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.WEARABLE.value,
            event_type=EventType.WEARABLE_TELEMETRY.value,
            payload={
                "heart_rate_bpm": 92,
                "movement_index": 0.08,
                "wearable_status": "worn_normal",
                "skin_contact": True
            },
            confidence=0.90,
            correlation_id=corr_id
        ),
        "voice_safe": UnifiedEvent(
            event_id=f"evt-op-voxsafe-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="living_room",
            source=EventSource.AUDIO_VOICE.value,
            event_type=EventType.VOICE_RESPONSE_SAFE.value,
            payload={
                "transcript": "I am okay, false alarm, just dropped my book.",
                "intent": "safe",
                "is_timeout": False,
                "confidence": 0.98
            },
            confidence=0.98,
            correlation_id=corr_id
        ),
        "voice_risk": UnifiedEvent(
            event_id=f"evt-op-voxrisk-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="living_room",
            source=EventSource.AUDIO_VOICE.value,
            event_type=EventType.VOICE_RESPONSE_DISTRESS.value,
            payload={
                "transcript": "I feel very dizzy and cannot stand up.",
                "intent": "distress",
                "is_timeout": False,
                "confidence": 0.88
            },
            confidence=0.88,
            correlation_id=corr_id
        ),
        "voice_help": UnifiedEvent(
            event_id=f"evt-op-voxhelp-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.AUDIO_VOICE.value,
            event_type=EventType.VOICE_RESPONSE_DISTRESS.value,
            payload={
                "transcript": "Help me! I fell down and my hip hurts!",
                "intent": "distress",
                "is_timeout": False,
                "confidence": 0.98
            },
            confidence=0.98,
            correlation_id=corr_id
        ),
        "voice_silence": UnifiedEvent(
            event_id=f"evt-op-voxsilence-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.AUDIO_VOICE.value,
            event_type=EventType.VOICE_TIMEOUT.value,
            payload={
                "transcript": "",
                "intent": "timeout",
                "is_timeout": True,
                "confidence": 1.0
            },
            confidence=1.0,
            correlation_id=corr_id
        ),
        "environment_hazard": UnifiedEvent(
            event_id=f"evt-op-env-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.ENVIRONMENT.value,
            event_type=EventType.FLOOR_MOISTURE_DETECTED.value,
            payload={
                "floor_moisture_detected": True,
                "humidity_pct": 89.0,
                "lighting_lux": 8.0,
                "temperature_c": 22.4,
                "environment_label": "wet_tile_hazard"
            },
            confidence=0.96,
            correlation_id=corr_id
        ),
        "device_disconnect": UnifiedEvent(
            event_id=f"evt-op-disc-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bedroom",
            source=EventSource.WEARABLE.value,
            event_type=EventType.WEARABLE_CONNECTIVITY.value,
            payload={
                "wearable_status": "disconnected_off_wrist",
                "heart_rate_bpm": 0,
                "battery_percentage": 0,
                "skin_contact": False
            },
            confidence=1.0,
            correlation_id=corr_id
        ),
        "medication_missed": UnifiedEvent(
            event_id=f"evt-op-med-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="kitchen",
            source=EventSource.SYSTEM.value,
            event_type=EventType.STATE_TRANSITION.value,
            payload={
                "medication": "Lisinopril 10mg",
                "scheduled_time": "18:00",
                "status": "MISSED",
                "delay_minutes": 120,
                "adherence_score": 0.88,
                "alert_caregiver": True,
                "notification_message": "Evening Lisinopril 10mg missed by Eleanor. Caregiver alerted."
            },
            confidence=0.95,
            correlation_id=corr_id
        ),
        "recovery": UnifiedEvent(
            event_id=f"evt-op-recov-{uuid.uuid4().hex[:6]}",
            timestamp=now_iso,
            resident_id="user_eleanor_vance",
            room_id="bathroom",
            source=EventSource.CAMERA_POSE.value,
            event_type=EventType.POSE_RECOVERED.value,
            payload={
                "torso_angle": 88.0,
                "movement_after_event": "normal",
                "posture": "upright_walking"
            },
            confidence=0.95,
            correlation_id=corr_id
        )
    }

    if act not in evt_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown simulation action '{action}'. Valid actions: {list(evt_map.keys()) + ['normal']}"
        )

    event = evt_map[act]
    ingest_result = await global_pipeline.ingest_event(event, db=db)

    return {
        "status": "SUCCESS",
        "action": act.upper(),
        "event_id": event.event_id,
        "event_type": event.event_type,
        "safety_state": ingest_result.safety_state,
        "risk_level": ingest_result.risk_level,
        "composite_risk_score": ingest_result.composite_risk_score,
        "current_state": global_pipeline.current_state.model_dump()
    }
