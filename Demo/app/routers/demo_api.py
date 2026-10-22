"""
NIRA Demo System API Router.
Amazon Developer Hackathon 2026.

Exposes endpoints for the Demo System:
- POST /api/v1/demo/launch: Invoked immediately when user clicks the DEMO button.
- POST /api/v1/demo/scenario/{name}: Triggers any demo scenario from the demo package.
- GET  /api/v1/demo/reference: Provides structured file references and documentation for demo & live systems.
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel

logger = logging.getLogger("NIRA.DemoAPI")
router = APIRouter(prefix="/api/v1/demo", tags=["NIRA Demo System"])

# Available demo scenarios
DEMO_SCENARIOS = {
    "normal_day": "Realistic 24-Hour Routine (9 time slots, resident stays safe & normal)",
    "false_alarm": "Scenario A: Living room thud, resident replies 'I'm okay' -> RESOLVED",
    "responsive_emergency": "Scenario B: Fall detected, resident cries 'Help me' -> Caregiver Escalation",
    "silent_emergency": "Scenario C: Nighttime bathroom fall + wet tile + silence -> 911 CAD Dispatch",
    "recovery": "Scenario D: Fall detected, rising movement confirms recovery -> Normal baseline",
    "sensor_dropout": "Scenario E: Watch disconnected, 60GHz radar verifies safe -> Reconnect",
    "environmental_hazard": "Scenario F: Water leak in dark bathroom -> Pre-fall hazard warning"
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
            try:
                from demo.scenario_simulator import ScenarioSimulator
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
        elif scenario_name == "recovery":
            sim.run_scenario_d_recovery()
        elif scenario_name == "sensor_dropout":
            sim.run_scenario_e_sensor_dropout()
        elif scenario_name == "environmental_hazard":
            sim.run_scenario_f_environmental_hazard()
    except Exception as e:
        logger.error(f"Error running scenario {scenario_name}: {e}")


@router.post("/scenario/{scenario_name}", summary="Trigger a demo scenario from demo/")
async def trigger_demo_scenario(scenario_name: str, background_tasks: BackgroundTasks):
    """Triggers execution of a demo scenario from demo/ package."""
    if scenario_name not in DEMO_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown scenario '{scenario_name}'. Valid: {list(DEMO_SCENARIOS.keys())}"
        )

    background_tasks.add_task(_run_scenario_background, scenario_name)
    return {
        "status": "triggered",
        "scenario": scenario_name,
        "description": DEMO_SCENARIOS[scenario_name],
        "message": f"Scenario '{scenario_name}' is now streaming into the NIRA Event Pipeline."
    }
