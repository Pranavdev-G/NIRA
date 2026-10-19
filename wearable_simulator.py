"""
Wearable Telemetry Simulator for Aegis Ambient Care.
Amazon Developer Hackathon 2026.

Simulates biometric and inertial signals from smartwatches or medical wearables:
  - Heart rate (BPM) & arrhythmia detection
  - Movement / Immobility index
  - Wearable operational status (worn_normal, high_heart_rate, etc.)
  - Step cadence and battery telemetry
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


class WearableSimulator:
    """Generates continuous or episodic wearable biometric telemetry."""

    PRESETS: Dict[str, Dict[str, Any]] = {
        "normal_resting": {
            "description": "Senior resting calmly; vitals completely normal.",
            "heart_rate_range": (68, 76),
            "movement_index": 0.05,
            "wearable_status": "worn_normal",
            "arrhythmia": False,
            "cadence_spm": 0
        },
        "walking_normal": {
            "description": "Senior walking around residence.",
            "heart_rate_range": (82, 94),
            "movement_index": 0.70,
            "wearable_status": "worn_normal",
            "arrhythmia": False,
            "cadence_spm": 92
        },
        "tachycardia_fall_impact": {
            "description": "Acute sympathetic surge / tachycardia following fall trauma; zero motion.",
            "heart_rate_range": (132, 148),
            "movement_index": 0.0,
            "wearable_status": "high_heart_rate",
            "arrhythmia": False,
            "cadence_spm": 0
        },
        "cardiac_arrhythmia": {
            "description": "Irregular rhythm flagged by photoplethysmography (PPG) sensor.",
            "heart_rate_range": (110, 126),
            "movement_index": 0.12,
            "wearable_status": "arrhythmia_flag",
            "arrhythmia": True,
            "cadence_spm": 0
        },
        "bradycardia": {
            "description": "Abnormally low heart rate.",
            "heart_rate_range": (44, 48),
            "movement_index": 0.0,
            "wearable_status": "low_heart_rate",
            "arrhythmia": False,
            "cadence_spm": 0
        },
        "disconnected": {
            "description": "Device taken off wrist or battery depleted.",
            "heart_rate_range": (0, 0),
            "movement_index": 0.0,
            "wearable_status": "disconnected",
            "arrhythmia": False,
            "cadence_spm": 0
        }
    }

    @classmethod
    def generate(
        cls,
        preset: str = "normal_resting",
        user_id: str = "user_eleanor_vance",
        hr_override: Optional[int] = None
    ) -> Dict[str, Any]:
        cfg = cls.PRESETS.get(preset, cls.PRESETS["normal_resting"])
        now_iso = datetime.now(timezone.utc).isoformat()

        if hr_override is not None:
            hr = hr_override
        elif cfg["heart_rate_range"] == (0, 0):
            hr = 0
        else:
            hr = random.randint(*cfg["heart_rate_range"])

        return {
            "telemetry_type": "wearable_vitals",
            "user_id": user_id,
            "device_id": "watch_apple_series_9_eleanor",
            "timestamp": now_iso,
            "heart_rate_bpm": hr,
            "movement_index": cfg["movement_index"],
            "wearable_status": cfg["wearable_status"],
            "arrhythmia_detected": cfg["arrhythmia"],
            "step_cadence_spm": cfg["cadence_spm"],
            "battery_percentage": random.randint(75, 98),
            "skin_contact": cfg["wearable_status"] != "disconnected"
        }


def main():
    parser = argparse.ArgumentParser(description="Aegis CARE - Wearable Biometric Telemetry Simulator")
    parser.add_argument(
        "--preset",
        type=str,
        default="tachycardia_fall_impact",
        choices=list(WearableSimulator.PRESETS.keys()),
        help="Select preset scenario"
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
        print(f"Starting continuous wearable simulation ({args.preset}) every {args.interval}s...")
        try:
            while True:
                data = WearableSimulator.generate(preset=args.preset)
                print(json.dumps(data, indent=2))
                if args.post_url and requests:
                    try:
                        requests.post(args.post_url, json=data, timeout=1.5)
                    except Exception as e:
                        print(f"POST error: {e}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nWearable stream stopped.")
    else:
        data = WearableSimulator.generate(preset=args.preset)
        print(json.dumps(data, indent=2))
        if args.post_url and requests:
            try:
                resp = requests.post(args.post_url, json=data, timeout=2.0)
                print(f"Server response [{resp.status_code}]")
            except Exception as e:
                print(f"POST error: {e}")


if __name__ == "__main__":
    main()
