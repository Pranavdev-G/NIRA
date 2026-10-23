"""
REST, SSE, and WebSocket Router for Authoritative NIRA Live Safety Core.
Amazon Developer Hackathon 2026.
"""

import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from Live.core.core_service import get_live_core, CoreService
from Live.core.models import SafetyState

router = APIRouter(prefix="/api/v1/live/core", tags=["Authoritative Safety Core"])


class EventIngestPayload(BaseModel):
    event_id: Optional[str] = None
    event_type: str = Field(..., description="Standardized event category")
    source: str = Field(..., description="Sensor or subsystem source")
    resident_id: Optional[str] = "resident_eleanor_vance"
    timestamp: Optional[str] = None
    zone: Optional[str] = "living_room"
    confidence: Optional[float] = 1.0
    correlation_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class WellnessCheckTriggerPayload(BaseModel):
    incident_id: Optional[str] = None
    prompt: Optional[str] = None


class VoiceResponsePayload(BaseModel):
    incident_id: Optional[str] = None
    response_text: str = Field(..., description="Resident transcript from speech-to-text")
    duration_sec: Optional[float] = None


class IncidentResolvePayload(BaseModel):
    outcome: str = Field("SAFE_CONFIRMED", description="SAFE_CONFIRMED, FALSE_ALARM_LEARNED, PARAMEDIC_TREATED, etc.")
    resolved_by: str = Field("CARE_TEAM", description="Resolving actor")
    notes: Optional[str] = ""


# ----------------------------------------------------------------------
# 1. Authoritative State & Health
# ----------------------------------------------------------------------
@router.get("/state", summary="Get authoritative live safety state snapshot")
def get_authoritative_state():
    core: CoreService = get_live_core()
    return {
        "success": True,
        "state": core.get_current_state()
    }


# ----------------------------------------------------------------------
# 2. Event Ingestion
# ----------------------------------------------------------------------
@router.post("/events", summary="Ingest normalized event into Authoritative Safety Core")
def ingest_core_event(payload: EventIngestPayload):
    core: CoreService = get_live_core()
    data = payload.model_dump(exclude_none=True)
    event, risk, incident = core.ingest_event(data)

    return {
        "success": True,
        "event_accepted": event is not None,
        "event_id": event.event_id if event else None,
        "safety_state": core.incident_manager.current_state.value,
        "risk_assessment": risk.model_dump(),
        "active_incident_id": incident.incident_id if incident else None
    }


# ----------------------------------------------------------------------
# 3. Incident Lifecycle & Auditing
# ----------------------------------------------------------------------
@router.get("/incidents/active", summary="Get current active safety incident")
def get_active_incident():
    core: CoreService = get_live_core()
    inc = core.get_active_incident()
    return {
        "success": True,
        "active": inc is not None,
        "incident": inc.model_dump() if inc else None
    }


@router.get("/incidents/{incident_id}/timeline", summary="Get chronological audit timeline for incident")
def get_incident_timeline(incident_id: str):
    core: CoreService = get_live_core()
    timeline = core.get_incident_timeline(incident_id)
    return {
        "success": True,
        "incident_id": incident_id,
        "timeline": [t.model_dump() for t in timeline]
    }


@router.get("/incidents/{incident_id}/packet", summary="Generate authoritative emergency packet")
def get_incident_emergency_packet(incident_id: str):
    core: CoreService = get_live_core()
    packet = core.generate_emergency_packet(incident_id)
    if not packet:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {
        "success": True,
        "emergency_packet": packet.model_dump()
    }


@router.post("/incidents/{incident_id}/resolve", summary="Resolve safety incident")
def resolve_incident(incident_id: str, payload: IncidentResolvePayload):
    core: CoreService = get_live_core()
    inc = core.resolve_incident(
        incident_id=incident_id,
        outcome=payload.outcome,
        resolved_by=payload.resolved_by,
        notes=payload.notes or ""
    )
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {
        "success": True,
        "incident": inc.model_dump()
    }


# ----------------------------------------------------------------------
# 4. Conversational Wellness & Automatic Microphone Integration
# ----------------------------------------------------------------------
@router.post("/wellness/check", summary="Trigger vocal wellness inquiry")
def trigger_wellness_check(payload: WellnessCheckTriggerPayload):
    core: CoreService = get_live_core()
    result = core.start_wellness_check(
        incident_id=payload.incident_id,
        prompt=payload.prompt
    )
    return result


@router.post("/wellness/response", summary="Process resident spoken response")
def process_wellness_response(payload: VoiceResponsePayload):
    core: CoreService = get_live_core()
    result = core.process_wellness_response(
        response_text=payload.response_text,
        incident_id=payload.incident_id,
        duration_sec=payload.duration_sec
    )
    return result


@router.post("/wellness/silence-timeout", summary="Handle 15s vocal silence timeout")
def handle_silence_timeout(payload: WellnessCheckTriggerPayload):
    core: CoreService = get_live_core()
    result = core.handle_silence_timeout(incident_id=payload.incident_id)
    return result


# ----------------------------------------------------------------------
# 5. Realtime SSE Streaming & WebSocket
# ----------------------------------------------------------------------
@router.get("/events/stream", summary="Server-Sent Events real-time state stream")
async def sse_stream():
    core: CoreService = get_live_core()
    return StreamingResponse(
        core.bus.sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    core: CoreService = get_live_core()
    q = await core.bus.subscribe()

    try:
        # Send initial snapshot
        init_state = core.get_current_state()
        await websocket.send_text(json.dumps({"topic": "state_snapshot", "data": init_state}))

        while True:
            # Wait for either incoming message or bus broadcast
            recv_task = asyncio.create_task(websocket.receive_text())
            bus_task = asyncio.create_task(q.get())

            done, pending = await asyncio.wait(
                [recv_task, bus_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if bus_task in done:
                msg = bus_task.result()
                await websocket.send_text(json.dumps(msg))

            if recv_task in done:
                client_text = recv_task.result()
                # Handle client ping
                try:
                    data = json.loads(client_text)
                    if data.get("action") == "ping":
                        await websocket.send_text(json.dumps({"action": "pong", "time": init_state["timestamp"]}))
                except Exception:
                    pass

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        await core.bus.unsubscribe(q)
