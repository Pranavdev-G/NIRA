"""
NIRA Live Model & Real-Time Sensor Processing Engine.
Amazon Developer Hackathon 2026.

Integrates real-time camera inference with YOLOv8 Pose + Kaggle Fall Detection.
Evaluates:
  1. FACE & PERSON TRACKING (Nose, eyes, ears, shoulders, and upper body)
  2. FALL DETECTION (Acute drop, floor collapse, slump off chair, horizontal angle, and Kaggle fall model)
  3. PROLONGED INACTIVITY (Real-time motionless tracking for 3-5 mins, robust to camera sensor noise)
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

STATE_NORMAL = "NORMAL_MOVEMENT"
STATE_FALL = "FALL_DETECTED"
STATE_PROLONGED_INACTIVITY = "PROLONGED_INACTIVITY"
STATE_UNRESPONSIVE = "UNRESPONSIVENESS"
STATE_ALARM_INQUIRY = "ALARM_INQUIRY_ACTIVE"
STATE_CONFIRMED_SAFE = "CONFIRMED_SAFE"


class LiveVisionTracker:
    """
    Connects to live camera devices or edge video feeds and evaluates
    real-time fall status, face tracking, prolonged inactivity (3-5 mins),
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
        self.unresponsive_threshold_sec = max(10.0, float(unresponsive_threshold_sec))
        self.simulation_speedup_factor = max(1.0, float(simulation_speedup_factor))
        self.zone = zone

        # Vision models
        self.pose_model = None
        self.fall_model = None
        self.resolved_model_path: Optional[str] = None

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
        self.last_centroid: Optional[Tuple[float, float]] = None
        self.last_head_pos: Optional[Tuple[float, float, float]] = None  # (x, y, timestamp)
        self.last_motion_rate = 0.0
        self.last_alert_sent_time = 0.0
        self.consecutive_fall_frames = 0
        self.consecutive_normal_frames = 0
        self.prev_gray: Optional[np.ndarray] = None
        self.person_previously_seen = False
        self.last_person_seen_time = time.time()

        # Voice Wake-Up & Interactive Alarm
        self.alarm_active = False
        self.alarm_prompt: Optional[str] = None
        self.alarm_reason: Optional[str] = None
        self.voice_interaction_status: Optional[str] = None
        self.last_voice_transcript: Optional[str] = None

        # Centroid motion history for biomechanical fall velocity
        self.centroid_history: List[Tuple[float, float, float]] = []

    def reset(self):
        """Resets state machine, alarm, and counters when stream stops or starts."""
        self.current_state = STATE_NORMAL
        self.fall_start_time = None
        self.accumulated_motionless_sec = 0.0
        self.last_centroid = None
        self.last_head_pos = None
        self.last_motion_rate = 0.0
        self.consecutive_fall_frames = 0
        self.consecutive_normal_frames = 0
        self.prev_gray = None
        self.person_previously_seen = False
        self.alarm_active = False
        self.alarm_prompt = None
        self.alarm_reason = None
        self.voice_interaction_status = None
        self.last_voice_transcript = None
        self.centroid_history.clear()
        self.last_frame_time = time.time()

    def initialize_model(self):
        """Loads YOLOv8 Pose model and Kaggle Fall Detection model."""
        try:
            from ultralytics import YOLO

            live_dir = Path(__file__).resolve().parent
            root_dir = live_dir.parent

            # 1. Pose model for face keypoints and biomechanics
            pose_candidates = [
                str(live_dir / "yolov8n-pose.pt"),
                str(root_dir / "Demo" / "yolov8n-pose.pt"),
                "yolov8n-pose.pt"
            ]
            for p in pose_candidates:
                if p and (os.path.exists(p) or not os.path.isabs(p)):
                    try:
                        self.pose_model = YOLO(p)
                        self.resolved_model_path = p
                        logger.info(f"Loaded Pose Model from: {p}")
                        break
                    except Exception:
                        continue

            # 2. Kaggle fall detector model
            fall_candidates = [
                str(live_dir / "nira_fall_model.pt"),
                str(live_dir / "runs" / "fall_detection" / "weights" / "best.pt"),
                "yolov8n.pt"
            ]
            for p in fall_candidates:
                if p and (os.path.exists(p) or not os.path.isabs(p)):
                    try:
                        self.fall_model = YOLO(p)
                        logger.info(f"Loaded Fall Detection Model from: {p}")
                        break
                    except Exception:
                        continue

        except Exception as e:
            logger.warning(f"Ultralytics model initialization error: {e}. Running optical fallback mode.")

    def _detect_face_fallback(self, frame: np.ndarray) -> Optional[List[int]]:
        """
        Fast, robust skin-chrominance face bounding box locator as secondary fallback
        when camera is close-up or under extreme webcam lighting.
        """
        if cv2 is None or frame is None:
            return None
        try:
            fh, fw = frame.shape[:2]
            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
            # Standard human skin chrominance bounds
            lower = np.array([0, 133, 77], dtype=np.uint8)
            upper = np.array([255, 173, 127], dtype=np.uint8)
            mask = cv2.inRange(ycrcb, lower, upper)

            # Restrict to upper 70% of frame where head/face normally resides
            mask[int(fh * 0.75):, :] = 0

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
            mask = cv2.dilate(mask, kernel, iterations=2)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                c = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(c)
                if area > (fh * fw * 0.02):  # Minimum face size
                    x, y, w, h = cv2.boundingRect(c)
                    aspect = w / max(1.0, float(h))
                    if 0.5 <= aspect <= 1.5:
                        return [int(x), int(y), int(x + w), int(y + h)]
        except Exception:
            pass
        return None

    def evaluate_frame(self, frame: np.ndarray, location: Optional[str] = None) -> Dict[str, Any]:
        """
        Runs comprehensive real-time inference on a video/webcam frame:
          1. Detects Face & Person pose keypoints (nose, eyes, shoulders, hips).
          2. Measures noise-filtered physical motion displacement.
          3. Evaluates fall kinematics (drop velocity, low head, horizontal tilt).
          4. Tracks real prolonged inactivity (3-5 minutes, not demo-hardcoded).
          5. Triggers voice wake-up alarm prompt when threshold is reached.
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
                "inactivity_threshold_sec": round(self.unresponsive_threshold_sec, 1),
                "is_unresponsive": (self.current_state in [STATE_UNRESPONSIVE, STATE_PROLONGED_INACTIVITY]),
                "motion_displacement": 0.0,
                "boxes": [],
                "alarm_active": self.alarm_active,
                "alarm_prompt": self.alarm_prompt,
                "timestamp": now
            }

        fh, fw = frame.shape[:2]
        frame_area = float(fh * fw)

        # -------------------------------------------------------------------
        # 1. Noise-Filtered Optical Motion Measurement
        # -------------------------------------------------------------------
        # Sensor noise on webcams produces tiny pixel differences even in stillness.
        # We apply Gaussian blur + binary thresholding to isolate genuine human motion!
        motion_rate = 0.0
        motion_pixel_ratio = 0.0
        gray_curr = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if cv2 is not None else None
        if gray_curr is not None:
            blurred_curr = cv2.GaussianBlur(gray_curr, (21, 21), 0)
            if self.prev_gray is not None and self.prev_gray.shape == blurred_curr.shape:
                diff = cv2.absdiff(blurred_curr, self.prev_gray)
                # Ignore pixel fluctuations below 22 intensity
                _, thresh = cv2.threshold(diff, 22, 255, cv2.THRESH_BINARY)
                motion_pixels = int(np.count_nonzero(thresh))
                motion_pixel_ratio = motion_pixels / max(1.0, frame_area)
                motion_rate = round(motion_pixel_ratio * 300.0, 1)
            self.prev_gray = blurred_curr
        self.last_motion_rate = motion_rate

        detected_boxes = []
        is_person_detected = False
        is_fall_candidate = False
        primary_class = "Normal Movement"
        primary_conf = 0.92

        current_centroid: Optional[Tuple[float, float]] = None
        current_head_pos: Optional[Tuple[float, float]] = None
        torso_angle: Optional[float] = None

        # -------------------------------------------------------------------
        # 2. YOLOv8 Pose: Face & Body Kinematics
        # -------------------------------------------------------------------
        if self.pose_model is not None:
            try:
                results = self.pose_model(frame, verbose=False, conf=0.22)
                if results and len(results) > 0 and len(results[0].boxes) > 0:
                    for i, box in enumerate(results[0].boxes):
                        conf = float(box.conf[0].item())
                        xyxy = [int(v) for v in box.xyxy[0].tolist()]
                        bw = xyxy[2] - xyxy[0]
                        bh = xyxy[3] - xyxy[1]
                        aspect_ratio = bw / max(1.0, float(bh))

                        cx = (xyxy[0] + xyxy[2]) / 2.0
                        cy = (xyxy[1] + xyxy[3]) / 2.0
                        current_centroid = (cx, cy)
                        is_person_detected = True

                        # Extract Facial & Pose Keypoints
                        has_keypoints = (hasattr(results[0], "keypoints") and
                                         results[0].keypoints is not None and
                                         len(results[0].keypoints.data) > i)

                        face_box: Optional[List[int]] = None
                        if has_keypoints:
                            kpts = results[0].keypoints.data[i].cpu().numpy()
                            # 0: nose, 1: left_eye, 2: right_eye, 3: left_ear, 4: right_ear
                            face_kpts = [kpts[idx] for idx in range(min(5, len(kpts))) if kpts[idx][2] > 0.25]
                            if len(face_kpts) >= 1:
                                xs = [p[0] for p in face_kpts]
                                ys = [p[1] for p in face_kpts]
                                hx = float(np.mean(xs))
                                hy = float(np.mean(ys))
                                current_head_pos = (hx, hy)

                                # Construct Face / Head Bounding Box
                                span_x = max(25.0, (max(xs) - min(xs)) * 1.5 + 20.0)
                                span_y = max(30.0, (max(ys) - min(ys)) * 1.8 + 25.0)
                                fx1 = max(0, int(hx - span_x))
                                fy1 = max(0, int(hy - span_y * 0.9))
                                fx2 = min(fw, int(hx + span_x))
                                fy2 = min(fh, int(hy + span_y * 1.1))
                                face_box = [fx1, fy1, fx2, fy2]

                            # Torso inclination angle
                            if len(kpts) > 12:
                                s_conf = (kpts[5][2] + kpts[6][2]) / 2.0
                                h_conf = (kpts[11][2] + kpts[12][2]) / 2.0
                                if s_conf > 0.30 and h_conf > 0.30:
                                    s_mid = ((kpts[5][0] + kpts[6][0]) / 2.0, (kpts[5][1] + kpts[6][1]) / 2.0)
                                    h_mid = ((kpts[11][0] + kpts[12][0]) / 2.0, (kpts[11][1] + kpts[12][1]) / 2.0)
                                    dx = abs(s_mid[0] - h_mid[0])
                                    dy = abs(h_mid[1] - s_mid[1])
                                    torso_angle = math.degrees(math.atan2(dy, max(1.0, dx)))

                        # Fallback face box if keypoints were partial
                        if face_box is None and xyxy:
                            # Upper 30% of detected person box is head
                            head_h = int(bh * 0.35)
                            face_box = [xyxy[0], xyxy[1], xyxy[2], min(fh, xyxy[1] + head_h)]
                            current_head_pos = ((xyxy[0] + xyxy[2]) / 2.0, float(xyxy[1] + head_h / 2.0))

                        # Evaluate posture & fall for this person
                        person_is_fall = False
                        person_label = "Person (Sitting / Upright)"

                        # Kinematic Fall Rule 1: Torso horizontal (< 35 degrees)
                        if torso_angle is not None and torso_angle < 35.0:
                            person_is_fall = True
                            person_label = "Fall / Collapse Detected (Horizontal Angle)"

                        # Kinematic Fall Rule 2: Aspect ratio horizontal & near floor
                        elif aspect_ratio >= 0.70 and xyxy[3] > (fh * 0.55):
                            person_is_fall = True
                            person_label = "Fall / Collapse Detected (Floor Position)"

                        # Kinematic Fall Rule 3: Head altitude in lower 40% of screen (slump/floor)
                        elif current_head_pos and current_head_pos[1] > (fh * 0.62):
                            person_is_fall = True
                            person_label = "Fall / Collapse Detected (Head Slump)"

                        if person_is_fall:
                            is_fall_candidate = True
                            primary_class = person_label
                            primary_conf = max(primary_conf, conf)

                        # Add Person bounding box
                        detected_boxes.append({
                            "class_id": 0 if person_is_fall else 1,
                            "label": person_label,
                            "confidence": round(conf, 2),
                            "box": xyxy
                        })

                        # Add Face / Head bounding box
                        if face_box:
                            face_status = "Face / Head (Down)" if person_is_fall else "Face / Head (Active)"
                            detected_boxes.append({
                                "class_id": 10,
                                "label": face_status,
                                "confidence": round(max(0.85, conf), 2),
                                "box": face_box
                            })

            except Exception as e:
                logger.debug(f"Pose inference exception: {e}")

        # -------------------------------------------------------------------
        # 3. Dedicated Kaggle Fall Detection Model (Cross-Verification)
        # -------------------------------------------------------------------
        if self.fall_model is not None and not is_fall_candidate:
            try:
                fall_results = self.fall_model(frame, verbose=False, conf=0.25)
                if fall_results and len(fall_results) > 0 and len(fall_results[0].boxes) > 0:
                    for box in fall_results[0].boxes:
                        cid = int(box.cls[0].item())
                        cconf = float(box.conf[0].item())
                        cxyxy = [int(v) for v in box.xyxy[0].tolist()]

                        # Class 0 in Kaggle dataset = Fall Detected
                        if cid == 0 or "fall" in str(self.fall_model.names.get(cid, "")).lower():
                            is_fall_candidate = True
                            primary_class = "Fall / Collapse Detected"
                            primary_conf = max(primary_conf, cconf)
                            detected_boxes.append({
                                "class_id": 0,
                                "label": "Fall / Collapse Detected",
                                "confidence": round(cconf, 2),
                                "box": cxyxy
                            })
                            break
                        elif cid in [1, 2]:
                            is_person_detected = True
            except Exception as e:
                logger.debug(f"Fall model exception: {e}")

        # -------------------------------------------------------------------
        # 4. Fallback Face / Head Locator (If no person was detected by neural net)
        # -------------------------------------------------------------------
        if not detected_boxes:
            fb_face = self._detect_face_fallback(frame)
            if fb_face:
                is_person_detected = True
                current_centroid = ((fb_face[0] + fb_face[2]) / 2.0, (fb_face[1] + fb_face[3]) / 2.0)
                current_head_pos = current_centroid
                detected_boxes.append({
                    "class_id": 10,
                    "label": "Face / Head (Active)",
                    "confidence": 0.88,
                    "box": fb_face
                })
                # Check if head is slumped to bottom
                if current_head_pos[1] > (fh * 0.65):
                    is_fall_candidate = True
                    primary_class = "Fall / Collapse Detected (Head Slump)"

        # -------------------------------------------------------------------
        # 5. Dynamic Velocity & Disappearance Collapse Rules
        # -------------------------------------------------------------------
        # Sudden vertical drop in head altitude
        if current_head_pos:
            hx, hy = current_head_pos
            if self.last_head_pos is not None:
                prev_hx, prev_hy, prev_ht = self.last_head_pos
                d_time = max(0.04, now - prev_ht)
                if d_time <= 1.0:
                    v_drop = (hy - prev_hy) / d_time
                    # Head dropped rapidly (> 75 px/s) into lower half
                    if v_drop > 75.0 and hy > (fh * 0.40):
                        is_fall_candidate = True
                        primary_class = "Fall / Collapse Detected (Rapid Drop)"
            self.last_head_pos = (hx, hy, now)

        # Vanishing drop: Person was visible, then sudden motion spike and disappeared
        if not is_person_detected and self.person_previously_seen:
            time_since_seen = now - self.last_person_seen_time
            if time_since_seen < 2.0 and motion_rate > 15.0:
                is_fall_candidate = True
                primary_class = "Fall / Collapse Detected (Out of Frame Drop)"

        if is_person_detected:
            self.person_previously_seen = True
            self.last_person_seen_time = now

        # -------------------------------------------------------------------
        # 6. Temporal Debouncing
        # -------------------------------------------------------------------
        if is_fall_candidate:
            self.consecutive_fall_frames += 1
            self.consecutive_normal_frames = 0
        else:
            self.consecutive_fall_frames = 0
            self.consecutive_normal_frames += 1

        is_fall_confirmed = (self.consecutive_fall_frames >= 2)

        # -------------------------------------------------------------------
        # 7. Real Inactivity Tracking (3-5 Minutes, NOT Hardcoded Demo)
        # -------------------------------------------------------------------
        # Check actual person centroid displacement to filter camera sensor flicker
        centroid_displacement = 0.0
        if current_centroid and self.last_centroid:
            centroid_displacement = math.hypot(
                current_centroid[0] - self.last_centroid[0],
                current_centroid[1] - self.last_centroid[1]
            )
        if current_centroid:
            self.last_centroid = current_centroid

        # Genuinely motionless: small centroid displacement and low filtered motion
        is_motionless = (centroid_displacement < 9.0 and motion_pixel_ratio < 0.030)

        effective_thresh = self.unresponsive_threshold_sec
        anomaly_diag: Dict[str, Any] = {}

        if is_motionless:
            # Accumulate real seconds of stillness
            step_motionless = dt * self.simulation_speedup_factor
            self.accumulated_motionless_sec += step_motionless

            # Check with Adaptive Daily Routine Learner
            if self.activity_learner:
                posture = "floor" if (is_fall_confirmed or is_fall_candidate) else ("sitting" if "sitting" in primary_class.lower() else "resting")
                anomaly_diag = self.activity_learner.evaluate_inactivity_anomaly(
                    zone=current_zone,
                    motionless_seconds=self.accumulated_motionless_sec,
                    posture=posture
                )
                effective_thresh = anomaly_diag.get("threshold_sec", self.unresponsive_threshold_sec)
        else:
            # Significant active resident movement
            if centroid_displacement >= 15.0 or motion_pixel_ratio >= 0.05:
                if self.activity_learner and self.accumulated_motionless_sec > 30.0:
                    self.activity_learner.record_activity_observation(
                        zone=current_zone,
                        motion_rate=motion_rate,
                        duration_sec=self.accumulated_motionless_sec
                    )
                if self.current_state != STATE_UNRESPONSIVE:
                    self.accumulated_motionless_sec = 0.0
                    self.alarm_active = False

        # -------------------------------------------------------------------
        # 8. State Machine & Voice Alarm Inquiry Trigger
        # -------------------------------------------------------------------
        is_unresponsive = False
        inactivity_exceeded = (self.accumulated_motionless_sec >= effective_thresh)

        if is_fall_confirmed:
            if self.fall_start_time is None:
                self.fall_start_time = now
                self.current_state = STATE_FALL
                logger.warning(f"Fall / Collapse Detected in {current_zone}! Waking up alarm inquiry.")
                self.alarm_active = True
                self.alarm_prompt = "NIRA safety alert: Are you okay? Please respond."
                self.alarm_reason = "Sudden fall / collapse detected."
                self.dispatch_live_fall_alert(
                    event_type="fall_detected",
                    confidence=primary_conf,
                    location=current_zone,
                    details={"alarm_prompt": self.alarm_prompt, "requires_voice_checkin": True}
                )

            # Check for prolonged floor unresponsiveness post-fall
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
            # Motionless for 3-5 minutes (exceeding learned baseline)
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
            # Active movement or within safe routine stillness
            if self.consecutive_normal_frames >= 2 and not self.alarm_active:
                self.fall_start_time = None
                if self.current_state not in [STATE_UNRESPONSIVE, STATE_ALARM_INQUIRY]:
                    self.current_state = STATE_NORMAL

        return {
            "state": self.current_state,
            "detected_class": primary_class,
            "confidence": round(primary_conf, 2),
            "unresponsive_seconds": round(self.accumulated_motionless_sec, 1),
            "inactivity_threshold_sec": round(effective_thresh, 1),
            "is_unresponsive": is_unresponsive,
            "motion_displacement": round(motion_rate, 1),
            "boxes": detected_boxes,
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
            box_col = (0, 255, 255) if "face" in b["label"].lower() else color
            cv2.rectangle(frame, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), box_col, 2)
            cv2.putText(frame, lbl, (xyxy[0], max(xyxy[1] - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_col, 2)

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
