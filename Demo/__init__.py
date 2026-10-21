"""
NIRA Demo Systems Package.
Contains all ambient sensor simulators, scenario runners, and event generators.
"""

from demo.wearable_simulator import WearableSimulator
from demo.environment_simulator import EnvironmentSimulator
from demo.radar_simulator import RadarSimulator
from demo.vision_simulator import VisionSimulator
from demo.voice_simulator import VoiceSimulator
from demo.scenario_simulator import ScenarioSimulator
from demo.fall_detector import AegisFallDetector, AegisFallDetector as FallDetector
from demo.mock_event_emitter import emit_event, build_payload, run_e2e_voice_simulation, SCENARIOS

__all__ = [
    "WearableSimulator",
    "EnvironmentSimulator",
    "RadarSimulator",
    "VisionSimulator",
    "VoiceSimulator",
    "ScenarioSimulator",
    "AegisFallDetector",
    "FallDetector",
    "emit_event",
    "build_payload",
    "run_e2e_voice_simulation",
    "SCENARIOS",
]
