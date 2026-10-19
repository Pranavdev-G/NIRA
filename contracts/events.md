# NIRA Multimodal Event Contract
**Standard:** NIRA Event Specification v2.0  
**Status:** Authoritative Contract  
**Protocol:** REST Ingestion (`/api/v1/events/ingest`, `/api/v1/events/batch`, `/api/v1/events`) & Real-Time Stream (`/api/v1/events/stream`, `/events`, `/sse`, `/api/v1/events/ws`)

---

## 1. Unified Event Envelope

Every event ingested into NIRA MUST conform to this schema:

```json
{
  "event_id": "evt-20261020-001a2b",
  "timestamp": "2026-10-20T00:54:12.345Z",
  "resident_id": "user_eleanor_vance",
  "room_id": "bathroom",
  "source": "wearable",
  "event_type": "heart_rate",
  "payload": {
    "heart_rate": 118,
    "battery_pct": 92,
    "charging": false
  },
  "confidence": 0.96,
  "correlation_id": "corr-8f12a34b"
}
```

### Required Fields

| Field | Type | Description |
|---|---|---|
| `event_id` | String | Globally unique event identifier (e.g. `evt-UUID` or `evt-TIMESTAMP-HEX`). |
| `timestamp` | String (ISO 8601) | UTC timestamp with timezone offset (`YYYY-MM-DDTHH:MM:SS.sssZ`). |
| `resident_id` | String | Identifier of resident (default: `user_eleanor_vance`). |
| `room_id` | String | Spatial location tag (`bedroom`, `bathroom`, `living`, `kitchen`, `hallway`, `outdoor`). |
| `source` | String | Subsystem emitting the event: `wearable`, `radar_mmwave`, `camera_pose`, `environmental`, `voice_dialog`, `state_machine`, `simulator`. |
| `event_type` | String | Sensor-specific event type. |
| `payload` | Object | Arbitrary strongly typed key-value payload containing sensor metrics. |
| `confidence` | Float (0.0 to 1.0) | Sensor measurement confidence score. |
| `correlation_id` | String | Distributed correlation ID linking multi-sensor events belonging to the same observation or incident. |

---

## 2. Supported Event Types by Source

### A. Wearable (`source: "wearable"`)
- `heart_rate`: payload `{ "heart_rate": int, "hrv": float, "battery_pct": int }`
- `motion`: payload `{ "steps_last_minute": int, "step_cadence": float, "acceleration_g": float }`
- `immobility`: payload `{ "duration_seconds": int, "posture": "lying"|"sitting"|"standing" }`
- `device_connectivity`: payload `{ "connected": bool, "ble_rssi": int, "packet_loss": float }`

### B. 60GHz mmWave Radar (`source: "radar_mmwave"`)
- `room_occupancy`: payload `{ "detected": bool, "count": int, "doppler_motion": float }`
- `radar_presence`: payload `{ "distance_m": float, "azimuth_deg": float, "respiration_rate": float }`
- `posture_change`: payload `{ "posture": "lying"|"sitting"|"standing", "height_m": float, "rapid_descent": bool }`

### C. Vision & Pose Estimation (`source: "camera_pose"`)
- `possible_fall`: payload `{ "confidence": float, "movement_after_event": "none"|"slow"|"normal", "bbox": [...] }`
- `dropped_object_reach`: payload `{ "confidence": float, "reach_duration_seconds": float }`
- `pose_abnormality`: payload `{ "keypoints": {...}, "torso_angle_deg": float }`

### D. Environmental (`source: "environmental"`)
- `temperature`: payload `{ "temp_c": float, "humidity_pct": float }`
- `ambient_light`: payload `{ "lux": float, "dark_hazard": bool }`
- `floor_wetness`: payload `{ "resistance_ohms": int, "liquid_detected": bool }`

### E. Voice Agent & Wellness (`source: "voice_dialog"`)
- `wellness_timeout`: payload `{ "prompt_window_seconds": 20, "is_timeout": true }`
- `voice_response`: payload `{ "transcript": string, "intent": "safe"|"distress"|"immobile"|"ambiguous" }`

### F. State Machine & Incident (`source: "state_machine"`)
- `state_transition`: payload `{ "previous_state": string, "new_state": string, "reason": string }`
- `risk_assessment`: payload `{ "risk_level": "LOW"|"MODERATE"|"HIGH"|"CRITICAL", "score": float }`

---

## 3. Ingestion HTTP APIs

### Ingest Single Event
`POST /api/v1/events/ingest`
- Returns: `200 OK` with `EventIngestResult`:
```json
{
  "status": "ACCEPTED",
  "event_id": "evt-20261020-001a2b",
  "correlation_id": "corr-8f12a34b",
  "timestamp": "2026-10-20T00:54:12.345Z",
  "safety_state": "NORMAL",
  "is_duplicate": false
}
```

### Ingest Batch Events
`POST /api/v1/events/batch`
- Accepts `List[UnifiedEvent]`
- Returns: `200 OK` with `List[EventIngestResult]`

### Ingest Scenario Event (Frontend Dispatch)
`POST /api/v1/events`
- Accepts: `{"event": {...}, "context": {...}, "user_id": "..."}`
- Evaluates risk with `AegisRiskEngine`, generates `Incident`, records `IncidentTimeline`, and returns:
```json
{
  "incident_id": "INC-20261020-A1B2C3",
  "status": "ACTIVE",
  "location": "bathroom",
  "risk_assessment": {
    "risk_level": "CRITICAL",
    "score": 0.94,
    "confidence": 0.95,
    "reasons": ["High fall probability", "Bathroom hazard", "Immobility"],
    "requires_wellness_check": true,
    "recommended_action": "IMMEDIATE_CAD_EMERGENCY_DISPATCH"
  }
}
```
