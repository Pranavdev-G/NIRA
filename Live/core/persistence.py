"""
Safe Persistence Layer for NIRA Live Core.
Amazon Developer Hackathon 2026.

Persists incidents, timelines, telemetry, and emergency packets to MongoDB Atlas:
- Collections: incidents, incident_timelines, telemetry_events, emergency_packets
- Non-blocking, fault-tolerant: gracefully falls back to memory if MongoDB is unavailable
- Never logs unmasked credentials
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from Live.core.models import (
    LiveEvent,
    IncidentRecord,
    TimelineEntry,
    EmergencyPacket
)

logger = logging.getLogger("NIRA.LiveCore.Persistence")


class CorePersistenceManager:
    """
    Manages safe persistence for the Live safety core.
    """

    def __init__(self):
        self._mongo_db = None
        self._init_db()

    def _init_db(self):
        try:
            from Live.app.database import get_mongo_db
            self._mongo_db = get_mongo_db()
            if self._mongo_db is not None:
                logger.info("[Persistence] Connected to MongoDB Atlas for Live Core storage.")
        except Exception as e:
            logger.warning(f"[Persistence] MongoDB initialization note: {e}")
            self._mongo_db = None

    def save_incident(self, incident: IncidentRecord) -> bool:
        """Persists or updates an incident record."""
        doc = incident.model_dump()
        doc["id"] = incident.incident_id  # Satisfies MongoDB legacy unique index on id
        if self._mongo_db is not None:
            try:
                self._mongo_db.incidents.replace_one(
                    {"incident_id": incident.incident_id},
                    doc,
                    upsert=True
                )
                return True
            except Exception as e:
                logger.warning(f"[Persistence] Error writing incident to MongoDB: {e}")
        return False

    def save_timeline_entry(self, incident_id: str, entry: TimelineEntry) -> bool:
        """Appends a timeline entry to MongoDB incident_timelines."""
        doc = {
            "incident_id": incident_id,
            "timestamp": entry.timestamp,
            "state": entry.state.value,
            "action": entry.action,
            "description": entry.description,
            "actor": entry.actor,
            "metadata": entry.metadata
        }
        if self._mongo_db is not None:
            try:
                self._mongo_db.incident_timelines.insert_one(doc)
                return True
            except Exception as e:
                logger.warning(f"[Persistence] Error writing timeline entry: {e}")
        return False

    def save_emergency_packet(self, packet: EmergencyPacket) -> bool:
        """Persists an authoritative emergency packet."""
        doc = packet.model_dump()
        if self._mongo_db is not None:
            try:
                self._mongo_db.emergency_packets.replace_one(
                    {"incident_id": packet.incident_id},
                    doc,
                    upsert=True
                )
                return True
            except Exception as e:
                logger.warning(f"[Persistence] Error writing emergency packet: {e}")
        return False

    def save_telemetry_event(self, event: LiveEvent) -> bool:
        """Persists a normalized LiveEvent to telemetry_events."""
        doc = {
            "id": event.event_id,
            "correlation_id": event.correlation_id,
            "resident_id": event.resident_id,
            "source": event.source.value,
            "event_type": event.event_type.value,
            "confidence": event.confidence,
            "location": event.location.model_dump(),
            "payload": event.payload,
            "timestamp": event.timestamp,
            "persisted_at": datetime.now(timezone.utc).isoformat()
        }
        if self._mongo_db is not None:
            try:
                self._mongo_db.telemetry_events.replace_one(
                    {"id": event.event_id},
                    doc,
                    upsert=True
                )
                return True
            except Exception as e:
                logger.debug(f"[Persistence] Error writing telemetry event: {e}")
        return False

    def query_active_incident(self) -> Optional[Dict[str, Any]]:
        """Queries the latest non-resolved incident from MongoDB."""
        if self._mongo_db is not None:
            try:
                doc = self._mongo_db.incidents.find_one(
                    {"state": {"$ne": "RESOLVED"}},
                    {"_id": 0},
                    sort=[("start_time", -1)]
                )
                return doc
            except Exception as e:
                logger.debug(f"[Persistence] Query active incident note: {e}")
        return None
