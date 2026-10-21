# NIRA Live Model Workspace

This folder is reserved for your **Live Models** and physical real-time pipelines.

## Suggested Live Components to Add:
- Real-time physical camera inputs (Webcam, RTSP stream, USB camera)
- Edge AI inference models (Custom YOLOv8 models, pose classification weights)
- Live IoT / Bluetooth device adapters (Apple Watch HealthKit receiver, mmWave radar serial port reader)
- Live audio microphone / voice stream processing

## Already Scaffolded:
- `live_vision_tracker.py` — Webcam YOLOv8 skeletal fall tracker
- `live_ingest_stream.py` — Real-time event streamer into NIRA Event Pipeline
