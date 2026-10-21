"""
mmWave Radar Sensor Telemetry Simulator for NIRA.
Amazon Developer Hackathon 2026.

Simulates privacy-preserving wall/ceiling mmWave radar hardware:
  - Presence detection & room occupancy count
  - Micro-motion (respiration rate / vital chest displacement)
  - Macro-motion level (0.0 to 1.0)
  - Biomechanical posture classification (standing, seated, lying_bed, floor_collapse, rising)
  - Room zone tracking (center, couch, bed, floor)
  - Configurable noise, confidence, latency, and streaming

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


class RadarSimulator:
    """Simulates 60GHz FMCW radar point-cloud and target-tracking algorithms."""

    PRESETS: Dict[str, Dict[str, Any]] = {
        "upright_walking": {
            "description": "Resident walking through room; normal upright posture.",
            "presence": True,
            "occupancy_count": 1,
            "motion_level": 0.75,
            "posture": "standing",
            "zone": "center",
            "velocity_mps": 0.95,
            "respiration_bpm": 16.0,
            "event_type": "radar_presence"
        },
        "seated_relaxing": {
            "description": "Resident seated in armchair or sofa.",
            "presence": True,
            "occupancy_count": 1,
            "motion_level": 0.15,
            "posture": "seated",
            "zone": "couch",
            "velocity_mps": 0.0,
            "respiration_bpm": 15.0,
            "event_type": "radar_presence"
        },
        "bed_sleeping": {
            "description": "Resident lying in bed; subtle rhythmic chest motion.",
            "presence": True,
            "occupancy_count": 1,
            "motion_level": 0.05,
            "posture": "lying_bed",
            "zone": "bed",
            "velocity_mps": 0.0,
            "respiration_bpm": 14.0,
            "event_type": "radar_presence"
        },
        "floor_collapse_immobile": {
            "description": "Radar target abruptly dropped below 0.3m height plane; zero motion on floor.",
            "presence": True,
            "occupancy_count": 1,
            "motion_level": 0.0,
            "posture": "floor_collapse",
            "zone": "floor",
            "velocity_mps": 0.0,
            "respiration_bpm": 22.0,
            "event_type": "radar_fall_detected"
        },
        "recovery_rising": {
            "description": "Target centroid elevating from floor level back to standing height.",
            "presence": True,
            "occupancy_count": 1,
            "motion_level": 0.65,
            "posture": "rising",
            "zone": "floor_to_standing",
            "velocity_mps": 0.40,
            "respiration_bpm": 18.0,
            "event_type": "radar_presence"
        },
        "empty_room": {
            "description": "No human targets in field of view.",
            "presence": False,
            "occupancy_count": 0,
            "motion_level": 0.0,
            "posture": "none",
            "zone": "none",
            "velocity_mps": 0.0,
            "respiration_bpm": 0.0,
            "event_type": "radar_presence"
        }
    }

    def __init__(
        self,
        resident_id: str = "user_eleanor_vance",
        target_url: str = "http://localhost:8000/api/v1/events/ingest",
        noise_level: float = 0.02,
        confidence: float = 0.92,
        latency_sec: float = 0.0
    ):
        self.resident_id = resident_id
        self.target_url = target_url
        self.noise_level = noise_level
        self.confidence = confidence
        self.latency_sec = latency_sec

    def generate_raw(
        self,
        preset: str = "upright_walking",
        room_id: str = "living_room"
    ) -> Dict[str, Any]:
        """Generates raw radar telemetry dict with noise jitter."""
        cfg = self.PRESETS.get(preset, self.PRESETS["upright_walking"])
        now_iso = datetime.now(timezone.utc).isoformat()

        # Motion jitter
        base_motion = cfg["motion_level"]
        if base_motion == 0.0:
            motion_jitter = 0.0
        else:
            motion_jitter = round(max(0.0, min(1.0, base_motion + random.uniform(-self.noise_level, self.noise_level))), 2)

        return {
            "telemetry_type": "radar_target_telemetry",
            "device_id": f"radar_ti_iwr6843_{room_id}_01",
            "timestamp": now_iso,
            "room_id": room_id,
            "presence": cfg["presence"],
            "occupancy_count": cfg["occupancy_count"],
            "motion_level": motion_jitter,
            "posture": cfg["posture"],
            "zone": cfg["zone"],
            "velocity_mps": cfg["velocity_mps"],
            "respiration_rate_bpm": cfg["respiration_bpm"],
            "point_cloud_targets": 1 if cfg["presence"] else 0,
            "rf_snr_db": round(18.5 + random.uniform(-1.0, 1.0), 1)
        }

    def generate_unified_event(
        self,
        preset: str = "upright_walking",
        room_id: str = "living_room",
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates a standardized NIRA UnifiedEvent payload."""
        cfg = self.PRESETS.get(preset, self.PRESETS["upright_walking"])
        raw = self.generate_raw(preset=preset, room_id=room_id)
        event_id = f"evt-radar-{uuid.uuid4().hex[:8]}"
        corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"

        return {
            "event_id": event_id,
            "timestamp": raw["timestamp"],
            "resident_id": self.resident_id,
            "room_id": room_id,
            "source": "radar",
            "event_type": cfg["event_type"],
            "payload": raw,
            "confidence": self.confidence,
            "correlation_id": corr_id
        }

    def emit_event(
        self,
        preset: str = "upright_walking",
        room_id: str = "living_room",
        correlation_id: Optional[str] = None,
        target_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Emits event via genuine HTTP POST to backend."""
        url = target_url or self.target_url
        payload = self.generate_unified_event(
            preset=preset,
            room_id=room_id,
            correlation_id=correlation_id
        )

        if self.latency_sec > 0:
            time.sleep(self.latency_sec)

        if not requests:
            print(f"[RadarSimulator] requests not available; dry-run output:\n{json.dumps(payload, indent=2)}")
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


RadarDeviceSimulator = RadarSimulator


def main():
    parser = argparse.ArgumentParser(description="NIRA - Genuine mmWave Radar Sensor Producer")
    parser.add_argument(
        "--preset",
        type=str,
        default="upright_walking",
        choices=list(RadarSimulator.PRESETS.keys()),
        help="Select radar preset"
    )
    parser.add_argument("--room", type=str, default="living_room", help="Room location")
    parser.add_argument("--noise", type=float, default=0.02, help="Radar noise jitter factor")
    parser.add_argument("--confidence", type=float, default=0.92, help="Radar confidence rating")
    parser.add_argument("--latency", type=float, default=0.0, help="Simulated network latency in seconds")
    parser.add_argument("--continuous", action="store_true", help="Continuously stream radar readings")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval between readings in seconds")
    parser.add_argument(
        "--post-url",
        type=str,
        default="http://localhost:8000/api/v1/events/ingest",
        help="Target backend HTTP endpoint"
    )

    args = parser.parse_args()
    sim = RadarSimulator(
        target_url=args.post_url,
        noise_level=args.noise,
        confidence=args.confidence,
        latency_sec=args.latency
    )

    if args.continuous:
        print(f"[RadarSimulator] Starting continuous streaming ({args.preset}) in {args.room} to {args.post_url}...")
        try:
            while True:
                res = sim.emit_event(preset=args.preset, room_id=args.room)
                if res and "response" in res:
                    pl = res["sent_event"]["payload"]
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Posture: {pl['posture']} | Motion: {pl['motion_level']} | Zone: {pl['zone']} | State: {res['response'].get('safety_state')}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[RadarSimulator] Stream stopped.")
    else:
        res = sim.emit_event(preset=args.preset, room_id=args.room)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
