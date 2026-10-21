"""
Direct HTTP Endpoints for Aegis Ambient Care MCP Tools.
Optimized for sub-500ms execution with latency monitoring headers.
"""

import time
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Response, Request
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    AssessRiskRequest, AssessRiskResponse,
    StartWellnessCheckRequest, WellnessCheckResponse,
    WellnessCheckReplyRequest, WellnessCheckResolutionResponse,
    NotifyCaregiverRequest, CaregiverNotificationResponse,
    GenerateEmergencyPacketRequest, EmergencyPacket,
    EscalateEmergencyRequest, EscalateEmergencyResponse
)
from app.services.risk_engine import RiskEngine
from app.services.state_machine import WellnessStateMachine
from app.services.caregiver_service import CaregiverService
from app.services.emergency_service import EmergencyService


router = APIRouter(prefix="/tools", tags=["MCP Tools HTTP"])


@router.post("/assess_risk", response_model=AssessRiskResponse)
async def assess_risk_endpoint(request: AssessRiskRequest, response: Response):
    """
    Tool 1: assess_risk
    Consumes event/context data and returns the updated risk state (LOW, MODERATE, HIGH, CRITICAL).
    """
    start_time = time.perf_counter()
    result = RiskEngine.evaluate_and_respond(request.event, request.context)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    result.latency_ms = round(elapsed_ms, 2)
    response.headers["X-Response-Time-Ms"] = str(result.latency_ms)
    return result


@router.post("/start_wellness_check", response_model=WellnessCheckResponse)
async def start_wellness_check_endpoint(request: StartWellnessCheckRequest, response: Response):
    """
    Tool 2: start_wellness_check
    Initiates an interactive conversational prompt asking the user if they are okay.
    """
    start_time = time.perf_counter()
    result = WellnessStateMachine.start_wellness_check(
        session_id=request.session_id,
        event=request.event,
        context=request.context,
        initial_risk=request.initial_risk,
        prompt_override=request.prompt_override
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return result


@router.post("/respond_wellness_check", response_model=WellnessCheckResolutionResponse)
async def respond_wellness_check_endpoint(request: WellnessCheckReplyRequest, response: Response):
    """
    Tool 2 (Part B): respond_wellness_check
    Conversational state machine transitions:
    - 'I'm okay' -> Downgrade risk -> Cancel escalation
    - 'Help me' -> Elevate risk -> Trigger caregiver notify & emergency packet
    - No response / Timeout -> CRITICAL -> Trigger emergency escalation
    """
    start_time = time.perf_counter()
    result = await WellnessStateMachine.process_reply(request)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return result


@router.post("/notify_caregiver", response_model=CaregiverNotificationResponse)
async def notify_caregiver_endpoint(request: NotifyCaregiverRequest, response: Response):
    """
    Tool 3: notify_caregiver
    Triggers mock caregiver notifications for MODERATE/HIGH risk across Alexa Drop-In, Push, SMS.
    """
    start_time = time.perf_counter()
    result = await CaregiverService.dispatch_notification(request)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return result


@router.post("/generate_emergency_packet", response_model=EmergencyPacket)
async def generate_emergency_packet_endpoint(request: GenerateEmergencyPacketRequest, response: Response):
    """
    Tool 4: generate_emergency_packet
    Compiles incident metadata, risk breakdown, and temporal signals into a structured JSON summary.
    """
    start_time = time.perf_counter()
    result = EmergencyService.generate_packet(
        event=request.event,
        context=request.context,
        risk=request.risk,
        patient_id=request.patient_id
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return result


@router.post("/escalate_emergency", response_model=EscalateEmergencyResponse)
async def escalate_emergency_endpoint(request: EscalateEmergencyRequest, response: Response):
    """
    Tool 5: escalate_emergency
    Directs CRITICAL alerts to a simulated emergency service endpoint (CAD 911 dispatch).
    """
    start_time = time.perf_counter()
    result = await EmergencyService.escalate_to_cad(request)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return result


@router.get("/stream_session/{session_id}")
async def stream_session_events(session_id: str, request: Request):
    """
    Streamable HTTP / SSE endpoint providing real-time telemetry updates for active wellness sessions.
    """
    async def event_generator():
        session = WellnessStateMachine.get_session(session_id)
        if not session:
            yield f"event: error\ndata: Session {session_id} not found\n\n"
            return

        yield f"event: session_init\ndata: {{\"session_id\": \"{session.session_id}\", \"state\": \"{session.state.value}\", \"risk\": \"{session.risk.risk_level}\"}}\n\n"

        for _ in range(5):
            if await request.is_disconnected():
                break
            await asyncio.sleep(1.0)
            yield f"event: heartbeat\ndata: {{\"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\", \"session_state\": \"{session.state.value}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
