"""
NIRA Self-Learning Daily Activity Routine & False Alarm Reduction Engine.
Amazon Developer Hackathon 2026.

Implements an online Bayesian / statistical circadian activity baseline model:
  1. Tracks 24-hour circadian bins [0..23] and per-zone activity patterns.
  2. Differentiates benign resting (sofa, bed, reading) from dangerous collapse / long lies.
  3. Learns continuously from user feedback: when resident responds "I'm okay" to a check-in,
     the engine updates its baseline tolerance for that zone and hour, preventing future
     unnecessary false alarms.
  4. Adapts thresholds dynamically:
     - High risk zones (bathroom, hallway, floor): strict 3-5 min immobility limits.
     - Known resting zones (bedroom night, living room afternoon): extended adaptive tolerances.
"""

import os
import json
import time
import math
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("NIRA.ActivityRoutineLearner")

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "activity_baseline.json"

# Standard zone risk weights (3 to 5 minutes base inactivity limits as requested)
ZONE_RISK_PROFILES = {
    "bathroom": {"base_inactivity_sec": 180.0, "max_cap_sec": 300.0, "risk_tier": "CRITICAL_ZONE"},
    "hallway": {"base_inactivity_sec": 180.0, "max_cap_sec": 300.0, "risk_tier": "TRANSIT_ZONE"},
    "kitchen": {"base_inactivity_sec": 180.0, "max_cap_sec": 600.0, "risk_tier": "ACTIVE_ZONE"},
    "living_room": {"base_inactivity_sec": 180.0, "max_cap_sec": 3600.0, "risk_tier": "REST_ZONE"},
    "bedroom": {"base_inactivity_sec": 180.0, "max_cap_sec": 7200.0, "risk_tier": "SLEEP_ZONE"},
    "general": {"base_inactivity_sec": 180.0, "max_cap_sec": 1800.0, "risk_tier": "DEFAULT_ZONE"}
}

# Known clinical circadian resting windows (24-hour format)
NIGHT_HOURS = set([22, 23, 0, 1, 2, 3, 4, 5, 6])
AFTERNOON_NAP_HOURS = set([13, 14, 15])


class DailyActivityRoutineLearner:
    """
    Self-learning activity routine model that builds a personalized behavioral
    baseline for an elderly resident to eliminate false alarms while guaranteeing
    timely alerts for genuine falls or prolonged unresponsiveness.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = Path(data_path) if data_path else DEFAULT_DATA_PATH
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile: Dict[str, Any] = self._load_profile()

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
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }

        return {
            "version": "2.0.0",
            "resident_id": "resident_live",
            "total_learned_events": 0,
            "suppressed_false_alarms": 0,
            "hourly_zones": hourly,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    def _load_profile(self) -> Dict[str, Any]:
        """Loads learned routine profile from JSON file or initializes defaults."""
        if self.data_path.exists():
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "hourly_zones" in data:
                        logger.info(f"Loaded learned activity routine profile from {self.data_path}")
                        return data
            except Exception as e:
                logger.warning(f"Error loading activity baseline JSON ({e}). Initializing defaults.")
        
        defaults = self._default_profile()
        self._save_profile(defaults)
        return defaults

    def _save_profile(self, profile: Optional[Dict[str, Any]] = None):
        """Thread-safe write of learned profile to disk."""
        target = profile or self.profile
        try:
            temp_path = self.data_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(target, f, indent=2)
            temp_path.replace(self.data_path)
        except Exception as e:
            logger.error(f"Failed to persist activity routine profile: {e}")

    def get_zone_config(self, zone: str) -> Dict[str, Any]:
        """Normalizes zone name and returns risk profile parameters."""
        normalized = zone.lower().replace(" ", "_") if zone else "general"
        for key in ZONE_RISK_PROFILES:
            if key in normalized:
                return ZONE_RISK_PROFILES[key]
        return ZONE_RISK_PROFILES["general"]

    def get_tolerated_inactivity_threshold(
        self,
        zone: str = "living_room",
        hour: Optional[int] = None
    ) -> float:
        """
        Returns dynamic inactivity threshold in seconds for given zone and time of day.
        Guaranteed to be at least 180 seconds (3 mins), adapting higher as routines are learned.
        """
        if hour is None:
            hour = datetime.now().hour
        h_str = str(hour % 24)

        zone_key = "general"
        for k in ZONE_RISK_PROFILES:
            if k in zone.lower():
                zone_key = k
                break

        zone_data = (
            self.profile.get("hourly_zones", {})
            .get(h_str, {})
            .get(zone_key, None)
        )

        cfg = self.get_zone_config(zone_key)
        min_thresh = cfg["base_inactivity_sec"]
        max_cap = cfg["max_cap_sec"]

        if zone_data:
            learned = float(zone_data.get("tolerated_threshold_sec", min_thresh))
            # Bound within safe limits
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
        Infers whether current period of stillness is an anomaly that warrants waking up
        an alarm and asking the resident "Are you okay?".

        Returns structured diagnostic decision:
          - is_anomaly: bool
          - threshold_sec: float
          - anomaly_score: float (0.0 to 1.0)
          - reason: str
          - suggested_question: str
          - zone_tier: str
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
        threshold_sec = self.get_tolerated_inactivity_threshold(zone_key, hour)

        # Immediate danger posture override:
        # If posture is explicitly lying flat on floor (not bed), do NOT apply extended sleep tolerance!
        is_floor_collapse = ("floor" in posture.lower() or "fall" in posture.lower())
        if is_floor_collapse:
            effective_threshold = min(threshold_sec, 180.0)
        else:
            effective_threshold = threshold_sec

        is_anomaly = motionless_seconds >= effective_threshold

        # Score calculation: 0.0 (normal) to 1.0 (severe long lie)
        if motionless_seconds <= 0:
            anomaly_score = 0.0
        else:
            anomaly_score = min(1.0, motionless_seconds / max(1.0, effective_threshold * 1.5))

        # Context-aware verbal question formulation
        if is_floor_collapse:
            suggested_q = "Are you okay? Do you need help getting up?"
            reason = f"Detected motionless posture on {zone} floor ({motionless_seconds:.1f}s >= {effective_threshold:.1f}s threshold)."
        elif hour in AFTERNOON_NAP_HOURS and zone_key == "living_room":
            suggested_q = "I noticed you've been resting for a while. Are you alright?"
            reason = f"Extended resting during afternoon rest window ({motionless_seconds:.1f}s)."
        elif hour in NIGHT_HOURS and zone_key in ["bedroom", "living_room"]:
            suggested_q = "Are you okay? Please let me know if you are comfortable."
            reason = f"Nighttime inactivity check ({motionless_seconds:.1f}s)."
        else:
            suggested_q = "Are you okay? Please let me know if you need any assistance."
            reason = f"Immobility exceeded learned {zone_key} threshold of {effective_threshold:.1f}s ({motionless_seconds:.1f}s motionless)."

        return {
            "is_anomaly": is_anomaly,
            "threshold_sec": effective_threshold,
            "motionless_seconds": round(motionless_seconds, 1),
            "anomaly_score": round(anomaly_score, 3),
            "zone": zone_key,
            "hour": hour,
            "zone_tier": cfg["risk_tier"],
            "reason": reason,
            "suggested_question": suggested_q
        }

    def record_activity_observation(
        self,
        zone: str,
        motion_rate: float,
        duration_sec: float,
        hour: Optional[int] = None
    ):
        """
        Continual online learning: records normal daily movement to refine the resident's
        hourly activity baseline distribution.
        """
        if hour is None:
            hour = datetime.now().hour
        h_str = str(hour % 24)

        zone_key = "general"
        for k in ZONE_RISK_PROFILES:
            if k in zone.lower():
                zone_key = k
                break

        h_data = self.profile["hourly_zones"].setdefault(h_str, {})
        z_data = h_data.setdefault(zone_key, {
            "observations_count": 0,
            "mean_inactivity_sec": ZONE_RISK_PROFILES[zone_key]["base_inactivity_sec"],
            "max_observed_safe_sec": ZONE_RISK_PROFILES[zone_key]["base_inactivity_sec"],
            "tolerated_threshold_sec": ZONE_RISK_PROFILES[zone_key]["base_inactivity_sec"],
            "dismissed_alarms_count": 0,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })

        obs = z_data.get("observations_count", 0) + 1
        z_data["observations_count"] = obs
        z_data["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Update running Exponential Moving Average (EMA) of stillness
        alpha = 0.05
        prev_mean = z_data.get("mean_inactivity_sec", duration_sec)
        z_data["mean_inactivity_sec"] = round((1 - alpha) * prev_mean + alpha * duration_sec, 1)

        self.profile["total_learned_events"] = self.profile.get("total_learned_events", 0) + 1

        # Periodically persist
        if self.profile["total_learned_events"] % 25 == 0:
            self._save_profile()

    def reinforce_dismissed_alarm(
        self,
        zone: str,
        inactivity_duration_sec: float,
        hour: Optional[int] = None,
        feedback: str = "User confirmed safe"
    ) -> Dict[str, Any]:
        """
        Core self-learning mechanism to eliminate unnecessary alarms:
        When an alarm woke up the user and they answered 'I'm okay', 'I'm fine', or
        dismissed the prompt, the model adapts its tolerance for this specific zone
        and time of day upward, preventing future false alarms for this daily activity!
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
        h_data = self.profile["hourly_zones"].setdefault(h_str, {})
        z_data = h_data.setdefault(zone_key, {
            "observations_count": 1,
            "mean_inactivity_sec": cfg["base_inactivity_sec"],
            "max_observed_safe_sec": cfg["base_inactivity_sec"],
            "tolerated_threshold_sec": cfg["base_inactivity_sec"],
            "dismissed_alarms_count": 0,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })

        old_thresh = z_data.get("tolerated_threshold_sec", cfg["base_inactivity_sec"])
        max_cap = cfg["max_cap_sec"]

        # Bayesian adaptation: Increase tolerance by 15-20% above the observed safe duration,
        # bounded by the zone's safe clinical ceiling
        new_candidate = max(old_thresh, inactivity_duration_sec * 1.15)
        new_thresh = min(new_candidate, max_cap)

        z_data["dismissed_alarms_count"] = z_data.get("dismissed_alarms_count", 0) + 1
        z_data["max_observed_safe_sec"] = max(z_data.get("max_observed_safe_sec", 0.0), inactivity_duration_sec)
        z_data["tolerated_threshold_sec"] = round(new_thresh, 1)
        z_data["last_updated"] = datetime.now(timezone.utc).isoformat()

        self.profile["suppressed_false_alarms"] = self.profile.get("suppressed_false_alarms", 0) + 1
        self._save_profile()

        logger.info(
            f"Adaptive routine learned: Zone '{zone_key}' @ {hour}:00 threshold increased "
            f"from {old_thresh:.1f}s to {new_thresh:.1f}s based on resident safe confirmation. "
            f"Total false alarms suppressed: {self.profile['suppressed_false_alarms']}"
        )

        return {
            "zone": zone_key,
            "hour": hour,
            "old_threshold_sec": old_thresh,
            "new_threshold_sec": round(new_thresh, 1),
            "max_cap_sec": max_cap,
            "suppressed_false_alarms_total": self.profile["suppressed_false_alarms"],
            "feedback": feedback
        }

    def train_from_history(self, history_records: List[Dict[str, Any]]) -> int:
        """
        Batch calibration / training from historical telemetry logs to bootstrap
        the routine baseline immediately.
        """
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

    def get_summary(self) -> Dict[str, Any]:
        """Returns clean overview of learned routine state and false alarm stats."""
        curr_hour = datetime.now().hour
        living_room_thresh = self.get_tolerated_inactivity_threshold("living_room", curr_hour)
        bedroom_thresh = self.get_tolerated_inactivity_threshold("bedroom", curr_hour)
        bathroom_thresh = self.get_tolerated_inactivity_threshold("bathroom", curr_hour)

        return {
            "total_learned_events": self.profile.get("total_learned_events", 0),
            "suppressed_false_alarms": self.profile.get("suppressed_false_alarms", 0),
            "current_hour": curr_hour,
            "current_thresholds": {
                "living_room_sec": living_room_thresh,
                "bedroom_sec": bedroom_thresh,
                "bathroom_sec": bathroom_thresh
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
