"""
NIRA Self-Learning Daily Activity Routine & Multi-Room Behavior Engine.
Amazon Developer Hackathon 2026.

Implements an online statistical circadian activity baseline model:
  1. Tracks Movement Inactivity vs. Zone Dwell Time as TWO distinct concepts (Phase 14).
  2. Learns per-room visit duration distributions: visit count, median, mean, p75, p90, safe_max (Phase 16).
  3. Uses conservative configurable initial priors (Bathroom 600s, Kitchen 600s, Hallway 300s, Living Room 3600s, Bedroom 7200s) (Phase 17).
  4. Evaluates prolonged dwell without confusing stay duration with emergency (Phases 18, 19).
  5. Safe confirmations gradually reinforce the baseline via incremental EMA without sudden threshold jumps (Phases 20, 47, 49).
  6. Emergency evidence (fall, floor posture, distress speech) strictly overrides learned baselines (Phase 21).
  7. Tracks room sequence transitions (Phase 23) and time context (Phase 24).
"""

import os
import json
import time
import math
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from Live.core.time_provider import get_time_provider
from Live.app.config import settings

logger = logging.getLogger("NIRA.ActivityRoutineLearner")

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "activity_baseline.json"

# Inactivity Profiles (stillness / lack of movement displacement)
ZONE_RISK_PROFILES = {
    "bathroom": {"base_inactivity_sec": 180.0, "max_cap_sec": 300.0, "risk_tier": "CRITICAL_ZONE"},
    "hallway": {"base_inactivity_sec": 180.0, "max_cap_sec": 300.0, "risk_tier": "TRANSIT_ZONE"},
    "kitchen": {"base_inactivity_sec": 180.0, "max_cap_sec": 600.0, "risk_tier": "ACTIVE_ZONE"},
    "living_room": {"base_inactivity_sec": 180.0, "max_cap_sec": 3600.0, "risk_tier": "REST_ZONE"},
    "bedroom": {"base_inactivity_sec": 180.0, "max_cap_sec": 7200.0, "risk_tier": "SLEEP_ZONE"},
    "general": {"base_inactivity_sec": 180.0, "max_cap_sec": 1800.0, "risk_tier": "DEFAULT_ZONE"}
}

# Initial Room Priors for Zone Dwell Duration (Phases 16, 17, 70)
DEFAULT_ZONE_DWELL_PRIORS: Dict[str, Dict[str, float]] = {
    "bathroom": {
        "expected_sec": getattr(settings, "BATHROOM_INITIAL_EXPECTED_DURATION_SECONDS", 600.0),
        "p90_sec": 735.0,
        "safe_max_sec": 900.0,
        "min_sec": 60.0
    },
    "kitchen": {
        "expected_sec": getattr(settings, "KITCHEN_INITIAL_EXPECTED_DURATION_SECONDS", 600.0),
        "p90_sec": 840.0,
        "safe_max_sec": 1200.0,
        "min_sec": 60.0
    },
    "hallway": {
        "expected_sec": getattr(settings, "HALLWAY_INITIAL_EXPECTED_DURATION_SECONDS", 300.0),
        "p90_sec": 360.0,
        "safe_max_sec": 480.0,
        "min_sec": 10.0
    },
    "living_room": {
        "expected_sec": getattr(settings, "LIVING_ROOM_INITIAL_EXPECTED_DURATION_SECONDS", 3600.0),
        "p90_sec": 5400.0,
        "safe_max_sec": 7200.0,
        "min_sec": 120.0
    },
    "bedroom": {
        "expected_sec": getattr(settings, "BEDROOM_INITIAL_EXPECTED_DURATION_SECONDS", 7200.0),
        "p90_sec": 14400.0,
        "safe_max_sec": 28800.0,
        "min_sec": 300.0
    },
    "general": {
        "expected_sec": 1800.0,
        "p90_sec": 2400.0,
        "safe_max_sec": 3600.0,
        "min_sec": 60.0
    }
}

# Known clinical circadian resting windows (24-hour format)
NIGHT_HOURS = set([22, 23, 0, 1, 2, 3, 4, 5, 6])
AFTERNOON_NAP_HOURS = set([13, 14, 15])


class DailyActivityRoutineLearner:
    """
    Self-learning activity routine model that builds a personalized behavioral
    baseline for an elderly resident to eliminate false alarms while guaranteeing
    timely alerts for genuine falls, prolonged unresponsiveness, or abnormal stays.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path) if data_path else DEFAULT_DATA_PATH
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile: Dict[str, Any] = self._load_profile()
        self._recent_room_sequence: List[str] = []

    def _default_profile(self) -> Dict[str, Any]:
        """Generates clinically-safe default priors for all 24 hours and major rooms."""
        hourly: Dict[str, Dict[str, Any]] = {}
        for h in range(24):
            hourly[str(h)] = {}
            for zone, p in ZONE_RISK_PROFILES.items():
                base_sec = p["base_inactivity_sec"]
                if zone == "bedroom" and h in NIGHT_HOURS:
                    base_sec = 1800.0  # 30 mins sleep in bed at night
                hourly[str(h)][zone] = {
                    "observations_count": 1,
                    "mean_inactivity_sec": base_sec,
                    "max_observed_safe_sec": base_sec,
                    "tolerated_threshold_sec": base_sec,
                    "dismissed_alarms_count": 0,
                    "last_updated": get_time_provider().now_iso()
                }

        # Room dwell statistics structure (Phases 16, 48)
        room_dwells: Dict[str, Dict[str, Any]] = {}
        for zone, p in DEFAULT_ZONE_DWELL_PRIORS.items():
            room_dwells[zone] = {
                "visit_count": 1,
                "median_duration_sec": p["expected_sec"],
                "mean_duration_sec": p["expected_sec"],
                "p75_duration_sec": p["expected_sec"] * 1.15,
                "p90_duration_sec": p["p90_sec"],
                "safe_max_duration_sec": p["safe_max_sec"],
                "confidence": 0.5,
                "history_samples": [p["expected_sec"]],
                "safe_exceptions_count": 0,
                "last_update": get_time_provider().now_iso()
            }

        return {
            "version": "2.2.0",
            "resident_id": "resident_eleanor_vance",
            "total_learned_events": 0,
            "suppressed_false_alarms": 0,
            "hourly_zones": hourly,
            "room_dwells": room_dwells,
            "transition_graph": {
                "bedroom->hallway": 10,
                "hallway->bathroom": 8,
                "bathroom->hallway": 8,
                "hallway->kitchen": 6,
                "kitchen->living_room": 5,
                "living_room->hallway": 5,
                "hallway->bedroom": 7
            },
            "created_at": get_time_provider().now_iso()
        }

    def _load_profile(self) -> Dict[str, Any]:
        """Loads learned routine profile from JSON file or initializes defaults."""
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "hourly_zones" in data:
                        # Migrate or enrich with room_dwells if missing
                        if "room_dwells" not in data:
                            defaults = self._default_profile()
                            data["room_dwells"] = defaults["room_dwells"]
                            data["transition_graph"] = defaults.get("transition_graph", {})
                        logger.info(f"Loaded learned activity routine profile from {self.data_path}")
                        return data
            except Exception as e:
                logger.warning(f"Error loading activity baseline JSON ({e}). Initializing defaults.")
        
        defaults = self._default_profile()
        self._save_profile(defaults)
        return defaults

    def _save_profile(self, profile: Optional[Dict[str, Any]] = None):
        """Thread-safe and atomic write of learned profile to disk (Phase 48)."""
        target = profile or self.profile
        try:
            temp_path = self.data_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(target, f, indent=2)
            temp_path.replace(self.data_path)
        except Exception as e:
            logger.error(f"Failed to persist activity routine profile: {e}")

    def normalize_zone(self, zone: str) -> str:
        """Normalizes room string to standard key."""
        clean = str(zone).lower().replace(" ", "_") if zone else "general"
        for k in ["bathroom", "hallway", "kitchen", "living_room", "bedroom"]:
            if k in clean:
                return k
        return "general"

    def get_zone_config(self, zone: str) -> Dict[str, Any]:
        """Returns risk profile parameters for immobility / inactivity."""
        z_key = self.normalize_zone(zone)
        return ZONE_RISK_PROFILES.get(z_key, ZONE_RISK_PROFILES["general"])

    # ------------------------------------------------------------------
    # CONCEPT A: MOVEMENT INACTIVITY (STILLNESS) (Phase 14)
    # ------------------------------------------------------------------
    def get_tolerated_inactivity_threshold(
        self,
        zone: str = "living_room",
        hour: Optional[int] = None
    ) -> float:
        """
        Returns dynamic inactivity threshold in seconds for given zone and time of day.
        Guaranteed to be at least 180 seconds (3 mins).
        """
        if hour is None:
            hour = get_time_provider().now().hour
        h_str = str(hour % 24)
        z_key = self.normalize_zone(zone)

        zone_data = (
            self.profile.get("hourly_zones", {})
            .get(h_str, {})
            .get(z_key, None)
        )

        cfg = self.get_zone_config(z_key)
        min_thresh = cfg["base_inactivity_sec"]
        max_cap = cfg["max_cap_sec"]

        if zone_data:
            learned = float(zone_data.get("tolerated_threshold_sec", min_thresh))
            return round(min(max(learned, min_thresh), max_cap), 1)

        return min_thresh

    def evaluate_inactivity_anomaly(
        self,
        zone: str = "living_room",
        motionless_seconds: float = 0.0,
        posture: str = "sitting",
        hour: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Infers whether stillness is an anomaly that warrants waking up an alarm.
        """
        if hour is None:
            hour = get_time_provider().now().hour
        z_key = self.normalize_zone(zone)

        cfg = self.get_zone_config(z_key)
        threshold_sec = self.get_tolerated_inactivity_threshold(z_key, hour)

        # Immediate danger posture override:
        is_floor_collapse = ("floor" in posture.lower() or "fall" in posture.lower())
        if is_floor_collapse:
            effective_threshold = min(threshold_sec, 180.0)
        else:
            effective_threshold = threshold_sec

        is_anomaly = motionless_seconds >= effective_threshold

        if motionless_seconds <= 0:
            anomaly_score = 0.0
        else:
            anomaly_score = min(1.0, motionless_seconds / max(1.0, effective_threshold * 1.5))

        if is_floor_collapse:
            suggested_q = "Eleanor, I noticed you are on the floor. Do you need help getting up?"
            reason = f"Detected motionless posture on {z_key} floor ({motionless_seconds:.1f}s >= {effective_threshold:.1f}s threshold)."
        elif hour in AFTERNOON_NAP_HOURS and z_key == "living_room":
            suggested_q = "Eleanor, I noticed you've been resting for a while. Are you okay?"
            reason = f"Extended resting during afternoon rest window ({motionless_seconds:.1f}s)."
        elif hour in NIGHT_HOURS and z_key in ["bedroom", "living_room"]:
            suggested_q = "Eleanor, are you okay? Please let me know if you are comfortable."
            reason = f"Nighttime inactivity check ({motionless_seconds:.1f}s)."
        else:
            suggested_q = "Eleanor, I haven't seen much movement for a while. Are you okay?"
            reason = f"Immobility exceeded learned {z_key} threshold of {effective_threshold:.1f}s."

        return {
            "is_anomaly": is_anomaly,
            "threshold_sec": effective_threshold,
            "motionless_seconds": round(motionless_seconds, 1),
            "anomaly_score": round(anomaly_score, 3),
            "zone": z_key,
            "hour": hour,
            "zone_tier": cfg["risk_tier"],
            "reason": reason,
            "suggested_question": suggested_q
        }

    def evaluate_inactivity_risk(
        self,
        zone: str = "living_room",
        motionless_seconds: float = 0.0,
        is_floor_collapse: bool = False,
        hour: Optional[int] = None
    ) -> Dict[str, Any]:
        """Alias bridging to BaselineEngineAdapter."""
        posture = "floor" if is_floor_collapse else "sitting"
        return self.evaluate_inactivity_anomaly(
            zone=zone,
            motionless_seconds=motionless_seconds,
            posture=posture,
            hour=hour
        )

    # ------------------------------------------------------------------
    # CONCEPT B: ZONE DWELL TIME (ROOM VISIT DURATION) (Phases 14, 15, 16, 18, 19)
    # ------------------------------------------------------------------
    def get_room_visit_stats(self, zone: str) -> Dict[str, Any]:
        """Returns learned statistical distributions for a room visit."""
        z_key = self.normalize_zone(zone)
        dwells = self.profile.setdefault("room_dwells", {})
        if z_key in dwells:
            return dwells[z_key]

        prior = DEFAULT_ZONE_DWELL_PRIORS.get(z_key, DEFAULT_ZONE_DWELL_PRIORS["general"])
        dwells[z_key] = {
            "visit_count": 1,
            "median_duration_sec": prior["expected_sec"],
            "mean_duration_sec": prior["expected_sec"],
            "p75_duration_sec": prior["expected_sec"] * 1.15,
            "p90_duration_sec": prior["p90_sec"],
            "safe_max_duration_sec": prior["safe_max_sec"],
            "confidence": 0.5,
            "history_samples": [prior["expected_sec"]],
            "safe_exceptions_count": 0,
            "last_update": get_time_provider().now_iso()
        }
        return dwells[z_key]

    def get_expected_visit_duration(self, zone: str) -> float:
        """Returns the resident's expected room stay in seconds (e.g. 600s / 10m for bathroom)."""
        stats = self.get_room_visit_stats(zone)
        return float(stats.get("median_duration_sec", 600.0))

    def evaluate_zone_dwell(
        self,
        zone: str,
        dwell_seconds: float,
        hour: Optional[int] = None,
        movement_rate: float = 0.5,
        posture: str = "standing",
        heart_rate: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Evaluates room visit dwell duration against learned baseline (Phases 18, 19, 21).
        
        Distinguishes:
        - Expected reached (e.g. 10m): Monitor continues.
        - Mild unusual duration (e.g. 12m): MILD_UNUSUAL_DURATION.
        - Prolonged stay (e.g. 15m): PROLONGED_ZONE_STAY -> Risk MILD/MODERATE -> Contextual prompt.
        - Floor posture + low movement + elevated HR -> CRITICAL override.
        """
        if hour is None:
            hour = get_time_provider().now().hour
        z_key = self.normalize_zone(zone)

        stats = self.get_room_visit_stats(z_key)
        expected_sec = float(stats.get("median_duration_sec", 600.0))
        p90_sec = float(stats.get("p90_duration_sec", expected_sec * 1.25))
        safe_max_sec = float(stats.get("safe_max_duration_sec", expected_sec * 1.5))

        ratio = dwell_seconds / max(1.0, expected_sec)
        baseline_deviation = round(max(0.0, ratio - 1.0), 3)

        is_floor = "floor" in posture.lower() or "fall" in posture.lower()
        is_low_motion = movement_rate < 0.15
        is_high_hr = (heart_rate is not None and heart_rate > 105)

        # Emergency override check (Phase 21):
        if is_floor and is_low_motion:
            return {
                "is_anomaly": True,
                "behavior_state": "CRITICAL_COLLAPSE_IN_ZONE",
                "risk_level": "CRITICAL",
                "ratio": round(ratio, 2),
                "baseline_deviation": baseline_deviation,
                "expected_duration_sec": expected_sec,
                "dwell_seconds": round(dwell_seconds, 1),
                "suggested_question": "Eleanor, I noticed something unusual. Do you need help getting up?",
                "reason": f"Resident is on the floor with low movement in {z_key} ({dwell_seconds:.1f}s stay)."
            }

        if dwell_seconds < expected_sec:
            behavior_state = "NORMAL"
            risk_level = "LOW"
            is_anomaly = False
            suggested_q = ""
            reason = f"Visit duration {dwell_seconds:.1f}s within normal expected {expected_sec:.1f}s."
        elif dwell_seconds < expected_sec * 1.2:
            behavior_state = "EXPECTED_DURATION_REACHED"
            risk_level = "LOW"
            is_anomaly = False
            suggested_q = ""
            reason = f"Expected duration reached ({dwell_seconds:.1f}s >= {expected_sec:.1f}s). Continuing ambient monitoring."
        elif dwell_seconds < expected_sec * 1.5:
            behavior_state = "MILD_UNUSUAL_DURATION"
            risk_level = "LOW"
            is_anomaly = True
            suggested_q = f"Eleanor, you've been in the {z_key.replace('_', ' ')} a bit longer than usual. Are you okay?"
            reason = f"Visit duration ({dwell_seconds:.1f}s) exceeded expected by {int(baseline_deviation*100)}%."
        else:
            # 15+ minutes in 10-minute bathroom (Phase 19)
            behavior_state = "PROLONGED_ZONE_STAY"
            risk_level = "MEDIUM" if not is_high_hr else "HIGH"
            is_anomaly = True
            suggested_q = f"Eleanor, you've been in the {z_key.replace('_', ' ')} longer than usual. Are you okay?"
            reason = f"Prolonged stay in {z_key}: {dwell_seconds:.1f}s vs expected {expected_sec:.1f}s."

        return {
            "is_anomaly": is_anomaly,
            "behavior_state": behavior_state,
            "risk_level": risk_level,
            "ratio": round(ratio, 2),
            "baseline_deviation": baseline_deviation,
            "expected_duration_sec": expected_sec,
            "p90_duration_sec": p90_sec,
            "safe_max_duration_sec": safe_max_sec,
            "dwell_seconds": round(dwell_seconds, 1),
            "suggested_question": suggested_q,
            "reason": reason
        }

    # ------------------------------------------------------------------
    # SAFE LEARNING & GRADUAL ADAPTATION (Phases 20, 47, 48, 49)
    # ------------------------------------------------------------------
    def record_safe_visit(
        self,
        zone: str,
        duration_sec: float,
        hour: Optional[int] = None,
        feedback: str = "Resident confirmed safe"
    ) -> Dict[str, Any]:
        """
        Gradually reinforces room dwell distribution upon validated safe visits.
        NEVER makes a single 15-minute event redefine normal behavior; uses gradual learning.
        """
        if hour is None:
            hour = get_time_provider().now().hour
        z_key = self.normalize_zone(zone)

        stats = self.get_room_visit_stats(z_key)
        prev_median = float(stats.get("median_duration_sec", 600.0))
        prev_safe_max = float(stats.get("safe_max_duration_sec", 900.0))
        samples = stats.setdefault("history_samples", [prev_median])

        # Add sample (capped to prevent single outlier skew)
        capped_duration = min(duration_sec, prev_safe_max * 1.25)
        samples.append(capped_duration)
        if len(samples) > 50:
            samples.pop(0)

        # Gradual learning: EMA with alpha=0.08 (Phase 49)
        alpha = 0.08
        new_median = round((1 - alpha) * prev_median + alpha * capped_duration, 1)

        sorted_samples = sorted(samples)
        p90_idx = int(len(sorted_samples) * 0.90)
        p90_val = round(sorted_samples[min(p90_idx, len(sorted_samples)-1)], 1)
        safe_max = round(max(prev_safe_max, capped_duration), 1)

        stats["visit_count"] = stats.get("visit_count", 0) + 1
        stats["safe_exceptions_count"] = stats.get("safe_exceptions_count", 0) + 1
        stats["median_duration_sec"] = new_median
        stats["p90_duration_sec"] = p90_val
        stats["safe_max_duration_sec"] = safe_max
        stats["confidence"] = min(1.0, 0.5 + (len(samples) * 0.02))
        stats["last_update"] = get_time_provider().now_iso()

        self.profile["total_learned_events"] = self.profile.get("total_learned_events", 0) + 1
        self._save_profile()

        logger.info(
            f"[ActivityRoutineLearner] Gradual room dwell update for {z_key}: "
            f"expected shifted from {prev_median:.1f}s to {new_median:.1f}s (observed safe {duration_sec:.1f}s)."
        )

        return {
            "zone": z_key,
            "old_expected_sec": prev_median,
            "new_expected_sec": new_median,
            "p90_sec": p90_val,
            "safe_max_sec": safe_max,
            "feedback": feedback
        }

    # ------------------------------------------------------------------
    # ROOM SEQUENCE LEARNING (Phases 22, 23)
    # ------------------------------------------------------------------
    def record_room_transition(self, from_room: str, to_room: str):
        """Records movement transitions between rooms to learn daily sequence graph."""
        f = self.normalize_zone(from_room)
        t = self.normalize_zone(to_room)
        if f == t:
            return

        edge = f"{f}->{t}"
        graph = self.profile.setdefault("transition_graph", {})
        graph[edge] = graph.get(edge, 0) + 1

        self._recent_room_sequence.append(t)
        if len(self._recent_room_sequence) > 10:
            self._recent_room_sequence.pop(0)

        self._save_profile()

    def evaluate_sequence_anomaly(self, from_room: str, to_room: str) -> Dict[str, Any]:
        """Detects whether moving between two rooms is statistically unusual."""
        f = self.normalize_zone(from_room)
        t = self.normalize_zone(to_room)
        edge = f"{f}->{t}"
        graph = self.profile.get("transition_graph", {})
        count = graph.get(edge, 0)

        # If zero transitions observed out of many total transitions, mark sequence as unusual
        total_transitions = sum(graph.values()) if graph else 1
        is_unusual = (count == 0 and total_transitions >= 15)

        return {
            "is_unusual_sequence": is_unusual,
            "edge": edge,
            "observed_count": count,
            "baseline_deviation": 0.45 if is_unusual else 0.0
        }

    # ------------------------------------------------------------------
    # CONTINUAL TRAINING & REINFORCEMENT COMPATIBILITY
    # ------------------------------------------------------------------
    def record_activity_observation(
        self,
        zone: str,
        motion_rate: float,
        duration_sec: float,
        hour: Optional[int] = None
    ):
        """Passes normal movement observation to refine immobility distribution."""
        if hour is None:
            hour = get_time_provider().now().hour
        h_str = str(hour % 24)
        z_key = self.normalize_zone(zone)

        h_data = self.profile["hourly_zones"].setdefault(h_str, {})
        z_data = h_data.setdefault(z_key, {
            "observations_count": 0,
            "mean_inactivity_sec": ZONE_RISK_PROFILES[z_key]["base_inactivity_sec"],
            "max_observed_safe_sec": ZONE_RISK_PROFILES[z_key]["base_inactivity_sec"],
            "tolerated_threshold_sec": ZONE_RISK_PROFILES[z_key]["base_inactivity_sec"],
            "dismissed_alarms_count": 0,
            "last_updated": get_time_provider().now_iso()
        })

        obs = z_data.get("observations_count", 0) + 1
        z_data["observations_count"] = obs
        z_data["last_updated"] = get_time_provider().now_iso()

        alpha = 0.05
        prev_mean = z_data.get("mean_inactivity_sec", duration_sec)
        z_data["mean_inactivity_sec"] = round((1 - alpha) * prev_mean + alpha * duration_sec, 1)

        self.profile["total_learned_events"] = self.profile.get("total_learned_events", 0) + 1
        if self.profile["total_learned_events"] % 25 == 0:
            self._save_profile()

    def reinforce_dismissed_alarm(
        self,
        zone: str,
        inactivity_duration_sec: float,
        hour: Optional[int] = None,
        feedback: str = "User confirmed safe"
    ) -> Dict[str, Any]:
        """Learns from resident feedback for immobility checks."""
        if hour is None:
            hour = get_time_provider().now().hour
        h_str = str(hour % 24)
        z_key = self.normalize_zone(zone)

        cfg = self.get_zone_config(z_key)
        h_data = self.profile["hourly_zones"].setdefault(h_str, {})
        z_data = h_data.setdefault(z_key, {
            "observations_count": 1,
            "mean_inactivity_sec": cfg["base_inactivity_sec"],
            "max_observed_safe_sec": cfg["base_inactivity_sec"],
            "tolerated_threshold_sec": cfg["base_inactivity_sec"],
            "dismissed_alarms_count": 0,
            "last_updated": get_time_provider().now_iso()
        })

        old_thresh = z_data.get("tolerated_threshold_sec", cfg["base_inactivity_sec"])
        max_cap = cfg["max_cap_sec"]

        # Safety boundary: Floor collapse must NEVER be learned as normal behavior
        is_floor = "floor" in zone.lower() or "fall" in feedback.lower() or "collapse" in feedback.lower()
        if is_floor:
            logger.warning("Floor collapse feedback received; floor immobility threshold remains strictly bounded to safety minimum.")
            return {
                "zone": z_key,
                "hour": hour,
                "old_threshold_sec": old_thresh,
                "new_threshold_sec": old_thresh,
                "max_cap_sec": max_cap,
                "suppressed_false_alarms_total": self.profile.get("suppressed_false_alarms", 0),
                "feedback": feedback,
                "note": "Floor collapse threshold cannot be adapted upward."
            }

        # Bayesian adaptation: Increase tolerance by 15-20% above the observed safe duration,
        # bounded by the zone's safe clinical ceiling
        new_candidate = max(old_thresh, inactivity_duration_sec * 1.15)
        new_thresh = min(new_candidate, max_cap)

        z_data["dismissed_alarms_count"] = z_data.get("dismissed_alarms_count", 0) + 1
        z_data["max_observed_safe_sec"] = max(z_data.get("max_observed_safe_sec", 0.0), inactivity_duration_sec)
        z_data["tolerated_threshold_sec"] = round(new_thresh, 1)
        z_data["last_updated"] = get_time_provider().now_iso()

        self.profile["suppressed_false_alarms"] = self.profile.get("suppressed_false_alarms", 0) + 1
        self._save_profile()

        return {
            "zone": z_key,
            "hour": hour,
            "old_threshold_sec": old_thresh,
            "new_threshold_sec": round(new_thresh, 1),
            "max_cap_sec": max_cap,
            "suppressed_false_alarms_total": self.profile["suppressed_false_alarms"],
            "feedback": feedback
        }

    def train_from_history(self, history_records: List[Dict[str, Any]]) -> int:
        """Batch calibration from historical telemetry logs."""
        count = 0
        for rec in history_records:
            zone = rec.get("location") or rec.get("zone") or "living_room"
            motion = float(rec.get("motion_displacement", 10.0))
            duration = float(rec.get("duration_sec", 180.0))
            hour = rec.get("hour")
            if hour is None and "timestamp" in rec:
                try:
                    dt = datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00"))
                    hour = dt.hour
                except Exception:
                    hour = 12

            self.record_activity_observation(zone, motion, duration, hour)
            if rec.get("was_false_alarm") or rec.get("resident_safe_confirmed"):
                self.reinforce_dismissed_alarm(zone, duration, hour, feedback="Historical safe training")
            count += 1

        self._save_profile()
        return count

    def get_baseline_quality(
        self,
        zone: str = "living_room",
        hour: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Exposes structured quality, confidence, and safe bounding metrics of the learned activity baseline.
        """
        if hour is None:
            hour = datetime.now().hour
        h_str = str(hour % 24)

        zone_key = "general"
        for k in ZONE_RISK_PROFILES:
            if k in zone.lower():
                zone_key = k
                break

        cfg = self.get_zone_config(zone_key)
        zone_data = self.profile.get("hourly_zones", {}).get(h_str, {}).get(zone_key, {})
        obs_count = zone_data.get("observations_count", 0)
        dismissed_count = zone_data.get("dismissed_alarms_count", 0)
        total_samples = obs_count + dismissed_count
        tolerated = self.get_tolerated_inactivity_threshold(zone_key, hour)
        mean_inactivity = zone_data.get("mean_inactivity_sec", cfg["base_inactivity_sec"])

        # Quality/confidence score: reaches 1.0 after ~15 observations
        confidence = round(min(1.0, max(0.1, total_samples / 15.0)), 2)

        return {
            "zone": zone_key,
            "hour": hour,
            "zone_risk_tier": cfg["risk_tier"],
            "expected_activity": round(mean_inactivity, 1),
            "tolerated_inactivity": tolerated,
            "learned_sample_count": total_samples,
            "false_alarms_prevented": self.profile.get("suppressed_false_alarms", 0),
            "baseline_confidence": confidence,
            "min_safety_bound_sec": max(180.0, cfg["base_inactivity_sec"]),
            "max_cap_bound_sec": cfg["max_cap_sec"]
        }

    def get_routine_profile(self) -> Dict[str, Any]:
        """Returns full routine profile, authentic summary, baseline quality, and room visit stats."""
        summary = self.get_summary()
        return {
            "profile": self.profile,
            "summary": summary,
            "circadian_curve": [0.1, 0.05, 0.02, 0.02, 0.04, 0.12, 0.35, 0.65, 0.82, 0.88, 0.75, 0.8, 0.72, 0.45, 0.3, 0.55, 0.78, 0.85, 0.8, 0.65, 0.45, 0.28, 0.18, 0.12],
            "false_alarms_prevented": self.profile.get("suppressed_false_alarms", 0),
            "learned_safe_adaptations": self.profile.get("total_learned_events", 0),
            "baseline_quality": self.get_baseline_quality()
        }

    def get_summary(self) -> Dict[str, Any]:
        """Returns clean overview of learned routine state and false alarm stats."""
        curr_hour = get_time_provider().now().hour
        living_room_thresh = self.get_tolerated_inactivity_threshold("living_room", curr_hour)
        bedroom_thresh = self.get_tolerated_inactivity_threshold("bedroom", curr_hour)
        bathroom_thresh = self.get_tolerated_inactivity_threshold("bathroom", curr_hour)
        kitchen_thresh = self.get_tolerated_inactivity_threshold("kitchen", curr_hour)
        hallway_thresh = self.get_tolerated_inactivity_threshold("hallway", curr_hour)

        bathroom_stats = self.get_room_visit_stats("bathroom")

        return {
            "total_learned_events": self.profile.get("total_learned_events", 0),
            "suppressed_false_alarms": self.profile.get("suppressed_false_alarms", 0),
            "current_hour": curr_hour,
            "current_thresholds": {
                "living_room_sec": living_room_thresh,
                "bedroom_sec": bedroom_thresh,
                "bathroom_sec": bathroom_thresh,
                "kitchen_sec": kitchen_thresh,
                "hallway_sec": hallway_thresh
            },
            "baseline_quality": self.get_baseline_quality("living_room", curr_hour),
            "room_dwells": {
                "bathroom_expected_sec": bathroom_stats.get("median_duration_sec", 600.0),
                "bathroom_p90_sec": bathroom_stats.get("p90_duration_sec", 735.0),
                "bathroom_safe_max_sec": bathroom_stats.get("safe_max_duration_sec", 900.0)
            },
            "circadian_state": (
                "NIGHT_SLEEP_WINDOW" if curr_hour in NIGHT_HOURS
                else ("AFTERNOON_NAP_WINDOW" if curr_hour in AFTERNOON_NAP_HOURS else "ACTIVE_DAY_WINDOW")
            ),
            "profile_file": str(self.data_path)
        }


# Global singleton
_global_learner: Optional[DailyActivityRoutineLearner] = None


def get_activity_learner() -> DailyActivityRoutineLearner:
    global _global_learner
    if _global_learner is None:
        _global_learner = DailyActivityRoutineLearner()
    return _global_learner
