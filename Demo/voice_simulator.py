"""
Alexa Smart Home Voice Interaction Simulator for NIRA.
Amazon Developer Hackathon 2026.

Simulates two-way conversational wellness checks:
  - Safe verbal confirmations ("I'm okay")
  - Distress calls for assistance ("Help me")
  - Severe physical incapacitation ("I cannot move")
  - Ambiguous verbal responses ("Uh, I don't know...")
  - Complete silence / timeout windows (is_timeout=True)
  - Recovery verbal confirmations ("I got back up")

Communicates via standard HTTP POST endpoints:
  - /api/v1/events/ingest (as UnifiedEvent)
  - /api/v1/incidents/{incident_id}/respond-voice (for conversational state machine)
Does NOT modify database state or frontend state directly.
"""

import sys
import time
import json
import uuid
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


class VoiceSimulator:
    """Simulates Alexa voice assistant resident conversational telemetry."""

    PRESETS: Dict[str, Dict[str, Any]] = {
        "safe_verbal_confirmation": {
            "description": "Resident verbally confirms they are okay.",
            "transcript": "I'm okay, false alarm, just dropped my book.",
            "is_timeout": False,
            "intent": "safe",
            "confidence": 0.98
        },
        "distress_help": {
            "description": "Resident verbally calls for help.",
            "transcript": "Help me, I fell down and my hip hurts!",
            "is_timeout": False,
            "intent": "distress",
            "confidence": 0.97
        },
        "severe_immobility": {
            "description": "Resident reports severe incapacitation and inability to move.",
            "transcript": "I cannot move, my hip is broken and I can't move at all!",
            "is_timeout": False,
            "intent": "severe_immobility",
            "confidence": 0.99
        },
        "ambiguous_reply": {
            "description": "Resident responds with confusion or mumbling.",
            "transcript": "Uh... what... I don't know what is happening...",
            "is_timeout": False,
            "intent": "ambiguous",
            "confidence": 0.70
        },
        "prompt_timeout": {
            "description": "20 seconds of complete silence following prompt.",
            "transcript": None,
            "is_timeout": True,
            "intent": "timeout",
            "confidence": 1.0
        },
        "recovery_confirmation": {
            "description": "Resident confirms recovery after standing back up.",
            "transcript": "I managed to get back up, I'm okay now.",
            "is_timeout": False,
            "intent": "safe",
            "confidence": 0.96
        },
        "negation": {
            "description": "Resident explicitly states negation: 'I'm not okay.'",
            "transcript": "I'm not okay.",
            "is_timeout": False,
            "intent": "distress",
            "confidence": 0.98
        },
        "risk_unwell": {
            "description": "Resident reports risk symptom: 'I don't feel well.'",
            "transcript": "I don't feel well, I feel dizzy.",
            "is_timeout": False,
            "intent": "distress",
            "confidence": 0.92
        },
        "uncertainty": {
            "description": "Resident responds with uncertainty: 'I don't know.'",
            "transcript": "I don't know...",
            "is_timeout": False,
            "intent": "ambiguous",
            "confidence": 0.75
        }
    }

    def __init__(
        self,
        resident_id: str = "user_eleanor_vance",
        base_url: str = "http://localhost:8000",
        latency_sec: float = 0.0
    ):
        self.resident_id = resident_id
        self.base_url = base_url.rstrip("/")
        self.latency_sec = latency_sec

    def generate_unified_event(
        self,
        preset: str = "safe_verbal_confirmation",
        room_id: str = "living_room",
        transcript_override: Optional[str] = None,
        is_timeout_override: Optional[bool] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates a standardized NIRA UnifiedEvent payload for voice responses."""
        aliases = {
            "safe": "safe_verbal_confirmation",
            "risk": "risk_unwell",
            "emergency": "distress_help",
            "help": "distress_help",
            "uncertain": "uncertainty",
            "silence": "prompt_timeout",
            "timeout": "prompt_timeout",
            "negation": "negation"
        }
        normalized_preset = aliases.get(preset.lower(), preset)
        cfg = self.PRESETS.get(normalized_preset, self.PRESETS.get("safe_verbal_confirmation"))
        now_iso = datetime.now(timezone.utc).isoformat()
        tr = transcript_override if transcript_override is not None else cfg["transcript"]
        to = is_timeout_override if is_timeout_override is not None else cfg["is_timeout"]

        event_type = "voice_timeout" if to else (
            "voice_response_safe" if cfg["intent"] == "safe" else "voice_response_distress"
        )

        return {
            "event_id": f"evt-vox-{uuid.uuid4().hex[:8]}",
            "timestamp": now_iso,
            "resident_id": self.resident_id,
            "room_id": room_id,
            "source": "voice_assistant",
            "event_type": event_type,
            "payload": {
                "transcript": tr,
                "is_timeout": to,
                "intent": cfg["intent"],
                "device_id": f"echo_show_{room_id}_01",
                "mic_snr_db": 24.5
            },
            "confidence": cfg["confidence"],
            "correlation_id": correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
        }

    def emit_event(
        self,
        preset: str = "safe_verbal_confirmation",
        room_id: str = "living_room",
        correlation_id: Optional[str] = None,
        transcript_override: Optional[str] = None,
        is_timeout_override: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Emits voice event as a UnifiedEvent to /api/v1/events/ingest."""
        payload = self.generate_unified_event(
            preset=preset,
            room_id=room_id,
            transcript_override=transcript_override,
            is_timeout_override=is_timeout_override,
            correlation_id=correlation_id
        )

        if self.latency_sec > 0:
            time.sleep(self.latency_sec)

        if not requests:
            print(f"[VoiceSimulator] requests not available; dry-run output:\n{json.dumps(payload, indent=2)}")
            return payload

        url = f"{self.base_url}/api/v1/events/ingest"
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

    def respond_to_incident(
        self,
        incident_id: str,
        preset: str = "safe_verbal_confirmation",
        transcript_override: Optional[str] = None,
        is_timeout_override: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Invokes the /incidents/{incident_id}/respond-voice verification API."""
        cfg = self.PRESETS.get(preset, self.PRESETS["safe_verbal_confirmation"])
        tr = transcript_override if transcript_override is not None else cfg["transcript"]
        to = is_timeout_override if is_timeout_override is not None else cfg["is_timeout"]

        req_body = {
            "transcript": tr,
            "is_timeout": to
        }

        if self.latency_sec > 0:
            time.sleep(self.latency_sec)

        if not requests:
            print(f"[VoiceSimulator] Incident response dry-run:\n{json.dumps(req_body, indent=2)}")
            return req_body

        url = f"{self.base_url}/api/v1/incidents/{incident_id}/respond-voice"
        try:
            t0 = time.perf_counter()
            resp = requests.post(url, json=req_body, headers={"Content-Type": "application/json"}, timeout=4.0)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            resp_json = resp.json() if resp.status_code == 200 else {"status": f"HTTP_{resp.status_code}", "text": resp.text}
            return {
                "incident_id": incident_id,
                "response": resp_json,
                "status_code": resp.status_code,
                "latency_ms": round(elapsed_ms, 2)
            }
        except Exception as e:
            return {"error": str(e), "incident_id": incident_id}


VoiceDeviceSimulator = VoiceSimulator


def main():
    parser = argparse.ArgumentParser(description="NIRA - Genuine Alexa Voice Interaction Producer")
    parser.add_argument(
        "--preset",
        type=str,
        default="safe_verbal_confirmation",
        choices=list(VoiceSimulator.PRESETS.keys()),
        help="Select voice response preset"
    )
    parser.add_argument("--room", type=str, default="living_room", help="Room location")
    parser.add_argument("--transcript", type=str, default=None, help="Custom speech transcript")
    parser.add_argument("--timeout", action="store_true", help="Simulate timeout/silence")
    parser.add_argument("--incident-id", type=str, default=None, help="Respond to specific incident ID")
    parser.add_argument("--latency", type=float, default=0.0, help="Simulated speech latency in seconds")
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Target backend base URL"
    )

    args = parser.parse_args()
    sim = VoiceSimulator(base_url=args.base_url, latency_sec=args.latency)

    if args.incident_id:
        res = sim.respond_to_incident(
            incident_id=args.incident_id,
            preset=args.preset,
            transcript_override=args.transcript,
            is_timeout_override=args.timeout or None
        )
    else:
        res = sim.emit_event(
            preset=args.preset,
            room_id=args.room,
            transcript_override=args.transcript,
            is_timeout_override=args.timeout or None
        )

    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
