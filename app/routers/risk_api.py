"""
REST API Endpoints for Aegis CARE Risk Engine (v1).
Amazon Developer Hackathon 2026.

Exposes:
  - POST /api/v1/assess-risk: Initial multimodal risk evaluation
  - POST /api/v1/reassess-risk: Adaptive risk re-evaluation incorporating voice response
"""

import time
from fastapi import APIRouter, Response
from app.models.schemas import (
    AssessRiskRequest, ReassessRiskRequest,
    RiskAssessmentResponse
)
from app.services.aegis_risk_engine import AegisRiskEngine


router = APIRouter(prefix="/api/v1", tags=["Aegis Risk Engine v1"])


@router.post("/assess-risk", response_model=RiskAssessmentResponse)
async def assess_risk_api(request: AssessRiskRequest, response: Response):
    """
    Evaluates raw vision event, environmental context, and personal circadian baseline.
    Returns:
      {
        "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
        "confidence": 0.94,
        "reasons": [...]
      }
    """
    start_time = time.perf_counter()
    result = AegisRiskEngine.evaluate(request.event, request.context, voice_response=None)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    result.latency_ms = round(elapsed_ms, 2)
    response.headers["X-Response-Time-Ms"] = str(result.latency_ms)
    return result


@router.post("/reassess-risk", response_model=RiskAssessmentResponse)
async def reassess_risk_api(request: ReassessRiskRequest, response: Response):
    """
    Reassesses risk state after conversational Alexa+ wellness verification:
      - 'I am okay' -> LOW (Cancelled)
      - 'Help me' -> HIGH (Caregiver notified)
      - No response / Timeout -> CRITICAL (Silent emergency / CAD escalation)
    """
    start_time = time.perf_counter()
    result = AegisRiskEngine.evaluate(request.event, request.context, voice_response=request.voice_response)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    result.latency_ms = round(elapsed_ms, 2)
    response.headers["X-Response-Time-Ms"] = str(result.latency_ms)
    return result


from app.services.risk_intelligence import ExplainableRiskResult


@router.post("/risk/explain", response_model=ExplainableRiskResult)
async def explain_risk_api(request: ReassessRiskRequest):
    """
    Exposes full explainable risk breakdown:
      - contributing_factors with weights
      - suppressed_factors with mitigating weights
      - sensor_conflict_detected
      - missing_sensors
      - hysteresis stabilization
    """
    result = AegisRiskEngine.evaluate_explainable(
        event=request.event,
        context=request.context,
        voice_response=request.voice_response
    )
    return result
