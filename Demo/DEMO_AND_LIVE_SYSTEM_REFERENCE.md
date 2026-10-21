# NIRA System Architecture & Reference: Demo vs Live Folders

Amazon Developer Hackathon 2026

---

## 1. Directory Structure

```
NIRA/
├── demo/                                # DEMO & SIMULATION SYSTEMS
│   ├── __init__.py                     # Exports all simulators and scenario orchestrators
│   ├── nira_simulator.py               # Master CLI interactive scenario runner & multi-device generator
│   ├── scenario_simulator.py           # Multi-device timeline scenario generator (Scenarios A - F & 24h routine)
│   ├── wearable_simulator.py           # Apple Watch biometrics & IMU fall telemetry generator
│   ├── radar_simulator.py              # 60GHz mmWave radar micro-motion, macro-motion, and posture classifier
│   ├── vision_simulator.py             # Optical skeleton pose estimation simulator
│   ├── voice_simulator.py              # Alexa Echo Show 15 two-way dialog & timeout simulator
│   ├── environment_simulator.py        # Ambient room temperature, lux, and water leak simulator
│   ├── fall_detector.py                # Pose angles & rapid drop velocity detection logic
│   └── mock_event_emitter.py           # Fast mock event dispatcher for synthetic test runs
│
├── live/                                # LIVE MODEL & PHYSICAL HARDWARE INGESTION
│   ├── __init__.py                     # Exports LiveVisionTracker and LiveIngestStream
│   ├── live_vision_tracker.py          # Real-time webcam YOLOv8-pose skeleton tracker & fall evaluator
│   └── live_ingest_stream.py           # Real-time HTTP ingestion stream for live IoT/edge physical hardware
│
├── app/                                 # AUTHORITATIVE BACKEND & FRONTEND SERVER
│   ├── main.py                         # FastAPI master entry point
│   ├── routers/
│   │   ├── demo_api.py                 # REST API for demo launch & scenario invocation from demo/
│   │   ├── events_api.py               # Multimodal event ingestion & SSE state streams
│   │   ├── incidents_api.py            # Incident lifecycle, CAD packet, escalation, and verification
│   │   ├── risk_api.py                 # Multi-layered risk assessment engine endpoints
│   │   ├── mcp_server.py               # Model Context Protocol (MCP) Streamable HTTP & SSE endpoints
│   │   └── tools_http.py               # Direct tool execution endpoints for Alexa+
│   ├── static/                         # High-fidelity Tesla/Apple-grade frontend dashboard
│   │   ├── index.html                  # Landing gateway (Apex: NIRA, Base: DEMO & LIVE MODEL)
│   │   ├── dashboard.js                # Frontend controllers & state-machine sync
│   │   ├── dashboard.css               # Styling, dark mode, animations
│   │   └── ...
│   └── ...
```

---

## 2. Demo System Reference (`demo/`)

All simulators communicate strictly via HTTP POST endpoints (`/api/v1/events/ingest`, `/api/v1/incidents/...`), never directly modifying database state.

| File | Purpose | Key Classes / Functions |
|---|---|---|
| `demo/nira_simulator.py` | Master CLI interface | `run_interactive(base_url, resident_id)`, `main()` |
| `demo/scenario_simulator.py` | Multi-device scenarios | `ScenarioSimulator`, `run_normal_day()`, `run_scenario_a_false_alarm()`, `run_scenario_b_responsive_emergency()`, `run_scenario_c_silent_emergency()`, `run_scenario_d_recovery()`, `run_scenario_e_sensor_dropout()`, `run_scenario_f_environmental_hazard()` |
| `demo/wearable_simulator.py` | Smartwatch biometrics | `WearableSimulator.emit_event(preset, room_id)` |
| `demo/radar_simulator.py` | mmWave 60GHz radar | `RadarSimulator.emit_event(preset, room_id)` |
| `demo/vision_simulator.py` | Edge camera skeleton | `VisionSimulator.emit_event(preset, room_id)` |
| `demo/voice_simulator.py` | Alexa Echo Show 15 | `VoiceSimulator.emit_verification_reply(scenario)` |
| `demo/environment_simulator.py`| Environmental sensors | `EnvironmentSimulator.emit_event(preset, room_override)` |
| `demo/fall_detector.py` | Kinematic fall analysis | `FallDetector.evaluate_frame(keypoints)` |
| `demo/mock_event_emitter.py` | Rapid batch test events | `MockEventEmitter.dispatch_event(...)` |

### Running the Demo System via CLI:
```bash
# Run interactive multi-device simulator menu
python demo/nira_simulator.py --interactive

# Run specific scenario
python demo/scenario_simulator.py --scenario silent_emergency
```

---

## 3. Live System Reference (`live/`)

Interfaces physical sensors and webcams directly with the live model pipeline:

| File | Purpose | Key Classes / Functions |
|---|---|---|
| `live/live_vision_tracker.py` | Live webcam YOLOv8 pose detector | `LiveVisionTracker.initialize_model()`, `LiveVisionTracker.process_live_frame()`, `LiveVisionTracker.dispatch_live_fall_alert()` |
| `live/live_ingest_stream.py` | Real-time physical device streamer | `LiveIngestStream.ingest_live_sensor(device_type, data)` |

---

## 4. Web Gateway Integration

- **Clicking `[ DEMO ]`**:
  - Immediately transitions to Demo mode workspace (`#sectionDemoMode`).
  - Calls `POST /api/v1/demo/launch` to connect the demo backend.
  - Test scenario pills dispatch to `/api/v1/demo/scenario/{scenario_name}`.
  - Updates URL hash to `#demo` (refreshing maintains demo mode).
- **Clicking `[ LIVE MODEL ]`**:
  - Immediately transitions to Live Model workspace (`#sectionLiveMode`).
  - Engages live camera and microphone ingestion feeds.
  - Updates URL hash to `#live`.
