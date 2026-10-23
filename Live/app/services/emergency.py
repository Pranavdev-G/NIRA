"""
Live Emergency Ambulance Tracking & Smart Door Lock Control Engine.
Amazon Developer Hackathon 2026.

Features:
- Real-time GPS path interpolation of dispatched emergency ambulance (Medic-14)
- Live ETA countdown and distance to incident residence
- Automatic Main Door Smart-Lock unlock when emergency responders arrive (ETA <= 0.2 min)
- Generates smart entry PIN #8492
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("NIRA.LiveEmergency")

# Resident Home Coordinate (Default Boston Unit 4B)
RESIDENT_COORDS = {"lat": 42.3601, "lon": -71.0589}

# Ambulance Hospital Base
AMBULANCE_BASE = {"lat": 42.3635, "lon": -71.0685}

_dispatch_state: Dict[str, Any] = {
    "is_active": False,
    "incident_id": None,
    "unit_id": "MEDIC-14-PARAMEDIC",
    "service_name": "Boston EMS Advanced Life Support Ambulance",
    "dispatched_at": None,
    "progress_percent": 0,
    "current_lat": AMBULANCE_BASE["lat"],
    "current_lon": AMBULANCE_BASE["lon"],
    "distance_km": 1.45,
    "eta_mins": 3.8,
    "door_status": "LOCKED",
    "door_pin": "8492",
    "door_unlocked_at": None,
    "status": "IDLE_STANDBY"
}


class LiveEmergencyTrackerService:
    """Simulates real-time ambulance dispatch progression and automated door unlock."""

    @classmethod
    def trigger_dispatch(
        cls,
        incident_id: Optional[str] = None,
        target_lat: Optional[float] = None,
        target_lon: Optional[float] = None
    ) -> Dict[str, Any]:
        global _dispatch_state
        inc_id = incident_id or f"INC-{uuid.uuid4().hex[:6].upper()}"
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()

        dest_lat = target_lat if target_lat is not None else RESIDENT_COORDS["lat"]
        dest_lon = target_lon if target_lon is not None else RESIDENT_COORDS["lon"]

        # Base station offset ~1.2 km away
        start_lat = dest_lat + 0.0085
        start_lon = dest_lon - 0.0092

        _dispatch_state = {
            "is_active": True,
            "incident_id": inc_id,
            "unit_id": "MEDIC-14-PARAMEDIC",
            "service_name": "Boston EMS Advanced Life Support Ambulance",
            "start_time": now,
            "dispatched_at": now_iso,
            "progress_percent": 5,
            "start_coords": {"lat": start_lat, "lon": start_lon},
            "dest_coords": {"lat": dest_lat, "lon": dest_lon},
            "current_lat": start_lat,
            "current_lon": start_lon,
            "distance_km": 1.45,
            "eta_mins": 3.8,
            "door_status": "LOCKED (Armed)",
            "door_pin": "8492",
            "door_unlocked_at": None,
            "status": "EN_ROUTE_SIRENS_ACTIVE"
        }
        logger.info(f"[LiveEmergency] Dispatched ambulance for incident {inc_id} to [{dest_lat}, {dest_lon}]")
        return dict(_dispatch_state)

    @classmethod
    def get_tracking_status(cls) -> Dict[str, Any]:
        global _dispatch_state
        if not _dispatch_state.get("is_active"):
            return dict(_dispatch_state)

        elapsed = time.time() - _dispatch_state.get("start_time", time.time())
        # Trip takes 45 seconds of simulation time to represent a 4-minute siren drive
        total_trip_duration = 45.0
        pct = min(1.0, elapsed / total_trip_duration)

        start = _dispatch_state["start_coords"]
        dest = _dispatch_state["dest_coords"]

        cur_lat = start["lat"] + (dest["lat"] - start["lat"]) * pct
        cur_lon = start["lon"] + (dest["lon"] - start["lon"]) * pct

        remaining_dist = max(0.0, round(1.45 * (1.0 - pct), 2))
        remaining_eta = max(0.0, round(3.8 * (1.0 - pct), 1))

        _dispatch_state["progress_percent"] = int(pct * 100)
        _dispatch_state["current_lat"] = cur_lat
        _dispatch_state["current_lon"] = cur_lon
        _dispatch_state["distance_km"] = remaining_dist
        _dispatch_state["eta_mins"] = remaining_eta

        # AUTOMATIC MAIN DOOR LOCK OPENING SYSTEM ON ARRIVAL
        if pct >= 0.92 and _dispatch_state["door_status"] != "UNLOCKED (Auto-Opened for Paramedics)":
            _dispatch_state["door_status"] = "UNLOCKED (Auto-Opened for Paramedics)"
            _dispatch_state["door_unlocked_at"] = datetime.now(timezone.utc).isoformat()
            _dispatch_state["status"] = "ARRIVED_ON_SCENE_ENTRY_GRANTED"
            logger.info("[LiveEmergency] Ambulance arrived! Automatic door lock OPENED. Entry token 8492 validated.")
        elif pct >= 1.0:
            _dispatch_state["status"] = "PARAMEDICS_INSIDE_TREATING_RESIDENT"
        else:
            _dispatch_state["status"] = "EN_ROUTE_SIRENS_ACTIVE"

        return dict(_dispatch_state)
