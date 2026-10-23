"""
NIRA Live Telemetry Stream Ingestion Client.
Directly interfaces live physical devices (smartwatches, radar boards, smart locks)
with the NIRA Event Pipeline.
"""

import time
import json
import logging
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger("NIRA.LiveIngestStream")


class LiveIngestStream:
    """
    Manages live physical sensor ingestion streams to NIRA.
    Prefers direct in-process CoreService ingestion when running in the same process (Phase 39).
    """
    def __init__(self, backend_url: str = "http://localhost:8000", core_service: Optional[Any] = None):
        self.backend_url = backend_url.rstrip("/")
        self.core_service = core_service

    def ingest_live_sensor(self, device_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sends live sensor reading into authoritative Live Core event ingestion API (Phase 39)."""
        payload = {
            "source": f"live_{device_type}",
            "event_type": data.get("event_type", "sensor_reading"),
            "confidence": data.get("confidence", 1.0),
            "location": {"zone": data.get("location") or data.get("zone") or "living_room"},
            "payload": data
        }

        # 1. In-process direct Core ingestion
        if self.core_service and hasattr(self.core_service, "ingest_event"):
            try:
                evt, risk, inc = self.core_service.ingest_event(payload)
                return {
                    "success": True,
                    "event_id": evt.event_id if evt else None,
                    "risk_level": risk.risk_level.value if risk else "LOW",
                    "incident_id": inc.incident_id if inc else None
                }
            except Exception as e:
                logger.error(f"In-process Core ingestion error: {e}")

        # 2. HTTP to Authoritative Live Core Endpoint (/api/v1/live/core/events)
        endpoint = f"{self.backend_url}/api/v1/live/core/events"
        if requests:
            try:
                res = requests.post(endpoint, json=payload, timeout=2.0)
                return res.json()
            except Exception as e:
                logger.error(f"Live Core HTTP ingest error: {e}")
                return {"error": str(e)}
        return {"status": "buffered", "payload": payload}
