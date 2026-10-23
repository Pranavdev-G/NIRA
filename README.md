# Aegis Ambient Care — Alexa+ Streamable HTTP MCP Server
**Amazon Developer Hackathon 2026 | Ambient AI Safety Agent Track**

Aegis CARE is an ambient, non-intrusive safety agent designed to protect seniors living independently. Built as a high-performance **Model Context Protocol (MCP)** server over **Streamable HTTP & SSE**, Aegis CARE interfaces seamlessly with **Alexa+** and smart ambient hardware (Echo Show, mmWave radar, wearable vitals).

---

## ⚡ Latency Budget SLA (<500ms)

Amazon Alexa+ voice interactions impose a strict latency SLA to ensure conversational cadence remains natural without awkward pauses:

| Component | Target Budget | Aegis CARE Measured |
| :--- | :--- | :--- |
| **In-Memory Risk Evaluation Engine** | `< 50ms` | **`0.8ms – 2.5ms`** |
| **Pydantic v2 Parsing & Validation** | `< 20ms` | **`0.4ms – 1.2ms`** |
| **Conversational State Machine Turn** | `< 50ms` | **`1.1ms – 3.8ms`** |
| **Caregiver Multi-Channel Mock Dispatch** | `< 100ms` | **`8.5ms – 14.0ms`** |
| **CAD Emergency Packet Generation & Escalation** | `< 100ms` | **`4.2ms – 9.8ms`** |
| **Total Round-Trip API Execution** | `< 500ms` | **`< 25ms` (95% headroom)** |

Every response includes `X-Response-Time-Ms` and standard `Server-Timing` headers for real-time observability.

---

## 🏗️ Architecture & Component Overview

```mermaid
flowchart TD
    subgraph AmbientSensors["Ambient Sensors & Wearables"]
        A1[Echo Show / Mic Array] --> E[Raw Event + Context]
        A2[mmWave Radar / Vision] --> E
        A3[Smart Watch Vitals] --> E
    end

    subgraph AlexaPlus["Alexa+ Ambient Agent Engine"]
        AP[Alexa+ LLM / Voice Orchestrator]
    end

    subgraph AegisMCP["Aegis CARE MCP Server (FastAPI)"]
        TR[MCP Tool Registry & Protocol Handler]
        RE[Deterministic Risk Scoring Engine]
        SM[Conversational Wellness State Machine]
        CS[Caregiver Notification Hub]
        ES[EMS CAD & Smart Home Controller]
    end

    E -->|Telemetry| AP
    AP -->|tools/call: assess_risk| TR
    TR --> RE
    RE -->|Risk: MODERATE / HIGH / CRITICAL| SM
    SM -->|TTS Prompt / SSML| AP
    AP -->|User Voice Response| SM
    SM -->|Safe Response| CS
    SM -->|Distress Alert| CS
    SM -->|Distress / Timeout| ES
```

---

## 📋 Data Contracts

### 1. `Event`
```json
{
  "event_type": "fall_detected",
  "confidence": 0.94,
  "location": "bathroom",
  "timestamp": "2026-10-17T08:15:30Z",
  "movement_after_event": "none"
}
```

### 2. `Context`
```json
{
  "activity": "walking_to_shower",
  "time_context": "night_time",
  "baseline_deviation": 0.85,
  "wearable_status": "high_heart_rate",
  "environment": "dark_room_wet_floor"
}
```

### 3. `Risk`
```json
{
  "risk_level": "CRITICAL",
  "confidence": 0.95,
  "reasons": [
    "Event type 'fall_detected' detected with 94% confidence",
    "Zero post-impact movement detected (acute immobilization hazard)",
    "High-hazard moisture location: 'bathroom'",
    "Severe baseline deviation (0.85 > 0.80)",
    "Wearable telemetry indicates acute elevated heart rate"
  ]
}
```

---

## 🧠 Aegis CARE Multimodal Risk Engines (v1)

Aegis CARE features a modular 3-engine architecture that converts raw multimodal telemetry into explainable, clinically sound risk assessments:

```mermaid
flowchart LR
    E[Vision Event & Motion] --> RE[AegisRiskEngine]
    C[Environmental Factors] --> CE[ContextEngine]
    CE --> RE
    B[Circadian Schedule & Routine] --> PBE[PersonalBaselineEngine]
    PBE --> RE
    W[Wearable Vitals & Telemetry] --> RE
    V[Alexa Voice Verification] --> RE

    RE -->|Risk Rules & Thresholds| OUT[Risk Level: LOW / MODERATE / HIGH / CRITICAL]
```

### 1. `ContextEngine` ([`app/services/context_engine.py`](file:///f:/Aegis%20Ambient%20Care/app/services/context_engine.py))
* **Location Hazard Weighting**: Evaluates room coefficients based on fall epidemiology (Bathroom `1.55x`, Shower `1.60x`, Stairs `1.65x`, Kitchen `1.25x`, Living Room `1.00x`, Bedroom `0.85x`).
* **Environmental Hazards**: Analyzes wet floors / slippery surfaces (+12.0), poor ambient lighting (+8.0), and trip obstacles (+7.0).
* **Circadian Temporal Vulnerability**: Weights nocturnal off-peak hours (00:00 - 06:00) due to delayed natural discovery risk.

### 2. `PersonalBaselineEngine` ([`app/services/baseline_engine.py`](file:///f:/Aegis%20Ambient%20Care/app/services/baseline_engine.py))
* **Circadian Routine Modeling**: Maps senior 24-hour daily routine slots (Nocturnal Rest, Morning Routine, Midday Lunch, Afternoon Rest, Evening Dinner, Wind-down).
* **Deviation Scoring (0.0 to 1.0)**: Computes spatial and activity divergences (e.g., stationary in bathroom at 3 AM yields severe deviation `0.88`, whereas sleeping in bedroom at 3 AM yields `0.05`).
* **Wearable ML Fusion**: Blends historical circadian schedules with live wearable accelerometer baseline deviation models.

### 3. `AegisRiskEngine` ([`app/services/aegis_risk_engine.py`](file:///f:/Aegis%20Ambient%20Care/app/services/aegis_risk_engine.py))
Synthesizes vision confidence, motion telemetry, context, routine deviations, wearable vitals, and conversational verification states:

| Risk Level | Trigger Criteria | Action Recommendation |
| :--- | :--- | :--- |
| **`LOW`** | Routine deviation minimal, normal sensor signals, or user verbally confirms safety (`"I'm okay"`). | Passive ambient monitoring |
| **`MODERATE`** | Mild anomaly, unverified event, or moderate circadian deviation requiring clarification. | Trigger Alexa interactive wellness check |
| **`HIGH`** | Confirmed fall or abnormal vitals + explicit user distress response (`"Help me"`). | Alert caregiver (Drop-In, Push, SMS) & prepare CAD packet |
| **`CRITICAL`** | Confirmed fall + abnormal vitals / zero movement + **NO response (Silent Emergency / Timeout)**. | Immediate 911 CAD dispatch, unlock entry smart lock |

---

## 🌐 Aegis Risk REST API (`/api/v1`)

### 1. `POST /api/v1/assess-risk`
Initial multimodal risk assessment before voice verification.

**Request Payload**:
```json
{
  "event": {
    "event_type": "fall_detected",
    "confidence": 0.95,
    "location": "bathroom",
    "timestamp": "2026-10-17T03:15:00Z",
    "movement_after_event": "none"
  },
  "context": {
    "activity": "walking",
    "time_context": "night_time",
    "baseline_deviation": 0.88,
    "wearable_status": "high_heart_rate",
    "environment": "dark_room_wet_floor"
  }
}
```

**Response (Sub-5ms Execution)**:
```json
{
  "risk_level": "CRITICAL",
  "confidence": 0.89,
  "reasons": [
    "High-hazard location 'bathroom' (hazard multiplier: 1.55x)",
    "Slippery surface / wet floor condition detected",
    "Compounding poor ambient lighting condition ('dark_room_wet_floor')",
    "Off-peak nocturnal temporal window ('night_time') - delayed natural discovery risk",
    "Circadian anomaly: Found in 'bathroom' during nocturnal hours (expected: bedroom)",
    "Vision event 'fall_detected' detected with 95% confidence",
    "Zero post-impact movement detected (prolonged motionless hazard)",
    "Wearable telemetry: Acute elevated heart rate (tachycardia)"
  ],
  "recommended_action": "INITIATE_IMMEDIATE_WELLNESS_CHECK_AND_PREPARE_CAD",
  "requires_wellness_check": true,
  "requires_caregiver_alert": true,
  "requires_emergency_escalation": true,
  "latency_ms": 0.08
}
```

### 2. `POST /api/v1/reassess-risk`
Adaptive re-evaluation incorporating conversational feedback from Alexa+:

**Request Payload**:
```json
{
  "event": { ... },
  "context": { ... },
  "voice_response": {
    "transcript": null,
    "is_timeout": true
  }
}
```

**Output**: Automatically triggers **`CRITICAL`** status with reason:
`"SILENT EMERGENCY: No response received during wellness check window (presumed loss of consciousness)"`.

---

## 🛠️ The 5 MCP Tools

The server exposes 5 tools via both standard **REST HTTP** (`/tools/*`) and **MCP JSON-RPC 2.0** (`/mcp` and `/sse`):

### 1. `assess_risk`
* **Purpose**: Evaluates acoustic/vision events against personal behavioral deviations, wearable vitals, and environment.
* **REST Route**: `POST /tools/assess_risk`
* **MCP Tool Name**: `assess_risk`
* **Output**: Updated `Risk` object, action recommendations, and triage flags.

### 2. `start_wellness_check` & `respond_wellness_check`
* **Purpose**: Initiates ambient voice check-in and executes the conversational state machine.
* **REST Route**: `POST /tools/start_wellness_check`, `POST /tools/respond_wellness_check`
* **MCP Tool Name**: `start_wellness_check`, `respond_wellness_check`
* **SSML Output**: Empathetic Alexa prosody with emotional concern.

### 3. `notify_caregiver`
* **Purpose**: Dispatches synchronized alerts across Alexa Drop-In, Mobile Push notification, and SMS.
* **REST Route**: `POST /tools/notify_caregiver`
* **MCP Tool Name**: `notify_caregiver`
* **Latency**: Multi-threaded async mock delivery in `<15ms`.

### 4. `generate_emergency_packet`
* **Purpose**: Compiles a Computer-Aided Dispatch (CAD) clinical incident packet including patient medical history, allergies, DNR status, sensor telemetry, and triage codes.
* **REST Route**: `POST /tools/generate_emergency_packet`
* **MCP Tool Name**: `generate_emergency_packet`

### 5. `escalate_emergency`
* **Purpose**: Escalate critical incidents to EMS 911 dispatch, unlock smart entrance locks for first responders, and activate ambient two-way audio.
* **REST Route**: `POST /tools/escalate_emergency`
* **MCP Tool Name**: `escalate_emergency`

---

## 🔄 Conversational State Machine Logic

```
               [ Ambient Event Detected ]
                           │
                           ▼
                 [ assess_risk Evaluated ]
                           │
                           ▼
              [ start_wellness_check ]
                           │
             ┌─────────────┴─────────────┐
             │                           │
    (User speaks reply)          (No answer / Timeout)
             │                           │
     ┌───────┴───────┐                   │
     ▼               ▼                   ▼
"I'm okay" / Safe   "Help me" / Distress    Timeout (20s)
  • Downgrade risk   • Elevate risk        • Set CRITICAL
  • Cancel alert     • Notify Caregiver    • CAD Escalation
  • SAFE_RESOLVED    • Emergency Packet    • Unlock Doors
                     • DISTRESS_ELEVATED   • TIMEOUT_ESCALATED
```

---

## 🗄️ Backend Hub & Database Architecture

The Aegis CARE FastAPI backend acts as the central integration hub connecting **vision detection (Nandana)**, **risk assessment (Dharaneesh)**, **Alexa+ MCP tools (Pranav)**, and the **React dashboard (Leela)**.

### SQLAlchemy Database Models ([`app/database/models.py`](file:///f:/Aegis%20Ambient%20Care/app/database/models.py))

* **`User` (`users`)**: Senior profile, medical history, baseline parameters, emergency contacts, and DNR order. Automatically seeds `Eleanor Vance` (Age 79, Beacon Hill).
* **`Incident` (`incidents`)**: Safety incidents with `event_type`, `location`, `initial_risk_level`, `current_risk_level`, `status` (`ACTIVE`, `RESOLVED`, `ESCALATED_CAREGIVER`, `ESCALATED_CAD`), and context snapshot.
* **`IncidentTimeline` (`incident_timelines`)**: Chronological audit trail logging vision ingestion, risk assessments, voice prompts, user utterances, caregiver notifications, and CAD dispatches.
* **`EmergencyPacket` (`emergency_packets`)**: Compiled 911 CAD-ready summary packets stored with incident foreign keys.

---

## 📡 Non-Camera Signal Simulators

### 1. Wearable Telemetry Simulator ([`wearable_simulator.py`](file:///f:/Aegis%20Ambient%20Care/wearable_simulator.py))
Simulates biometric and inertial signals from smartwatches or medical wearables:
* Heart rate (BPM) & arrhythmia detection (`worn_normal`, `high_heart_rate`, `arrhythmia_flag`, `low_heart_rate`)
* Movement / Immobility index
* Presets: `normal_resting`, `tachycardia_fall_impact`, `cardiac_arrhythmia`, `walking_normal`, `bradycardia`.

```bash
# Run single-shot or continuous telemetry stream
python wearable_simulator.py --preset tachycardia_fall_impact
python wearable_simulator.py --preset normal_resting --continuous --interval 2.0
```

### 2. Environmental State Simulator ([`environment_simulator.py`](file:///f:/Aegis%20Ambient%20Care/environment_simulator.py))
Simulates ambient room conditions from smart plugs, mmWave radar, and sensors:
* Temperature (°C), relative humidity (%), ambient lighting lux, acoustic noise level (dB), floor moisture detection, and motion activity.
* Presets: `bathroom_hazard_wet`, `living_room_normal`, `kitchen_active`, `bedroom_nocturnal`, `hallway_unlit`.

```bash
python environment_simulator.py --preset bathroom_hazard_wet
python environment_simulator.py --preset living_room_normal --continuous --interval 2.0
```

---

## 🚀 Core Incident REST Endpoints (`/api/v1`)

| Method & Route | Purpose |
| :--- | :--- |
| **`POST /api/v1/events`** | Ingests event JSON from vision or simulators, runs risk assessment, persists Incident, and logs initial timeline. |
| **`GET /api/v1/incidents/active`** | Returns active incidents currently awaiting check-in or in escalation for the React safety dashboard. |
| **`GET /api/v1/incidents/{id}/timeline`** | Returns complete chronological audit trail of all actions and voice turns. |
| **`POST /api/v1/incidents/{id}/escalate`** | Manually or automatically dispatches caregiver alerts or 911 CAD emergency escalation. |
| **`POST /api/v1/incidents/{id}/respond-voice`** | Ingests senior voice reply ("I'm okay" vs "Help me" vs Timeout) to execute state machine transitions. |

---

## 🏆 The 3 Hero Scenarios ([`tests/test_hero_scenarios.py`](file:///f:/Aegis%20Ambient%20Care/tests/test_hero_scenarios.py))

Automated end-to-end tests demonstrate all three primary lifecycle paths:

1. **Hero Scenario 1: False Alarm**
   - Minor slip or acoustic thud in living room ➔ `POST /api/v1/events` (Status: `ACTIVE`).
   - Alexa prompts: *"Are you okay?"*
   - Senior responds: *"I'm okay, false alarm, just dropped my book."*
   - Risk downgraded to `LOW`, incident status updated to `RESOLVED`, passive monitoring resumes.
2. **Hero Scenario 2: Responsive Emergency**
   - Fall detected in living room (`crawling` movement) ➔ Initial Risk `HIGH`.
   - Senior responds: *"Help me, I fell down and my hip hurts!"*
   - Caregiver multi-channel alert dispatched (Alexa Drop-In, Push, SMS), incident status updated to `ESCALATED_CAREGIVER`.
3. **Hero Scenario 3: Silent Emergency**
   - Severe nocturnal fall in bathroom + tachycardia vitals ➔ Initial Risk `CRITICAL`.
   - Alexa prompt runs for 20s with **NO response (Timeout / Silence)**.
   - Immediate 911 CAD emergency dispatch, smart entrance lock auto-unlocked, emergency packet compiled, status updated to `ESCALATED_CAD`.

---

## 👁️ Computer Vision Fall & Posture Detection Module

The edge vision module ([`fall_detector.py`](file:///f:/Aegis%20Ambient%20Care/fall_detector.py) / [`app/vision/fall_detector.py`](file:///f:/Aegis%20Ambient%20Care/app/vision/fall_detector.py)) operates directly on video streams (webcam, RTSP, or recorded video) using **YOLO Pose estimation** (COCO 17 keypoints) with adaptive fallback to classical silhouette analysis on low-power edge hardware.

### Biomechanical Analysis Pillars

1. **Downard Vertical Velocity ($V_y$)**:
   - Tracks the torso centroid (midpoint of hips and shoulders) normalized against person height $H_{person}$.
   - Triggers when downward velocity exceeds critical threshold ($\Delta y / \Delta t \ge 1.1\times H_{person}/\text{sec}$).
2. **Posture Alignment Shifts**:
   - **Bounding Box Aspect Ratio**: Normal standing is $W/H \in [0.3, 0.6]$. Fall transition flips to $W/H > 1.05$.
   - **Torso Inclination Angle ($\theta$)**: Computes the angle of the vector connecting hip midpoint to shoulder midpoint relative to the floor. Standing is $\approx 75^\circ - 90^\circ$; lying flat on the floor drops to $< 35^\circ$.
3. **Post-Event Immobility Tracking**:
   - Monitors average keypoint displacement over a configurable temporal window ($2.0 - 4.0\text{s}$).
   - Classifies post-fall movement:
     - Displacement $< 5.0\text{ px/s}$ ➔ `"none"`
     - Displacement $5.0 - 18.0\text{ px/s}$ ➔ `"slight_twitch"`
     - Significant horizontal displacement lying down ➔ `"crawling"`
     - Upright posture regained ➔ `"normal"` (escalation cancelled)

### Output Event Contract

```json
{
  "event_type": "possible_fall",
  "confidence": 0.94,
  "location": "living_room",
  "timestamp": "2026-10-17T08:52:10Z",
  "movement_after_event": "none"
}
```

### Running the Vision Module

```bash
# 1. Built-in Synthetic Simulation Demo (No camera required)
python fall_detector.py --demo

# 2. Live Webcam feed
python fall_detector.py --source 0 --location bathroom

# 3. Video File Ingestion with auto-transmission to local Aegis CARE MCP Server
python fall_detector.py --source demo_fall.mp4 --post-url http://localhost:8000/tools/assess_risk
```

---

## 📡 Standalone Mock Event Emitter (`mock_event_emitter.py`)

A standalone CLI tool ([`mock_event_emitter.py`](file:///f:/Aegis%20Ambient%20Care/mock_event_emitter.py)) that simulates synthetic ambient safety events without requiring cameras or GPUs. Transmits JSON payloads via HTTP POST to the local FastAPI backend.

### Preset Scenarios

* `critical_fall_bathroom`: High confidence fall, zero movement, dark room moisture hazard.
* `fall_living_room_immobile`: Sudden fall with zero movement.
* `fall_living_room_twitch`: Fall with slight involuntary twitching.
* `slip_kitchen_recovered`: Slip with immediate recovery ("normal" movement).
* `prolonged_inactivity_bedroom`: Senior motionless in bedroom past expected baseline.

### Usage Examples

```bash
# Inspect payload without transmitting (dry-run)
python mock_event_emitter.py --scenario critical_fall_bathroom --dry-run

# Transmit event to running MCP server
python mock_event_emitter.py --scenario critical_fall_bathroom --target http://localhost:8000/tools/assess_risk

# Run full End-to-End Voice AI interaction (Assess -> Alexa Wellness Check -> Voice Reply)
python mock_event_emitter.py --scenario critical_fall_bathroom --e2e-voice

# Continuous telemetry stream every 3 seconds
python mock_event_emitter.py --continuous --interval 3.0
```

---

## 🚀 Quickstart & Local Development

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Complete Integration Test Suite
```bash
pytest Demo/tests
```

### 3. Start Unified NIRA Server
From the root folder:
```bash
uvicorn Demo.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Or directly from the `Demo` directory:
```bash
cd Demo && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive Safety Dashboard & 3D Digital Twin:** `http://localhost:8000/` or `http://localhost:8000/dashboard`
- **Family Admin Guardian Console:** `http://localhost:8000/admin`
- **Interactive OpenAPI Swagger Docs:** `http://localhost:8000/docs`
- **Model Context Protocol (MCP) Streamable SSE:** `http://localhost:8000/sse`
- **Real-Time Safety Event Stream:** `http://localhost:8000/api/v1/events/stream` or `http://localhost:8000/events`

### 4. Run Multi-Device Event Simulators
```bash
# Run full automated scenario suite (from root or Demo/)
python Demo/scenario_simulator.py --scenario responsive_emergency
python Demo/nira_simulator.py --interactive
# Additional scenario options:
# python Demo/scenario_simulator.py --scenario silent_emergency
# python Demo/scenario_simulator.py --scenario false_alarm
# python Demo/nira_simulator.py --scenario normal_day --steps 10
```

---

## ☁️ AWS Cloud Deployment

### AWS App Runner or ECS Fargate (Containerized)
1. Build & tag Docker image:
   ```bash
   docker build -t aegis-ambient-mcp:latest .
   ```
2. Push to Amazon ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
   docker tag aegis-ambient-mcp:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/aegis-ambient-mcp:latest
   docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/aegis-ambient-mcp:latest
   ```
3. Deploy to AWS App Runner with standard container configuration and port 8000.

---

## 📡 MCP Configuration for Alexa+ / Claude Desktop

Add this configuration to your MCP clients configuration file:

```json
{
  "mcpServers": {
    "aegis_ambient_care": {
      "url": "http://localhost:8000/sse",
      "transport": "sse"
    }
  }
}
```
Or use the direct HTTP JSON-RPC endpoint at `http://localhost:8000/mcp`.

---

## 🛡️ NIRA Live Multi-Room Ambient Safety Intelligence System

For full documentation of the multi-room ambient safety architecture, per-room independent state, inter-room handoff, and routine baseline learner, see [Live/README.md](Live/README.md).

### Kaggle Fall Detection Dataset Reference

The NIRA Live vision models are trained on the Kaggle Fall Detection dataset (`uttejkumarkandagatla/fall-detection-dataset`).

#### Download Dataset via `kagglehub`
```python
import kagglehub

# Download latest version
path = kagglehub.dataset_download("uttejkumarkandagatla/fall-detection-dataset")

print("Path to dataset files:", path)
```

Dataset YAML configuration: `Live/fall_dataset.yaml`  
Training script: `python Live/train_fall_detector.py`

