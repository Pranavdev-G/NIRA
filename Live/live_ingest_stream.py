"""
NIRA Live Telemetry Stream Ingestion Client.
Amazon Developer Hackathon 2026.

Normalized event producer layer for live physical and simulated sensors.
Connects camera inference, microphones, wearables, radar, environment, and GPS
to the central NIRA Live backend without performing emergency escalation.
"""

import os
import time
import uuid
import json
import queue
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger("NIRA.LiveIngestStream")

DEFAULT_BACKEND_URL = os.getenv("NIRA_BACKEND_URL", "http://localhost:8000")
DEFAULT_RESIDENT_ID = os.getenv("NIRA_RESIDENT_ID", "resident_live")
MAX_BUFFER_SIZE = 1000
SEEN_ID_CACHE_SIZE = 2000


def utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def build_live_event(
    event_type: str,
    source: str,
    zone: str = "living_room",
    confidence: float = 1.0,
    payload: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    resident_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs a normalized NIRA Live Event dictionary with standard fields.
    """
    evt_id = event_id or f"evt_{uuid.uuid4().hex[:12]}"
    corr_id = correlation_id or f"corr_{evt_id}"
    res_id = resident_id or DEFAULT_RESIDENT_ID

    return {
        "event_id": evt_id,
        "event_type": event_type,
        "source": source,
        "resident_id": res_id,
        "timestamp": utc_now_iso(),
        "zone": zone,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "correlation_id": corr_id,
        "payload": payload or {},
        "metadata": metadata or {}
    }


class LiveIngestStream:
    """
    Manages normalized live sensor and AI evidence ingestion to the NIRA backend.
    Supports direct in-process CoreService ingestion or HTTP dispatch to Authoritative Core.

    Features:
      - Direct in-process CoreService integration when available
      - Non-blocking async publishing with worker thread
      - Dual endpoints: /api/v1/live/core/events and /api/v1/events/ingest
      - Configurable backend URL via constructor or NIRA_BACKEND_URL
      - Retry mechanism with exponential backoff
      - Connection failure tolerance with offline buffer
      - Duplicate event ID suppression
      - Sensor & vision evidence streaming
    """

    def __init__(
        self,
        backend_url: Optional[str] = None,
        max_retries: int = 3,
        timeout_sec: float = 2.0,
        enable_worker: bool = True,
        core_service: Optional[Any] = None
    ):
        raw_url = backend_url or DEFAULT_BACKEND_URL
        self.backend_url = raw_url.rstrip("/")
        self.max_retries = max(0, max_retries)
        self.timeout_sec = max(0.2, float(timeout_sec))
        self.core_service = core_service

        # Duplicate suppression
        self._seen_lock = threading.Lock()
        self._seen_event_ids: List[str] = []
        self._seen_set = set()

        # Offline buffer and queue
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_lock = threading.Lock()
        self._event_queue: queue.Queue = queue.Queue(maxsize=MAX_BUFFER_SIZE)

        # Worker thread
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        if enable_worker:
            self._start_worker()

    def _start_worker(self):
        """Starts asynchronous background worker for non-blocking publishing."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="NIRA-LiveIngestWorker"
            )
            self._worker_thread.start()

    def _worker_loop(self):
        """Background thread consuming queued events and dispatching over HTTP."""
        while not self._stop_event.is_set():
            try:
                event = self._event_queue.get(timeout=0.25)
            except queue.Empty:
                continue

            try:
                self._send_http(event)
            except Exception as e:
                logger.debug(f"Worker failed to dispatch event {event.get('event_id')}: {e}")
            finally:
                self._event_queue.task_done()

    def is_duplicate(self, event_id: str) -> bool:
        """Checks if an event_id was already processed recently."""
        with self._seen_lock:
            return event_id in self._seen_set

    def _mark_seen(self, event_id: str):
        """Adds event_id to dedup cache with ring-buffer eviction."""
        with self._seen_lock:
            if event_id in self._seen_set:
                return
            if len(self._seen_event_ids) >= SEEN_ID_CACHE_SIZE:
                oldest = self._seen_event_ids.pop(0)
                self._seen_set.discard(oldest)
            self._seen_event_ids.append(event_id)
            self._seen_set.add(event_id)

    def publish_event(self, event: Dict[str, Any], blocking: bool = False) -> Dict[str, Any]:
        """
        Publishes a normalized live event to NIRA Live Core.
        Checks for duplicates and supports either immediate blocking HTTP or background queuing.
        """
        evt_id = event.get("event_id")
        if not evt_id:
            evt_id = f"evt_{uuid.uuid4().hex[:12]}"
            event["event_id"] = evt_id

        # Deduplication check
        if self.is_duplicate(evt_id):
            logger.info(f"Suppressed duplicate event {evt_id}")
            return {"status": "duplicate_ignored", "event_id": evt_id}

        self._mark_seen(evt_id)

        # In-process direct Core ingestion
        if self.core_service and hasattr(self.core_service, "ingest_event"):
            try:
                evt, risk, inc = self.core_service.ingest_event(event)
                return {
                    "status": "published",
                    "event_id": evt.event_id if evt else evt_id,
                    "risk_level": risk.risk_level.value if risk else "LOW",
                    "incident_id": inc.incident_id if inc else None
                }
            except Exception as e:
                logger.error(f"In-process Core ingestion error: {e}")

        if blocking:
            return self._send_http(event)

        # Non-blocking async queue
        try:
            self._event_queue.put_nowait(event)
            return {"status": "queued", "event_id": evt_id}
        except queue.Full:
            logger.warning(f"Live event queue full. Buffering event {evt_id}")
            self._buffer_event(event)
            return {"status": "buffered", "event_id": evt_id, "reason": "queue_full"}

    def _buffer_event(self, event: Dict[str, Any]):
        """Buffers an event in memory when the network or worker is unavailable."""
        with self._buffer_lock:
            if len(self._buffer) >= MAX_BUFFER_SIZE:
                self._buffer.pop(0)
            self._buffer.append(event)

    def _send_http(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transmits event to the NIRA backend ingestion endpoint with retries.
        """
        # In-process direct Core ingestion
        if self.core_service and hasattr(self.core_service, "ingest_event"):
            try:
                evt, risk, inc = self.core_service.ingest_event(event)
                return {
                    "status": "published",
                    "status_code": 200,
                    "event_id": evt.event_id if evt else event.get("event_id"),
                    "response": {
                        "success": True,
                        "risk_level": risk.risk_level.value if risk else "LOW",
                        "incident_id": inc.incident_id if inc else None
                    }
                }
            except Exception as e:
                logger.error(f"In-process Core ingestion error: {e}")

        endpoints = [
            f"{self.backend_url}/api/v1/live/core/events",
            f"{self.backend_url}/api/v1/events/ingest"
        ]

        payload = {
            "source": event.get("source", "live_sensor"),
            "event_type": event.get("event_type", "sensor_reading"),
            "confidence": event.get("confidence", 1.0),
            "zone": event.get("zone") or "living_room",
            "location": {"zone": event.get("zone") or "living_room"},
            "payload": event.get("payload", {}),
            "event_id": event.get("event_id"),
            "resident_id": event.get("resident_id", "resident_eleanor_vance"),
            "correlation_id": event.get("correlation_id"),
            "timestamp": event.get("timestamp"),
            "details": {
                "event_id": event.get("event_id"),
                "resident_id": event.get("resident_id"),
                "correlation_id": event.get("correlation_id"),
                "timestamp": event.get("timestamp"),
                "payload": event.get("payload", {}),
                "metadata": event.get("metadata", {})
            }
        }

        if requests is None:
            self._buffer_event(event)
            return {"status": "buffered", "event_id": event.get("event_id"), "reason": "requests_not_installed"}

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            for endpoint in endpoints:
                try:
                    res = requests.post(endpoint, json=payload, timeout=self.timeout_sec)
                    if res.status_code in [200, 201, 202]:
                        try:
                            resp_data = res.json()
                        except Exception:
                            resp_data = {"status": "accepted"}
                        return {
                            "status": "published",
                            "status_code": res.status_code,
                            "event_id": event.get("event_id"),
                            "response": resp_data
                        }
                    elif res.status_code != 404:
                        last_error = f"HTTP {res.status_code}: {res.text[:100]}"
                except Exception as e:
                    last_error = str(e)
                    logger.debug(f"Ingest attempt {attempt} to {endpoint} exception: {e}")

            if attempt < self.max_retries:
                time.sleep(0.08 * (2 ** (attempt - 1)))

        # All retries failed
        logger.warning(f"Failed to publish event {event.get('event_id')} after {self.max_retries} attempts: {last_error}")
        self._buffer_event(event)
        return {
            "status": "buffered",
            "event_id": event.get("event_id"),
            "error": last_error,
            "buffered_count": len(self._buffer)
        }

    def ingest_live_sensor(self, device_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convenience wrapper preserving backward compatibility with existing telemetry callers.
        Supports both direct in-process CoreService ingestion and background queued dispatch.
        """
        if self.core_service and hasattr(self.core_service, "ingest_event"):
            payload = {
                "source": f"live_{device_type}",
                "event_type": data.get("event_type", "sensor_reading"),
                "confidence": data.get("confidence", 1.0),
                "location": {"zone": data.get("location") or data.get("zone") or "living_room"},
                "zone": data.get("location") or data.get("zone") or "living_room",
                "payload": data
            }
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

        evt = build_live_event(
            event_type=data.get("event_type", f"{device_type}_reading"),
            source=f"live_{device_type}",
            zone=data.get("location") or data.get("zone", "living_room"),
            confidence=data.get("confidence", 1.0),
            payload=data,
            correlation_id=data.get("correlation_id"),
            resident_id=data.get("resident_id")
        )
        return self.publish_event(evt, blocking=False)

    def get_buffer_status(self) -> Dict[str, Any]:
        """Returns statistics on the current offline buffer and worker queue."""
        with self._buffer_lock:
            buf_len = len(self._buffer)
        return {
            "buffered_events_count": buf_len,
            "queue_size": self._event_queue.qsize(),
            "backend_url": self.backend_url,
            "is_worker_alive": self._worker_thread.is_alive() if self._worker_thread else False
        }

    def clear_buffer(self):
        """Clears all buffered events."""
        with self._buffer_lock:
            self._buffer.clear()

    def flush_buffer(self) -> int:
        """
        Attempts to re-send all buffered events synchronously.
        Returns the number of successfully published events.
        """
        with self._buffer_lock:
            if not self._buffer:
                return 0
            to_send = list(self._buffer)
            self._buffer.clear()

        succeeded = 0
        failed = []
        for evt in to_send:
            res = self._send_http(evt)
            if res.get("status") == "published":
                succeeded += 1
            else:
                failed.append(evt)

        if failed:
            with self._buffer_lock:
                self._buffer = failed + self._buffer
                if len(self._buffer) > MAX_BUFFER_SIZE:
                    self._buffer = self._buffer[-MAX_BUFFER_SIZE:]

        return succeeded

    def shutdown(self, timeout: float = 2.0):
        """Clean shutdown of background worker thread."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
