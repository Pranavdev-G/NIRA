"""
Zone, Environmental, and Circadian Context Engine for NIRA Live Core.
Amazon Developer Hackathon 2026.

Modifies risk multipliers and tolerances dynamically based on:
- Zone risk tiers (Bathroom = CRITICAL, Bedroom = SLEEP_ZONE, etc.)
- Circadian phases (Night sleep, afternoon nap, active day)
- Environmental hazards (Wet floors, dark rooms, anomalous temperatures)
- Emergency context
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from Live.core.models import ZoneType, ContextState

logger = logging.getLogger("NIRA.LiveCore.ContextEngine")

# Zone Risk Tiers and Multipliers
ZONE_METADATA: Dict[ZoneType, Dict[str, Any]] = {
    ZoneType.BATHROOM: {
        "tier": "CRITICAL_ZONE",
        "hazard_weight": 1.45,
        "base_immobility_cap_sec": 180.0,  # 3 minutes strict in bathroom
        "requires_rapid_escalation": True
    },
    ZoneType.HALLWAY: {
        "tier": "TRANSIT_ZONE",
        "hazard_weight": 1.25,
        "base_immobility_cap_sec": 180.0,  # 3 minutes strict on floor
        "requires_rapid_escalation": True
    },
    ZoneType.KITCHEN: {
        "tier": "ACTIVE_ZONE",
        "hazard_weight": 1.15,
        "base_immobility_cap_sec": 300.0,  # 5 minutes in kitchen
        "requires_rapid_escalation": False
    },
    ZoneType.LIVING_ROOM: {
        "tier": "REST_ZONE",
        "hazard_weight": 1.0,
        "base_immobility_cap_sec": 600.0,  # 10 minutes (sofa resting permitted)
        "requires_rapid_escalation": False
    },
    ZoneType.BEDROOM: {
        "tier": "SLEEP_ZONE",
        "hazard_weight": 0.85,
        "base_immobility_cap_sec": 1800.0, # 30 mins (bed sleep)
        "requires_rapid_escalation": False
    },
    ZoneType.UNKNOWN: {
        "tier": "DEFAULT_ZONE",
        "hazard_weight": 1.0,
        "base_immobility_cap_sec": 300.0,
        "requires_rapid_escalation": False
    }
}

# Circadian Hour Definitions (Local Hour 0..23)
NIGHT_HOURS = {22, 23, 0, 1, 2, 3, 4, 5, 6}
AFTERNOON_NAP_HOURS = {13, 14, 15}


class ContextEngine:
    """
    Maintains real-time situational awareness across rooms, environmental sensors,
    and circadian cycles. Provides risk multipliers to the Risk Engine.
    """

    def __init__(self):
        self._current_contexts: Dict[ZoneType, ContextState] = {}
        for z in ZoneType:
            self._current_contexts[z] = self._create_default_context(z)

    def _create_default_context(self, zone: ZoneType) -> ContextState:
        meta = ZONE_METADATA.get(zone, ZONE_METADATA[ZoneType.UNKNOWN])
        now = datetime.now()
        h = now.hour
        is_night = h in NIGHT_HOURS
        is_nap = h in AFTERNOON_NAP_HOURS

        phase = "NIGHT_SLEEP" if is_night else ("AFTERNOON_NAP" if is_nap else "ACTIVE_DAY")

        return ContextState(
            zone=zone,
            zone_risk_tier=meta["tier"],
            circadian_phase=phase,
            is_night=is_night,
            is_afternoon_nap=is_nap,
            hazard_multiplier=meta["hazard_weight"],
            is_dark=is_night,
            is_wet_floor=(zone == ZoneType.BATHROOM),
            temperature_c=21.5,
            last_updated=datetime.now(timezone.utc).isoformat()
        )

    def update_environment(
        self,
        zone: ZoneType,
        is_dark: Optional[bool] = None,
        is_wet_floor: Optional[bool] = None,
        temperature_c: Optional[float] = None
    ) -> ContextState:
        """Updates environmental hazard flags for a given room."""
        ctx = self.get_context(zone)
        if is_dark is not None:
            ctx.is_dark = is_dark
        if is_wet_floor is not None:
            ctx.is_wet_floor = is_wet_floor
        if temperature_c is not None:
            ctx.temperature_c = temperature_c

        # Recalculate dynamic hazard multiplier
        base_multiplier = ZONE_METADATA.get(zone, ZONE_METADATA[ZoneType.UNKNOWN])["hazard_weight"]
        multiplier = base_multiplier

        if ctx.is_wet_floor:
            multiplier += 0.35  # Slip danger significantly amplifies risk
        if ctx.is_dark:
            multiplier += 0.20  # Nighttime / unlit area increases fall likelihood
        if ctx.temperature_c is not None and (ctx.temperature_c < 16.0 or ctx.temperature_c > 32.0):
            multiplier += 0.25  # Hypothermia or hyperthermia hazard during long lie

        ctx.hazard_multiplier = round(multiplier, 2)
        ctx.last_updated = datetime.now(timezone.utc).isoformat()
        self._current_contexts[zone] = ctx
        return ctx

    def get_context(self, zone: ZoneType, hour: Optional[int] = None) -> ContextState:
        """Returns the active ContextState for a specific zone."""
        if hour is None:
            hour = datetime.now().hour

        ctx = self._current_contexts.get(zone)
        if ctx is None:
            ctx = self._create_default_context(zone)
            self._current_contexts[zone] = ctx

        # Update circadian attributes
        ctx.is_night = hour in NIGHT_HOURS
        ctx.is_afternoon_nap = hour in AFTERNOON_NAP_HOURS
        ctx.circadian_phase = (
            "NIGHT_SLEEP" if ctx.is_night
            else ("AFTERNOON_NAP" if ctx.is_afternoon_nap else "ACTIVE_DAY")
        )
        return ctx

    def get_zone_base_tolerance_seconds(self, zone: ZoneType, hour: Optional[int] = None) -> float:
        """Returns baseline immobility tolerance in seconds before warning."""
        if hour is None:
            hour = datetime.now().hour

        meta = ZONE_METADATA.get(zone, ZONE_METADATA[ZoneType.UNKNOWN])
        base_sec = meta["base_immobility_cap_sec"]

        # Sleep zone at night allows longer immobility
        if zone == ZoneType.BEDROOM and hour in NIGHT_HOURS:
            return 3600.0  # 1 hour
        if zone == ZoneType.LIVING_ROOM and hour in AFTERNOON_NAP_HOURS:
            return 900.0   # 15 minutes rest tolerance

        return base_sec
