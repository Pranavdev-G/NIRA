"""
Event contracts, validation, and normalization for NIRA Live Core.
Amazon Developer Hackathon 2026.
"""

import json
import logging
import hashlib
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path

from Live.core.models import (
    LiveEvent,
    EventType,
    EventSource,
    ZoneType,
    LocationModel
)

from Live.core.time_provider import get_time_provider

logger = logging.getLogger("NIRA.LiveCore.EventContracts")

MAX_EVENT_STALENESS_SECONDS = 300.0  # 5 minutes
MAX_FUTURE_DRIFT_SECONDS = 60.0      # 1 minute clock skew allowance


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Robustly parses ISO-8601 UTC timestamp."""
    try:
        clean = str(dt_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def validate_event_freshness(timestamp_str: str) -> Tuple[bool, str]:
    """Validates that the event timestamp is neither excessively stale nor impossibly in the future."""
    dt = parse_iso_datetime(timestamp_str)
    if dt is None:
        return False, "Invalid ISO-8601 timestamp format"

    now = get_time_provider().now()
    age_seconds = (now - dt).total_seconds()

    if age_seconds > MAX_EVENT_STALENESS_SECONDS:
        return False, f"Stale event: age {age_seconds:.1f}s exceeds threshold {MAX_EVENT_STALENESS_SECONDS}s"

    if age_seconds < -MAX_FUTURE_DRIFT_SECONDS:
        return False, f"Clock skew rejected: timestamp is {-age_seconds:.1f}s in the future"

    return True, "Fresh"


def normalize_zone(zone_raw: Any) -> ZoneType:
    """Normalizes string or enum to standard ZoneType."""
    if not zone_raw:
        return ZoneType.UNKNOWN
    clean = str(zone_raw).lower().replace(" ", "_").strip()
    for z in ZoneType:
        if z.value in clean or clean in z.value:
            return z
    return ZoneType.UNKNOWN


def normalize_event_type(raw_type: Any) -> EventType:
    """Safely normalizes input event string into an authoritative EventType."""
    clean = str(raw_type).lower().strip().replace("-", "_")
    for et in EventType:
        if et.value == clean or et.name.lower() == clean:
            return et

    # Specific heuristic mappings
    if "prolonged" in clean or "stay" in clean or "long_stay" in clean:
        return EventType.PROLONGED_ZONE_STAY
    if "zone_dwell_start" in clean or "dwell_start" in clean:
        return EventType.ZONE_DWELL_START
    if "zone_dwell_anomaly" in clean or "dwell_anomaly" in clean:
        return EventType.ZONE_DWELL_ANOMALY
    if "dwell" in clean:
        return EventType.ZONE_DWELL_UPDATE
    if "entry" in clean:
        return EventType.ROOM_ENTRY
    if "exit" in clean:
        return EventType.ROOM_EXIT
    if "not_visible" in clean or "lost" in clean:
        return EventType.PERSON_NOT_VISIBLE
    if "detected" in clean and "person" in clean:
        return EventType.PERSON_DETECTED
    if "candidate" in clean and "fall" in clean:
        return EventType.FALL_CANDIDATE
    if "fall" in clean:
        return EventType.FALL_DETECTED
    if "recovery" in clean and "no" in clean:
        return EventType.NO_RECOVERY
    if "recovery" in clean:
        return EventType.RECOVERY_MOVEMENT
    if "floor" in clean:
        return EventType.PERSISTENT_FLOOR_POSTURE
    if "inactivity" in clean or "immobile" in clean:
        return EventType.INACTIVITY_WARNING
    if "camera" in clean and "off" in clean:
        return EventType.CAMERA_OFFLINE
    if "camera" in clean and "on" in clean:
        return EventType.CAMERA_ONLINE
    if "mic" in clean and "off" in clean:
        return EventType.MIC_OFFLINE
    if "mic" in clean and "recov" in clean:
        return EventType.MIC_RECOVERED
    if "mic" in clean and "on" in clean:
        return EventType.MIC_ONLINE
    if "transcribed" in clean:
        return EventType.VOICE_TRANSCRIBED
    if "heart" in clean or "bpm" in clean:
        return EventType.HEART_RATE_NORMAL
    if "safe" in clean:
        return EventType.VOICE_RESPONSE_SAFE
    if "help" in clean or "distress" in clean:
        return EventType.VOICE_RESPONSE_HELP

    return EventType.SYSTEM_HEALTH_HEARTBEAT


def normalize_event_source(raw_source: Any) -> EventSource:
    """Safely normalizes input source string into an authoritative EventSource."""
    clean = str(raw_source).lower().strip().replace("-", "_")
    for src in EventSource:
        if src.value == clean or src.name.lower() == clean:
            return src

    if "room_tracker" in clean:
        return EventSource.ROOM_TRACKER
    if "camera_manager" in clean:
        return EventSource.CAMERA_MANAGER
    if "camera" in clean or "vision" in clean:
        return EventSource.CAMERA_VISION
    if "continuous_mic" in clean:
        return EventSource.CONTINUOUS_MIC
    if "voice" in clean or "mic" in clean or "whisper" in clean:
        return EventSource.VOICE_ASSISTANT
    if "wearable" in clean or "band" in clean:
        return EventSource.WEARABLE_SENSOR
    if "gps" in clean or "loc" in clean:
        return EventSource.GPS_TRACKER
    if "med" in clean or "pill" in clean:
        return EventSource.MEDICATION_MANAGER

    return EventSource.SYSTEM_MONITOR


def create_event_fingerprint(event: LiveEvent) -> str:
    """Generates unique idempotent signature for deduplication."""
    # Deduplicate on event_id if given, or payload contents within time window
    base_str = f"{event.event_id}:{event.source.value}:{event.event_type.value}:{event.location.zone.value}:{event.correlation_id}"
    return hashlib.sha256(base_str.encode("utf-8")).hexdigest()


def normalize_raw_event(raw: Dict[str, Any]) -> Tuple[Optional[LiveEvent], Optional[str]]:
    """
    Validates and normalizes raw dictionary into a guaranteed valid LiveEvent.
    Never throws exceptions. Returns (event, None) on success or (None, error_reason).
    """
    try:
        if not isinstance(raw, dict):
            return None, "Event payload is not a valid dictionary"

        # Check required fields
        event_id = raw.get("event_id") or f"evt-auto-{hashlib.md5(str(raw).encode()).hexdigest()[:12]}"
        event_type = normalize_event_type(raw.get("event_type", "system_health_heartbeat"))
        source = normalize_event_source(raw.get("source", "system_monitor"))
        resident_id = str(raw.get("resident_id") or "resident_eleanor_vance")

        ts_str = raw.get("timestamp")
        if not ts_str:
            ts_str = get_time_provider().now_iso()

        is_fresh, freshness_reason = validate_event_freshness(ts_str)
        if not is_fresh:
            logger.warning(f"[EventContracts] Freshness rejection for {event_id}: {freshness_reason}")
            # Mark in payload rather than crashing, or return rejected
            return None, freshness_reason

        # Location normalization
        loc_raw = raw.get("location")
        if isinstance(loc_raw, dict):
            zone = normalize_zone(loc_raw.get("zone"))
            location = LocationModel(
                zone=zone,
                camera_id=loc_raw.get("camera_id"),
                address=loc_raw.get("address"),
                latitude=loc_raw.get("latitude"),
                longitude=loc_raw.get("longitude")
            )
        else:
            zone = normalize_zone(raw.get("zone") or raw.get("room_id") or "living_room")
            location = LocationModel(zone=zone)

        # Confidence bounds checking
        try:
            confidence = float(raw.get("confidence", 1.0))
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5

        correlation_id = str(raw.get("correlation_id") or f"corr-{event_id}")
        device_id = raw.get("device_id")
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}

        # If payload was empty, preserve other raw parameters
        if not payload:
            payload = {k: v for k, v in raw.items() if k not in ["event_id", "event_type", "source", "location", "confidence", "correlation_id"]}

        event = LiveEvent(
            event_id=event_id,
            event_type=event_type,
            source=source,
            resident_id=resident_id,
            timestamp=ts_str,
            location=location,
            confidence=confidence,
            correlation_id=correlation_id,
            device_id=device_id,
            payload=payload
        )
        return event, None

    except Exception as e:
        logger.error(f"[EventContracts] Normalization exception: {e}")
        return None, f"Exception during normalization: {str(e)}"
