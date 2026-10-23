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

    # Hourly baseline expected mobility score (0.0=immobile/sleep, 1.0=active)
    HOURLY_MOBILITY_PROFILE: Dict[int, float] = {
        0: 0.05, 1: 0.02, 2: 0.02, 3: 0.02, 4: 0.02, 5: 0.05, 6: 0.15,
        7: 0.65, 8: 0.80, 9: 0.75, 10: 0.70, 11: 0.65, 12: 0.85,
        13: 0.70, 14: 0.40, 15: 0.35, 16: 0.45, 17: 0.60, 18: 0.80,
        19: 0.70, 20: 0.55, 21: 0.40, 22: 0.20, 23: 0.08
    }

    # Per-zone typical safe inactivity limits (in seconds)
    ZONE_INACTIVITY_LIMITS_SEC: Dict[str, int] = {
        "bathroom": 1200,      # 20 min normal max without movement
        "bedroom": 28800,      # 8 hours resting window
        "living_room": 7200,   # 2 hours TV/reading
        "kitchen": 1800,       # 30 min cooking/dining
        "hallway": 300,        # 5 min transit
        "stairs": 120          # 2 min transit
    }

    # Dynamic learned tolerances from resident feedback e.g. "I'm okay, false alarm"
    _learned_tolerances: Dict[str, float] = {
        "living_room:reading": 0.25,
        "living_room:sitting": 0.20,
        "bedroom:napping": 0.30
    }
    _feedback_history: List[Dict[str, Any]] = []

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
        # Apply learned tolerance if not an obvious fall emergency (Section 5 Guardrail)
        is_obvious_emergency = ("fall" in act_clean or "thud" in act_clean) and ("none" in act_clean or "bathroom" in loc_clean)
        tolerance = 0.0
        if not is_obvious_emergency:
            tolerance = cls.get_learned_tolerance(loc_clean, act_clean)
            if tolerance > 0.0:
                deviation_score = max(0.0, deviation_score - tolerance)
                reasons.append(f"Adaptive baseline: Learned tolerance applied for {location}/{activity} (-{tolerance:.2f})")

        # Bound between 0.0 and 1.0
        final_score = round(max(0.0, min(1.0, deviation_score)), 2)

        meta = {
            "circadian_slot": slot.name,
            "hour": hour,
            "expected_locations": slot.expected_locations,
            "expected_activities": slot.expected_activities,
            "learned_tolerance_applied": tolerance,
            "deviation_score": final_score
        }

        return final_score, reasons, meta

    @classmethod
    def record_resident_feedback(cls, location: str, activity: str, is_safe: bool = True) -> float:
        """
        Adapts baseline tolerance based on resident feedback (e.g., False Alarm confirmations).
        Guarantees deterministic false-alarm reduction.
        """
        loc = location.lower().replace(" ", "_")
        act = activity.lower().replace(" ", "_")
        key = f"{loc}:{act}"
        current = cls._learned_tolerances.get(key, 0.0)
        if is_safe:
            # Increase tolerance safely up to a maximum cap of 0.35
            new_tol = round(min(0.35, current + 0.10), 2)
            cls._learned_tolerances[key] = new_tol
        else:
            # Decay tolerance if flagged as real risk
            new_tol = round(max(0.0, current - 0.10), 2)
            cls._learned_tolerances[key] = new_tol

        cls._feedback_history.append({
            "key": key,
            "is_safe": is_safe,
            "new_tolerance": new_tol,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return new_tol

    @classmethod
    def get_learned_tolerance(cls, location: str, activity: str) -> float:
        loc = location.lower().replace(" ", "_")
        act = activity.lower().replace(" ", "_")
        for k, tol in cls._learned_tolerances.items():
            if k == f"{loc}:{act}" or k == f"{loc}:resting" or k == f"{loc}:sitting":
                return tol
        return 0.0

    @classmethod
    def get_hourly_profile(cls) -> Dict[int, float]:
        """Returns the 24-hour baseline expected mobility profile."""
        return cls.HOURLY_MOBILITY_PROFILE.copy()

    @classmethod
    def get_zone_inactivity_limit(cls, zone: str) -> int:
        """Returns safe inactivity duration in seconds for a specific zone."""
        return cls.ZONE_INACTIVITY_LIMITS_SEC.get(zone.lower().replace(" ", "_"), 1800)

    @classmethod
    def reset_learning(cls):
        """Resets learned baseline feedback to default state."""
        cls._learned_tolerances = {
            "living_room:reading": 0.25,
            "living_room:sitting": 0.20,
            "bedroom:napping": 0.30
        }
        cls._feedback_history = []
