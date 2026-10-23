"""
Base Sensor Adapter Interfaces and Normalized Sensor Contracts for NIRA Live.
Amazon Developer Hackathon 2026.

Ensures all live physical devices and explicit test simulators produce
normalized evidence events without competing with the central safety core.
Strictly distinguishes real hardware from simulation.
"""

import time
import uuid
import logging
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union

try:
    from Live.live_ingest_stream import LiveIngestStream, build_live_event
except ImportError:
    try:
        from live_ingest_stream import LiveIngestStream, build_live_event
    except ImportError:
        LiveIngestStream = None
        build_live_event = None

logger = logging.getLogger("NIRA.Sensors.Base")


class SensorSourceType(str, Enum):
    """Authoritative declaration of data provenance."""
    REAL_HARDWARE = "REAL_HARDWARE"
    REAL_WEARABLE = "REAL_WEARABLE"
    SIMULATED = "SIMULATED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class ConnectionState(str, Enum):
    """Device physical/link connection state."""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    SIMULATED = "SIMULATED"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SensorReading:
    """
    Normalized sensor reading data packet.
    """
    def __init__(
        self,
        sensor_id: str,
        sensor_type: str,
        source_type: SensorSourceType,
        data: Dict[str, Any],
        is_valid: bool = True,
        error_message: Optional[str] = None,
        timestamp: Optional[str] = None,
        zone: str = "living_room",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.source_type = source_type
        self.data = data
        self.is_valid = is_valid
        self.error_message = error_message
        self.timestamp = timestamp or utc_now_iso()
        self.zone = zone
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type,
            "source_type": self.source_type.value if hasattr(self.source_type, "value") else str(self.source_type),
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "zone": self.zone,
            "data": self.data,
            "metadata": self.metadata
        }

    def to_live_event(
        self,
        resident_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Converts reading into a normalized NIRA live event dictionary."""
        source_str = f"live_{self.sensor_type}"
        event_type = f"{self.sensor_type.upper()}_READING" if self.is_valid else f"{self.sensor_type.upper()}_ERROR"

        if build_live_event:
            return build_live_event(
                event_type=event_type,
                source=source_str,
                zone=self.zone,
                confidence=1.0 if self.is_valid else 0.0,
                payload={
                    "sensor_id": self.sensor_id,
                    "source_type": self.source_type.value if hasattr(self.source_type, "value") else str(self.source_type),
                    "reading": self.data,
                    "is_valid": self.is_valid,
                    "error": self.error_message
                },
                correlation_id=correlation_id,
                resident_id=resident_id,
                metadata={
                    "adapter_type": self.sensor_type,
                    "source_provenance": self.source_type.value if hasattr(self.source_type, "value") else str(self.source_type),
                    **self.metadata
                }
            )

        return {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "source": source_str,
            "timestamp": self.timestamp,
            "zone": self.zone,
            "confidence": 1.0 if self.is_valid else 0.0,
            "payload": self.data,
            "metadata": self.metadata
        }


class BaseSensorAdapter(ABC):
    """
    Abstract Base Class for all physical sensor and telemetry adapters.
    Guarantees non-crashing hardware failure behavior, connection lifecycle,
    and event publishing to the NIRA Live event pipeline.
    """

    def __init__(
        self,
        sensor_id: str,
        sensor_type: str,
        source_type: SensorSourceType = SensorSourceType.UNAVAILABLE,
        zone: str = "living_room",
        ingest_stream: Optional[Any] = None
    ):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.source_type = source_type
        self.zone = zone
        self.connection_state = ConnectionState.DISCONNECTED
        self.ingest_stream = ingest_stream or (LiveIngestStream() if LiveIngestStream else None)
        self.last_reading_time = 0.0
        self.last_error: Optional[str] = None
        self._readings_count = 0

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the sensor device or interface."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Closes connection to the sensor device."""
        pass

    @abstractmethod
    def read(self) -> SensorReading:
        """
        Polls or reads the current sensor telemetry.
        Must catch all internal driver/IO exceptions and return an invalid
        SensorReading with error_message rather than crashing the caller.
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """Returns standard sensor health diagnostic dictionary."""
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type,
            "source_type": self.source_type.value if hasattr(self.source_type, "value") else str(self.source_type),
            "connection_state": self.connection_state.value if hasattr(self.connection_state, "value") else str(self.connection_state),
            "zone": self.zone,
            "readings_count": self._readings_count,
            "last_reading_time": self.last_reading_time,
            "last_error": self.last_error,
            "is_operational": self.connection_state in [ConnectionState.CONNECTED, ConnectionState.SIMULATED]
        }

    def publish_reading(
        self,
        reading: Optional[SensorReading] = None,
        zone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reads current data and publishes a normalized evidence event.
        Never crashes caller if network or backend fails.
        """
        target_zone = zone or self.zone
        try:
            r = reading or self.read()
            r.zone = target_zone
            event = r.to_live_event()

            if self.ingest_stream:
                return self.ingest_stream.publish_event(event, blocking=False)
            return {"status": "buffered_locally", "event": event}
        except Exception as e:
            self.last_error = f"Publish failed: {e}"
            logger.error(f"Sensor [{self.sensor_id}] publish error: {e}")
            return {"status": "error", "error": str(e)}

    def publish_sensor_health_event(
        self,
        status: str = "HEALTH_CHECK",
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dispatches an explicit SENSOR_HEALTH evidence event."""
        health = self.health_check()
        if details:
            health.update(details)

        if build_live_event:
            evt = build_live_event(
                event_type="SENSOR_HEALTH",
                source=f"live_{self.sensor_type}",
                zone=self.zone,
                confidence=1.0 if health["is_operational"] else 0.0,
                payload=health,
                metadata={"status_descriptor": status}
            )
            if self.ingest_stream:
                return self.ingest_stream.publish_event(evt, blocking=False)
        return {"status": "dispatched", "health": health}
