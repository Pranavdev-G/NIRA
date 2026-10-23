"""
Train YOLOv8 on the Kaggle Fall Detection Dataset with dynamic path resolution.
Amazon Developer Hackathon 2026.

Classes:
  0: Fall Detected
  1: Walking (Normal Movement)
  2: Sitting (Normal Movement / Resting)
"""

import os
import glob
import shutil
import logging
from pathlib import Path
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NIRA.TrainFallDetector")


def resolve_or_download_dataset() -> Path:
    """Finds existing fall dataset or downloads via kagglehub if needed."""
    live_dir = Path(__file__).resolve().parent

    # Candidate locations on current machine
    candidates = [
        Path(os.path.expanduser("~/Downloads/archive(13)/fall_dataset")),
        Path(os.path.expanduser("~/.cache/kagglehub/datasets/uttejkumarkandagatla/fall-detection-dataset/versions/1/fall_dataset")),
        live_dir / "fall_dataset",
        live_dir.parent / "datasets" / "fall_dataset"
    ]

    # Also search glob in user cache
    cache_glob = glob.glob(os.path.expanduser("~/.cache/kagglehub/**/fall_dataset"), recursive=True)
    for p in cache_glob:
        candidates.append(Path(p))

    for c in candidates:
        if c.exists() and (c / "images").exists():
            logger.info(f"Found existing Kaggle dataset at: {c}")
            return c

    # Attempt download via kagglehub
    try:
        import kagglehub
        logger.info("Dataset not found locally; downloading 'uttejkumarkandagatla/fall-detection-dataset' via kagglehub...")
        download_path = kagglehub.dataset_download("uttejkumarkandagatla/fall-detection-dataset")
        ds_path = Path(download_path)
        if (ds_path / "fall_dataset").exists():
            ds_path = ds_path / "fall_dataset"
        logger.info(f"Downloaded dataset to: {ds_path}")
        return ds_path
    except Exception as e:
        logger.warning(f"Could not auto-download dataset: {e}")
        return live_dir / "fall_dataset"


def generate_runtime_yaml(dataset_path: Path) -> Path:
    """Writes a dynamic dataset YAML with current machine's absolute paths."""
    live_dir = Path(__file__).resolve().parent
    yaml_path = live_dir / "fall_dataset.yaml"

    yaml_content = f"""path: {dataset_path.as_posix()}
train: images/train
val: images/val

names:
  0: Fall Detected
  1: Walking
  2: Sitting
"""
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    logger.info(f"Generated runtime dataset configuration: {yaml_path}")
    return yaml_path


def train_model(epochs: int = 5, imgsz: int = 416, batch: int = 8, device: str = "cpu"):
    """Trains YOLOv8 nano on fall dataset and updates nira_fall_model.pt."""
    live_dir = Path(__file__).resolve().parent
    target_model_path = live_dir / "nira_fall_model.pt"

    ds_path = resolve_or_download_dataset()
    if not ds_path.exists() or not (ds_path / "images").exists():
        logger.warning(f"Dataset images not found at {ds_path}. Preserving existing model: {target_model_path}")
        return target_model_path

    yaml_path = generate_runtime_yaml(ds_path)
    logger.info(f"Starting training on {yaml_path} with epochs={epochs}, imgsz={imgsz}, batch={batch}, device={device}...")

    # Load base YOLOv8 nano model
    model = YOLO("yolov8n.pt")

    # Train model
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
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
    trained_path = train_model(epochs=5, imgsz=416, batch=8, device="cpu")
    print(f"Model training process complete. Model located at: {trained_path}")
