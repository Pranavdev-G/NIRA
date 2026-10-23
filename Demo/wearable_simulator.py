"""
Wearable Telemetry Simulator for NIRA Ambient Safety System.
Amazon Developer Hackathon 2026.

Simulates biometric and inertial signals from smartwatches or medical wearables:
  - Heart rate (BPM) & arrhythmia detection
  - Movement / Immobility index
  - Wearable operational status (worn_normal, high_heart_rate, etc.)
  - Step cadence and battery telemetry
  - Configurable noise, confidence, latency, disconnect/reconnect

Communicates via standard HTTP POST endpoints (/api/v1/events/ingest).
Does NOT modify database state or frontend state directly.
"""

import sys
import time
import json
import uuid
import random
import argparse
import logging
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

logger = logging.getLogger("NIRA.WearableSimulator")


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
        "recovery_movement": {
            "description": "Post-fall recovery; senior movement index increasing and heart rate stabilizing.",
            "heart_rate_range": (88, 98),
            "movement_index": 0.65,
            "wearable_status": "worn_normal",
            "arrhythmia": False,
            "cadence_spm": 45
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

    def __init__(
        self,
        resident_id: str = "user_eleanor_vance",
        device_id: str = "watch_apple_series_9_eleanor",
        target_url: str = "http://localhost:8000/api/v1/events/ingest",
        noise_level: float = 0.02,
        confidence: float = 0.98,
        latency_sec: float = 0.0,
        confidence_score: Optional[float] = None
    ):
        self.resident_id = resident_id
        self.device_id = device_id
        self.target_url = target_url
        self.noise_level = noise_level
        self.confidence = confidence_score if confidence_score is not None else confidence
        self.confidence_score = self.confidence
        self.latency_sec = latency_sec
        self.is_connected: bool = True
        self.battery_percentage = 94

    def disconnect(self):
        """Simulates watch taken off or dropped connection."""
        self.is_connected = False

    def reconnect(self):
        """Simulates watch put back on wrist."""
        self.is_connected = True
        self.battery_percentage = max(self.battery_percentage, 85)

    def generate_raw(
        self,
        preset: str = "normal_resting",
        hr_override: Optional[int] = None,
        movement_override: Optional[float] = None,
        noise: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generates raw device telemetry payload with configurable noise."""
        if not self.is_connected:
            preset = "disconnected"

        cfg = self.PRESETS.get(preset, self.PRESETS["normal_resting"])
        now_iso = datetime.now(timezone.utc).isoformat()
        eff_noise = noise if noise is not None else self.noise_level

        if hr_override is not None:
            hr = hr_override
        elif cfg["heart_rate_range"] == (0, 0):
            hr = 0
        else:
            base_hr = random.randint(*cfg["heart_rate_range"])
            noise_delta = int(base_hr * eff_noise * random.uniform(-1.0, 1.0))
            hr = max(30, min(220, base_hr + noise_delta))

        # Movement index jitter
        if movement_override is not None:
            mov_jitter = round(max(0.0, min(1.0, movement_override)), 2)
        elif cfg["movement_index"] == 0.0:
            mov_jitter = 0.0
        else:
            base_mov = cfg["movement_index"]
            mov_jitter = round(max(0.0, min(1.0, base_mov + random.uniform(-eff_noise, eff_noise))), 2)

        return {
            "telemetry_type": "wearable_vitals",
            "user_id": self.resident_id,
            "device_id": self.device_id,
            "timestamp": now_iso,
            "heart_rate_bpm": hr,
            "movement_index": mov_jitter,
            "wearable_status": cfg["wearable_status"],
            "arrhythmia_detected": cfg["arrhythmia"],
            "step_cadence_spm": cfg["cadence_spm"],
            "battery_percentage": self.battery_percentage,
            "skin_contact": self.is_connected and (cfg["wearable_status"] != "disconnected")
        }

    def generate_unified_event(
        self,
        preset: str = "normal_resting",
        room_id: str = "living_room",
        hr_override: Optional[int] = None,
        movement_override: Optional[float] = None,
        correlation_id: Optional[str] = None,
        confidence_override: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generates a standardized NIRA UnifiedEvent payload."""
        raw = self.generate_raw(preset=preset, hr_override=hr_override, movement_override=movement_override)
        event_id = f"evt-wear-{uuid.uuid4().hex[:8]}"
        corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
        conf = confidence_override if confidence_override is not None else self.confidence

        return {
            "event_id": event_id,
            "timestamp": raw["timestamp"],
            "resident_id": self.resident_id,
            "room_id": room_id,
            "source": "wearable",
            "event_type": "wearable_telemetry",
            "payload": raw,
            "confidence": conf,
            "correlation_id": corr_id
        }

    def emit_event(
        self,
        preset: str = "normal_resting",
        room_id: str = "living_room",
        hr_override: Optional[int] = None,
        correlation_id: Optional[str] = None,
        target_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Emits event via genuine HTTP POST to backend."""
        url = target_url or self.target_url
        payload = self.generate_unified_event(
            preset=preset,
            room_id=room_id,
            hr_override=hr_override,
            correlation_id=correlation_id
        )

        if self.latency_sec > 0:
            time.sleep(self.latency_sec)

        if not requests:
            print(f"[WearableSimulator] requests library not available; dry-run output:\n{json.dumps(payload, indent=2)}")
            return payload

        try:
            t0 = time.perf_counter()
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=4.0)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            resp_json = resp.json() if resp.status_code == 200 else {"status": f"HTTP_{resp.status_code}", "text": resp.text}
            return {
                "sent_event": payload,
                "response": resp_json,
                "status_code": resp.status_code,
                "latency_ms": round(elapsed_ms, 2)
            }
        except Exception as e:
            return {"error": str(e), "sent_event": payload}

    def start_continuous_stream(
        self,
        preset: Optional[str] = None,
        frequency_hz: float = 1.0,
        count: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        """Stream continuous wearable telemetry events."""
        active_preset = preset or "normal_resting"
        interval = 1.0 / max(0.01, frequency_hz)
        emitted = 0
        print(f"[WearableSimulator] Starting continuous streaming ({active_preset}) at {frequency_hz}Hz...")
        try:
            while count is None or emitted < count:
                res = self.emit_event(preset=active_preset, **kwargs)
                emitted += 1
                if res and "sent_event" in res:
                    hr = res["sent_event"].get("payload", {}).get("heart_rate_bpm", "N/A")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Emitted Wearable #{emitted}: HR={hr}bpm Status={res.get('status_code')}")
                if count is not None and emitted >= count:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[WearableSimulator] Stream stopped.")

    # Backward compatibility classmethods
    @classmethod
    def generate(
        cls,
        preset: str = "normal_resting",
        user_id: str = "user_eleanor_vance",
        hr_override: Optional[int] = None
    ) -> Dict[str, Any]:
        sim = cls(resident_id=user_id)
        return sim.generate_raw(preset=preset, hr_override=hr_override)

    @classmethod
    def generate_unified_event_legacy(
        cls,
        preset: str = "normal_resting",
        user_id: str = "user_eleanor_vance",
        room_id: str = "living_room",
        hr_override: Optional[int] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        sim = cls(resident_id=user_id)
        return sim.generate_unified_event(
            preset=preset,
            room_id=room_id,
            hr_override=hr_override,
            correlation_id=correlation_id
        )


# Backward compatibility alias
WearableDeviceSimulator = WearableSimulator


def main():
    parser = argparse.ArgumentParser(description="NIRA - Genuine Wearable Biometric Telemetry Producer")
    parser.add_argument(
        "--preset",
        type=str,
        default="normal_resting",
        choices=list(WearableSimulator.PRESETS.keys()),
        help="Select telemetry preset"
    )
    parser.add_argument("--room", type=str, default="living_room", help="Resident room location")
    parser.add_argument("--noise", type=float, default=0.02, help="Noise jitter factor (0.0 to 0.2)")
    parser.add_argument("--confidence", type=float, default=0.98, help="Sensor confidence rating")
    parser.add_argument("--latency", type=float, default=0.0, help="Simulated network latency in seconds")
    parser.add_argument("--continuous", action="store_true", help="Continuously emit telemetry")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval between events (seconds)")
    parser.add_argument("--disconnect", action="store_true", help="Simulate disconnected state")
    parser.add_argument(
        "--post-url",
        type=str,
        default="http://localhost:8000/api/v1/events/ingest",
        help="Target backend HTTP endpoint"
    )

    args = parser.parse_args()
    sim = WearableSimulator(
        target_url=args.post_url,
        noise_level=args.noise,
        confidence=args.confidence,
        latency_sec=args.latency
    )
    if args.disconnect:
        sim.disconnect()

    if args.continuous:
        print(f"[WearableSimulator] Starting continuous streaming ({args.preset}) to {args.post_url} every {args.interval}s...")
        try:
            while True:
                res = sim.emit_event(preset=args.preset, room_id=args.room)
                if res and "response" in res:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] HR: {res['sent_event']['payload']['heart_rate_bpm']} bpm | Status: {res['status_code']} | State: {res['response'].get('safety_state')}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[WearableSimulator] Stream stopped.")
    else:
        res = sim.emit_event(preset=args.preset, room_id=args.room)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
