"""
Personal Baseline Engine for Aegis Ambient Care.
Amazon Developer Hackathon 2026.

Learns and models circadian routines to compute personal routine deviation
scores (0.0 to 1.0) based on expected spatial and activity patterns over time.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple


class RoutineSlot:
    def __init__(
        self,
        name: str,
        start_hour: int,
        end_hour: int,
        expected_locations: List[str],
        expected_activities: List[str],
        base_vulnerability: float = 0.0
    ):
        self.name = name
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.expected_locations = [loc.lower() for loc in expected_locations]
        self.expected_activities = [act.lower() for act in expected_activities]
        self.base_vulnerability = base_vulnerability


class PersonalBaselineEngine:
    """
    Evaluates observed behavior against circadian baseline routines.
    """

    # Senior daily circadian schedule model (e.g., Eleanor Vance, 79)
    CIRCADIAN_SCHEDULE: List[RoutineSlot] = [
        RoutineSlot("Nocturnal Rest", 23, 7, ["bedroom"], ["sleeping", "resting"], base_vulnerability=0.35),
        RoutineSlot("Morning Routine", 7, 9, ["bedroom", "bathroom", "kitchen"], ["waking_up", "hygiene", "breakfast", "walking"], base_vulnerability=0.15),
        RoutineSlot("Morning Activity", 9, 12, ["living_room", "patio", "kitchen"], ["reading", "sitting", "walking", "resting"], base_vulnerability=0.05),
        RoutineSlot("Midday Lunch", 12, 14, ["kitchen", "dining_room", "living_room"], ["cooking", "eating", "lunch", "walking"], base_vulnerability=0.10),
        RoutineSlot("Afternoon Rest", 14, 18, ["living_room", "bedroom"], ["resting", "napping", "reading", "watching_tv"], base_vulnerability=0.05),
        RoutineSlot("Evening Dinner", 18, 21, ["kitchen", "living_room"], ["cooking", "dinner", "eating", "watching_tv"], base_vulnerability=0.10),
        RoutineSlot("Night Wind-down", 21, 23, ["living_room", "bedroom", "bathroom"], ["hygiene", "reading", "preparing_for_bed"], base_vulnerability=0.20),
    ]

    @classmethod
    def get_slot_for_hour(cls, hour: int) -> RoutineSlot:
        """Finds matching circadian routine slot for given 24h clock hour."""
        for slot in cls.CIRCADIAN_SCHEDULE:
            if slot.start_hour <= slot.end_hour:
                if slot.start_hour <= hour < slot.end_hour:
                    return slot
            else:
                # Wraps past midnight (e.g. 23 to 7)
                if hour >= slot.start_hour or hour < slot.end_hour:
                    return slot
        # Default fallback
        return cls.CIRCADIAN_SCHEDULE[0]

    @classmethod
    def parse_hour_from_timestamp(cls, timestamp_str: str) -> int:
        """Parses hour from ISO timestamp or falls back to current local hour."""
        try:
            # Handle ISO formats
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.hour
        except Exception:
            return datetime.now(timezone.utc).hour

    @classmethod
    def calculate_deviation(
        cls,
        location: str,
        activity: str,
        timestamp_str: Optional[str] = None,
        provided_baseline_deviation: Optional[float] = None
    ) -> Tuple[float, List[str], Dict[str, Any]]:
        """
        Calculates routine deviation score (0.0 to 1.0) and generates explanatory clinical reasons.
        If a provided_baseline_deviation is already supplied by external wearable ML,
        blends it with circadian schedule heuristics.
        """
        hour = cls.parse_hour_from_timestamp(timestamp_str or "")
        slot = cls.get_slot_for_hour(hour)

        loc_clean = location.lower().replace(" ", "_")
        act_clean = activity.lower().replace(" ", "_")

        loc_match = any(exp in loc_clean for exp in slot.expected_locations)
        act_match = any(exp in act_clean for exp in slot.expected_activities)

        deviation_score = 0.0
        reasons: List[str] = []

        # Location divergence penalty
        if not loc_match:
            # Location divergence at night is much more critical
            if slot.start_hour == 23 or slot.end_hour == 7:
                deviation_score += 0.50
                reasons.append(
                    f"Circadian anomaly: Found in '{location}' during nocturnal hours (expected: {', '.join(slot.expected_locations)})"
                )
            else:
                deviation_score += 0.30
                reasons.append(
                    f"Routine divergence: Present in '{location}' (expected: {', '.join(slot.expected_locations)})"
                )

        # Activity divergence penalty
        if not act_match:
            if "fall" in act_clean or "thud" in act_clean or "inactivity" in act_clean:
                deviation_score += 0.40
                reasons.append(f"Acute abnormal activity pattern detected: '{activity}'")
            else:
                deviation_score += 0.20

        # Base slot vulnerability
        deviation_score += slot.base_vulnerability

        # Blend with wearable external sensor baseline deviation if present
        if provided_baseline_deviation is not None:
            # Weighted average between circadian model and wearable model
            deviation_score = 0.45 * deviation_score + 0.55 * float(provided_baseline_deviation)

        # Bound between 0.0 and 1.0
        final_score = round(max(0.0, min(1.0, deviation_score)), 2)

        meta = {
            "circadian_slot": slot.name,
            "hour": hour,
            "expected_locations": slot.expected_locations,
            "expected_activities": slot.expected_activities,
            "deviation_score": final_score
        }

        return final_score, reasons, meta
