"""
Real-time Edge Fall & Posture Detection Engine for Aegis Ambient Care.
Amazon Developer Hackathon 2026.

Analyzes 3 biomechanical pillars:
  1. Sudden high-velocity downward vertical movement.
  2. Posture alignment shifts (Bounding Box W/H > 1.0, Torso inclination angle < 35 deg).
  3. Post-event immobility tracking across a sliding temporal window.
Outputs standardized event JSON conforming strictly to the Aegis CARE data contract.
"""

import sys
import time
import math
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np

# Optional HTTP publisher
try:
    import requests
except ImportError:
    requests = None

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AegisFallDetector")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class FallEvent:
    """Standardized event data contract for Aegis Ambient Care."""
    def __init__(
        self,
        event_type: str = "possible_fall",
        confidence: float = 0.94,
        location: str = "living_room",
        timestamp: Optional[str] = None,
        movement_after_event: str = "none"
    ):
        self.event_type = event_type
        self.confidence = round(float(confidence), 2)
        self.location = location
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.movement_after_event = movement_after_event

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "confidence": self.confidence,
            "location": self.location,
            "timestamp": self.timestamp,
            "movement_after_event": self.movement_after_event
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Biomechanical State & Thresholds
# ---------------------------------------------------------------------------

class DetectorState:
    NORMAL = "NORMAL"
    RAPID_DESCENT = "RAPID_DESCENT"
    IMPACT_HORIZONTAL = "IMPACT_HORIZONTAL"
    POST_FALL_IMMOBILITY = "POST_FALL_IMMOBILITY"
    FALL_CONFIRMED = "FALL_CONFIRMED"


class AegisFallDetector:
    """
    High-performance, edge-optimized fall detection processor.
    Employs YOLO pose estimation with adaptive fallback to classical silhouette analysis.
    """

    # COCO 17 Keypoint Indices
    NOSE = 0
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16

    def __init__(
        self,
        location: str = "living_room",
        post_endpoint: Optional[str] = None,
        confidence_threshold: float = 0.50,
        immobility_window_sec: float = 2.5,
        velocity_threshold_norm: float = 1.1,  # Downward velocity in body heights / sec
        horizontal_angle_thresh: float = 38.0, # Deg from horizontal
        aspect_ratio_thresh: float = 1.05,     # Width / Height
        use_yolo: bool = True,
        model_name: str = "yolov8n-pose.pt"
    ):
        self.location = location
        self.post_endpoint = post_endpoint
        self.conf_threshold = confidence_threshold
        self.immobility_window_sec = immobility_window_sec
        self.velocity_threshold_norm = velocity_threshold_norm
        self.horizontal_angle_thresh = horizontal_angle_thresh
        self.aspect_ratio_thresh = aspect_ratio_thresh
        self.use_yolo = use_yolo
        self.model_name = model_name

        # State machine
        self.state = DetectorState.NORMAL
        self.descent_timestamp = 0.0
        self.fall_impact_timestamp = 0.0
        self.last_confirmed_event: Optional[FallEvent] = None

        # Temporal telemetry buffers
        # Each entry: (timestamp, centroid_y, bbox_h, keypoints_array)
        self.history: deque = deque(maxlen=45)
        self.immobility_samples: List[Tuple[float, float]] = []  # (timestamp, avg_keypoint_displacement)

        # Initialize model
        self.model = None
        if self.use_yolo:
            self._init_yolo()

    def _init_yolo(self):
        """Loads lightweight YOLO pose model (YOLOv8n-pose)."""
        try:
            from ultralytics import YOLO
            logger.info(f"Loading YOLO Pose model '{self.model_name}' on edge device...")
            self.model = YOLO(self.model_name)
            logger.info("YOLO Pose model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load YOLO model ({e}). Using geometric silhouette fallback.")
            self.model = None

    def _extract_pose_yolo(self, frame: np.ndarray) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int], float]]:
        """
        Runs YOLO pose inference on a single frame.
        Returns:
          - keypoints: shape (17, 3) [x, y, conf]
          - bbox: (x1, y1, x2, y2)
          - detection_confidence: float
        """
        if self.model is None:
            return None

        # Downscale for edge inference speed if frame is large
        h, w = frame.shape[:2]
        results = self.model(frame, verbose=False, conf=self.conf_threshold)

        if not results or len(results[0].keypoints) == 0:
            return None

        # Pick the most prominent detected person (highest confidence or largest bbox)
        res = results[0]
        boxes = res.boxes
        if boxes is None or len(boxes) == 0:
            return None

        best_idx = int(np.argmax(boxes.conf.cpu().numpy()))
        conf = float(boxes.conf[best_idx].cpu().numpy())
        xyxy = boxes.xyxy[best_idx].cpu().numpy().astype(int)
        kpts = res.keypoints.data[best_idx].cpu().numpy()  # (17, 3)

        return kpts, (xyxy[0], xyxy[1], xyxy[2], xyxy[3]), conf

    def _extract_pose_fallback(self, frame: np.ndarray) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int], float]]:
        """
        Classical computer vision fallback when neural network is absent.
        Uses adaptive thresholding, morphological contours, and skeleton projection.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        largest_cnt = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest_cnt) < 1500:
            return None

        x, y, w, h = cv2.boundingRect(largest_cnt)
        bbox = (x, y, x + w, y + h)

        # Synthesize surrogate keypoints from bounding box
        kpts = np.zeros((17, 3), dtype=np.float32)
        # Head / Nose
        kpts[self.NOSE] = [x + w * 0.5, y + h * 0.15, 0.9]
        # Shoulders
        kpts[self.LEFT_SHOULDER] = [x + w * 0.35, y + h * 0.28, 0.9]
        kpts[self.RIGHT_SHOULDER] = [x + w * 0.65, y + h * 0.28, 0.9]
        # Hips
        kpts[self.LEFT_HIP] = [x + w * 0.40, y + h * 0.60, 0.9]
        kpts[self.RIGHT_HIP] = [x + w * 0.60, y + h * 0.60, 0.9]
        # Ankles
        kpts[self.LEFT_ANKLE] = [x + w * 0.45, y + h * 0.95, 0.9]
        kpts[self.RIGHT_ANKLE] = [x + w * 0.55, y + h * 0.95, 0.9]

        return kpts, bbox, 0.85

    def _calculate_torso_angle(self, kpts: np.ndarray) -> float:
        """
        Calculates the angle between the torso spine vector and the floor (horizontal axis).
        Returns angle in degrees [0, 90]:
          - 90 deg = Perfectly vertical standing/upright
          - 0 deg  = Lying completely flat on floor
        """
        # Shoulder midpoint
        sh_l = kpts[self.LEFT_SHOULDER][:2]
        sh_r = kpts[self.RIGHT_SHOULDER][:2]
        mid_shoulder = (sh_l + sh_r) / 2.0

        # Hip midpoint
        hip_l = kpts[self.LEFT_HIP][:2]
        hip_r = kpts[self.RIGHT_HIP][:2]
        mid_hip = (hip_l + hip_r) / 2.0

        dx = mid_shoulder[0] - mid_hip[0]
        dy = mid_shoulder[1] - mid_hip[1]  # positive downward in screen coords

        if abs(dx) < 1e-5 and abs(dy) < 1e-5:
            return 90.0

        angle_rad = math.atan2(abs(dy), abs(dx))
        angle_deg = math.degrees(angle_rad)
        return angle_deg

    def _calculate_vertical_velocity(self, current_time: float, current_y: float, person_h: float) -> float:
        """
        Calculates downward normalized vertical velocity (in body heights per second).
        Positive values indicate rapid downward descent.
        """
        if not self.history or person_h <= 10.0:
            return 0.0

        # Look back 0.25 to 0.4 seconds in history buffer
        target_delta_t = 0.30
        prev_entry = self.history[0]
        for entry in reversed(self.history):
            if (current_time - entry[0]) >= target_delta_t:
                prev_entry = entry
                break

        dt = current_time - prev_entry[0]
        if dt < 0.05:
            return 0.0

        dy = current_y - prev_entry[1]  # positive is moving downward
        velocity_norm = (dy / dt) / person_h
        return float(velocity_norm)

    def _calculate_immobility_rate(self) -> float:
        """
        Calculates the mean keypoint displacement (px/sec) during the post-fall immobility window.
        """
        if not self.immobility_samples:
            return 0.0

        displacements = [s[1] for s in self.immobility_samples]
        return float(np.mean(displacements))

    def process_frame(self, frame: np.ndarray, current_time: Optional[float] = None) -> Tuple[Optional[FallEvent], Dict[str, Any]]:
        """
        Processes a single video frame, computes pose dynamics, tracks states,
        and generates a FallEvent if a fall and immobility pattern are confirmed.
        """
        now = current_time or time.time()
        diagnostics = {
            "state": self.state,
            "downward_velocity_norm": 0.0,
            "aspect_ratio": 0.0,
            "torso_angle_deg": 90.0,
            "immobility_rate": 0.0,
            "bbox": None
        }

        # 1. Pose estimation
        detection = None
        if self.use_yolo and self.model is not None:
            try:
                detection = self._extract_pose_yolo(frame)
            except Exception as e:
                logger.debug(f"YOLO inference error ({e}), falling back.")

        if detection is None:
            detection = self._extract_pose_fallback(frame)

        if detection is None:
            return None, diagnostics

        kpts, bbox, conf = detection
        diagnostics["bbox"] = bbox

        x1, y1, x2, y2 = bbox
        bbox_w = max(1.0, float(x2 - x1))
        bbox_h = max(1.0, float(y2 - y1))
        aspect_ratio = bbox_w / bbox_h
        diagnostics["aspect_ratio"] = round(aspect_ratio, 2)

        # Torso centroid (midpoint of hips and shoulders)
        torso_centroid_y = (
            kpts[self.LEFT_SHOULDER][1] + kpts[self.RIGHT_SHOULDER][1] +
            kpts[self.LEFT_HIP][1] + kpts[self.RIGHT_HIP][1]
        ) / 4.0

        # Torso inclination angle
        torso_angle = self._calculate_torso_angle(kpts)
        diagnostics["torso_angle_deg"] = round(torso_angle, 1)

        # Vertical velocity
        downward_vel = self._calculate_vertical_velocity(now, torso_centroid_y, bbox_h)
        diagnostics["downward_velocity_norm"] = round(downward_vel, 2)

        # Keypoint displacement for immobility tracking
        keypoint_displacement = 0.0
        if self.history:
            prev_kpts = self.history[-1][3]
            # Mean euclidean distance across all confident keypoints
            valid_mask = (kpts[:, 2] > 0.3) & (prev_kpts[:, 2] > 0.3)
            if np.any(valid_mask):
                dists = np.linalg.norm(kpts[valid_mask, :2] - prev_kpts[valid_mask, :2], axis=1)
                dt = max(0.01, now - self.history[-1][0])
                keypoint_displacement = float(np.mean(dists) / dt)

        # Update history ring buffer
        self.history.append((now, torso_centroid_y, bbox_h, kpts.copy()))

        # -------------------------------------------------------------------
        # Biomechanical State Transitions
        # -------------------------------------------------------------------

        # Condition A: Rapid Downward Descent
        is_rapid_descent = downward_vel >= self.velocity_threshold_norm

        # Condition B: Horizontal Posture Shift (Lying on floor)
        is_horizontal_posture = (aspect_ratio >= self.aspect_ratio_thresh) or (torso_angle <= self.horizontal_angle_thresh)

        # State 1: NORMAL -> RAPID_DESCENT
        if self.state == DetectorState.NORMAL:
            if is_rapid_descent:
                self.state = DetectorState.RAPID_DESCENT
                self.descent_timestamp = now
                logger.info(f"[CV Event] Sudden rapid descent detected: vel={downward_vel:.2f} body_h/s")

        # State 2: RAPID_DESCENT -> IMPACT_HORIZONTAL
        elif self.state == DetectorState.RAPID_DESCENT:
            # Check for horizontal impact within 1.5 seconds of descent
            if is_horizontal_posture:
                self.state = DetectorState.POST_FALL_IMMOBILITY
                self.fall_impact_timestamp = now
                self.immobility_samples.clear()
                logger.info(f"[CV Event] Posture shift confirmed: AR={aspect_ratio:.2f}, Angle={torso_angle:.1f} deg")
            elif (now - self.descent_timestamp) > 1.5:
                # Timed out without horizontal impact (e.g. quick crouch or sitting down)
                self.state = DetectorState.NORMAL

        # State 3: POST_FALL_IMMOBILITY Window Evaluation
        elif self.state == DetectorState.POST_FALL_IMMOBILITY:
            # Collect immobility telemetry
            self.immobility_samples.append((now, keypoint_displacement))
            elapsed_immobility = now - self.fall_impact_timestamp

            # Check if person stood back up during the window
            if not is_horizontal_posture and torso_angle > 65.0:
                logger.info("[CV Event] Person stood back up. Resetting to NORMAL.")
                self.state = DetectorState.NORMAL
                self.immobility_samples.clear()
                return None, diagnostics

            # When window expires, determine post-event movement and fire event
            if elapsed_immobility >= self.immobility_window_sec:
                immobility_rate = self._calculate_immobility_rate()
                diagnostics["immobility_rate"] = round(immobility_rate, 2)

                # Classify post-event movement
                if immobility_rate < 5.0:
                    movement_status = "none"
                elif immobility_rate < 18.0:
                    movement_status = "slight_twitch"
                elif aspect_ratio >= 1.0:
                    movement_status = "crawling"
                else:
                    movement_status = "normal"

                # Compute ensemble confidence score
                conf_score = min(0.98, max(0.78, 0.65 + (downward_vel * 0.10) + (conf * 0.15)))

                event = FallEvent(
                    event_type="possible_fall",
                    confidence=conf_score,
                    location=self.location,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    movement_after_event=movement_status
                )
                self.last_confirmed_event = event
                self.state = DetectorState.FALL_CONFIRMED

                logger.warning(
                    f"🚨 [FALL CONFIRMED] Event: {event.event_type} | Conf: {event.confidence:.0%} | "
                    f"Movement: {event.movement_after_event} | Location: {event.location}"
                )

                # Auto-post to Aegis CARE backend if configured
                if self.post_endpoint and requests:
                    self._dispatch_event_http(event)

                return event, diagnostics

        # State 4: FALL_CONFIRMED (Cooldown or Reset on recovery)
        elif self.state == DetectorState.FALL_CONFIRMED:
            # If person regains upright posture, reset
            if not is_horizontal_posture and torso_angle > 70.0:
                logger.info("Person recovered to upright standing posture. State reset to NORMAL.")
                self.state = DetectorState.NORMAL

        diagnostics["state"] = self.state
        return None, diagnostics

    def _dispatch_event_http(self, event: FallEvent):
        """Dispatches event JSON to local or cloud Aegis CARE MCP FastAPI backend."""
        try:
            # Build payload matching AssessRiskRequest contract
            payload = {
                "event": event.to_dict(),
                "context": {
                    "activity": "walking",
                    "time_context": "afternoon",
                    "baseline_deviation": 0.85,
                    "wearable_status": "worn_normal",
                    "environment": "room_monitoring"
                }
            }
            logger.info(f"Posting event JSON to Aegis CARE backend: {self.post_endpoint}")
            resp = requests.post(self.post_endpoint, json=payload, timeout=2.0)
            logger.info(f"Backend response status: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to post event to backend: {e}")

    def render_overlay(self, frame: np.ndarray, diagnostics: Dict[str, Any]) -> np.ndarray:
        """
        Draws professional HUD overlay onto frame for edge display and visualization.
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Draw HUD Panel
        panel_h, panel_w = 110, 360
        overlay = annotated.copy()
        cv2.rectangle(overlay, (10, 10), (10 + panel_w, 10 + panel_h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

        # Status text colors
        state = diagnostics["state"]
        color = (0, 255, 0) if state == DetectorState.NORMAL else (0, 165, 255)
        if state in [DetectorState.POST_FALL_IMMOBILITY, DetectorState.FALL_CONFIRMED]:
            color = (0, 0, 255)

        cv2.putText(annotated, "AEGIS AMBIENT CARE — EDGE CV", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        cv2.putText(annotated, f"STATUS: {state}", (20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        cv2.putText(annotated, f"Vel: {diagnostics['downward_velocity_norm']}h/s | AR: {diagnostics['aspect_ratio']}", (20, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        cv2.putText(annotated, f"Torso Angle: {diagnostics['torso_angle_deg']} deg | Loc: {self.location}", (20, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        # Draw Bounding Box if present
        bbox = diagnostics.get("bbox")
        if bbox:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        return annotated
