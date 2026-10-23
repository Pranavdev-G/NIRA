"""
NIRA Unified Simulator CLI & Multi-Device Event Generator.
Amazon Developer Hackathon 2026.

Single master command interface to simulate external IoT/Edge devices:
  - Wearable Telemetry Simulator (biometrics, PPG, IMU, disconnect/reconnect)
  - Environmental Array Simulator (lux, temp, humidity, wet floor)
  - mmWave Radar Simulator (micro-motion, macro-motion, posture, presence)
  - Edge AI Camera / Fall Simulator (YOLOv8 keypoint torso angles, velocity)
  - Alexa Voice Interaction Simulator (two-way conversational wellness checks)
  - Multi-Device Scenario Orchestrator (A through F + 24-hour routine)

All simulators communicate strictly via external HTTP POST APIs:
  - POST /api/v1/events/ingest (UnifiedEvent)
  - POST /api/v1/incidents/{incident_id}/respond-voice

Usage Examples:
  python nira_simulator.py --scenario normal_day
  python nira_simulator.py --scenario false_alarm
  python nira_simulator.py --scenario responsive_emergency
  python nira_simulator.py --scenario silent_emergency
  python nira_simulator.py --scenario recovery
  python nira_simulator.py --scenario sensor_dropout
  python nira_simulator.py --scenario environmental_hazard
  python nira_simulator.py --all-scenarios
  python nira_simulator.py --stream --device wearable --preset normal_resting --frequency 1.0
  python nira_simulator.py --interactive
"""

import sys
import argparse
import logging

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from .wearable_simulator import WearableSimulator
    from .environment_simulator import EnvironmentSimulator
    from .radar_simulator import RadarSimulator
    from .vision_simulator import VisionSimulator
    from .voice_simulator import VoiceSimulator
    from .scenario_simulator import ScenarioSimulator
except (ImportError, ValueError):
    try:
        from Demo.wearable_simulator import WearableSimulator
        from Demo.environment_simulator import EnvironmentSimulator
        from Demo.radar_simulator import RadarSimulator
        from Demo.vision_simulator import VisionSimulator
        from Demo.voice_simulator import VoiceSimulator
        from Demo.scenario_simulator import ScenarioSimulator
    except ImportError:
        try:
            from demo.wearable_simulator import WearableSimulator
            from demo.environment_simulator import EnvironmentSimulator
            from demo.radar_simulator import RadarSimulator
            from demo.vision_simulator import VisionSimulator
            from demo.voice_simulator import VoiceSimulator
            from demo.scenario_simulator import ScenarioSimulator
        except ImportError:
            from wearable_simulator import WearableSimulator
            from environment_simulator import EnvironmentSimulator
            from radar_simulator import RadarSimulator
            from vision_simulator import VisionSimulator
            from voice_simulator import VoiceSimulator
            from scenario_simulator import ScenarioSimulator

logger = logging.getLogger("NIRA.SimulatorCLI")


def print_banner():
    banner = r"""
========================================================================
    _   _ ___ ____      _     ____  _                 _       _             
   | \ | |_ _|  _ \    / \   / ___|(_)_ __ ___  _   _| | __ _| |_ ___  _ __ 
   |  \| || || |_) |  / _ \  \___ \| | '_ ` _ \| | | | |/ _` | __/ _ \| '__|
   | |\  || ||  _ <  / ___ \  ___) | | | | | | | |_| | | (_| | || (_) | |   
   |_| \_|___|_| \_\/_/   \_\____/ |_|_| |_| |_|\__,_|_|\__,_|\__\___/|_|   
                                                                            
   Never Ignore Risk Assistant - Multi-Device Ambient Telemetry Engine
========================================================================
"""
    print(banner)


def run_interactive(base_url: str, resident_id: str):
    """Interactive console menu for demonstrating NIRA ambient safety."""
    orchestrator = ScenarioSimulator(base_url=base_url, resident_id=resident_id, step_delay_sec=0.4)
    print_banner()

    menu = """
Select a Scenario or Device Stream to Run:
------------------------------------------------------------------------
  [1] Normal Routine: Realistic 24-Hour Day (9 slots, stays NORMAL)
  [2] Scenario A: False Alarm (Stumble -> "I'm okay" -> RESOLVED)
  [3] Scenario B: Responsive Emergency (Fall -> "Help me" -> CAREGIVER_ESCALATION)
  [4] Scenario C: Silent Emergency (Wet floor fall + tachycardia + silence -> DISPATCH_READY)
  [5] Scenario D: Recovery After Emergency (Fall -> movement climbs -> rises -> NORMAL)
  [6] Scenario E: Sensor Dropout & Reconnect (Off-wrist -> Radar verifies safe -> Reconnect)
  [7] Scenario F: Environmental Hazard (Dark room wet floor pre-fall warning)
  [8] Run ALL Scenarios Sequentially (Comprehensive Demonstration)
  [9] Stream Single Device (Continuous Telemetry Loop)
  [0] Exit
------------------------------------------------------------------------
"""
    while True:
        print(menu)
        try:
            choice = input("Enter choice (0-9): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "0":
            print("Exiting NIRA Simulator.")
            break
        elif choice == "1":
            orchestrator.run_normal_day(slot_delay_sec=0.4)
        elif choice == "2":
            orchestrator.run_scenario_a_false_alarm()
        elif choice == "3":
            orchestrator.run_scenario_b_responsive_emergency()
        elif choice == "4":
            orchestrator.run_scenario_c_silent_emergency()
        elif choice == "5":
            orchestrator.run_scenario_d_recovery()
        elif choice == "6":
            orchestrator.run_scenario_e_sensor_dropout()
        elif choice == "7":
            orchestrator.run_scenario_f_environmental_hazard()
        elif choice == "8":
            run_all_scenarios(orchestrator)
        elif choice == "9":
            interactive_stream_device(base_url, resident_id)
        else:
            print("Invalid choice, please select 0-9.")


def run_all_scenarios(orchestrator: ScenarioSimulator):
    """Executes all scenarios with concise summaries."""
    print("\n" + "=" * 75)
    print("🚀 EXECUTING COMPLETE NIRA MULTI-DEVICE SIMULATION SUITE")
    print("=" * 75)

    print("\n>>> 1/7: 24-Hour Normal Routine...")
    orchestrator.run_normal_day(slot_delay_sec=0.2)

    print("\n>>> 2/7: Scenario A (False Alarm)...")
    orchestrator.run_scenario_a_false_alarm()

    print("\n>>> 3/7: Scenario B (Responsive Emergency)...")
    orchestrator.run_scenario_b_responsive_emergency()

    print("\n>>> 4/7: Scenario C (Silent Emergency)...")
    orchestrator.run_scenario_c_silent_emergency()

    print("\n>>> 5/7: Scenario D (Recovery After Emergency)...")
    orchestrator.run_scenario_d_recovery()

    print("\n>>> 6/7: Scenario E (Sensor Dropout & Reconnect)...")
    orchestrator.run_scenario_e_sensor_dropout()

    print("\n>>> 7/7: Scenario F (Environmental Hazard Pre-Warning)...")
    orchestrator.run_scenario_f_environmental_hazard()

    print("\n" + "=" * 75)
    print("🎉 ALL SCENARIOS COMPLETED SUCCESSFULLY VIA GENUINE BACKEND TELEMETRY!")
    print("=" * 75)


def interactive_stream_device(base_url: str, resident_id: str):
    """Stream a single device continuously."""
    print("\nChoose device to stream:")
    print("  [w] Wearable (Smartwatch)")
    print("  [e] Environment (Multi-room array)")
    print("  [r] mmWave Radar")
    print("  [v] Edge Vision Camera")
    choice = input("Device [w/e/r/v]: ").strip().lower()

    count_str = input("How many events to emit (e.g. 5, or 0 for infinite): ").strip()
    count = int(count_str) if count_str.isdigit() else 5
    count_val = None if count == 0 else count

    freq_str = input("Frequency in Hz (e.g. 1.0 for 1/sec): ").strip()
    freq = float(freq_str) if freq_str else 1.0

    if choice == "w":
        sim = WearableSimulator(resident_id=resident_id, target_url=f"{base_url}/api/v1/events/ingest")
        sim.start_continuous_stream(frequency_hz=freq, count=count_val)
    elif choice == "e":
        sim = EnvironmentSimulator(resident_id=resident_id, target_url=f"{base_url}/api/v1/events/ingest")
        sim.start_continuous_stream(frequency_hz=freq, count=count_val)
    elif choice == "r":
        sim = RadarSimulator(resident_id=resident_id, target_url=f"{base_url}/api/v1/events/ingest")
        sim.start_continuous_stream(frequency_hz=freq, count=count_val)
    elif choice == "v":
        sim = VisionSimulator(resident_id=resident_id, target_url=f"{base_url}/api/v1/events/ingest")
        sim.start_continuous_stream(frequency_hz=freq, count=count_val)
    else:
        print("Unknown device selection.")


def main():
    parser = argparse.ArgumentParser(
        description="NIRA Multi-Device Ambient Telemetry Simulator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scenarios available:
  normal_day            24-hour realistic routine across 9 time slots
  false_alarm           Scenario A: Stumble -> "I'm okay" -> RESOLVED
  responsive_emergency  Scenario B: Fall -> "Help me" -> CAREGIVER_ESCALATION
  silent_emergency      Scenario C: Wet floor fall + tachycardia + silence -> DISPATCH_READY
  recovery              Scenario D: Fall -> movement climbs -> rises -> NORMAL
  sensor_dropout        Scenario E: Off-wrist -> Radar verifies safe -> Reconnect
  environmental_hazard  Scenario F: Dark room wet floor pre-fall warning
  all                   Run all scenarios sequentially
"""
    )
    parser.add_argument("--scenario", "-s", type=str, choices=[
        "normal_day", "false_alarm", "responsive_emergency", "silent_emergency",
        "recovery", "sensor_dropout", "environmental_hazard", "all"
    ], help="Scenario to execute")
    parser.add_argument("--all-scenarios", action="store_true", help="Execute all scenarios sequentially")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive menu")
    parser.add_argument("--stream", action="store_true", help="Stream single device continuously")
    parser.add_argument("--device", "-d", type=str, choices=["wearable", "environment", "radar", "vision", "voice"],
                        default="wearable", help="Device to stream")
    parser.add_argument("--preset", "-p", type=str, default=None, help="Preset name for device")
    parser.add_argument("--frequency", "-f", type=float, default=1.0, help="Event frequency (Hz)")
    parser.add_argument("--noise", type=float, default=0.05, help="Noise jitter level (0.0 to 1.0)")
    parser.add_argument("--confidence", type=float, default=0.95, help="Device sensor confidence (0.0 to 1.0)")
    parser.add_argument("--latency", type=float, default=0.0, help="Simulated network latency (seconds)")
    parser.add_argument("--count", "-c", type=int, default=10, help="Number of events to emit when streaming")
    parser.add_argument("--speed", type=float, default=0.4, help="Step delay between scenario events (seconds)")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", help="NIRA Backend base URL")
    parser.add_argument("--resident-id", type=str, default="user_eleanor_vance", help="Resident ID")

    args = parser.parse_args()

    if args.interactive:
        run_interactive(base_url=args.base_url, resident_id=args.resident_id)
        return

    orchestrator = ScenarioSimulator(
        base_url=args.base_url,
        resident_id=args.resident_id,
        step_delay_sec=args.speed
    )

    if args.all_scenarios or args.scenario == "all":
        print_banner()
        run_all_scenarios(orchestrator)
        return

    if args.scenario:
        print_banner()
        scen = args.scenario
        if scen == "normal_day":
            orchestrator.run_normal_day(slot_delay_sec=args.speed)
        elif scen == "false_alarm":
            orchestrator.run_scenario_a_false_alarm()
        elif scen == "responsive_emergency":
            orchestrator.run_scenario_b_responsive_emergency()
        elif scen == "silent_emergency":
            orchestrator.run_scenario_c_silent_emergency()
        elif scen == "recovery":
            orchestrator.run_scenario_d_recovery()
        elif scen == "sensor_dropout":
            orchestrator.run_scenario_e_sensor_dropout()
        elif scen == "environmental_hazard":
            orchestrator.run_scenario_f_environmental_hazard()
        return

    if args.stream:
        print_banner()
        ingest_url = f"{args.base_url.rstrip('/')}/api/v1/events/ingest"
        preset = args.preset
        count = None if args.count <= 0 else args.count

        if args.device == "wearable":
            sim = WearableSimulator(
                resident_id=args.resident_id,
                target_url=ingest_url,
                noise_level=args.noise,
                confidence_score=args.confidence,
                latency_sec=args.latency
            )
            sim.start_continuous_stream(preset=preset or "normal_resting", frequency_hz=args.frequency, count=count)
        elif args.device == "environment":
            sim = EnvironmentSimulator(
                resident_id=args.resident_id,
                target_url=ingest_url,
                noise_level=args.noise,
                confidence_score=args.confidence,
                latency_sec=args.latency
            )
            sim.start_continuous_stream(preset=preset or "living_room_normal", frequency_hz=args.frequency, count=count)
        elif args.device == "radar":
            sim = RadarSimulator(
                resident_id=args.resident_id,
                target_url=ingest_url,
                noise_level=args.noise,
                confidence_score=args.confidence,
                latency_sec=args.latency
            )
            sim.start_continuous_stream(preset=preset or "upright_walking", frequency_hz=args.frequency, count=count)
        elif args.device == "vision":
            sim = VisionSimulator(
                resident_id=args.resident_id,
                target_url=ingest_url,
                noise_level=args.noise,
                confidence_score=args.confidence,
                latency_sec=args.latency
            )
            sim.start_continuous_stream(preset=preset or "upright_standing", frequency_hz=args.frequency, count=count)
        elif args.device == "voice":
            sim = VoiceSimulator(
                resident_id=args.resident_id,
                base_url=args.base_url,
                latency_sec=args.latency
            )
            ev = sim.emit_event(preset=preset or "safe_verbal_confirmation")
            print(f"Emitted voice event: {ev}")
        return

    # If no arguments provided, show help
    parser.print_help()


if __name__ == "__main__":
    main()
