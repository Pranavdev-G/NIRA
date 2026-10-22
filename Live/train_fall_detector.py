"""
Train YOLOv8 on the Kaggle Fall Detection Dataset.
Classes:
  0: Fall Detected
  1: Walking (Normal Movement)
  2: Sitting (Normal Movement / Resting)
"""

import os
import shutil
import logging
from pathlib import Path
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NIRA.TrainFallDetector")

def train_model(epochs: int = 5, imgsz: int = 416, batch: int = 8):
    live_dir = Path(__file__).resolve().parent
    yaml_path = live_dir / "fall_dataset.yaml"
    target_model_path = live_dir / "nira_fall_model.pt"

    logger.info(f"Starting training on {yaml_path} with epochs={epochs}, imgsz={imgsz}, batch={batch}...")

    # Load base YOLOv8 nano model
    model = YOLO("yolov8n.pt")

    # Train model
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device="cpu",
        workers=2,
        project=str(live_dir / "runs"),
        name="fall_detection",
        exist_ok=True,
        verbose=True
    )

    # Locate best.pt or last.pt
    best_weights = live_dir / "runs" / "fall_detection" / "weights" / "best.pt"
    if not best_weights.exists():
        best_weights = live_dir / "runs" / "fall_detection" / "weights" / "last.pt"

    if best_weights.exists():
        shutil.copy(best_weights, target_model_path)
        logger.info(f"Successfully copied trained weights to: {target_model_path}")
    else:
        logger.warning(f"Weights not found at expected path: {best_weights}")

    return target_model_path

if __name__ == "__main__":
    trained_path = train_model(epochs=5, imgsz=416, batch=8)
    print(f"Model training complete. Target model saved at: {trained_path}")
