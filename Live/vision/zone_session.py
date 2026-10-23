"""
Zone Session Tracking and Room Dwell Lifecycle Manager (Phase 15).
Amazon Developer Hackathon 2026.

Maintains fine-grained session metrics for the resident's continuous stay in a specific room.
Differentiates between:
  - Movement Inactivity (how long since last physical displacement)
  - Zone Dwell Time (how long resident has occupied the room)
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from Live.core.models import ZoneType
from Live.core.time_provider import get_time_provider

logger = logging.getLogger("NIRA.LiveVision.ZoneSession")


class ZoneSession:
    """Represents a continuous stay by the resident in a single room."""

    def __init__(
        self,
        room_id: ZoneType,
        resident_id: str = "resident_eleanor_vance",
        correlation_id: Optional[str] = None
    ):
        self.session_id: str = f"zsess-{uuid.uuid4().hex[:10]}"
        self.room_id: ZoneType = room_id
        self.resident_id: str = resident_id
        self.correlation_id: str = correlation_id or f"corr-{self.session_id}"
        
        # Time management
        self.entry_timestamp: float = get_time_provider().time()
        self.entry_time_iso: str = get_time_provider().now_iso()
        self.last_update_timestamp: float = self.entry_timestamp
        self.exit_timestamp: Optional[float] = None
        self.exit_time_iso: Optional[str] = None

        # Movement vs Inactivity metrics (Phase 14)
        self.last_meaningful_movement_timestamp: float = self.entry_timestamp
        self.current_inactivity_sec: float = 0.0
        self.max_inactivity_sec: float = 0.0

        # Behavioral history
        self.activity_history: List[str] = []
        self.posture_history: List[str] = []
        self.movement_rates: List[float] = []
        self.safe_outcome: bool = True
        self.anomaly_status: str = "NORMAL"

    def get_dwell_seconds(self) -> float:
        """Returns the total elapsed seconds the resident has remained in this zone."""
        current_t = self.exit_timestamp if self.exit_timestamp else get_time_provider().time()
        return max(0.0, current_t - self.entry_timestamp)

    def update(
        self,
        movement_rate: float,
        posture: str,
        activity: str,
        is_meaningful_movement: bool = True
    ):
        """Updates real-time zone telemetry and evaluates movement inactivity."""
        now = get_time_provider().time()
        self.last_update_timestamp = now

        # Record distributions
        self.activity_history.append(activity)
        self.posture_history.append(posture)
        self.movement_rates.append(movement_rate)
        if len(self.movement_rates) > 200:
            self.movement_rates.pop(0)

        # Inactivity tracking (Phase 14 & 26)
        if is_meaningful_movement:
            self.last_meaningful_movement_timestamp = now
            self.current_inactivity_sec = 0.0
        else:
            self.current_inactivity_sec = max(0.0, now - self.last_meaningful_movement_timestamp)
            if self.current_inactivity_sec > self.max_inactivity_sec:
                self.max_inactivity_sec = self.current_inactivity_sec

    def close(self, safe_outcome: bool = True) -> Dict[str, Any]:
        """Terminates session on room exit, returning final session telemetry."""
        now = get_time_provider().time()
        self.exit_timestamp = now
        self.exit_time_iso = get_time_provider().now_iso()
        self.safe_outcome = safe_outcome

        dwell = self.get_dwell_seconds()
        avg_motion = sum(self.movement_rates) / max(1, len(self.movement_rates))

        return {
            "session_id": self.session_id,
            "room_id": self.room_id.value,
            "resident_id": self.resident_id,
            "correlation_id": self.correlation_id,
            "entry_time": self.entry_time_iso,
            "exit_time": self.exit_time_iso,
            "total_dwell_sec": round(dwell, 1),
            "max_inactivity_sec": round(self.max_inactivity_sec, 1),
            "average_movement_rate": round(avg_motion, 3),
            "safe_outcome": self.safe_outcome,
            "anomaly_status": self.anomaly_status
        }
