"""
Edge AI Vision & Pose Camera Simulator for NIRA.
Amazon Developer Hackathon 2026.

Simulates edge computer vision and YOLOv8 biomechanical keypoint analysis:
  - Keypoint torso angle (vertical upright ~90°, fallen horizontal <30°)
  - Bounding box aspect ratio (height-to-width transition)
  - Downward vertical velocity norm
  - Post-event movement classification (none, slight_twitch, crawling, normal)
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


class VisionSimulator:
    """Simulates edge computer vision keypoint posture analysis."""

    PRESETS: Dict[str, Dict[str, Any]] = {
        "upright_standing": {
            "description": "Senior standing upright; keypoints vertical.",
            "event_type": "camera_activity",
            "confidence": 0.96,
            "torso_angle": 88.0,
            "aspect_ratio": 0.42,
            "downward_velocity": 0.05,
            "movement_after_event": "normal",
            "fall_confirmed": False
        },
        "upright_walking": {
            "description": "Senior walking across camera field of view.",
            "event_type": "camera_activity",
            "confidence": 0.94,
            "torso_angle": 85.0,
            "aspect_ratio": 0.45,
            "downward_velocity": 0.12,
            "movement_after_event": "normal",
            "fall_confirmed": False
        },
        "fall_impact_immobile": {
            "description": "Sudden fall onto floor followed by zero movement.",
            "event_type": "possible_fall",
            "confidence": 0.96,
            "torso_angle": 12.0,
            "aspect_ratio": 2.30,
            "downward_velocity": 0.92,
            "movement_after_event": "none",
            "fall_confirmed": True
        },
        "fall_impact_crawling": {
            "description": "Senior on floor attempting to crawl or drag self.",
            "event_type": "possible_fall",
            "confidence": 0.89,
            "torso_angle": 22.0,
            "aspect_ratio": 1.85,
            "downward_velocity": 0.80,
            "movement_after_event": "crawling",
            "fall_confirmed": True
        },
        "fall_impact_twitch": {
            "description": "Senior on floor with slight twitching / minor limb movements.",
            "event_type": "possible_fall",
            "confidence": 0.91,
            "torso_angle": 15.0,
            "aspect_ratio": 2.10,
            "downward_velocity": 0.85,
            "movement_after_event": "slight_twitch",
            "fall_confirmed": True
        },
        "minor_stumble": {
            "description": "Transient loss of balance / trip, but senior caught balance.",
            "event_type": "minor_stumble",
            "confidence": 0.65,
            "torso_angle": 60.0,
            "aspect_ratio": 0.70,
            "downward_velocity": 0.45,
            "movement_after_event": "normal",
            "fall_confirmed": False
        },
        "posture_recovered_upright": {
            "description": "Resident was on floor, now stood back up with upright posture restored.",
            "event_type": "posture_recovered",
            "confidence": 0.94,
            "torso_angle": 86.0,
            "aspect_ratio": 0.44,
            "downward_velocity": 0.0,
            "movement_after_event": "normal",
            "fall_confirmed": False
        }
    }

    def __init__(
        self,
        resident_id: str = "user_eleanor_vance",
        target_url: str = "http://localhost:8000/api/v1/events/ingest",
        noise_level: float = 0.02,
        confidence_override: Optional[float] = None,
        latency_sec: float = 0.0,
        confidence_score: Optional[float] = None
    ):
        self.resident_id = resident_id
        self.target_url = target_url
        self.noise_level = noise_level
        self.confidence_override = confidence_score if confidence_score is not None else confidence_override
        self.confidence_score = self.confidence_override
        self.latency_sec = latency_sec

    def generate_raw(
        self,
        preset: str = "upright_standing",
        room_id: str = "living_room"
    ) -> Dict[str, Any]:
        """Generates raw vision inference dictionary with noise jitter."""
        cfg = self.PRESETS.get(preset, self.PRESETS["upright_standing"])
        now_iso = datetime.now(timezone.utc).isoformat()

        # Angle jitter
        angle_jitter = round(max(0.0, min(90.0, cfg["torso_angle"] + random.uniform(-2.0, 2.0) * self.noise_level * 10)), 1)
        conf = self.confidence_override if self.confidence_override is not None else cfg["confidence"]

        return {
            "telemetry_type": "vision_pose_telemetry",
            "camera_id": f"cam_edge_{room_id}_01",
            "timestamp": now_iso,
            "room_id": room_id,
            "fall_confirmed": cfg["fall_confirmed"],
            "movement_after_event": cfg["movement_after_event"],
            "torso_angle_deg": angle_jitter,
            "aspect_ratio": cfg["aspect_ratio"],
            "downward_velocity_norm": cfg["downward_velocity"],
            "keypoint_confidence": round(conf - random.uniform(0.0, 0.03), 2),
            "model_version": "YOLOv8n-pose-opt-2026"
        }

    def generate_unified_event(
        self,
        preset: str = "upright_standing",
        room_id: str = "living_room",
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates a standardized NIRA UnifiedEvent payload."""
        cfg = self.PRESETS.get(preset, self.PRESETS["upright_standing"])
        raw = self.generate_raw(preset=preset, room_id=room_id)
        event_id = f"evt-vis-{uuid.uuid4().hex[:8]}"
        corr_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
        conf = self.confidence_override if self.confidence_override is not None else cfg["confidence"]

        return {
            "event_id": event_id,
            "timestamp": raw["timestamp"],
            "resident_id": self.resident_id,
            "room_id": room_id,
            "source": "camera_pose",
            "event_type": cfg["event_type"],
            "payload": raw,
            "confidence": conf,
            "correlation_id": corr_id
        }

    def emit_event(
        self,
        preset: str = "upright_standing",
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
            print(f"[VisionSimulator] requests not available; dry-run output:\n{json.dumps(payload, indent=2)}")
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
        """Stream continuous edge vision telemetry events."""
        active_preset = preset or "upright_standing"
        interval = 1.0 / max(0.01, frequency_hz)
        emitted = 0
        print(f"[VisionSimulator] Starting continuous streaming ({active_preset}) at {frequency_hz}Hz...")
        try:
            while count is None or emitted < count:
                res = self.emit_event(preset=active_preset, **kwargs)
                emitted += 1
                if res and "sent_event" in res:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Emitted Vision #{emitted}: Status={res.get('status_code')}")
                if count is not None and emitted >= count:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[VisionSimulator] Stream stopped.")


VisionDeviceSimulator = VisionSimulator


def main():
    parser = argparse.ArgumentParser(description="NIRA - Genuine Edge AI Vision & Fall Pose Producer")
    parser.add_argument(
        "--preset",
        type=str,
        default="upright_standing",
        choices=list(VisionSimulator.PRESETS.keys()),
        help="Select vision pose preset"
    )
    parser.add_argument("--room", type=str, default="living_room", help="Room location")
    parser.add_argument("--confidence", type=float, default=None, help="Override detection confidence rating")
    parser.add_argument("--noise", type=float, default=0.02, help="Noise factor")
    parser.add_argument("--latency", type=float, default=0.0, help="Simulated latency in seconds")
    parser.add_argument("--continuous", action="store_true", help="Continuously stream vision inferences")
    parser.add_argument("--interval", type=float, default=2.0, help="Interval between frames in seconds")
    parser.add_argument(
        "--post-url",
        type=str,
        default="http://localhost:8000/api/v1/events/ingest",
        help="Target backend HTTP endpoint"
    )

    args = parser.parse_args()
    sim = VisionSimulator(
        target_url=args.post_url,
        confidence_override=args.confidence,
        noise_level=args.noise,
        latency_sec=args.latency
    )

    if args.continuous:
        print(f"[VisionSimulator] Starting continuous streaming ({args.preset}) in {args.room} to {args.post_url}...")
        try:
            while True:
                res = sim.emit_event(preset=args.preset, room_id=args.room)
                if res and "response" in res:
                    pl = res["sent_event"]["payload"]
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Event: {res['sent_event']['event_type']} | Angle: {pl['torso_angle_deg']}° | Mov: {pl['movement_after_event']} | State: {res['response'].get('safety_state')}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[VisionSimulator] Stream stopped.")
    else:
        res = sim.emit_event(preset=args.preset, room_id=args.room)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
