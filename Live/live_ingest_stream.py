"""
NIRA Live Telemetry Stream Ingestion Client.
Directly interfaces live physical devices (smartwatches, radar boards, smart locks)
with the NIRA Event Pipeline.
"""

import logging
from typing import Dict, Any

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger("NIRA.LiveIngestStream")


class LiveIngestStream:
    """
    Manages live physical sensor ingestion streams to NIRA.
    """
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url.rstrip("/")

    def ingest_live_sensor(self, device_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sends live sensor reading into authoritative event ingestion API."""
        endpoint = f"{self.backend_url}/api/v1/events/ingest"
        payload = {
            "source": f"live_{device_type}",
            "event_type": data.get("event_type", "sensor_reading"),
            "confidence": data.get("confidence", 1.0),
            "location": data.get("location", "home"),
            "details": data
        }
        if requests:
            try:
                res = requests.post(endpoint, json=payload, timeout=2.0)
                return res.json()
            except Exception as e:
                logger.error(f"Live ingest error: {e}")
                return {"error": str(e)}
        return {"status": "buffered", "payload": payload}
