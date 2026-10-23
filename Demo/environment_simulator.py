"""
Environmental Sensor & Ambient Room State Simulator.
Amazon Developer Hackathon 2026.

Simulates ambient room state across residence rooms:
  - Ambient lighting (lux)
  - Temperature (°C) & Relative Humidity (%)
  - Acoustic noise level (dB)
  - Floor moisture / wetness detection
  - Configurable noise, confidence, latency, water hazard override

Communicates via standard HTTP POST endpoints (/api/v1/events/ingest).
Does NOT modify database state or frontend state directly.
"""

import sys
import time
import json
import uuid
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
    """Simulates smart home ambient sensor arrays across residence zones."""

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
        "bathroom_normal": {
            "description": "Bathroom under normal dry conditions with vanity lighting on.",
            "location": "bathroom",
            "temperature_c": 22.0,
            "humidity_pct": 48.0,
            "lighting_lux": 350.0,
            "ambient_noise_db": 34.0,
            "floor_moisture": False,
            "motion_activity": "morning_routine",
            "environment_label": "well_lit"
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
        "bedroom_morning": {
            "description": "Bedroom in morning with natural sunlight streaming in.",
            "location": "bedroom",
            "temperature_c": 21.0,
            "humidity_pct": 45.0,
            "lighting_lux": 180.0,
            "ambient_noise_db": 32.0,
            "floor_moisture": False,
            "motion_activity": "waking",
            "environment_label": "well_lit"
        },
        "hallway_unlit": {
            "description": "Unlit corridor at night with low visibility.",
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

    def __init__(
        self,
        resident_id: str = "user_eleanor_vance",
        target_url: str = "http://localhost:8000/api/v1/events/ingest",
        noise_level: float = 0.03,
        confidence: float = 0.95,
        latency_sec: float = 0.0,
        confidence_score: Optional[float] = None
    ):
        self.resident_id = resident_id
        self.target_url = target_url
        self.noise_level = noise_level
        self.confidence = confidence_score if confidence_score is not None else confidence
        self.confidence_score = self.confidence
        self.latency_sec = latency_sec

    def generate_raw(
        self,
        preset: str = "bathroom_hazard_wet",
        room_override: Optional[str] = None,
        moisture_override: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Generates raw environmental reading dictionary with noise jitter."""
        cfg = self.PRESETS.get(preset, self.PRESETS["bathroom_hazard_wet"])
        loc = room_override or cfg["location"]
        now_iso = datetime.now(timezone.utc).isoformat()

        # Apply noise jitter
        temp_jitter = round(cfg["temperature_c"] + random.uniform(-0.5, 0.5) * self.noise_level * 10, 1)
        hum_jitter = round(min(100.0, max(0.0, cfg["humidity_pct"] + random.uniform(-2.0, 2.0) * self.noise_level * 10)), 1)
        lux_jitter = round(max(0.0, cfg["lighting_lux"] + random.uniform(-5.0, 5.0) * self.noise_level * 5), 1)
        moisture = moisture_override if moisture_override is not None else cfg["floor_moisture"]

        return {
            "telemetry_type": "environmental_telemetry",
            "location": loc,
            "room_id": loc,
            "timestamp": now_iso,
            "temperature_c": temp_jitter,
            "humidity_pct": hum_jitter,
            "lighting_lux": lux_jitter,
            "ambient_noise_db": cfg["ambient_noise_db"],
            "floor_moisture_detected": moisture,
            "environment_label": cfg["environment_label"],
            "motion_activity": cfg["motion_activity"],
            "sensor_array_id": f"env_hub_{loc}_01"
        }

    def generate_unified_event(
        self,
        preset: str = "bathroom_hazard_wet",
        room_override: Optional[str] = None,
        moisture_override: Optional[bool] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates a standardized NIRA UnifiedEvent payload."""
        raw = self.generate_raw(preset=preset, room_override=room_override, moisture_override=moisture_override)
        loc = raw["location"]
        event_id = f"evt-env-{uuid.uuid4().hex[:8]}"
        corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"

        return {
            "event_id": event_id,
            "timestamp": raw["timestamp"],
            "resident_id": self.resident_id,
            "room_id": loc,
            "source": "environmental",
            "event_type": "environmental_conditions",
            "payload": raw,
            "confidence": self.confidence,
            "correlation_id": corr_id
        }

    def emit_event(
        self,
        preset: str = "bathroom_hazard_wet",
        room_override: Optional[str] = None,
        moisture_override: Optional[bool] = None,
        correlation_id: Optional[str] = None,
        target_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Emits event via genuine HTTP POST to backend."""
        url = target_url or self.target_url
        payload = self.generate_unified_event(
            preset=preset,
            room_override=room_override,
            moisture_override=moisture_override,
            correlation_id=correlation_id
        )

        if self.latency_sec > 0:
            time.sleep(self.latency_sec)

        if not requests:
            print(f"[EnvironmentSimulator] requests not available; dry-run output:\n{json.dumps(payload, indent=2)}")
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
        """Stream continuous environmental telemetry events."""
        active_preset = preset or "living_room_normal"
        interval = 1.0 / max(0.01, frequency_hz)
        emitted = 0
        print(f"[EnvironmentSimulator] Starting continuous streaming ({active_preset}) at {frequency_hz}Hz...")
        try:
            while count is None or emitted < count:
                res = self.emit_event(preset=active_preset, **kwargs)
                emitted += 1
                if res and "sent_event" in res:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Emitted Environment #{emitted}: Status={res.get('status_code')}")
                if count is not None and emitted >= count:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[EnvironmentSimulator] Stream stopped.")

    # Backward compatibility classmethods
    @classmethod
    def generate(
        cls,
        preset: str = "bathroom_hazard_wet",
        room_override: Optional[str] = None
    ) -> Dict[str, Any]:
        sim = cls()
        return sim.generate_raw(preset=preset, room_override=room_override)

    @classmethod
    def generate_unified_event_legacy(
        cls,
        preset: str = "bathroom_hazard_wet",
        resident_id: str = "user_eleanor_vance",
        room_override: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        sim = cls(resident_id=resident_id)
        return sim.generate_unified_event(
            preset=preset,
            room_override=room_override,
            correlation_id=correlation_id
        )


# Backward compatibility alias
EnvironmentDeviceSimulator = EnvironmentSimulator


def main():
    parser = argparse.ArgumentParser(description="NIRA - Genuine Environmental Sensor Producer")
    parser.add_argument(
        "--preset",
        type=str,
        default="bathroom_hazard_wet",
        choices=list(EnvironmentSimulator.PRESETS.keys()),
        help="Select environmental preset"
    )
    parser.add_argument("--room", type=str, default=None, help="Override room location")
    parser.add_argument("--wet-floor", action="store_true", help="Force floor moisture sensor True")
    parser.add_argument("--noise", type=float, default=0.03, help="Sensor noise jitter factor")
    parser.add_argument("--confidence", type=float, default=0.95, help="Sensor confidence rating")
    parser.add_argument("--latency", type=float, default=0.0, help="Simulated network latency in seconds")
    parser.add_argument("--continuous", action="store_true", help="Continuously emit telemetry")
    parser.add_argument("--interval", type=float, default=3.0, help="Interval between events (seconds)")
    parser.add_argument(
        "--post-url",
        type=str,
        default="http://localhost:8000/api/v1/events/ingest",
        help="Target backend HTTP endpoint"
    )

    args = parser.parse_args()
    sim = EnvironmentSimulator(
        target_url=args.post_url,
        noise_level=args.noise,
        confidence=args.confidence,
        latency_sec=args.latency
    )

    moisture_arg = True if args.wet_floor else None

    if args.continuous:
        print(f"[EnvironmentSimulator] Starting continuous streaming ({args.preset}) to {args.post_url} every {args.interval}s...")
        try:
            while True:
                res = sim.emit_event(preset=args.preset, room_override=args.room, moisture_override=moisture_arg)
                if res and "response" in res:
                    pl = res["sent_event"]["payload"]
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Room: {pl['location']} | Lux: {pl['lighting_lux']} | Wet: {pl['floor_moisture_detected']} | State: {res['response'].get('safety_state')}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[EnvironmentSimulator] Stream stopped.")
    else:
        res = sim.emit_event(preset=args.preset, room_override=args.room, moisture_override=moisture_arg)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
