"""
Mock Event Emitter for Aegis Ambient Care.
Amazon Developer Hackathon 2026.

Simulates synthetic ambient vision/sensor safety events and transmits them
via HTTP POST to the Aegis CARE FastAPI MCP backend without requiring physical cameras.
"""

import sys
import time
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import requests

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Pre-packaged Realistic Simulation Scenarios
# ---------------------------------------------------------------------------

SCENARIOS: Dict[str, Dict[str, Any]] = {
    "critical_fall_bathroom": {
        "description": "Severe slip & fall in bathroom with zero post-fall movement and elevated vitals.",
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.96,
            "location": "bathroom",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "bathing",
            "time_context": "night_time",
            "baseline_deviation": 0.92,
            "wearable_status": "high_heart_rate",
            "environment": "dark_room_wet_floor"
        }
    },
    "fall_living_room_immobile": {
        "description": "Sudden fall in living room; senior remains completely immobile on floor.",
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.94,
            "location": "living_room",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "walking_to_kitchen",
            "time_context": "early_morning",
            "baseline_deviation": 0.85,
            "wearable_status": "worn_normal",
            "environment": "dimly_lit"
        }
    },
    "fall_living_room_twitch": {
        "description": "Impact in living room with minor involuntary movement / slight twitching.",
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.89,
            "location": "living_room",
            "movement_after_event": "slight_twitch"
        },
        "context": {
            "activity": "resting",
            "time_context": "afternoon",
            "baseline_deviation": 0.68,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        }
    },
    "slip_kitchen_recovered": {
        "description": "Slip in kitchen where senior immediately stands back up (normal movement).",
        "event": {
            "event_type": "possible_fall",
            "confidence": 0.65,
            "location": "kitchen",
            "movement_after_event": "normal"
        },
        "context": {
            "activity": "cooking",
            "time_context": "afternoon",
            "baseline_deviation": 0.15,
            "wearable_status": "worn_normal",
            "environment": "well_lit"
        }
    },
    "prolonged_inactivity_bedroom": {
        "description": "Senior immobile in bedroom significantly past expected morning wake-up baseline.",
        "event": {
            "event_type": "prolonged_inactivity",
            "confidence": 0.88,
            "location": "bedroom",
            "movement_after_event": "none"
        },
        "context": {
            "activity": "sleeping",
            "time_context": "morning",
            "baseline_deviation": 0.87,
            "wearable_status": "low_heart_rate",
            "environment": "dark_room"
        }
    }
}


def build_payload(
    scenario_key: str,
    override_loc: Optional[str] = None,
    override_movement: Optional[str] = None,
    override_conf: Optional[float] = None
) -> Dict[str, Any]:
    """Builds the standardized event and context payload with current timestamp."""
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["fall_living_room_immobile"])
    now_iso = datetime.now(timezone.utc).isoformat()

    event = dict(scenario["event"])
    event["timestamp"] = now_iso

    if override_loc:
        event["location"] = override_loc
    if override_movement:
        event["movement_after_event"] = override_movement
    if override_conf is not None:
        event["confidence"] = override_conf

    context = dict(scenario["context"])

    return {
        "event": event,
        "context": context
    }


def emit_event(
    target_url: str,
    payload: Dict[str, Any],
    dry_run: bool = False
) -> Optional[Dict[str, Any]]:
    """Transmits payload via HTTP POST and logs server response and latency."""
    event = payload["event"]
    print("\n" + "=" * 65)
    print(f"📡 TRANSMITTING STANDARDIZED SAFETY EVENT")
    print(f"Target Endpoint: {target_url}")
    print(f"Event: {event['event_type']} | Conf: {event['confidence']:.0%} | Loc: {event['location']} | Movement: {event['movement_after_event']}")
    print("-" * 65)
    print(json.dumps(payload, indent=2))
    print("=" * 65)

    if dry_run:
        print("Dry run requested. Payload was not transmitted.")
        return None

    try:
        t0 = time.perf_counter()
        response = requests.post(
            target_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=3.0
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        print(f"\n📥 SERVER RESPONSE [{response.status_code}] (HTTP roundtrip: {elapsed_ms:.2f}ms)")
        if "X-Response-Time-Ms" in response.headers:
            print(f"⚡ Server-reported processing time: {response.headers['X-Response-Time-Ms']}ms")

        try:
            resp_data = response.json()
            print(json.dumps(resp_data, indent=2))
            return resp_data
        except Exception:
            print(response.text)
            return None

    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection Error: Could not connect to {target_url}")
        print("   Make sure the Aegis CARE FastAPI server is running: `uvicorn app.main:app --port 8000`")
        return None
    except Exception as e:
        print(f"\n❌ Transmission error: {e}")
        return None


def run_e2e_voice_simulation(backend_base_url: str, scenario_key: str):
    """
    Executes a complete end-to-end voice dialog simulation:
      1. Assess Risk
      2. Start Wellness Check on Alexa
      3. Simulate Alexa Voice Response ('Help me' vs 'I am okay' vs Timeout)
    """
    print(f"\n🚀 Executing End-to-End Voice AI Workflow for scenario: '{scenario_key}'")
    assess_url = f"{backend_base_url}/tools/assess_risk"
    payload = build_payload(scenario_key)

    risk_resp = emit_event(assess_url, payload)
    if not risk_resp:
        return

    risk_level = risk_resp["risk"]["risk_level"]
    print(f"\nEvaluated Risk Level: {risk_level}")

    # Step 2: Start Wellness Check
    start_url = f"{backend_base_url}/tools/start_wellness_check"
    session_id = f"sim_sess_{int(time.time())}"
    print(f"\n📢 Initiating Alexa Wellness Check (Session ID: {session_id})...")
    wellness_init = requests.post(
        start_url,
        json={
            "session_id": session_id,
            "event": payload["event"],
            "context": payload["context"],
            "initial_risk": risk_resp["risk"]
        }
    ).json()

    print(f"Alexa Speech Prompt: \"{wellness_init['prompt_text']}\"")
    print(f"Timeout duration: {wellness_init['timeout_seconds']}s")

    # Step 3: Simulate User Speech Responses
    respond_url = f"{backend_base_url}/tools/respond_wellness_check"
    print("\n--- SIMULATING USER VOICE INPUT ---")

    if "bathroom" in scenario_key or "immobile" in scenario_key:
        print("Voice input: \"Help me, I fell down and cannot get up!\" (Distress)")
        reply_resp = requests.post(
            respond_url,
            json={
                "session_id": session_id,
                "user_speech_transcript": "Help me, I fell down and cannot get up!",
                "is_timeout": False
            }
        ).json()
    elif "recovered" in scenario_key:
        print("Voice input: \"I'm okay, false alarm, just dropped my keys.\" (Safe)")
        reply_resp = requests.post(
            respond_url,
            json={
                "session_id": session_id,
                "user_speech_transcript": "I'm okay, false alarm, just dropped my keys.",
                "is_timeout": False
            }
        ).json()
    else:
        print("Voice input: <Silence> (Timeout / Presumed Unresponsive)")
        reply_resp = requests.post(
            respond_url,
            json={
                "session_id": session_id,
                "user_speech_transcript": None,
                "is_timeout": True
            }
        ).json()

    print("\nState Machine Resolution:")
    print(json.dumps(reply_resp, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Aegis Ambient Care - Synthetic Safety Event Emitter"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="critical_fall_bathroom",
        choices=list(SCENARIOS.keys()),
        help=f"Select scenario preset: {list(SCENARIOS.keys())}"
    )
    parser.add_argument(
        "--target",
        type=str,
        default="http://localhost:8000/tools/assess_risk",
        help="Target backend endpoint (default: http://localhost:8000/tools/assess_risk)"
    )
    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Override location e.g. living_room, bathroom, kitchen"
    )
    parser.add_argument(
        "--movement",
        type=str,
        default=None,
        choices=["none", "slight_twitch", "normal", "crawling"],
        help="Override movement_after_event"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=None,
        help="Override event confidence (0.0 to 1.0)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print event JSON without sending HTTP request"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Continuously stream events every N seconds"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Interval in seconds for continuous mode (default: 3.0)"
    )
    parser.add_argument(
        "--e2e-voice",
        action="store_true",
        help="Run complete end-to-end voice dialog simulation with state machine"
    )

    args = parser.parse_args()

    if args.e2e_voice:
        base_url = args.target.replace("/tools/assess_risk", "").rstrip("/")
        run_e2e_voice_simulation(base_url, args.scenario)
        return

    if args.continuous:
        print(f"Starting continuous event stream to {args.target} (every {args.interval}s)...")
        try:
            scenario_keys = list(SCENARIOS.keys())
            idx = 0
            while True:
                scen = scenario_keys[idx % len(scenario_keys)]
                payload = build_payload(scen, args.location, args.movement, args.confidence)
                emit_event(args.target, payload, args.dry_run)
                idx += 1
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStream terminated by user.")
            sys.exit(0)
    else:
        payload = build_payload(args.scenario, args.location, args.movement, args.confidence)
        emit_event(args.target, payload, args.dry_run)


if __name__ == "__main__":
    main()
