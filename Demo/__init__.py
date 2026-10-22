"""
NIRA Demo Systems Package.
Contains all ambient sensor simulators, scenario runners, and event generators.
"""

try:
    from Demo.wearable_simulator import WearableSimulator
    from Demo.environment_simulator import EnvironmentSimulator
    from Demo.radar_simulator import RadarSimulator
    from Demo.vision_simulator import VisionSimulator
    from Demo.voice_simulator import VoiceSimulator
    from Demo.scenario_simulator import ScenarioSimulator
    from Demo.fall_detector import AegisFallDetector, AegisFallDetector as FallDetector
    from Demo.mock_event_emitter import emit_event, build_payload, run_e2e_voice_simulation, SCENARIOS
except ImportError:
    try:
        from .wearable_simulator import WearableSimulator
        from .environment_simulator import EnvironmentSimulator
        from .radar_simulator import RadarSimulator
        from .vision_simulator import VisionSimulator
        from .voice_simulator import VoiceSimulator
        from .scenario_simulator import ScenarioSimulator
        from .fall_detector import AegisFallDetector, AegisFallDetector as FallDetector
        from .mock_event_emitter import emit_event, build_payload, run_e2e_voice_simulation, SCENARIOS
    except ImportError:
        from wearable_simulator import WearableSimulator
        from environment_simulator import EnvironmentSimulator
        from radar_simulator import RadarSimulator
        from vision_simulator import VisionSimulator
        from voice_simulator import VoiceSimulator
        from scenario_simulator import ScenarioSimulator
        from fall_detector import AegisFallDetector, AegisFallDetector as FallDetector
        from mock_event_emitter import emit_event, build_payload, run_e2e_voice_simulation, SCENARIOS

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
