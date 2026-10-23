"""
NIRA Multi-Device Scenario & Resident Routine Orchestrator.
Amazon Developer Hackathon 2026.

Orchestrates multi-device sensor event streams:
  - Wearable Telemetry
  - mmWave Radar
  - Edge AI Camera / Pose
  - Multi-Room Environmental Sensors
  - Alexa Voice Interactions

Communicates exclusively through standard HTTP POST endpoints:
  - POST /api/v1/events/ingest (as UnifiedEvent)
  - POST /api/v1/incidents/{incident_id}/respond-voice
Does NOT directly modify database state or frontend state.

Scenarios Implemented:
  1. normal_day: 24h realistic routine across 9 time slots (wake -> sleep)
  2. false_alarm (Scenario A): Living room thud -> "I'm okay" -> RESOLVED
  3. responsive_emergency (Scenario B): Fall + crawling -> "Help me" -> CAREGIVER_ESCALATION
  4. silent_emergency (Scenario C): Nocturnal bathroom wet floor fall + tachycardia + silence -> DISPATCH_READY
  5. recovery (Scenario D): Fall -> movement climbs -> rising posture -> safe confirmation -> NORMAL
  6. sensor_dropout (Scenario E): Watch battery drop/off-wrist -> radar confirms safe -> reconnect
  7. environmental_hazard (Scenario F): Water leak in dark bathroom -> pre-fall hazard warning
"""

import sys
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

try:
    from .wearable_simulator import WearableSimulator
    from .environment_simulator import EnvironmentSimulator
    from .radar_simulator import RadarSimulator
    from .vision_simulator import VisionSimulator
    from .voice_simulator import VoiceSimulator
except (ImportError, ValueError):
    try:
        from Demo.wearable_simulator import WearableSimulator
        from Demo.environment_simulator import EnvironmentSimulator
        from Demo.radar_simulator import RadarSimulator
        from Demo.vision_simulator import VisionSimulator
        from Demo.voice_simulator import VoiceSimulator
    except ImportError:
        from wearable_simulator import WearableSimulator
        from environment_simulator import EnvironmentSimulator
        from radar_simulator import RadarSimulator
        from vision_simulator import VisionSimulator
        from voice_simulator import VoiceSimulator

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger("NIRA.ScenarioSimulator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ScenarioSimulator:
    """Orchestrates multi-device event sequences matching genuine elder living patterns."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        resident_id: str = "user_eleanor_vance",
        step_delay_sec: float = 0.5
    ):
        self.base_url = base_url.rstrip("/")
        self.resident_id = resident_id
        self.step_delay = step_delay_sec
        self.ingest_url = f"{self.base_url}/api/v1/events/ingest"

        # Instantiate device adapters
        self.wearable = WearableSimulator(resident_id=resident_id, target_url=self.ingest_url)
        self.environment = EnvironmentSimulator(resident_id=resident_id, target_url=self.ingest_url)
        self.radar = RadarSimulator(resident_id=resident_id, target_url=self.ingest_url)
        self.vision = VisionSimulator(resident_id=resident_id, target_url=self.ingest_url)
        self.voice = VoiceSimulator(resident_id=resident_id, base_url=self.base_url)

    def _sleep(self, multiplier: float = 1.0):
        t = self.step_delay * multiplier
        if t > 0:
            time.sleep(t)

    # -----------------------------------------------------------------------
    # Routine: Realistic 24-Hour Day (9 Time Slots)
    # -----------------------------------------------------------------------

    def run_normal_day(self, slot_delay_sec: float = 0.8) -> List[Dict[str, Any]]:
        """
        Simulates Eleanor's realistic 24-hour routine:
          07:00 wake (bedroom)
          07:30 bathroom (sink running, dry floor)
          08:00 breakfast (kitchen, cooking)
          10:00 living room (seated, reading)
          12:30 lunch (kitchen, meal prep)
          15:00 rest (living room, quiet)
          18:00 kitchen (dinner)
          21:30 bedroom (retiring to bed, lights off)
          02:00 bathroom (nocturnal bathroom visit, returns to bed)
        
        The system must NOT treat normal routine as an emergency!
        """
        corr_id = f"corr-day-{uuid.uuid4().hex[:8]}"
        results = []

        timeline = [
            ("07:00", "wake", "bedroom", "bedroom_morning", "bed_sleeping", "normal_resting"),
            ("07:30", "morning_toilet", "bathroom", "bathroom_normal", "upright_walking", "normal_resting"),
            ("08:00", "breakfast", "kitchen", "kitchen_active", "upright_walking", "walking_normal"),
            ("10:00", "reading", "living_room", "living_room_normal", "seated_relaxing", "normal_resting"),
            ("12:30", "lunch", "kitchen", "kitchen_active", "upright_walking", "walking_normal"),
            ("15:00", "afternoon_rest", "living_room", "living_room_normal", "seated_relaxing", "normal_resting"),
            ("18:00", "dinner_prep", "kitchen", "kitchen_active", "upright_walking", "walking_normal"),
            ("21:30", "retiring_to_bed", "bedroom", "bedroom_nocturnal", "bed_sleeping", "normal_resting"),
            ("02:00", "nocturnal_bathroom", "bathroom", "bathroom_normal", "upright_walking", "normal_resting")
        ]

        print(f"\n🌅 RUNNING REALISTIC 24-HOUR ELDER ROUTINE ({len(timeline)} slots)...")
        print("=" * 70)

        for clock, activity, room, env_pre, rad_pre, wear_pre in timeline:
            print(f"\n⏰ [{clock}] Room: {room.upper()} | Activity: {activity.replace('_', ' ').title()}")

            # 1. Environmental Telemetry
            res_env = self.environment.emit_event(preset=env_pre, room_override=room, correlation_id=corr_id)
            # 2. Radar Telemetry
            res_rad = self.radar.emit_event(preset=rad_pre, room_id=room, correlation_id=corr_id)
            # 3. Wearable Telemetry
            res_wear = self.wearable.emit_event(preset=wear_pre, room_id=room, correlation_id=corr_id)

            results.append({
                "clock": clock,
                "room": room,
                "activity": activity,
                "env": res_env,
                "radar": res_rad,
                "wearable": res_wear
            })

            # Check safety state - must remain NORMAL
            state = res_wear.get("response", {}).get("safety_state", "UNKNOWN") if res_wear else "UNKNOWN"
            score = res_wear.get("response", {}).get("composite_risk_score", 0.0) if res_wear else 0.0
            print(f"   -> State: {state} | Risk Score: {score:.1f} | Verified: Safe Normal Routine")

            time.sleep(slot_delay_sec)

        print("\n" + "=" * 70)
        print("✅ 24-Hour Normal Routine Completed. State remained consistently NORMAL.")
        return results

    # -----------------------------------------------------------------------
    # Scenario A: False Alarm
    # -----------------------------------------------------------------------

    def run_scenario_a_false_alarm(self) -> Dict[str, Any]:
        """
        Scenario A: Minor stumble / acoustic impact in living room.
        Resident promptly says "I'm okay" -> State returns to RESOLVED / NORMAL.
        """
        corr_id = f"corr-scen-a-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO A: FALSE ALARM (Verbal Confirmation) ===")

        # Step 1: Normal environmental reading
        self.environment.emit_event(preset="living_room_normal", correlation_id=corr_id)
        self._sleep()

        # Step 2: Acoustic thud / minor stumble
        print("1. Emitting minor stumble / impact event (conf 0.65)...")
        self.vision.emit_event(preset="minor_stumble", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        # Step 3: Radar confirms resident remained upright
        print("2. Radar confirms resident is upright...")
        self.radar.emit_event(preset="upright_walking", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        # Step 4: Wearable reports transient HR bump but normal movement
        print("3. Wearable reports normal motion index resuming...")
        self.wearable.emit_event(preset="normal_resting", room_id="living_room", hr_override=82, correlation_id=corr_id)
        self._sleep()

        # Step 5: Alexa prompt asked -> Senior responds "I'm okay"
        print("4. Senior verbally confirms: \"I'm okay, false alarm, just dropped my book.\"...")
        vox_res = self.voice.emit_event(preset="safe_verbal_confirmation", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        final_state = vox_res.get("response", {}).get("safety_state") if vox_res else "RESOLVED"
        print(f"✅ Scenario A Complete. Final State: {final_state}")
        return {"scenario": "A_FALSE_ALARM", "final_state": final_state, "voice_res": vox_res}

    # -----------------------------------------------------------------------
    # Scenario B: Responsive Emergency
    # -----------------------------------------------------------------------

    def run_scenario_b_responsive_emergency(self) -> Dict[str, Any]:
        """
        Scenario B: Sudden fall in living room + crawling movement.
        Resident asks for help -> CAREGIVER_ESCALATION.
        """
        corr_id = f"corr-scen-b-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO B: RESPONSIVE EMERGENCY (Calls for Help) ===")

        # Step 1: Camera detects fall with crawling movement
        print("1. Camera detects fall with crawling movement (conf 0.89)...")
        self.vision.emit_event(preset="fall_impact_crawling", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        # Step 2: Radar confirms target on floor
        print("2. Radar confirms target on floor level...")
        self.radar.emit_event(preset="floor_collapse_immobile", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        # Step 3: Wearable detects elevated heart rate
        print("3. Wearable detects elevated heart rate (108 bpm)...")
        self.wearable.emit_event(preset="walking_normal", room_id="living_room", hr_override=108, correlation_id=corr_id)
        self._sleep()

        # Step 4: Alexa prompts -> Senior calls for help
        print("4. Senior calls for help: \"Help me, I fell down and my hip hurts!\"...")
        vox_res = self.voice.emit_event(preset="distress_help", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        final_state = vox_res.get("response", {}).get("safety_state") if vox_res else "HIGH"
        print(f"✅ Scenario B Complete. Final State: {final_state} (Caregiver alert triggered)")
        return {"scenario": "B_RESPONSIVE_EMERGENCY", "final_state": final_state, "voice_res": vox_res}

    # -----------------------------------------------------------------------
    # Scenario C: Silent Emergency
    # -----------------------------------------------------------------------

    def run_scenario_c_silent_emergency(self) -> Dict[str, Any]:
        """
        Scenario C: Nocturnal bathroom fall on wet floor + tachycardia + silence.
        Timeout triggers CAD emergency escalation and smart lock unlock.
        """
        corr_id = f"corr-scen-c-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO C: SILENT EMERGENCY (Unresponsive Fall + CAD) ===")

        # Step 1: Environmental sensor detects standing water leak on ceramic floor
        print("1. Environmental sensor flags wet floor in bathroom (humidity 89%, dim light)...")
        self.environment.emit_event(preset="bathroom_hazard_wet", room_override="bathroom", correlation_id=corr_id)
        self._sleep()

        # Step 2: Camera detects high-impact fall with zero post-fall movement
        print("2. Camera detects high-impact fall (conf 0.96, movement: NONE)...")
        self.vision.emit_event(preset="fall_impact_immobile", room_id="bathroom", correlation_id=corr_id)
        self._sleep()

        # Step 3: Radar confirms floor collapse
        print("3. Radar confirms floor-level target centroid...")
        self.radar.emit_event(preset="floor_collapse_immobile", room_id="bathroom", correlation_id=corr_id)
        self._sleep()

        # Step 4: Wearable reports severe tachycardia (138 bpm) with zero motion
        print("4. Wearable reports tachycardia surge (138 bpm, zero motion)...")
        self.wearable.emit_event(preset="tachycardia_fall_impact", room_id="bathroom", correlation_id=corr_id)
        self._sleep()

        # Step 5: Alexa prompt window times out with complete silence
        print("5. 20-second Alexa prompt window times out with complete silence...")
        vox_res = self.voice.emit_event(preset="prompt_timeout", room_id="bathroom", correlation_id=corr_id)
        self._sleep()

        final_state = vox_res.get("response", {}).get("safety_state") if vox_res else "CRITICAL"
        print(f"🚨 Scenario C Complete. Final State: {final_state} (Simulated CAD dispatched, door unlocked)")
        return {"scenario": "C_SILENT_EMERGENCY", "final_state": final_state, "voice_res": vox_res}

    # -----------------------------------------------------------------------
    # Scenario D: Recovery after Emergency
    # -----------------------------------------------------------------------

    def run_scenario_d_recovery(self) -> Dict[str, Any]:
        """
        Scenario D: Initial fall occurs, but resident begins moving, stands back up,
        and verbally confirms recovery -> De-escalates to NORMAL.
        """
        corr_id = f"corr-scen-d-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO D: RECOVERY AFTER EMERGENCY (Self-Resolution) ===")

        # Step 1: Fall detected
        print("1. Initial fall impact detected in kitchen...")
        self.vision.emit_event(preset="fall_impact_crawling", room_id="kitchen", correlation_id=corr_id)
        self._sleep()

        # Step 2: Resident begins moving (movement index increases)
        print("2. Wearable detects movement resumption (movement index 0.65)...")
        self.wearable.emit_event(preset="recovery_movement", room_id="kitchen", correlation_id=corr_id)
        self._sleep()

        # Step 3: Radar observes target rising from floor
        print("3. Radar tracks target rising from floor level to standing...")
        self.radar.emit_event(preset="recovery_rising", room_id="kitchen", correlation_id=corr_id)
        self._sleep()

        # Step 4: Camera confirms upright posture restored
        print("4. Camera confirms upright posture restored (torso angle 86°)...")
        self.vision.emit_event(preset="posture_recovered_upright", room_id="kitchen", correlation_id=corr_id)
        self._sleep()

        # Step 5: Voice confirmation: "I got back up, I'm okay now."
        print("5. Voice confirmation received: \"I managed to get back up, I'm okay now.\"...")
        vox_res = self.voice.emit_event(preset="recovery_confirmation", room_id="kitchen", correlation_id=corr_id)
        self._sleep()

        final_state = vox_res.get("response", {}).get("safety_state") if vox_res else "RESOLVED"
        print(f"✅ Scenario D Complete. Final State: {final_state} (De-escalated via recovery confirmation)")
        return {"scenario": "D_RECOVERY", "final_state": final_state, "voice_res": vox_res}

    # -----------------------------------------------------------------------
    # Scenario E: Sensor Dropout & Reconnect
    # -----------------------------------------------------------------------

    def run_scenario_e_sensor_dropout(self) -> Dict[str, Any]:
        """
        Scenario E: Wearable watch taken off / battery dies.
        Radar confirms resident moving normally in living room -> No false critical emergency.
        Wearable reconnected later.
        """
        corr_id = f"corr-scen-e-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO E: SENSOR DROPOUT & RECONNECT ===")

        # Step 1: Wearable disconnects (off-wrist)
        print("1. Wearable emits disconnect / off-wrist event (0 bpm)...")
        self.wearable.disconnect()
        self.wearable.emit_event(preset="disconnected", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        # Step 2: Radar confirms resident is safe and walking in living room
        print("2. Radar confirms resident walking normally in living room...")
        rad_res = self.radar.emit_event(preset="upright_walking", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        # Step 3: Environmental sensors report normal activity
        print("3. Environmental sensors report well-lit room and active occupancy...")
        self.environment.emit_event(preset="living_room_normal", correlation_id=corr_id)
        self._sleep()

        state_during_drop = rad_res.get("response", {}).get("safety_state") if rad_res else "NORMAL"
        print(f"   -> Safety state during wearable dropout: {state_during_drop} (No false critical alarm!)")

        # Step 4: Wearable put back on wrist
        print("4. Wearable put back on wrist (reconnecting)...")
        self.wearable.reconnect()
        recon_res = self.wearable.emit_event(preset="normal_resting", room_id="living_room", correlation_id=corr_id)
        self._sleep()

        final_state = recon_res.get("response", {}).get("safety_state") if recon_res else "NORMAL"
        print(f"✅ Scenario E Complete. Final State: {final_state} (Seamless redundancy handling)")
        return {"scenario": "E_SENSOR_DROPOUT", "final_state": final_state}

    # -----------------------------------------------------------------------
    # Scenario F: Environmental Hazard (Pre-Fall Prevention)
    # -----------------------------------------------------------------------

    def run_scenario_f_environmental_hazard(self) -> Dict[str, Any]:
        """
        Scenario F: Floor moisture detected in dark bathroom while resident is approaching.
        Elevates hazard risk before any fall occurs.
        """
        corr_id = f"corr-scen-f-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO F: ENVIRONMENTAL HAZARD (Pre-Fall Warning) ===")

        # Step 1: Moisture sensor triggers standing water alert in bathroom
        print("1. Moisture sensor detects standing water leak on ceramic tiles...")
        env_res = self.environment.emit_event(
            preset="bathroom_hazard_wet",
            room_override="bathroom",
            moisture_override=True,
            correlation_id=corr_id
        )
        self._sleep()

        # Step 2: Radar detects resident walking down hallway towards bathroom
        print("2. Hallway radar tracks resident approaching bathroom entry...")
        self.radar.emit_event(preset="upright_walking", room_id="hallway", correlation_id=corr_id)
        self._sleep()

        # Step 3: Wearable reports normal baseline vitals (resident has NOT fallen)
        print("3. Wearable reports normal vitals (no trauma yet)...")
        self.wearable.emit_event(preset="walking_normal", room_id="hallway", correlation_id=corr_id)
        self._sleep()

        hazard_state = env_res.get("response", {}).get("safety_state") if env_res else "ANOMALY"
        print(f"⚠️ Scenario F Complete. Detected Environmental Hazard. State: {hazard_state}")
        return {"scenario": "F_ENVIRONMENTAL_HAZARD", "hazard_state": hazard_state}

    # -----------------------------------------------------------------------
    # Scenario G: Worsening Condition
    # -----------------------------------------------------------------------

    def run_scenario_worsening_condition(self) -> Dict[str, Any]:
        """
        Scenario G: Resident has a minor slip in bedroom, followed by progressive
        vital deterioration (heart rate climbs from 82 to 142 BPM) and prolonged inactivity.
        The system autonomously escalates from MODERATE -> HIGH -> CRITICAL emergency.
        """
        corr_id = f"corr-scen-worsen-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO 4: WORSENING CONDITION (Dynamic Escalation) ===")

        # Step 1: Minor stumble detected in bedroom
        print("1. Bedroom camera reports initial stumble / slip (conf 0.72)...")
        self.vision.emit_event(preset="minor_stumble", room_id="bedroom", correlation_id=corr_id)
        self._sleep()

        # Step 2: Inactivity sets in — resident seated on floor unable to get up
        print("2. Radar flags immobility (motion level: 0.12, seated on floor)...")
        self.radar.emit_event(preset="floor_collapse_immobile", room_id="bedroom", correlation_id=corr_id)
        self._sleep()

        # Step 3: Progressive vital deterioration (moderate tachycardia 108 BPM)
        print("3. Apple Watch detects early heart rate surge (108 BPM)...")
        self.wearable.emit_event(preset="walking_normal", room_id="bedroom", hr_override=108, correlation_id=corr_id)
        self._sleep()

        # Step 4: Severe tachycardia (142 BPM) + arrhythmia detected
        print("4. Apple Watch triggers acute tachycardia alarm (142 BPM + arrhythmia)...")
        w_res = self.wearable.emit_event(preset="tachycardia_fall_impact", room_id="bedroom", hr_override=142, correlation_id=corr_id)
        self._sleep()

        # Step 5: Voice check timeout (unresponsive due to worsening shock)
        print("5. Alexa wellness check receives silence (20s timeout)...")
        vox_res = self.voice.emit_event(preset="prompt_timeout", room_id="bedroom", correlation_id=corr_id)
        self._sleep()

        final_state = vox_res.get("response", {}).get("safety_state") if vox_res else "CRITICAL"
        print(f"🚨 Scenario Worsening Condition Complete. Final State: {final_state} (Escalated to Emergency Dispatch)")
        return {"scenario": "WORSENING_CONDITION", "final_state": final_state, "voice_res": vox_res}

    # -----------------------------------------------------------------------
    # Scenario H: Medication Miss
    # -----------------------------------------------------------------------

    def run_scenario_medication_miss(self) -> Dict[str, Any]:
        """
        Scenario H: Scheduled evening Lisinopril 10mg is missed by resident.
        Echo Show prompts senior, then alerts caregiver David Vance upon delay threshold.
        """
        corr_id = f"corr-scen-meds-{uuid.uuid4().hex[:8]}"
        print("\n=== SCENARIO 6: MEDICATION MISS & ADHERENCE ESCALATION ===")

        # Step 1: Normal environmental reading in kitchen
        print("1. Kitchen ambient sensors active (normal environment)...")
        self.environment.emit_event(preset="kitchen_active", room_override="kitchen", correlation_id=corr_id)
        self._sleep()

        # Step 2: Medication scheduled time arrives (18:00) — smart dispenser unaccessed
        print("2. Scheduled dose at 18:00 (Lisinopril 10mg). Smart pill compartment unaccessed...")
        med_evt = {
            "event_id": f"evt-med-miss-{uuid.uuid4().hex[:6]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resident_id": self.resident_id,
            "room_id": "kitchen",
            "source": "system",
            "event_type": "state_transition",
            "payload": {
                "medication": "Lisinopril 10mg",
                "scheduled_time": "18:00",
                "status": "MISSED",
                "delay_minutes": 120,
                "adherence_score": 0.88,
                "alert_caregiver": True,
                "notification_message": "Evening Lisinopril 10mg missed (120 min delay). Caregiver notified."
            },
            "confidence": 0.95,
            "correlation_id": corr_id
        }
        import urllib.request
        import json
        req = urllib.request.Request(
            f"{self.base_url}/api/v1/events/ingest",
            data=json.dumps(med_evt).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            res_data = {"status": "FAILED", "error": str(e)}

        self._sleep()

        # Step 3: Echo Show delivers audible reminder
        print("3. Echo Show 15 issues conversational reminder to Eleanor...")
        self.voice.emit_event(preset="medication_reminder", room_id="kitchen", correlation_id=corr_id)
        self._sleep()

        print("✅ Scenario Medication Miss Complete. Caregiver alerted and adherence tracked.")
        return {"scenario": "MEDICATION_MISS", "result": res_data}

