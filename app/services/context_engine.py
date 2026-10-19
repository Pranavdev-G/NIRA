"""
Context Engine for Aegis Ambient Care.
Amazon Developer Hackathon 2026.

Merges raw vision event JSON with:
  - Environmental factors (lighting, moisture, floor surface, noise)
  - Activity type (sleeping, showering, cooking, walking, resting)
  - Location hazard weighting (bathroom, stairs, kitchen, bedroom)
  - Circadian time-of-day slots
Produces enriched contextual risk scoring and explainable safety rationale.
"""

from typing import Dict, Any, List, Tuple, Optional
from app.models.schemas import Event, Context


class ContextEngine:
    """
    Context synthesis engine that evaluates situational hazards and environmental amplifiers.
    """

    # Room hazard coefficients based on geriatric fall epidemiology
    LOCATION_HAZARD_WEIGHTS: Dict[str, float] = {
        "bathroom": 1.55,
        "shower": 1.60,
        "toilet": 1.50,
        "stairs": 1.65,
        "stairway": 1.65,
        "kitchen": 1.25,
        "hallway": 1.10,
        "living_room": 1.00,
        "bedroom": 0.85,
        "patio": 1.15
    }

    # Baseline activity risk profiles
    ACTIVITY_RISK_WEIGHTS: Dict[str, float] = {
        "showering": 1.45,
        "bathing": 1.45,
        "descending_stairs": 1.55,
        "ascending_stairs": 1.35,
        "cooking": 1.20,
        "walking_to_kitchen": 1.15,
        "walking": 1.10,
        "exercising": 1.05,
        "getting_out_of_bed": 1.25,  # Orthostatic hypotension vulnerability
        "resting": 0.80,
        "reading": 0.75,
        "sleeping": 0.70
    }

    @classmethod
    def get_location_hazard(cls, location: str) -> Tuple[float, Optional[str]]:
        """Returns multiplier and explanation for room location."""
        loc_clean = location.lower().replace(" ", "_")
        for key, weight in cls.LOCATION_HAZARD_WEIGHTS.items():
            if key in loc_clean:
                explanation = f"High-hazard location '{location}' (hazard multiplier: {weight:.2f}x)"
                return weight, explanation
        return 1.0, None

    @classmethod
    def get_environmental_hazards(cls, environment: str) -> Tuple[float, List[str]]:
        """Evaluates environmental factors like moisture, lighting, and clutter."""
        env_clean = environment.lower()
        score_add = 0.0
        reasons = []

        if "wet" in env_clean or "moisture" in env_clean:
            score_add += 12.0
            reasons.append("Slippery surface / wet floor condition detected")

        if "dark" in env_clean or "dim" in env_clean or "unlit" in env_clean:
            score_add += 8.0
            reasons.append(f"Compounding poor ambient lighting condition ('{environment}')")

        if "obstacle" in env_clean or "clutter" in env_clean:
            score_add += 7.0
            reasons.append("Trip hazard / floor obstacle identified in environment")

        return score_add, reasons

    @classmethod
    def evaluate_temporal_vulnerability(cls, time_context: str) -> Tuple[float, Optional[str]]:
        """Assesses circadian vulnerability (nighttime vs daytime)."""
        time_clean = time_context.lower()
        if "night" in time_clean or "midnight" in time_clean or "late" in time_clean:
            return 10.0, f"Off-peak nocturnal temporal window ('{time_context}') - delayed natural discovery risk"
        elif "early_morning" in time_clean or "dawn" in time_clean:
            return 5.0, f"Early morning transition window ('{time_context}')"
        return 0.0, None

    @classmethod
    def merge_and_enrich(cls, event: Event, context: Context) -> Dict[str, Any]:
        """
        Synthesizes event and contextual layers into a structured enrichment bundle.
        """
        loc_mult, loc_reason = cls.get_location_hazard(event.location)
        env_score, env_reasons = cls.get_environmental_hazards(context.environment)
        temporal_score, temporal_reason = cls.evaluate_temporal_vulnerability(context.time_context)

        # Activity factor
        act_clean = context.activity.lower().replace(" ", "_")
        act_weight = 1.0
        for act_key, weight in cls.ACTIVITY_RISK_WEIGHTS.items():
            if act_key in act_clean:
                act_weight = weight
                break

        composite_reasons = []
        if loc_reason:
            composite_reasons.append(loc_reason)
        composite_reasons.extend(env_reasons)
        if temporal_reason:
            composite_reasons.append(temporal_reason)

        return {
            "location_multiplier": loc_mult,
            "activity_weight": act_weight,
            "environmental_hazard_score": env_score,
            "temporal_vulnerability_score": temporal_score,
            "context_reasons": composite_reasons,
            "merged_timestamp": event.timestamp,
            "monitored_room": event.location,
            "activity": context.activity
        }
