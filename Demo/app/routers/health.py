"""
Health and Latency SLA Monitoring Endpoint.
Amazon Developer Hackathon 2026.
"""

import time
from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings
from app.models.schemas import Event, Context
from app.services.risk_engine import RiskEngine

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health")
async def health_check():
    """
    Healthcheck endpoint that also runs an active latency self-test to verify
    compliance with Amazon's sub-500ms voice latency budget.
    """
    start_test = time.perf_counter()
    sample_event = Event(
        event_type="ambient_heartbeat_check",
        confidence=0.99,
        location="living_room",
        timestamp=datetime.now(timezone.utc).isoformat(),
        movement_after_event="normal"
    )
    sample_context = Context(
        activity="idle",
        time_context="afternoon",
        baseline_deviation=0.05,
        wearable_status="worn_normal",
        environment="well_lit"
    )
    _ = RiskEngine.evaluate(sample_event, sample_context)
    self_test_latency_ms = (time.perf_counter() - start_test) * 1000.0

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "latency_sla": {
            "budget_ms": settings.LATENCY_BUDGET_MS,
            "engine_self_test_ms": round(self_test_latency_ms, 2),
            "compliant": self_test_latency_ms < settings.LATENCY_BUDGET_MS
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
