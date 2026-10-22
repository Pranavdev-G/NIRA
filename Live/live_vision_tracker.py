"""
NIRA Live Model & Real-Time Sensor Processing Engine.
Amazon Developer Hackathon 2026.

Integrates real-time camera inference with trained YOLOv8 model on Kaggle dataset.
Evaluates:
  1. NORMAL MOVEMENT (Walking / Sitting within daily circadian routine)
  2. FALL DETECTED (Class 0: Sudden Fall / Collapse via biomechanics + YOLOv8)
  3. PROLONGED INACTIVITY (Motionless without movement for 3-5 mins / learned routine limit)
  4. ALARM INQUIRY WAKE-UP & SPOKEN VOICE RESPONSE VERIFICATION (Microphone + Whisper STT)
  5. SELF-LEARNING DAILY ACTIVITY ROUTINE (Adapts baselines on safe feedback to eliminate false alarms)
"""

import os
import sys
import time
import math
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import requests
except ImportError:
    requests = None

# Internal package imports
try:
    from Live.activity_routine_learner import DailyActivityRoutineLearner, get_activity_learner
    from Live.voice.response_analyzer import ResponseAnalyzer
    from Live.voice.models import VoiceInteractionStatus
except ImportError:
    try:
        from activity_routine_learner import DailyActivityRoutineLearner, get_activity_learner
        from voice.response_analyzer import ResponseAnalyzer
        from voice.models import VoiceInteractionStatus
    except ImportError:
        DailyActivityRoutineLearner = None
        get_activity_learner = None
        ResponseAnalyzer = None
        VoiceInteractionStatus = None

logger = logging.getLogger("NIRA.LiveVisionTracker")

# Label mappings from Kaggle Fall Detection Dataset
CLASS_NAMES = {
    0: "Fall Detected",
    1: "Walking",
    2: "Sitting"
}

STATE_NORMAL = "NORMAL_MOVEMENT"
STATE_FALL = "FALL_DETECTED"
STATE_PROLONGED_INACTIVITY = "PROLONGED_INACTIVITY"
STATE_UNRESPONSIVE = "UNRESPONSIVENESS"
STATE_ALARM_INQUIRY = "ALARM_INQUIRY_ACTIVE"
STATE_CONFIRMED_SAFE = "CONFIRMED_SAFE"


class LiveVisionTracker:
    """
    Connects to live camera devices or edge video feeds and evaluates
    real-time fall status, biomechanics, prolonged inactivity (3-5 mins),
    and conversational voice check-in wake-ups.
    """
    def __init__(
        self,
        model_path: Optional[str] = None,
        backend_url: str = "http://localhost:8000",
        unresponsive_threshold_sec: float = 180.0,  # 3 minutes default (180s - 300s clinical range)
        simulation_speedup_factor: float = 1.0,     # Accelerates immobility timer for test runs
        zone: str = "living_room"
    ):
        self.backend_url = backend_url.rstrip("/")
        self.unresponsive_threshold_sec = unresponsive_threshold_sec
        self.simulation_speedup_factor = max(1.0, float(simulation_speedup_factor))
        self.zone = zone
        self.model = None
        self.model_type = "yolov8"

        # Adaptive daily activity routine learner
        if get_activity_learner is not None:
            self.activity_learner = get_activity_learner()
        elif DailyActivityRoutineLearner is not None:
            self.activity_learner = DailyActivityRoutineLearner()
        else:
            self.activity_learner = None

        # Clinical response analyzer for spoken voice feedback
        self.response_analyzer = ResponseAnalyzer() if ResponseAnalyzer else None

        # State tracking
        self.current_state = STATE_NORMAL
        self.last_detection_time = time.time()
        self.last_frame_time = time.time()
        self.fall_start_time: Optional[float] = None
        self.accumulated_motionless_sec = 0.0
        self.motionless_start_time: Optional[float] = None
        self.last_centroid: Optional[Tuple[float, float]] = None
        self.last_motion_rate = 0.0
        self.last_alert_sent_time = 0.0
        self.consecutive_fall_frames = 0
        self.consecutive_normal_frames = 0
        self.prev_gray: Optional[np.ndarray] = None

        # Voice Wake-Up & Interactive Alarm
        self.alarm_active = False
        self.alarm_prompt: Optional[str] = None
        self.alarm_reason: Optional[str] = None
        self.voice_interaction_status: Optional[str] = None
        self.last_voice_transcript: Optional[str] = None

        # Centroid motion history for biomechanical fall velocity
        self.centroid_history: List[Tuple[float, float, float]] = []

        # Model path resolution
        live_dir = Path(__file__).resolve().parent
        root_dir = live_dir.parent

        candidate_paths = [
            model_path,
            str(live_dir / "nira_fall_model.pt"),
            str(live_dir / "runs" / "fall_detection" / "weights" / "best.pt"),
            str(live_dir / "runs" / "fall_detection" / "weights" / "last.pt"),
            str(root_dir / "Demo" / "yolov8n-pose.pt"),
            str(root_dir / "yolov8n.pt")
        ]
        self.resolved_model_path = next((p for p in candidate_paths if p and os.path.exists(p)), None)

    def reset(self):
        """Resets state machine, alarm, and counters when stream stops or starts."""
        self.current_state = STATE_NORMAL
        self.fall_start_time = None
        self.accumulated_motionless_sec = 0.0
        self.motionless_start_time = None
        self.last_centroid = None
        self.last_motion_rate = 0.0
        self.consecutive_fall_frames = 0
        self.consecutive_normal_frames = 0
        self.prev_gray = None
        self.alarm_active = False
        self.alarm_prompt = None
        self.alarm_reason = None
        self.voice_interaction_status = None
        self.last_voice_transcript = None
        self.centroid_history.clear()
        self.last_frame_time = time.time()

    def initialize_model(self):
        """Loads trained YOLOv8 model if ultralytics is installed."""
        try:
            from ultralytics import YOLO

            live_dir = Path(__file__).resolve().parent
            custom_model = live_dir / "nira_fall_model.pt"
            if custom_model.exists():
                self.resolved_model_path = str(custom_model)

            if self.resolved_model_path and os.path.exists(self.resolved_model_path):
                self.model = YOLO(self.resolved_model_path)
                logger.info(f"Loaded YOLOv8 model from {self.resolved_model_path}")
            else:
                logger.warning("No custom weights found; loading standard YOLOv8n")
                self.model = YOLO("yolov8n.pt")
                self.resolved_model_path = "yolov8n.pt"
        except Exception as e:
            logger.warning(f"Ultralytics model initialization error: {e}. Running optical fallback mode.")
            self.model = None

    def evaluate_frame(self, frame: np.ndarray, location: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs comprehensive real-time inference on a video/webcam frame:
          1. Measures optical motion displacement (detects absence of movement).
          2. Runs YOLOv8 object & posture proposal detection.
          3. Evaluates biomechanical velocity and floor proximity.
          4. Tracks prolonged inactivity against learned circadian baseline (3-5 mins).
          5. Triggers alarm & speech inquiry prompt when threshold is exceeded.
        """
        now = time.time()
        dt = max(0.01, min(1.0, now - self.last_frame_time))
        self.last_frame_time = now

        current_zone = location or self.zone

        if frame is None or not hasattr(frame, "shape"):
            return {
                "state": self.current_state,
                "detected_class": "Normal Movement",
                "confidence": 0.95,
                "unresponsive_seconds": round(self.accumulated_motionless_sec, 1),
                "is_unresponsive": (self.current_state in [STATE_UNRESPONSIVE, STATE_PROLONGED_INACTIVITY]),
                "motion_displacement": 0.0,
                "boxes": [],
                "alarm_active": self.alarm_active,
                "alarm_prompt": self.alarm_prompt,
                "timestamp": now
            }

        fh, fw = frame.shape[:2]
        frame_area = float(fh * fw)

        # 1. Compute frame-to-frame pixel motion displacement
        motion_rate = 0.0
        gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if cv2 is not None else None
        if gray_curr is not None:
            blurred_curr = cv2.GaussianBlur(gray_curr, (21, 21), 0)
            if self.prev_gray is not None and self.prev_gray.shape == blurred_curr.shape:
                diff = cv2.absdiff(blurred_curr, self.prev_gray)
                motion_rate = round(float(np.mean(diff)) * 4.0, 1)
            self.prev_gray = blurred_curr
        self.last_motion_rate = motion_rate

        raw_candidates = []
        yolo_normal = False
        yolo_fall = False
        current_centroid: Optional[Tuple[float, float]] = None

        if self.model is not None:
            try:
                results = self.model(frame, verbose=False, conf=0.35)
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        cls_id = int(box.cls[0].item())
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]

                        bw = xyxy[2] - xyxy[0]
                        bh = xyxy[3] - xyxy[1]
                        box_area = bw * bh
                        area_ratio = box_area / frame_area
                        aspect_ratio = bw / max(1.0, float(bh))

                        if area_ratio > 0.85 or area_ratio < 0.005 or bw < 20 or bh < 20:
                            continue

                        label = CLASS_NAMES.get(cls_id, f"Class {cls_id}")
                        cx = (xyxy[0] + xyxy[2]) / 2.0
                        cy = (xyxy[1] + xyxy[3]) / 2.0
                        current_centroid = (cx, cy)

                        # Biomechanical posture check:
                        if cls_id == 0 or "fall" in label.lower():
                            if conf < 0.50:
                                continue

                            is_horizontal = aspect_ratio >= 0.70
                            is_low_in_frame = xyxy[3] > 0.48 * fh
                            if not (is_horizontal or is_low_in_frame):
                                label = "Sitting" if aspect_ratio > 0.50 else "Walking"
                                cls_id = 2 if label == "Sitting" else 1
                                yolo_normal = True
                            else:
                                yolo_fall = True
                        else:
                            if conf < 0.45:
                                continue
                            yolo_normal = True

                        raw_candidates.append({
                            "class_id": cls_id,
                            "label": label,
                            "confidence": round(conf, 2),
                            "box": xyxy,
                            "aspect_ratio": round(aspect_ratio, 2),
                            "centroid": (cx, cy)
                        })

            except Exception as e:
                logger.error(f"Inference error: {e}")

        # 2. Centroid velocity calculation (Biomechanics of sudden drop)
        is_high_velocity_drop = False
        if current_centroid:
            self.centroid_history.append((now, current_centroid[0], current_centroid[1]))
            # Keep only last 1.5 seconds of history
            self.centroid_history = [p for p in self.centroid_history if (now - p[0]) <= 1.5]
            if len(self.centroid_history) >= 2:
                t_old, _, y_old = self.centroid_history[0]
                t_new, _, y_new = self.centroid_history[-1]
                time_span = max(0.05, t_new - t_old)
                downward_speed = (y_new - y_old) / time_span
                # Rapid downward drop exceeds 120 pixels/sec normalized
                if downward_speed > 120.0 and y_new > (fh * 0.50):
                    is_high_velocity_drop = True

        # 3. Cross-class Non-Maximum Suppression
        def _compute_iou(b1, b2):
            x1 = max(b1[0], b2[0])
            y1 = max(b1[1], b2[1])
            x2 = min(b1[2], b2[2])
            y2 = min(b1[3], b2[3])
            inter = max(0, x2 - x1) * max(0, y2 - y1)
            a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
            a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
            union = a1 + a2 - inter
            return inter / max(1.0, float(union))

        filtered_boxes = []
        for cand in sorted(raw_candidates, key=lambda c: c["confidence"], reverse=True):
            if any(_compute_iou(cand["box"], kept["box"]) > 0.35 for kept in filtered_boxes):
                continue
            filtered_boxes.append(cand)

        # 4. Primary detection determination
        primary_class = "Normal Movement"
        primary_conf = 0.95
        is_fall_candidate = False

        if filtered_boxes:
            best = filtered_boxes[0]
            primary_class = best["label"]
            primary_conf = best["confidence"]
            if best["class_id"] == 0 or "fall" in best["label"].lower() or is_high_velocity_drop:
                is_fall_candidate = True

        # Fallback optical slump inspection
        if not yolo_normal and not is_fall_candidate and gray_curr is not None:
            top_h = int(fh * 0.45)
            dark_top = np.sum(gray_curr[:top_h, :] < 80)
            dark_bottom = np.sum(gray_curr[top_h:, :] < 80)
            total_dark = dark_top + dark_bottom

            if total_dark > (fh * fw * 0.06):
                bottom_ratio = dark_bottom / max(1, total_dark)
                top_mean = np.mean(gray_curr[:top_h, :])
                bottom_mean = np.mean(gray_curr[top_h:, :])
                if bottom_ratio > 0.65 and bottom_mean < (top_mean - 25):
                    is_fall_candidate = True
                    primary_class = "Fall / Collapse Detected"
                    primary_conf = 0.88
                    filtered_boxes = [{
                        "class_id": 0,
                        "label": "Fall / Collapse Detected",
                        "confidence": 0.88,
                        "box": [int(fw * 0.15), int(fh * 0.40), int(fw * 0.85), int(fh * 0.98)]
                    }]

        # 5. Temporal debouncing
        if is_fall_candidate:
            self.consecutive_fall_frames += 1
            self.consecutive_normal_frames = 0
        else:
            self.consecutive_fall_frames = 0
            self.consecutive_normal_frames += 1

        is_fall_confirmed = (self.consecutive_fall_frames >= 2)

        # 6. Prolonged Inactivity Tracking (3-5 Minutes or Learned Routine Baseline)
        effective_thresh = self.unresponsive_threshold_sec
        anomaly_diag: Dict[str, Any] = {}

        if motion_rate < 6.0:
            # Person is motionless: accumulate stillness
            step_motionless = dt * self.simulation_speedup_factor
            self.accumulated_motionless_sec += step_motionless

            # Check with Adaptive Routine Learner
            if self.activity_learner:
                posture = "floor" if (is_fall_confirmed or is_fall_candidate) else ("sitting" if "sitting" in primary_class.lower() else "resting")
                anomaly_diag = self.activity_learner.evaluate_inactivity_anomaly(
                    zone=current_zone,
                    motionless_seconds=self.accumulated_motionless_sec,
                    posture=posture
                )
                effective_thresh = anomaly_diag.get("threshold_sec", self.unresponsive_threshold_sec)
        else:
            # Significant resident motion detected
            if motion_rate >= 14.0:
                # If resident was resting safely and stood up, record routine observation
                if self.activity_learner and self.accumulated_motionless_sec > 30.0:
                    self.activity_learner.record_activity_observation(
                        zone=current_zone,
                        motion_rate=motion_rate,
                        duration_sec=self.accumulated_motionless_sec
                    )
                # If not locked in confirmed emergency, reset stillness
                if self.current_state != STATE_UNRESPONSIVE:
                    self.accumulated_motionless_sec = 0.0
                    self.alarm_active = False

        # 7. State Machine Evaluation & Voice Alarm Trigger
        is_unresponsive = False
        inactivity_exceeded = (self.accumulated_motionless_sec >= effective_thresh)

        if is_fall_confirmed:
            if self.fall_start_time is None:
                self.fall_start_time = now
                self.current_state = STATE_FALL
                logger.warning(f"Fall Detected in {current_zone}! Initiating immediate voice check-in.")
                self.alarm_active = True
                self.alarm_prompt = "NIRA safety alert: Are you okay? Please respond."
                self.alarm_reason = "Sudden fall / collapse detected."
                self.dispatch_live_fall_alert(
                    event_type="fall_detected",
                    confidence=primary_conf,
                    location=current_zone,
                    details={"alarm_prompt": self.alarm_prompt, "requires_voice_checkin": True}
                )

            # Check for prolonged floor immobility post-fall
            if self.accumulated_motionless_sec >= 15.0:
                self.current_state = STATE_UNRESPONSIVE
                is_unresponsive = True
                if now - self.last_alert_sent_time > 8.0:
                    self.last_alert_sent_time = now
                    self.dispatch_live_fall_alert(
                        event_type="unresponsiveness_detected",
                        confidence=primary_conf,
                        location=current_zone,
                        details={"motionless_seconds": round(self.accumulated_motionless_sec, 1)}
                    )

        elif inactivity_exceeded:
            # Person has stayed motionless without any movement for 3-5 mins (or exceeded learned limit)
            if self.current_state != STATE_UNRESPONSIVE:
                self.current_state = STATE_PROLONGED_INACTIVITY
                is_unresponsive = True
                self.alarm_active = True
                self.alarm_prompt = anomaly_diag.get("suggested_question", "Are you okay? I noticed you haven't moved in a while.")
                self.alarm_reason = anomaly_diag.get("reason", f"Resident motionless for {self.accumulated_motionless_sec:.1f}s.")

                if now - self.last_alert_sent_time > 10.0:
                    self.last_alert_sent_time = now
                    self.dispatch_live_fall_alert(
                        event_type="prolonged_inactivity_detected",
                        confidence=0.92,
                        location=current_zone,
                        details={
                            "motionless_seconds": round(self.accumulated_motionless_sec, 1),
                            "threshold_sec": effective_thresh,
                            "alarm_prompt": self.alarm_prompt,
                            "requires_voice_checkin": True
                        }
                    )
        else:
            # Normal movement or within safe learned resting tolerance
            if self.consecutive_normal_frames >= 2 and not self.alarm_active:
                self.fall_start_time = None
                if self.current_state not in [STATE_UNRESPONSIVE, STATE_ALARM_INQUIRY]:
                    self.current_state = STATE_NORMAL

        clean_boxes = [
            {
                "class_id": b["class_id"],
                "label": b["label"],
                "confidence": b["confidence"],
                "box": b["box"]
            }
            for b in filtered_boxes
        ]

        return {
            "state": self.current_state,
            "detected_class": primary_class,
            "confidence": round(primary_conf, 2),
            "unresponsive_seconds": round(self.accumulated_motionless_sec, 1),
            "inactivity_threshold_sec": round(effective_thresh, 1),
            "is_unresponsive": is_unresponsive,
            "motion_displacement": round(motion_rate, 1),
            "boxes": clean_boxes,
            "alarm_active": self.alarm_active,
            "alarm_prompt": self.alarm_prompt,
            "alarm_reason": self.alarm_reason,
            "voice_status": self.voice_interaction_status,
            "zone": current_zone,
            "learned_routine": {
                "suppressed_false_alarms": self.activity_learner.profile.get("suppressed_false_alarms", 0) if self.activity_learner else 0,
                "total_learned_events": self.activity_learner.profile.get("total_learned_events", 0) if self.activity_learner else 0
            },
            "timestamp": now
        }

    def handle_voice_response(
        self,
        transcript: str,
        elderly_id: str = "resident_live",
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Receives and notes resident spoken response (e.g., 'Yes, I'm okay', 'Help me'):
          1. Evaluates safety: SAFE, UNCERTAIN, RISK, or EMERGENCY.
          2. If SAFE: suppresses alarm, resets state to NORMAL, and trains the
             DailyActivityRoutineLearner to expand tolerance and prevent future false alarms!
          3. If RISK / EMERGENCY: escalates to emergency workflow and alerts caregivers.
        """
        current_zone = location or self.zone
        self.last_voice_transcript = transcript

        if not self.response_analyzer:
            logger.warning("Response analyzer not available; using basic keyword match.")
            is_safe = any(w in transcript.lower() for w in ["okay", "fine", "good", "alright"])
            status_val = "SAFE" if is_safe else "EMERGENCY"
            urgency = "LOW" if is_safe else "CRITICAL"
            reason = "Keyword matched safety response." if is_safe else "Emergency or uncertain voice."
        else:
            analysis = self.response_analyzer.analyze(transcript)
            status_val = analysis.status.value if hasattr(analysis.status, "value") else str(analysis.status)
            urgency = analysis.urgency.value if hasattr(analysis.urgency, "value") else str(analysis.urgency)
            reason = analysis.reason

        self.voice_interaction_status = status_val

        # -------------------------------------------------------------------
        # Branch 1: Resident confirms SAFE ("I'm okay", "I'm fine")
        # -------------------------------------------------------------------
        if status_val == "SAFE":
            old_duration = self.accumulated_motionless_sec
            self.current_state = STATE_NORMAL
            self.alarm_active = False
            self.fall_start_time = None
            self.accumulated_motionless_sec = 0.0

            # Self-learning routine update: Prevent future unnecessary alarms!
            learned_info = {}
            if self.activity_learner:
                learned_info = self.activity_learner.reinforce_dismissed_alarm(
                    zone=current_zone,
                    inactivity_duration_sec=max(180.0, old_duration),
                    feedback=f"Resident spoken confirmation: '{transcript}'"
                )

            self.dispatch_live_fall_alert(
                event_type="false_alarm_cleared_by_voice",
                confidence=1.0,
                location=current_zone,
                details={
                    "transcript": transcript,
                    "resolution": "SAFE",
                    "routine_updated": True,
                    "learned_threshold": learned_info.get("new_threshold_sec")
                }
            )

            return {
                "success": True,
                "status": "SAFE",
                "urgency": urgency,
                "action": "ALARM_DISMISSED",
                "message": "Resident confirmed safe. Alarm dismissed and daily routine updated to prevent future false alarms.",
                "transcript": transcript,
                "learned_update": learned_info
            }

        # -------------------------------------------------------------------
        # Branch 2: Resident in EMERGENCY ("Help me", "I fell down", "Can't move")
        # -------------------------------------------------------------------
        elif status_val == "EMERGENCY":
            self.current_state = STATE_UNRESPONSIVE
            self.alarm_active = True

            self.dispatch_live_fall_alert(
                event_type="voice_confirmed_emergency",
                confidence=1.0,
                location=current_zone,
                details={
                    "transcript": transcript,
                    "resolution": "EMERGENCY",
                    "reason": reason
                }
            )

            return {
                "success": True,
                "status": "EMERGENCY",
                "urgency": "CRITICAL",
                "action": "ESCALATE_EMERGENCY_CAD",
                "message": "Critical emergency confirmed via resident voice. Caregivers and emergency dispatch alerted.",
                "transcript": transcript,
                "reason": reason
            }

        # -------------------------------------------------------------------
        # Branch 3: Resident at RISK or UNCERTAIN ("I'm feeling dizzy", mumbled)
        # -------------------------------------------------------------------
        else:
            self.alarm_active = True
            if status_val == "RISK":
                self.current_state = "RISK_CONFIRMED"
                action = "CREATE_INCIDENT"
            else:
                self.current_state = STATE_ALARM_INQUIRY
                action = "REPEAT_CHECK_IN"

            return {
                "success": True,
                "status": status_val,
                "urgency": urgency,
                "action": action,
                "message": reason,
                "transcript": transcript
            }

    def simulate_inactivity(self, seconds: float):
        """Allows testing prolonged inactivity alarms directly without waiting real minutes."""
        self.accumulated_motionless_sec = max(0.0, float(seconds))
        return {
            "accumulated_motionless_sec": self.accumulated_motionless_sec,
            "threshold_sec": self.unresponsive_threshold_sec
        }

    def dispatch_live_fall_alert(
        self,
        event_type: str = "fall_detected",
        confidence: float = 0.94,
        location: str = "living_room",
        details: Optional[Dict[str, Any]] = None
    ):
        """Dispatches real-time detected fall/unresponsiveness event to NIRA backend."""
        payload = {
            "event_type": event_type,
            "source": "live_webcam_detector",
            "confidence": confidence,
            "location": location,
            "movement_after_event": "none" if event_type in ["unresponsiveness_detected", "prolonged_inactivity_detected"] else "slow",
            "details": details or {
                "detector": "yolov8-kaggle-fall",
                "mode": "live_physical_model"
            }
        }
        if requests:
            import threading
            def _post_async():
                try:
                    requests.post(f"{self.backend_url}/api/v1/events/ingest", json=payload, timeout=1.0)
                except Exception as e:
                    logger.debug(f"Failed to post to backend: {e}")
            threading.Thread(target=_post_async, daemon=True).start()
        return {"status": "dispatched_async"}


# Standalone live execution with local webcam
if __name__ == "__main__":
    if cv2 is None:
        print("OpenCV (cv2) is not available.")
        sys.exit(1)

    tracker = LiveVisionTracker()
    tracker.initialize_model()
    print("Opening live webcam feed (press 'q' to quit)...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open camera 0.")
        sys.exit(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        res = tracker.evaluate_frame(frame)
        state = res["state"]
        color = (0, 255, 0) if state == STATE_NORMAL else ((0, 165, 255) if state == STATE_FALL else (0, 0, 255))

        # Overlay bounding boxes
        for b in res["boxes"]:
            xyxy = b["box"]
            lbl = f"{b['label']} {b['confidence']}"
            cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)
            cv2.putText(frame, lbl, (xyxy[0], max(xyxy[1] - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Status HUD
        hud_text = f"STATE: {state} | {res['detected_class']} ({res['confidence']})"
        if res["unresponsive_seconds"] > 0:
            hud_text += f" | IMMOBILE: {res['unresponsive_seconds']}s / {res['inactivity_threshold_sec']}s"

        cv2.putText(frame, hud_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
        if res["alarm_active"]:
            cv2.putText(frame, f"ALARM: {res['alarm_prompt']}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)

        cv2.imshow("NIRA Live Vision - Fall & Inactivity Guardian", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
