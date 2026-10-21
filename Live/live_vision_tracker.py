"""
NIRA Live Model & Real-Time Sensor Processing Engine.
Amazon Developer Hackathon 2026.

Integrates real-time camera inference with trained YOLOv8 model on Kaggle dataset.
Evaluates:
  1. NORMAL MOVEMENT (Walking / Sitting)
  2. FALL DETECTED (Class 0: Fall Detected)
  3. UNRESPONSIVENESS (Motionless on floor > threshold seconds)
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

logger = logging.getLogger("NIRA.LiveVisionTracker")

# Label mappings from Kaggle Fall Detection Dataset
CLASS_NAMES = {
    0: "Fall Detected",
    1: "Walking",
    2: "Sitting"
}

STATE_NORMAL = "NORMAL_MOVEMENT"
STATE_FALL = "FALL_DETECTED"
STATE_UNRESPONSIVE = "UNRESPONSIVENESS"


class LiveVisionTracker:
    """
    Connects to live camera devices or edge video feeds and evaluates
    real-time fall status & unresponsiveness using custom-trained YOLOv8.
    """
    def __init__(
        self,
        model_path: Optional[str] = None,
        backend_url: str = "http://localhost:8000",
        unresponsive_threshold_sec: float = 4.0
    ):
        self.backend_url = backend_url.rstrip("/")
        self.unresponsive_threshold_sec = unresponsive_threshold_sec
        self.model = None
        self.model_type = "yolov8"

        # State tracking
        self.current_state = STATE_NORMAL
        self.last_detection_time = time.time()
        self.fall_start_time: Optional[float] = None
        self.unresponsive_start_time: Optional[float] = None
        self.last_centroid: Optional[Tuple[float, float]] = None
        self.last_motion_rate = 0.0
        self.last_alert_sent_time = 0.0
        self.consecutive_fall_frames = 0
        self.consecutive_normal_frames = 0
        self.prev_gray: Optional[np.ndarray] = None

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
        """Resets state machine and counters when stream stops or starts."""
        self.current_state = STATE_NORMAL
        self.fall_start_time = None
        self.unresponsive_start_time = None
        self.last_centroid = None
        self.last_motion_rate = 0.0
        self.consecutive_fall_frames = 0
        self.consecutive_normal_frames = 0
        self.prev_gray = None

    def initialize_model(self):
        """Loads trained YOLOv8 model if ultralytics is installed."""
        try:
            from ultralytics import YOLO

            # Refresh resolution in case training just completed
            live_dir = Path(__file__).resolve().parent
            custom_model = live_dir / "nira_fall_model.pt"
            if custom_model.exists():
                self.resolved_model_path = str(custom_model)

            if self.resolved_model_path and os.path.exists(self.resolved_model_path):
                self.model = YOLO(self.resolved_model_path)
                logger.info(f"Loaded YOLOv8 model from {self.resolved_model_path}")
            else:
                logger.warning("No existing model weights found; attempting YOLO('yolov8n.pt')")
                self.model = YOLO("yolov8n.pt")
                self.resolved_model_path = "yolov8n.pt"
        except Exception as e:
            logger.warning(f"Ultralytics model initialization error: {e}. Running optical fallback mode.")
            self.model = None

    def evaluate_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Runs inference on single image/frame and computes:
        - state: NORMAL_MOVEMENT | FALL_DETECTED | UNRESPONSIVENESS
        - detected_class: Fall Detected | Walking | Sitting | Normal Movement | Fall / Collapse Detected
        - boxes: list of detections [x1, y1, x2, y2]
        - unresponsive_seconds: seconds stationary on ground/desk
        """
        now = time.time()
        if frame is None or not hasattr(frame, "shape"):
            return {
                "state": self.current_state,
                "detected_class": "Normal Movement",
                "confidence": 0.95,
                "unresponsive_seconds": 0.0,
                "is_unresponsive": False,
                "motion_displacement": 0.0,
                "boxes": [],
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

        if self.model is not None:
            try:
                # Run YOLO proposal generation with conf=0.35 to catch candidate boxes
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

                        # Reject full-screen hallucinations (>85% of entire frame) and micro-noise
                        if area_ratio > 0.85 or area_ratio < 0.005 or bw < 20 or bh < 20:
                            continue

                        label = CLASS_NAMES.get(cls_id, f"Class {cls_id}")

                        # Confidence and posture validation for Fall Detected
                        if cls_id == 0 or "fall" in label.lower():
                            if conf < 0.50:
                                continue

                            # Biomechanical posture check:
                            # A real fall is horizontal (aspect_ratio >= 0.70) or in the lower half of frame
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
                            "centroid": ((xyxy[0] + xyxy[2]) / 2.0, (xyxy[1] + xyxy[3]) / 2.0)
                        })

            except Exception as e:
                logger.error(f"Inference error: {e}")

        # 2. Cross-class Non-Maximum Suppression (resolve Sitting vs Fall overlap on same person)
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

        # 3. Determine frame-level detection
        primary_class = "Normal Movement"
        primary_conf = 0.95
        is_fall_candidate = False

        if filtered_boxes:
            best = filtered_boxes[0]
            primary_class = best["label"]
            primary_conf = best["confidence"]
            if best["class_id"] == 0 or "fall" in best["label"].lower():
                is_fall_candidate = True

        # 4. Postural Slump / Head-Down Collapse (Webcam Close-Up Fall Detection)
        # If YOLO did not detect an upright standing/sitting resident, inspect visual mass distribution
        if not yolo_normal and not is_fall_candidate and gray_curr is not None:
            top_h = int(fh * 0.45)
            dark_top = np.sum(gray_curr[:top_h, :] < 80)
            dark_bottom = np.sum(gray_curr[top_h:, :] < 80)
            total_dark = dark_top + dark_bottom

            if total_dark > (fh * fw * 0.06): # Significant subject present
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

        # 5. Temporal debouncing (prevent single-frame flashes)
        if is_fall_candidate:
            self.consecutive_fall_frames += 1
            self.consecutive_normal_frames = 0
        else:
            self.consecutive_fall_frames = 0
            self.consecutive_normal_frames += 1

        # Fall confirmed after 2 consecutive detections
        is_fall_confirmed = (self.consecutive_fall_frames >= 2)

        # 6. Update Fall & Unresponsiveness State Machine
        unresponsive_seconds = 0.0
        is_unresponsive = False

        if is_fall_confirmed:
            if self.fall_start_time is None:
                self.fall_start_time = now
                self.current_state = STATE_FALL
                logger.warning("Fall / Collapse detected in camera feed!")
                self.dispatch_live_fall_alert(event_type="fall_detected", confidence=primary_conf)

            # Check if resident remains motionless
            fall_duration = now - self.fall_start_time
            if motion_rate < 8.0:
                unresponsive_seconds = fall_duration
                if fall_duration >= self.unresponsive_threshold_sec:
                    self.current_state = STATE_UNRESPONSIVE
                    is_unresponsive = True
                    if now - self.last_alert_sent_time > 10.0:
                        self.last_alert_sent_time = now
                        self.dispatch_live_fall_alert(
                            event_type="unresponsiveness_detected",
                            confidence=primary_conf,
                            details={"motionless_seconds": round(fall_duration, 1)}
                        )
                else:
                    self.current_state = STATE_FALL
            else:
                # Moderate/high movement post fall (e.g. resident recovered or stood up)
                if motion_rate > 18.0 and fall_duration > 3.0:
                    self.fall_start_time = None
                    self.current_state = STATE_NORMAL
        else:
            # Resident is normal or clear
            if self.consecutive_normal_frames >= 2 or primary_class in ["Walking", "Sitting"]:
                self.fall_start_time = None
                self.current_state = STATE_NORMAL

        # Output boxes without internal centroid field
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
            "unresponsive_seconds": round(unresponsive_seconds, 1),
            "is_unresponsive": is_unresponsive,
            "motion_displacement": round(motion_rate, 1),
            "boxes": clean_boxes,
            "timestamp": now
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
            "movement_after_event": "none" if event_type == "unresponsiveness_detected" else "slow",
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
            hud_text += f" | IMMOBILE: {res['unresponsive_seconds']}s"

        cv2.putText(frame, hud_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
        cv2.imshow("NIRA Live Vision - Fall & Unresponsiveness", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
