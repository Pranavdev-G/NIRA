# NIRA Real-Time Streaming & WebSocket Specification
**Version:** 2.0  
**Transports:** Server-Sent Events (SSE) & WebSocket (WS)  
**Primary Endpoint (SSE):** `GET /api/v1/events/stream` or `GET /events` or `GET /sse`  
**Optional Endpoint (WS):** `WS /api/v1/events/ws`  

---

## 1. Connection Lifecycle & Protocols

### A. Server-Sent Events (SSE)
- Headers:
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
- Initial Event on Connection:
  - Event type: `state_snapshot` (or `endpoint` for MCP clients)
  - Data: Initial authoritative snapshot of the resident and residence state.
- Ongoing Events:
  - Event type: `state_update` (when risk or state transitions occur) or `event_ingested` (for telemetry pulses)
- Keepalive Ping:
  - Comments `: keepalive-ping\n\n` or `: ping\n\n` transmitted every 15 seconds to prevent gateway timeouts.

### B. WebSocket (Full-Duplex)
- Upon handshake completion, sends:
  ```json
  {
    "type": "INITIAL_SNAPSHOT",
    "snapshot": { ... },
    "timestamp": "2026-10-20T00:54:12Z"
  }
  ```
- Receives real-time telemetry pulses and state transition messages matching the JSON envelope.
- Heartbeat: Pings sent every 20 seconds.

---

## 2. Event Payload Schema

```json
{
  "type": "state_update",
  "state_changed": true,
  "state": {
    "resident_id": "user_eleanor_vance",
    "safety_state": "WAITING_FOR_RESPONSE",
    "current_room": "bathroom",
    "heart_rate": 118,
    "last_movement_at": "2026-10-20T00:54:12Z",
    "device_connected": true,
    "active_incident_id": "INC-20261020-001A2B",
    "current_risk_level": "CRITICAL",
    "environmental_risk": "HAZARD"
  },
  "event": {
    "event_id": "evt-20261020-001A2B",
    "source": "camera_pose",
    "event_type": "possible_fall",
    "confidence": 0.94,
    "room_id": "bathroom",
    "payload": {
      "movement_after_event": "none"
    }
  },
  "timestamp": "2026-10-20T00:54:12.450Z"
}
```

---

## 3. Frontend Reconnection Protocol

Clients (`NiraStateStore` in `nira_store.js`) implement safe exponential backoff reconnection:
- Retry delays: `1s -> 2s -> 4s -> 8s -> 16s -> 30s max`
- Maximum retry attempts: 10
- Disconnection UI states:
  - `CONNECTING`: Pulse indicator
  - `CONNECTED`: Green active badge, latency telemetry < 50ms
  - `DISCONNECTED`: Red warning banner (`STREAM DISCONNECTED`) with manual retry button
  - `RECONNECTING`: Amber reconnection attempt indicator
  - `STALE`: Displayed when last telemetry timestamp > 60 seconds
