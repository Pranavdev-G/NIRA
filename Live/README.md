# NIRA Live Multi-Room Continuous Ambient Safety System
**Amazon Developer Hackathon 2026 | Ambient AI Safety Agent Track**

NIRA Live is a continuous multi-room ambient safety intelligence platform for senior care that unifies:
$$\text{ROOM} + \text{CAMERA} + \text{PERSON} + \text{POSTURE} + \text{MOVEMENT} + \text{ZONE DWELL} + \text{ACTIVITY ROUTINE} + \text{VOICE} + \text{VITALS} + \text{TIME CONTEXT}$$
into one authoritative, multimodal safety core.

---

## 🏛️ Core Architecture

```text
MULTIPLE ROOM CAMERAS (Living Room, Bathroom, Bedroom, Kitchen, Hallway)
        ↓
CAMERA MANAGER (Registry, Bounded Queues, Inter-Room Resident Handoff)
        ↓
PER-CAMERA ROOM TRACKER (YOLOv8 Pose + Kaggle Fall Model + Kinematics)
        ↓
ZONE SESSION TRACKING (Entry, Dwell Duration, Exit, Movement Intensity)
        ↓
ACTIVITY ROUTINE LEARNER (Personalized learned distributions: Median, P90, Safe Max)
        ↓
BEHAVIOR DEVIATION ENGINE (Irregular routines, Wandering, Sequence graphs)
        ↓
CONTINUOUS MICROPHONE (VAD Chunker, Whisper Large-v3-Turbo, ResponseAnalyzer)
        ↓
LIVE EVENT CONTRACT (Normalized, idempotent, tamper-evident LiveEvent)
        ↓
LIVE CORE (Single authoritative CoreService)
        ↓
MULTIMODAL RISK ENGINE (14-Signal Composite Evaluator + Context Engine)
        ↓
INCIDENT LIFECYCLE & EMERGENCY WORKFLOW FSM
        ↓
ADAPTERS: Caregiver SMS (TextBEE) | Paramedic CAD Dispatch | Smart Home Lock
        ↓
REALTIME EVENT BUS (SSE & WebSocket Live Dashboard)
```

---

## 📦 Kaggle Fall Detection Dataset & Model Training

The Live vision tracker and fall detector are trained on the Kaggle Fall Detection dataset.

### Dataset Reference & Download via `kagglehub`
To download the latest version of the dataset using `kagglehub`:

```python
import kagglehub

# Download latest version
path = kagglehub.dataset_download("uttejkumarkandagatla/fall-detection-dataset")

print("Path to dataset files:", path)
```

### Dataset Structure
```text
fall_dataset/
├── images/
│   ├── train/    # Training frames
│   └── val/      # Validation frames
└── labels/
    ├── train/    # YOLO format bounding boxes
    └── val/
```

### Classes
- **Class 0**: `Fall Detected`
- **Class 1**: `Walking` (Normal Movement)
- **Class 2**: `Sitting` (Resting / Normal Movement)

### Training Script
Execute training inside `Live/`:
```bash
python Live/train_fall_detector.py
```
This automatically resolves the dataset location (checking local download paths including `archive(13)` and kagglehub cache), generates runtime `fall_dataset.yaml`, trains YOLOv8 on the dataset, and outputs the optimized weights to `Live/nira_fall_model.pt`.

---

## 🏠 Multi-Room Support (5 Standard Rooms)

Each room maintains an independent, concurrent safety state:

| Room ID | Room Name | Risk Tier | Default Priors | Camera ID |
| :--- | :--- | :--- | :--- | :--- |
| `living_room` | Living Room (Main Area) | `REST_ZONE` | Expected: 3600s (60m) | `CAM-01-LIVING` |
| `bathroom` | Primary Bathroom | `CRITICAL_ZONE` | Expected: 600s (10m) | `CAM-02-BATH` |
| `bedroom` | East Wing Bedroom | `SLEEP_ZONE` | Expected: 7200s (120m) | `CAM-03-BED` |
| `kitchen` | Kitchen & Dining | `ACTIVE_ZONE` | Expected: 600s (10m) | `CAM-04-KITCHEN` |
| `hallway` | Central Hallway | `TRANSIT_ZONE` | Expected: 300s (5m) | `CAM-05-HALL` |

### Inter-Room Person Handoff
- When the resident moves `bedroom` $\to$ `hallway` $\to$ `bathroom`, the system recognizes a single continuous resident (`resident_id`).
- When a person disappears from one camera and appears in another within the configurable grace period (`PERSON_LOST_GRACE_SECONDS = 3.0s`), `ROOM_EXIT` and `ROOM_ENTRY` events are generated cleanly without duplicate fall or missing-person alerts.

---

## ⏱️ Separation of Inactivity vs. Zone Dwell Time

A critical safety principle of NIRA Live is maintaining **TWO distinct timers**:

1. **Movement Inactivity Timer**:
   - Measures time without meaningful displacement (centroid or keypoint motion).
   - Stages:
     - `0–5 min`: Normal / Resting
     - `5–8 min`: Low Activity Warning
     - `8–10 min`: Prolonged Low Activity
     - `10 min (600s)`: Inactivity Detected
   - *Override*: Fall + Floor Posture immediately overrides ordinary timers.

2. **Zone Dwell Timer (`ZoneSession`)**:
   - Measures continuous occupancy in a room regardless of whether the resident is moving.
   - Example: Resident enters bathroom and moves continuously for 15 minutes.
     - *Inactivity*: 0 seconds
     - *Dwell*: 15 minutes
     - *State*: `PROLONGED_ZONE_STAY` (Mild/Moderate risk, produces conversational check-in, **not an automatic ambulance dispatch**).

---

## 🎙️ Always-Available Continuous Microphone & Voice Intelligence

1. **Continuous VAD Listening (`Live/voice/continuous_monitor.py`)**:
   - Opens audio input once and listens passively.
   - **Never runs Whisper on silence**: VAD segments genuine speech chunks.
2. **Two Operating Modes**:
   - `PASSIVE_MONITORING`: Always active. If the resident spontaneously says *"Help me"*, Whisper transcribes, `ResponseAnalyzer` classifies `EMERGENCY`, and Core starts the emergency workflow immediately without requiring a camera trigger.
   - `PRIORITY_WELLNESS_CHECK`: System asks *"Eleanor, are you okay?"*. The next speech segment is correlated with the active incident.
3. **Clinical Priority Hierarchy**:
   $$\text{EMERGENCY} > \text{RISK} > \text{UNCERTAIN} > \text{SAFE}$$
   - Strict negation: *"I am not okay"* $\to$ `RISK`.
   - Mixed clauses: *"I'm okay, but I fell and can't get up"* $\to$ `EMERGENCY`.
   - Ambiguity: Never silently `SAFE`.
4. **Severity-Aware Silence Timeout**:
   - High severity (confirmed fall / floor posture) + silence $\to$ Immediate ambulance CAD dispatch.
   - Mild anomaly (15m bathroom stay while moving) + silence $\to$ Alert caregiver, repeat prompt; avoids false emergency dispatches.

---

## 📈 Self-Learning Behavioral Baselines

- **Safe Learning Only**: Only validated safe visits (`SAFE` verbal confirmations or normal exits) update routine baselines.
- **Gradual Bayesian Adaptation**: Safe visits adjust expected duration incrementally via EMA (e.g. 10m $\to$ 10.4m), preventing single long visits from distorting learned norms.
- **Critical Override**: High hazard events (falls, floor collapse, distress voice) strictly override routine baselines.

---

## 🚀 REST API Reference

### Vision Endpoints
- `POST /api/v1/live/vision/cameras/{camera_id}/frame`: Ingest real base64 image frame for YOLO inference.
- `GET  /api/v1/live/vision/rooms`: Get real-time states of all 5 rooms.
- `GET  /api/v1/live/vision/cameras`: Get camera registry status and inference FPS.
- `GET  /api/v1/live/vision/state`: Full vision and resident tracking snapshot.
- `POST /api/v1/live/vision/cameras/{camera_id}/start`: Start specific camera.
- `POST /api/v1/live/vision/cameras/{camera_id}/stop`: Stop specific camera.
- `POST /api/v1/live/vision/monitor/start`: Start multi-room monitoring.
- `POST /api/v1/live/vision/monitor/stop`: Stop monitoring.

### Core Endpoints
- `POST /api/v1/live/core/events`: Normalized safety event ingestion.
- `GET  /api/v1/live/core/state`: Authoritative composite resident safety state.
- `POST /api/v1/live/core/wellness/trigger`: Initiate contextual vocal check-in.
- `POST /api/v1/live/core/wellness/respond`: Process resident vocal response.
- `POST /api/v1/live/core/wellness/timeout`: Process silence timeout with severity-aware policy.
- `GET  /api/v1/live/core/events/stream`: Real-time SSE telemetry stream.

---

## 🧪 Automated Test Verification

Run the comprehensive test suite:
```bash
pytest Live/tests/ -v
```

All 10 required clinical scenarios (Phases 56–65) execute deterministically in seconds using the injectable `TestClock` (`clock.advance(seconds=...)`).

---

## 🔒 Security & Demo Isolation Guarantees

1. **Zero Demo Dependency**: The `Demo/` directory is strictly read-only and unreferenced by Live.
2. **Live-Contained Models**: All model weights resolve strictly within `Live/` (`Live/yolov8n-pose.pt`, `Live/nira_fall_model.pt`).
3. **Environment Security**: Sensitive tokens (MongoDB URI, TextBEE keys) read exclusively from environment variables with safe log masking.
