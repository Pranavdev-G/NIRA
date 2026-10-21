# NIRA Authoritative API Specification
**Version:** 2.0  
**Base URL:** `http://localhost:8000`  
**Authentication:** Bearer token / local session (default bypass for hackathon dev environment)  
**SLA Budget:** Voice and critical safety routes sub-500ms; health route sub-50ms  

---

## 1. System Health & Protocol Endpoints

### `GET /health`
Returns health check status and timestamp.
- **Response `200 OK`:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-10-20T00:54:12Z",
    "database": "connected",
    "version": "2.0.0"
  }
  ```

### `GET /api/info`
Service metadata, version, and endpoints overview.

---

## 2. Event Pipeline Endpoints

### `POST /api/v1/events/ingest`
Ingests a single `UnifiedEvent`.
- **Request:** See `contracts/events.md`.
- **Response `200 OK`:** `EventIngestResult`

### `POST /api/v1/events/batch`
Batch ingestion of multiple `UnifiedEvent` records in chronological order.
- **Request:** `[ { ... }, { ... } ]`
- **Response `200 OK`:** `[ EventIngestResult, ... ]`

### `GET /api/v1/resident/state` & `GET /api/v1/events/state`
Fetches current authoritative resident snapshot:
- **Response `200 OK`:**
  ```json
  {
    "resident_id": "user_eleanor_vance",
    "safety_state": "NORMAL",
    "current_room": "living",
    "heart_rate": 74,
    "last_movement_at": "2026-10-20T00:54:10Z",
    "device_connected": true,
    "active_incident_id": null,
    "current_risk_level": "LOW",
    "environmental_risk": "SAFE",
    "updated_at": "2026-10-20T00:54:12Z"
  }
  ```

### `GET /api/v1/events/history`
Query paginated historical telemetry events.
- **Query Params:** `limit` (default 50), `source` (optional), `resident_id` (optional).
- **Response `200 OK`:** Array of historical telemetry records.

### `POST /api/v1/events/reset`
Administrative reset hook restoring resident state back to `NORMAL` baseline.
- **Response `200 OK`:** `{"status": "SUCCESS", "message": "NIRA resident state reset to NORMAL baseline."}`

### `POST /api/v1/events/recover`
Administrative restart recovery hook rehydrating active incident state from database.
- **Response `200 OK`:** Recovery metadata and current state.

---

## 3. Incident Lifecycle & Emergency Orchestration Endpoints

### `POST /api/v1/events`
Scenario button / detector event dispatch.
- **Request:**
  ```json
  {
    "event": {
      "event_type": "possible_fall",
      "confidence": 0.94,
      "location": "bathroom",
      "movement_after_event": "none",
      "timestamp": "2026-10-20T00:54:12Z"
    },
    "context": {
      "activity": "sleeping",
      "time_context": "night",
      "baseline_deviation": 0.92,
      "wearable_status": "worn_normal",
      "environment": "dark_hazard"
    },
    "user_id": "user_eleanor_vance"
  }
  ```
- **Response `201 CREATED`:**
  ```json
  {
    "incident_id": "INC-20261020-001A2B",
    "user_id": "user_eleanor_vance",
    "location": "bathroom",
    "status": "ACTIVE",
    "workflow_state": "WAITING_FOR_RESPONSE",
    "created_at": "2026-10-20T00:54:12Z",
    "risk_assessment": {
      "risk_level": "CRITICAL",
      "score": 0.94,
      "confidence": 0.95,
      "reasons": ["High fall probability", "Bathroom hazard"],
      "requires_wellness_check": true,
      "recommended_action": "IMMEDIATE_CAD_EMERGENCY_DISPATCH"
    }
  }
  ```

### `GET /api/v1/incidents/active`
Lists all non-resolved incidents currently active in the home.
- **Response `200 OK`:**
  ```json
  [
    {
      "id": "INC-20261020-001A2B",
      "user_id": "user_eleanor_vance",
      "location": "bathroom",
      "event_type": "possible_fall",
      "confidence": 0.94,
      "initial_risk_level": "CRITICAL",
      "current_risk_level": "CRITICAL",
      "status": "ACTIVE",
      "workflow_state": "WAITING_FOR_RESPONSE",
      "created_at": "2026-10-20T00:54:12Z",
      "updated_at": "2026-10-20T00:54:12Z"
    }
  ]
  ```

### `GET /api/v1/incidents/{incident_id}/timeline`
Returns complete chronological audit log of all actions and transitions for an incident.
- **Response `200 OK`:**
  ```json
  [
    {
      "id": "TL-001",
      "incident_id": "INC-20261020-001A2B",
      "timestamp": "2026-10-20T00:54:12Z",
      "action_type": "VISION_EVENT_INGESTED",
      "actor": "VISION_AI",
      "previous_state": "NONE",
      "new_state": "DETECTED",
      "reason": "Detected possible_fall in bathroom with 94% confidence.",
      "description": "Detected possible_fall in bathroom with 94% confidence. Post-event movement: none."
    },
    {
      "id": "TL-002",
      "incident_id": "INC-20261020-001A2B",
      "timestamp": "2026-10-20T00:54:12Z",
      "action_type": "RISK_ASSESSED",
      "actor": "AEGIS_RISK_ENGINE",
      "previous_state": "DETECTED",
      "new_state": "DETECTED",
      "reason": "Assessed risk as CRITICAL (confidence 95%)."
    },
    {
      "id": "TL-003",
      "incident_id": "INC-20261020-001A2B",
      "timestamp": "2026-10-20T00:54:12Z",
      "action_type": "WELLNESS_CHECK_INITIATED",
      "actor": "ALEXA_VOICE_AGENT",
      "previous_state": "DETECTED",
      "new_state": "WELLNESS_CHECK",
      "reason": "Initiated Alexa+ ambient wellness check for Eleanor."
    }
  ]
  ```

### `POST /api/v1/incidents/{incident_id}/respond-voice`
Handles resident verbal response or timeout to ambient wellness check.
- **Request:**
  ```json
  {
    "transcript": "I'm okay, Alexa! I just dropped my glasses.",
    "is_timeout": false
  }
  ```
- **Response `200 OK` (Safe Reply):**
  ```json
  {
    "incident_id": "INC-20261020-001A2B",
    "status": "RESOLVED",
    "risk_level": "LOW",
    "workflow_state": "RESOLVED",
    "voice_intent": "safe",
    "action_taken": "RESOLVED_SAFE_CANCELLED",
    "transcript": "I'm okay, Alexa! I just dropped my glasses."
  }
  ```
- **Response `200 OK` (Silence / Timeout):**
  ```json
  {
    "incident_id": "INC-20261020-001A2B",
    "status": "ESCALATED_CAD",
    "risk_level": "CRITICAL",
    "action_taken": "SILENT_EMERGENCY_CAD_DISPATCH",
    "workflow_state": "DISPATCH_READY",
    "cad_details": {
      "dispatch_id": "CAD-DISP-001",
      "emergency_packet_id": "EPK-001",
      "units_dispatched": ["Medic 4", "Engine 12"],
      "door_lock_unlocked": true,
      "smart_lock_pin": "9482"
    }
  }
  ```

### `POST /api/v1/incidents/{incident_id}/escalate`
Triggers caregiver or emergency CAD escalation.
- **Request:**
  ```json
  {
    "escalation_type": "caregiver",
    "reason": "Senior called out for assistance"
  }
  ```
- **Response `200 OK` (Caregiver):**
  ```json
  {
    "incident_id": "INC-20261020-001A2B",
    "escalation_type": "caregiver",
    "status": "ESCALATED_CAREGIVER",
    "workflow_state": "CAREGIVER_ESCALATION",
    "notification_id": "NOTIF-001",
    "channels_delivered": [...]
  }
  ```
- **Response `200 OK` (Emergency CAD):**
  ```json
  {
    "incident_id": "INC-20261020-001A2B",
    "escalation_type": "emergency_cad",
    "status": "ESCALATED_CAD",
    "workflow_state": "DISPATCH_READY",
    "emergency_packet_id": "EPK-20261020-001",
    "units_dispatched": ["Medic 4", "Engine 12"],
    "door_lock_unlocked": true,
    "smart_lock_pin": "9482"
  }
  ```

### `POST /api/v1/incidents/{incident_id}/acknowledge`
Caregiver acknowledges emergency and takes responsibility.
- **Request:** `{"caregiver_actor": "Marcus Vance", "notes": "On my way."}`
- **Response `200 OK`:** Incident transitioned to `RESOLVED` with caregiver audit entry.

---

## 4. Model Context Protocol (MCP) Endpoints

### `POST /mcp`
JSON-RPC 2.0 endpoint supporting `initialize`, `tools/list`, and `tools/call`.

### `GET /sse`
MCP Server-Sent Events endpoint establishing event stream session and broadcasting real-time safety events.
