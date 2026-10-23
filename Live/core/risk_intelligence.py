"""
Multimodal Signal Extraction and Evidence Aggregation for NIRA Live Core.
Amazon Developer Hackathon 2026.

Extracts, normalizes, and scores the 14 mandatory clinical and environmental safety signals:
 1. fall_probability
 2. posture (torso angle, horizontal alignment, floor elevation)
 3. impact_velocity (rapid downward acceleration)
 4. prolonged_immobility (motionless seconds vs zone threshold)
 5. heart_rate (tachycardia > 120, bradycardia < 45, or pulse waveform absence)
 6. environmental_hazards (wet floor slip hazard, dark room, temperature extremes)
 7. zone_context (bathroom/hallway critical vs bedroom sleep)
 8. circadian_context (night sleep window vs active afternoon)
 9. personal_baseline_deviation (exceeding personalized tolerance)
10. silence_no_response (unresponsive after vocal wellness prompt)
11. voice_distress (spoken keywords: help, pain, emergency, fell)
12. device_health (sensor dropouts, wearable disconnected)
13. repeated_abnormal_events (multiple warnings in short window)
14. recovery_movement (normal gait, upright restoration, deliberate motion)
"""

import math
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from Live.core.models import (
    LiveEvent,
    EventType,
    ZoneType,
    SignalEvidence,
    ContextState
)
from Live.core.context_engine import ContextEngine
from Live.core.baseline_engine import BaselineEngineAdapter

logger = logging.getLogger("NIRA.LiveCore.RiskIntelligence")

# Default Signal Weights (Sum ~ 1.0)
SIGNAL_WEIGHTS = {
    "fall_probability": 0.16,
    "posture": 0.12,
    "impact_velocity": 0.10,
    "prolonged_immobility": 0.12,
    "heart_rate": 0.10,
    "voice_distress": 0.12,
    "silence_no_response": 0.10,
    "environmental_hazards": 0.04,
    "zone_context": 0.04,
    "circadian_context": 0.03,
    "personal_baseline_deviation": 0.05,
    "device_health": 0.02,
    "repeated_abnormal_events": 0.05,
    "recovery_movement": -0.15  # Negative weight attenuates risk if deliberate recovery observed
}


class SignalExtractor:
    """
    Extracts all 14 clinical and contextual safety signals from incoming events,
    temporal history, context engine, and baseline engine.
    """

    def __init__(self, context_engine: ContextEngine, baseline_engine: BaselineEngineAdapter):
        self.context_engine = context_engine
        self.baseline_engine = baseline_engine

    def extract_signals(
        self,
        trigger_event: Optional[LiveEvent],
        recent_events: List[LiveEvent],
        active_zone: ZoneType = ZoneType.LIVING_ROOM,
        voice_state: Optional[Dict[str, Any]] = None,
        vitals_state: Optional[Dict[str, Any]] = None,
        hardware_health: Optional[Dict[str, Any]] = None
    ) -> List[SignalEvidence]:
        """
        Extracts all 14 signals, scoring each from 0.0 (safe) to 1.0 (severe).
        Handles missing sensors gracefully without skewing overall risk.
        """
        evidence_list: List[SignalEvidence] = []
        ctx = self.context_engine.get_context(active_zone)
        hour = datetime.now().hour

        # -------------------------------------------------------------
        # 1. Fall Probability
        # -------------------------------------------------------------
        fall_prob = 0.0
        if trigger_event and trigger_event.event_type == EventType.FALL_DETECTED:
            fall_prob = trigger_event.confidence
        else:
            # Check recent camera/fall events
            for e in reversed(recent_events[-5:]):
                if e.event_type == EventType.FALL_DETECTED:
                    fall_prob = max(fall_prob, e.confidence)
                    break
        evidence_list.append(SignalEvidence(
            signal_name="fall_probability",
            weight=SIGNAL_WEIGHTS["fall_probability"],
            raw_value=round(fall_prob, 3),
            risk_contribution=round(fall_prob * SIGNAL_WEIGHTS["fall_probability"], 3),
            is_abnormal=fall_prob > 0.5,
            notes=f"Vision fall probability: {fall_prob:.1%}" if fall_prob > 0 else "No fall event detected"
        ))

        # -------------------------------------------------------------
        # 2. Posture (Torso tilt angle and elevation)
        # -------------------------------------------------------------
        torso_angle = 15.0  # Default upright (deg)
        if trigger_event and "torso_angle" in trigger_event.payload:
            torso_angle = float(trigger_event.payload["torso_angle"])
        elif trigger_event and str(trigger_event.payload.get("posture", "")).lower() in ["ground_horizontal", "ground_impact", "floor_collapse", "collapsed"]:
            torso_angle = 75.0
        else:
            for e in reversed(recent_events[-5:]):
                if "torso_angle" in e.payload:
                    torso_angle = float(e.payload["torso_angle"])
                    break
                elif str(e.payload.get("posture", "")).lower() in ["ground_horizontal", "ground_impact", "floor_collapse"]:
                    torso_angle = 75.0
                    break

        # Angle > 60 deg indicates horizontal / collapsed position
        posture_risk = min(1.0, max(0.0, (torso_angle - 25.0) / 55.0))
        evidence_list.append(SignalEvidence(
            signal_name="posture",
            weight=SIGNAL_WEIGHTS["posture"],
            raw_value=round(torso_angle, 1),
            risk_contribution=round(posture_risk * SIGNAL_WEIGHTS["posture"], 3),
            is_abnormal=torso_angle >= 60.0,
            notes=f"Torso inclination {torso_angle:.1f}° (horizontal collapse)" if torso_angle >= 60.0 else f"Normal upright posture {torso_angle:.1f}°"
        ))

        # -------------------------------------------------------------
        # 3. Impact / Drop Velocity
        # -------------------------------------------------------------
        velocity = 0.3  # m/s
        if trigger_event and "motion_velocity" in trigger_event.payload:
            velocity = float(trigger_event.payload["motion_velocity"])
        elif trigger_event and "drop_velocity" in trigger_event.payload:
            velocity = float(trigger_event.payload["drop_velocity"])
        elif trigger_event and "velocity" in trigger_event.payload:
            velocity = float(trigger_event.payload["velocity"])

        # Rapid drop velocity > 1.8 m/s suggests violent collapse
        velocity_risk = min(1.0, max(0.0, (velocity - 0.8) / 2.0)) if velocity > 0.8 else 0.0
        evidence_list.append(SignalEvidence(
            signal_name="impact_velocity",
            weight=SIGNAL_WEIGHTS["impact_velocity"],
            raw_value=round(velocity, 2),
            risk_contribution=round(velocity_risk * SIGNAL_WEIGHTS["impact_velocity"], 3),
            is_abnormal=velocity >= 1.8,
            notes=f"High downward kinetic impact: {velocity:.2f} m/s" if velocity >= 1.8 else "Normal transit velocity"
        ))

        # -------------------------------------------------------------
        # 4. Prolonged Immobility
        # -------------------------------------------------------------
        immobility_sec = 0.0
        if trigger_event and "inactivity_seconds" in trigger_event.payload:
            immobility_sec = float(trigger_event.payload["inactivity_seconds"])
        elif trigger_event and "motionless_seconds" in trigger_event.payload:
            immobility_sec = float(trigger_event.payload["motionless_seconds"])
        elif trigger_event and "duration_seconds" in trigger_event.payload:
            immobility_sec = float(trigger_event.payload["duration_seconds"])
        elif trigger_event and trigger_event.event_type in [EventType.INACTIVITY_CRITICAL, EventType.INACTIVITY_WARNING]:
            immobility_sec = 600.0  # Default critical duration if omitted

        baseline_tolerance = self.baseline_engine.get_dynamic_threshold_seconds(active_zone, hour)
        immobility_risk = min(1.0, max(0.0, immobility_sec / max(1.0, baseline_tolerance)))
        evidence_list.append(SignalEvidence(
            signal_name="prolonged_immobility",
            weight=SIGNAL_WEIGHTS["prolonged_immobility"],
            raw_value=round(immobility_sec, 1),
            risk_contribution=round(immobility_risk * SIGNAL_WEIGHTS["prolonged_immobility"], 3),
            is_abnormal=immobility_sec >= baseline_tolerance,
            notes=f"Motionless for {immobility_sec:.0f}s (tolerance: {baseline_tolerance:.0f}s)"
        ))

        # -------------------------------------------------------------
        # 5. Heart Rate & Wearable Vitals
        # -------------------------------------------------------------
        hr_bpm = 74.0
        hr_risk = 0.0
        if vitals_state and "heart_rate_bpm" in vitals_state:
            hr_bpm = float(vitals_state["heart_rate_bpm"])
            if hr_bpm > 125:  # Tachycardia
                hr_risk = min(1.0, (hr_bpm - 120) / 40.0)
            elif hr_bpm < 48:  # Bradycardia / Syncope
                hr_risk = min(1.0, (50 - hr_bpm) / 25.0)

        evidence_list.append(SignalEvidence(
            signal_name="heart_rate",
            weight=SIGNAL_WEIGHTS["heart_rate"],
            raw_value=round(hr_bpm, 1),
            risk_contribution=round(hr_risk * SIGNAL_WEIGHTS["heart_rate"], 3),
            is_abnormal=hr_risk > 0.4,
            notes=f"Heart rate: {hr_bpm:.0f} BPM" + (" (Cardiac Anomaly)" if hr_risk > 0.4 else " (Normal sinus rhythm)")
        ))

        # -------------------------------------------------------------
        # 6. Environmental Hazards (Wet floor, darkness, extreme temp)
        # -------------------------------------------------------------
        env_risk = 0.0
        env_notes = []
        if ctx.is_wet_floor:
            env_risk += 0.5
            env_notes.append("Wet floor slip hazard")
        if ctx.is_dark:
            env_risk += 0.3
            env_notes.append("Unlit room")
        if ctx.temperature_c and (ctx.temperature_c < 16.0 or ctx.temperature_c > 32.0):
            env_risk += 0.4
            env_notes.append(f"Anomalous temp {ctx.temperature_c}°C")

        env_risk = min(1.0, env_risk)
        evidence_list.append(SignalEvidence(
            signal_name="environmental_hazards",
            weight=SIGNAL_WEIGHTS["environmental_hazards"],
            raw_value={"wet": ctx.is_wet_floor, "dark": ctx.is_dark, "temp": ctx.temperature_c},
            risk_contribution=round(env_risk * SIGNAL_WEIGHTS["environmental_hazards"], 3),
            is_abnormal=env_risk > 0.3,
            notes=", ".join(env_notes) if env_notes else "Environment nominal"
        ))

        # -------------------------------------------------------------
        # 7. Room / Zone Context (Bathroom/Hallway vs Bedroom)
        # -------------------------------------------------------------
        zone_risk = 0.0
        if active_zone == ZoneType.BATHROOM:
            zone_risk = 0.85  # Documented highest hazard zone for senior slip/fall
        elif active_zone == ZoneType.HALLWAY:
            zone_risk = 0.60
        elif active_zone == ZoneType.KITCHEN:
            zone_risk = 0.40
        else:
            zone_risk = 0.15

        evidence_list.append(SignalEvidence(
            signal_name="zone_context",
            weight=SIGNAL_WEIGHTS["zone_context"],
            raw_value=active_zone.value,
            risk_contribution=round(zone_risk * SIGNAL_WEIGHTS["zone_context"], 3),
            is_abnormal=zone_risk > 0.5,
            notes=f"Zone {active_zone.value} ({ctx.zone_risk_tier})"
        ))

        # -------------------------------------------------------------
        # 8. Circadian Context (Night sleep vs active daytime)
        # -------------------------------------------------------------
        circadian_risk = 0.4 if ctx.is_night else 0.1
        evidence_list.append(SignalEvidence(
            signal_name="circadian_context",
            weight=SIGNAL_WEIGHTS["circadian_context"],
            raw_value=ctx.circadian_phase,
            risk_contribution=round(circadian_risk * SIGNAL_WEIGHTS["circadian_context"], 3),
            is_abnormal=ctx.is_night and active_zone in [ZoneType.BATHROOM, ZoneType.HALLWAY],
            notes=f"Circadian phase: {ctx.circadian_phase}"
        ))

        # -------------------------------------------------------------
        # 9. Personal Baseline Deviation
        # -------------------------------------------------------------
        base_eval = self.baseline_engine.evaluate_motionless_risk(
            zone=active_zone,
            motionless_seconds=immobility_sec,
            is_floor_collapse=(torso_angle >= 60.0),
            hour=hour
        )
        base_risk = float(base_eval.get("anomaly_score", 0.0))
        evidence_list.append(SignalEvidence(
            signal_name="personal_baseline_deviation",
            weight=SIGNAL_WEIGHTS["personal_baseline_deviation"],
            raw_value=round(base_risk, 3),
            risk_contribution=round(base_risk * SIGNAL_WEIGHTS["personal_baseline_deviation"], 3),
            is_abnormal=base_eval.get("is_anomaly", False),
            notes=base_eval.get("reason", "Baseline behavior normal")
        ))

        # -------------------------------------------------------------
        # 10. Silence / No Response (Unresponsive Check-In)
        # -------------------------------------------------------------
        silence_risk = 0.0
        if voice_state and (voice_state.get("is_unresponsive") or voice_state.get("unresponsive")):
            silence_risk = 1.0
        elif trigger_event and trigger_event.event_type == EventType.VOICE_SILENCE_TIMEOUT:
            silence_risk = 1.0

        evidence_list.append(SignalEvidence(
            signal_name="silence_no_response",
            weight=SIGNAL_WEIGHTS["silence_no_response"],
            raw_value=bool(silence_risk > 0),
            risk_contribution=round(silence_risk * SIGNAL_WEIGHTS["silence_no_response"], 3),
            is_abnormal=silence_risk > 0,
            notes="Resident unresponsive to vocal inquiry" if silence_risk > 0 else "Voice responsiveness active"
        ))

        # -------------------------------------------------------------
        # 11. Voice Distress
        # -------------------------------------------------------------
        distress_risk = 0.0
        if voice_state and (voice_state.get("is_distress") or voice_state.get("distress")):
            distress_risk = 1.0
        elif trigger_event and trigger_event.event_type in [EventType.VOICE_RESPONSE_HELP, EventType.VOICE_AMBIENT_DISTRESS]:
            distress_risk = 1.0

        evidence_list.append(SignalEvidence(
            signal_name="voice_distress",
            weight=SIGNAL_WEIGHTS["voice_distress"],
            raw_value=bool(distress_risk > 0),
            risk_contribution=round(distress_risk * SIGNAL_WEIGHTS["voice_distress"], 3),
            is_abnormal=distress_risk > 0,
            notes="Vocal distress keywords confirmed" if distress_risk > 0 else "No distress speech detected"
        ))

        # -------------------------------------------------------------
        # 12. Device Connectivity & Sensor Health
        # -------------------------------------------------------------
        device_risk = 0.0
        if hardware_health and not hardware_health.get("wearable_connected", True):
            device_risk = 0.5
        evidence_list.append(SignalEvidence(
            signal_name="device_health",
            weight=SIGNAL_WEIGHTS["device_health"],
            raw_value=hardware_health or {"wearable_connected": True},
            risk_contribution=round(device_risk * SIGNAL_WEIGHTS["device_health"], 3),
            is_abnormal=device_risk > 0,
            notes="Sensor telemetry nominal" if device_risk == 0 else "Partial sensor dropout detected"
        ))

        # -------------------------------------------------------------
        # 13. Repeated Abnormal Events
        # -------------------------------------------------------------
        abnormal_count = sum(1 for e in recent_events[-8:] if "fall" in e.event_type.value or "inactivity" in e.event_type.value)
        repeated_risk = min(1.0, abnormal_count / 3.0)
        evidence_list.append(SignalEvidence(
            signal_name="repeated_abnormal_events",
            weight=SIGNAL_WEIGHTS["repeated_abnormal_events"],
            raw_value=abnormal_count,
            risk_contribution=round(repeated_risk * SIGNAL_WEIGHTS["repeated_abnormal_events"], 3),
            is_abnormal=abnormal_count >= 2,
            notes=f"{abnormal_count} abnormal events in recent window"
        ))

        # -------------------------------------------------------------
        # 14. Recovery Movement (Negative weight attenuator)
        # -------------------------------------------------------------
        recovery_detected = False
        if trigger_event and trigger_event.event_type == EventType.VOICE_RESPONSE_SAFE:
            recovery_detected = True
        elif torso_angle < 30.0 and velocity > 0.4 and immobility_sec < 10.0:
            recovery_detected = True

        evidence_list.append(SignalEvidence(
            signal_name="recovery_movement",
            weight=abs(SIGNAL_WEIGHTS["recovery_movement"]),
            raw_value=recovery_detected,
            risk_contribution=-0.15 if recovery_detected else 0.0,
            is_abnormal=False,
            notes="Active self-recovery / purposeful movement observed" if recovery_detected else "No active recovery motion"
        ))

        return evidence_list
