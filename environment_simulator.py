"""
Environmental Sensor & Ambient Room State Simulator.
Amazon Developer Hackathon 2026.

Simulates ambient room state:
  - Ambient lighting (lux)
  - Temperature (°C) & Relative Humidity (%)
  - Acoustic noise level (dB)
  - Floor moisture / wetness presence
  - Room occupancy & motion activity
"""

import sys
import time
import json
import random
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import requests
except ImportError:
    requests = None


class EnvironmentSimulator:
    """Simulates smart home ambient sensor arrays (Echo Show, mmWave, Smart Plugs)."""

    PRESETS: Dict[str, Dict[str, Any]] = {
        "bathroom_hazard_wet": {
            "description": "Steamy shower room with moisture on ceramic tile floor and dim light.",
            "location": "bathroom",
            "temperature_c": 26.5,
            "humidity_pct": 89.0,
            "lighting_lux": 15.0,
            "ambient_noise_db": 58.0,
            "floor_moisture": True,
            "motion_activity": "showering",
            "environment_label": "dark_room_wet_floor"
        },
        "living_room_normal": {
            "description": "Well-lit living room in afternoon; dry floor, comfortable climate.",
            "location": "living_room",
            "temperature_c": 21.5,
            "humidity_pct": 42.0,
            "lighting_lux": 380.0,
            "ambient_noise_db": 38.0,
            "floor_moisture": False,
            "motion_activity": "resting",
            "environment_label": "well_lit"
        },
        "kitchen_active": {
            "description": "Kitchen during meal preparation; moderate ambient noise.",
            "location": "kitchen",
            "temperature_c": 23.0,
            "humidity_pct": 52.0,
            "lighting_lux": 450.0,
            "ambient_noise_db": 54.0,
            "floor_moisture": False,
            "motion_activity": "cooking",
            "environment_label": "well_lit"
        },
        "bedroom_nocturnal": {
            "description": "Pitch-dark bedroom during nocturnal rest hours.",
            "location": "bedroom",
            "temperature_c": 19.5,
            "humidity_pct": 45.0,
            "lighting_lux": 2.0,
            "ambient_noise_db": 28.0,
            "floor_moisture": False,
            "motion_activity": "sleeping",
            "environment_label": "dark_room"
        },
        "hallway_unlit": {
            "description": "Unlit corridor at night with floor obstacle.",
            "location": "hallway",
            "temperature_c": 20.0,
            "humidity_pct": 44.0,
            "lighting_lux": 4.0,
            "ambient_noise_db": 30.0,
            "floor_moisture": False,
            "motion_activity": "walking",
            "environment_label": "dark_room"
        }
    }

    @classmethod
    def generate(
        cls,
        preset: str = "bathroom_hazard_wet",
        room_override: Optional[str] = None
    ) -> Dict[str, Any]:
        cfg = cls.PRESETS.get(preset, cls.PRESETS["bathroom_hazard_wet"])
        now_iso = datetime.now(timezone.utc).isoformat()
        loc = room_override or cfg["location"]

        return {
            "telemetry_type": "environmental_state",
            "location": loc,
            "timestamp": now_iso,
            "temperature_c": round(cfg["temperature_c"] + random.uniform(-0.3, 0.3), 1),
            "humidity_pct": round(cfg["humidity_pct"] + random.uniform(-1.0, 1.0), 1),
            "lighting_lux": round(cfg["lighting_lux"] + random.uniform(-2.0, 2.0), 1),
            "ambient_noise_db": round(cfg["ambient_noise_db"] + random.uniform(-1.5, 1.5), 1),
            "floor_moisture_detected": cfg["floor_moisture"],
            "motion_activity": cfg["motion_activity"],
            "environment_label": cfg["environment_label"]
        }


def main():
    parser = argparse.ArgumentParser(description="Aegis CARE - Environmental Room State Simulator")
    parser.add_argument(
        "--preset",
        type=str,
        default="bathroom_hazard_wet",
        choices=list(EnvironmentSimulator.PRESETS.keys()),
        help="Select preset scenario"
    )
    parser.add_argument(
        "--room",
        type=str,
        default=None,
        help="Override room location"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Continuously stream telemetry every N seconds"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Streaming interval in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--post-url",
        type=str,
        default=None,
        help="Target HTTP endpoint to transmit telemetry"
    )

    args = parser.parse_args()

    if args.continuous:
        print(f"Starting continuous environmental simulation ({args.preset}) every {args.interval}s...")
        try:
            while True:
                data = EnvironmentSimulator.generate(preset=args.preset, room_override=args.room)
                print(json.dumps(data, indent=2))
                if args.post_url and requests:
                    try:
                        requests.post(args.post_url, json=data, timeout=1.5)
                    except Exception as e:
                        print(f"POST error: {e}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nEnvironmental stream stopped.")
    else:
        data = EnvironmentSimulator.generate(preset=args.preset, room_override=args.room)
        print(json.dumps(data, indent=2))
        if args.post_url and requests:
            try:
                resp = requests.post(args.post_url, json=data, timeout=2.0)
                print(f"Server response [{resp.status_code}]")
            except Exception as e:
                print(f"POST error: {e}")


if __name__ == "__main__":
    main()
