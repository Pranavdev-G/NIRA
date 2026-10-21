"""
Aegis Ambient Care - Real-time Edge Fall & Posture Detection CLI.
Amazon Developer Hackathon 2026.

Usage:
  # 1. Live Camera Feed
  python fall_detector.py --source 0 --location living_room

  # 2. Video File Input
  python fall_detector.py --source demo_fall.mp4 --location bathroom

  # 3. Synthetic Simulation Demo (No camera required)
  python fall_detector.py --source synthetic --demo

  # 4. Stream to local FastAPI MCP Server
  python fall_detector.py --source synthetic --post-url http://localhost:8000/tools/assess_risk
"""

import sys
import time
import argparse
import logging
from datetime import datetime, timezone
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np

from app.vision.fall_detector import AegisFallDetector, FallEvent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AegisFallRunner")


def generate_synthetic_frame(frame_idx: int, total_frames: int = 150) -> np.ndarray:
    """
    Generates a realistic synthetic test video frame showing:
      - Frames 0 - 40: Normal upright standing & subtle walking.
      - Frames 41 - 55: Sudden high-velocity downward fall (rapid drop).
      - Frames 56 - 150: Body horizontal on the floor with post-event immobility.
    """
    width, height = 640, 480
    frame = np.full((height, width, 3), 30, dtype=np.uint8)

    # Draw room background (floor line and ambient wall)
    cv2.line(frame, (0, 400), (width, 400), (70, 70, 70), 2)
    cv2.putText(frame, "AEGIS SYNTHETIC TEST SIMULATOR", (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)

    # Biomechanical sequence
    if frame_idx < 45:
        # Phase 1: Standing upright
        t_prog = frame_idx / 45.0
        center_x = int(240 + t_prog * 40)
        center_y = 250
        person_w = 70
        person_h = 190
    elif frame_idx < 58:
        # Phase 2: Rapid downward descent (The Fall)
        drop_prog = (frame_idx - 45) / 13.0
        center_x = int(280 + drop_prog * 60)
        center_y = int(250 + drop_prog * 120)  # Rapid vertical plunge
        # Transitioning from vertical to horizontal
        person_w = int(70 + drop_prog * 110)
        person_h = int(190 - drop_prog * 130)
    else:
        # Phase 3: Lying flat on floor with near-zero immobility
        center_x = 340
        center_y = 370
        person_w = 180
        person_h = 55
        # Add minimal realistic sensor noise (< 1.5px)
        jitter_x = int(np.random.normal(0, 0.4))
        jitter_y = int(np.random.normal(0, 0.3))
        center_x += jitter_x
        center_y += jitter_y

    x1 = max(10, center_x - person_w // 2)
    y1 = max(10, center_y - person_h // 2)
    x2 = min(width - 10, center_x + person_w // 2)
    y2 = min(height - 10, center_y + person_h // 2)

    # Render simulated person silhouette with distinct torso & head
    cv2.rectangle(frame, (x1, y1), (x2, y2), (200, 200, 200), -1)

    return frame


def run_pipeline(
    source: str,
    location: str = "living_room",
    post_url: Optional[str] = None,
    output_json_path: Optional[str] = None,
    headless: bool = False,
    immobility_sec: float = 2.0,
    max_frames: Optional[int] = None
) -> Optional[FallEvent]:
    """
    Executes the video ingestion and pose analysis loop.
    """
    logger.info("=" * 65)
    logger.info("Starting Aegis Fall Detection Vision Pipeline")
    logger.info(f"Source: {source} | Location: {location}")
    if post_url:
        logger.info(f"Auto-dispatch target: {post_url}")
    logger.info("=" * 65)

    detector = AegisFallDetector(
        location=location,
        post_endpoint=post_url,
        immobility_window_sec=immobility_sec,
        use_yolo=True
    )

    is_synthetic = (source.lower() == "synthetic")
    cap = None

    if not is_synthetic:
        # Check if source is integer (webcam index) or video file path
        if source.isdigit():
            cap_source = int(source)
        else:
            cap_source = source

        cap = cv2.VideoCapture(cap_source)
        if not cap.isOpened():
            logger.error(f"Failed to open video source: '{source}'. Falling back to synthetic simulation.")
            is_synthetic = True

    frame_idx = 0
    confirmed_event: Optional[FallEvent] = None
    t_start = time.time()

    if not is_synthetic and cap and cap.isOpened():
        logger.info(f"Live camera stream active. Monitoring frames... (Press Ctrl+C to stop{' or press q in GUI window' if not headless else ''})")

    try:
        while True:
            frame_time = t_start + (frame_idx * 0.033)  # Simulated 30 FPS clock

            if is_synthetic:
                frame = generate_synthetic_frame(frame_idx, total_frames=120)
                if max_frames and frame_idx >= max_frames:
                    break
                if not max_frames and frame_idx >= 120:
                    break
            else:
                ret, frame = cap.read()
                if not ret:
                    logger.info("End of video stream reached.")
                    break

            # Analyze frame through biomechanical 3-pillar engine
            event, diagnostics = detector.process_frame(frame, current_time=frame_time)

            if event:
                confirmed_event = event
                logger.info("\n" + "*" * 50)
                logger.info("STANDARDIZED EVENT JSON PAYLOAD:")
                logger.info(event.to_json(indent=2))
                logger.info("*" * 50 + "\n")

                if output_json_path:
                    with open(output_json_path, "w", encoding="utf-8") as f:
                        f.write(event.to_json(indent=2))
                    logger.info(f"Saved event JSON to {output_json_path}")

            # Visualization overlay
            if not headless:
                annotated = detector.render_overlay(frame, diagnostics)
                # Show frame if display environment available
                try:
                    cv2.imshow("Aegis Ambient Care - Fall Detection", annotated)
                    if cv2.waitKey(20) & 0xFF == ord('q'):
                        logger.info("User requested termination ('q').")
                        break
                except Exception:
                    # Headless or display error
                    pass

            frame_idx += 1

    except KeyboardInterrupt:
        logger.info("\nPipeline stopped by user (Ctrl+C).")
    finally:
        if cap:
            cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    logger.info(f"Pipeline completed: Processed {frame_idx} frames.")
    return confirmed_event


def main():
    parser = argparse.ArgumentParser(
        description="Aegis Ambient Care - Real-time Edge Fall & Posture Detection"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="synthetic",
        help="Video source: '0' (webcam), file path ('fall.mp4'), or 'synthetic' (default)"
    )
    parser.add_argument(
        "--location",
        type=str,
        default="living_room",
        help="Monitored room location (default: 'living_room')"
    )
    parser.add_argument(
        "--post-url",
        type=str,
        default=None,
        help="Optional HTTP URL to POST event JSON (e.g. http://localhost:8000/tools/assess_risk)"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional file path to write detected event JSON"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode without cv2.imshow GUI window (default: True)"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open an interactive GUI window displaying the live camera video with skeletal pose overlay (press 'q' to quit)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run short synthetic demonstration"
    )
    parser.add_argument(
        "--immobility-sec",
        type=float,
        default=1.5,
        help="Post-event immobility observation window in seconds (default: 1.5)"
    )

    args = parser.parse_args()

    if args.gui:
        args.headless = False

    if args.demo:
        args.source = "synthetic"
        args.headless = True

    try:
        event = run_pipeline(
            source=args.source,
            location=args.location,
            post_url=args.post_url,
            output_json_path=args.output_json,
            headless=args.headless,
            immobility_sec=args.immobility_sec
        )
    except KeyboardInterrupt:
        logger.info("\nPipeline stopped by user (Ctrl+C).")
        sys.exit(0)

    if event:
        print("\n=== FINAL CONFIRMED EVENT OUTPUT ===")
        print(event.to_json(indent=2))
        sys.exit(0)
    else:
        logger.info("No fall event met all confirmation thresholds during this run.")
        sys.exit(0)


if __name__ == "__main__":
    main()
