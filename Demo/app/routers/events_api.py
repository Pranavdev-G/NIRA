"""
Real-Time Multimodal Event Ingestion & Streaming REST/SSE API.
Amazon Developer Hackathon 2026.

Endpoints:
  - POST /api/v1/events/ingest: Ingests unified multimodal sensor events.
  - GET  /api/v1/events/stream: Real-time Server-Sent Events (SSE) state & event stream.
  - GET  /events: Root-level alias for SSE subscription.
  - GET  /api/v1/resident/state: Returns current authoritative resident & home state snapshot.
  - GET  /api/v1/events/history: Historical chronological audit log of telemetry events.
  - POST /api/v1/events/reset: Resets resident safety state to NORMAL baseline.
  - WS   /api/v1/events/ws: Optional full-duplex WebSocket stream.
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Request, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import TelemetryEventModel
from app.models.event_contracts import (
    UnifiedEvent, ResidentStateSnapshot, EventIngestResult
)
from app.services.event_pipeline import global_pipeline

router = APIRouter(tags=["Unified Real-Time Event Pipeline"])


# ---------------------------------------------------------------------------
# 1. Ingestion Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/events/ingest",
    response_model=EventIngestResult,
    status_code=status.HTTP_200_OK,
    summary="Ingest unified multimodal event"
)
async def ingest_unified_event(
    event: UnifiedEvent,
    db: Session = Depends(get_db)
):
    """
    Ingests a strongly typed UnifiedEvent from wearable, radar, vision, or environmental sensors.
    Validates event structure, checks for duplicate/stale timestamps, updates resident state,
    and broadcasts updates to all active SSE/WebSocket clients.
    """
    result = await global_pipeline.ingest_event(event, db=db)
    return result


@router.post(
    "/api/v1/events/batch",
    response_model=List[EventIngestResult],
    status_code=status.HTTP_200_OK,
    summary="Ingest batch of unified events in order"
)
async def ingest_event_batch(
    events: List[UnifiedEvent],
    db: Session = Depends(get_db)
):
    """Processes a batch of ordered events sequentially."""
    results = []
    for ev in events:
        res = await global_pipeline.ingest_event(ev, db=db)
        results.append(res)
    return results


# ---------------------------------------------------------------------------
# 2. Authoritative State & History Queries
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/resident/state",
    response_model=ResidentStateSnapshot,
    summary="Fetch current authoritative resident & residence state"
)
async def get_resident_state():
    """Returns the single authoritative state snapshot of the resident and residence."""
    return global_pipeline.current_state


@router.get(
    "/api/v1/events/state",
    response_model=ResidentStateSnapshot,
    summary="Alias to fetch current authoritative resident state"
)
async def get_events_state():
    return global_pipeline.current_state


@router.get(
    "/api/v1/events/history",
    summary="Fetch paginated historical telemetry events"
)
def get_event_history(
    limit: int = 50,
    source: Optional[str] = None,
    resident_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns chronological audit trail of processed telemetry events."""
    query = db.query(TelemetryEventModel).order_by(TelemetryEventModel.timestamp.desc())
    if source:
        query = query.filter(TelemetryEventModel.source == source)
    if resident_id:
        query = query.filter(TelemetryEventModel.resident_id == resident_id)

    rows = query.limit(limit).all()
    return [
        {
            "event_id": r.id,
            "correlation_id": r.correlation_id,
            "resident_id": r.resident_id,
            "room_id": r.room_id,
            "source": r.source,
            "event_type": r.event_type,
            "confidence": r.confidence,
            "payload": r.payload_json,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "safety_state_after": r.safety_state_after,
            "evidence_summary": r.evidence_summary
        }
        for r in rows
    ]


@router.post(
    "/api/v1/events/reset",
    summary="Reset system state back to NORMAL baseline"
)
async def reset_pipeline_state():
    """Administrative hook to reset NIRA state back to NORMAL baseline."""
    global_pipeline.reset_to_normal()
    await global_pipeline.broadcast({
        "type": "NIRA_STATE_RESET",
        "state": global_pipeline.current_state.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"status": "SUCCESS", "message": "NIRA resident state reset to NORMAL baseline."}


@router.post(
    "/api/v1/events/recover",
    summary="Recover active state and recent evidence from persistent database"
)
async def recover_pipeline_state(db: Session = Depends(get_db)):
    """Administrative hook to trigger restart-recovery of active emergency incident from database."""
    res = global_pipeline.recover_state_from_database(db)
    await global_pipeline.broadcast({
        "type": "NIRA_STATE_RECOVERED",
        "recovery_info": res,
        "state": global_pipeline.current_state.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"status": "SUCCESS", "recovery": res, "current_state": global_pipeline.current_state}


# ---------------------------------------------------------------------------
# 3. Real-Time Streaming: Server-Sent Events (SSE)
# ---------------------------------------------------------------------------

async def sse_event_stream(request: Request):
    """
    Asynchronous generator yielding real-time Server-Sent Events.
    Sends initial snapshot upon connection, then yields events as they occur.
    Transmits keepalive ping comments every 15s to maintain connection across NATs.
    """
    queue = global_pipeline.subscribe()

    # Initial state broadcast to newly connected client
    initial_event = {
        "type": "INITIAL_SNAPSHOT",
        "snapshot": global_pipeline.current_state.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    yield f"event: state_snapshot\ndata: {json.dumps(initial_event)}\n\n"

    try:
        while True:
            if await request.is_disconnected():
                break

            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                event_type = "state_update" if msg.get("state_changed") else "event_ingested"
                yield f"event: {event_type}\ndata: {json.dumps(msg)}\n\n"
            except asyncio.TimeoutError:
                # Keepalive comment
                yield ": keepalive-ping\n\n"
    finally:
        global_pipeline.unsubscribe(queue)


@router.get(
    "/api/v1/events/stream",
    summary="Real-time Server-Sent Events (SSE) stream"
)
async def events_sse_stream(request: Request):
    """
    Connect to this endpoint to receive live real-time safety events,
    vitals updates, and incident state transitions via SSE.
    """
    return StreamingResponse(
        sse_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get(
    "/events",
    summary="Root alias for real-time SSE event stream"
)
async def root_events_sse(request: Request):
    """Root-level convenience endpoint for frontend SSE subscription."""
    return await events_sse_stream(request)


# ---------------------------------------------------------------------------
# 4. Optional WebSocket Stream
# ---------------------------------------------------------------------------

@router.websocket("/api/v1/events/ws")
async def websocket_event_stream(websocket: WebSocket):
    """Full-duplex WebSocket stream for real-time bidirectional dashboard clients."""
    await websocket.accept()
    queue = global_pipeline.subscribe()

    # Send initial snapshot
    await websocket.send_json({
        "type": "INITIAL_SNAPSHOT",
        "snapshot": global_pipeline.current_state.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                await websocket.send_json(msg)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "PING", "timestamp": datetime.now(timezone.utc).isoformat()})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        global_pipeline.unsubscribe(queue)
