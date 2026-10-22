"""
FastAPI REST Router for NIRA Live Voice Interaction System.
Amazon Developer Hackathon 2026.

Exposes endpoints under /api/v1/live/voice:
  - POST /check-in: Runs live microphone check-in with resident
  - POST /analyze: Evaluates safety classification of a text transcript
  - POST /transcribe: Transcribes raw or uploaded audio
  - GET  /status: Reports Whisper large-v3-turbo engine and hardware status
  - GET  /history: Returns chronological voice interaction records
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Body, status
from pydantic import BaseModel, Field

from Live.voice.models import (
    VoiceInteractionResult,
    VoiceAnalysisResult,
    TranscriptionResult,
    CheckInRequest,
    VoiceInteractionStatus
)
from Live.voice.service import VoiceService
from Live.voice.whisper_engine import WhisperModelManager, detect_optimal_hardware, DEFAULT_MODEL_ID
from Live.voice.microphone import MicrophoneCapture
from Live.voice.response_analyzer import ResponseAnalyzer
from Live.voice.storage import VoiceStorage

logger = logging.getLogger("NIRA.VoiceAPI")
router = APIRouter(prefix="/api/v1/live/voice", tags=["NIRA Live Voice Interaction"])

# Global Service Singleton
_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService(auto_load_model=False)
    return _voice_service


class AnalyzeTranscriptRequest(BaseModel):
    transcript: str = Field(..., description="Resident spoken response transcript")
    question: str = Field("Are you okay?", description="Question prompt asked")


class VoiceStatusResponse(BaseModel):
    model: str
    backend: str
    is_loaded: bool
    device: str
    torch_dtype: str
    cuda_available: bool
    microphone_available: bool
    default_device: Optional[Dict[str, Any]] = None


@router.get("/status", response_model=VoiceStatusResponse, summary="Get Live Voice Engine Status")
def get_voice_status():
    """Returns runtime readiness of Whisper large-v3-turbo and microphone hardware."""
    mgr = WhisperModelManager.get_instance(model_id=DEFAULT_MODEL_ID)
    device, dtype = detect_optimal_hardware()
    mic_ok = MicrophoneCapture.is_available()
    dev_info = MicrophoneCapture.get_default_device_info()

    return VoiceStatusResponse(
        model=mgr.model_id,
        backend=mgr.backend,
        is_loaded=mgr._is_loaded,
        device=device,
        torch_dtype=str(dtype),
        cuda_available=device.startswith("cuda"),
        microphone_available=mic_ok,
        default_device=dev_info
    )


@router.post("/preload", summary="Preload Whisper large-v3-turbo weights")
def preload_whisper_model():
    """Warm-up hook to load Whisper large-v3-turbo into memory ahead of first request."""
    mgr = WhisperModelManager.get_instance(model_id=DEFAULT_MODEL_ID)
    mgr.load_model()
    return {
        "status": "ready",
        "model": mgr.model_id,
        "backend": mgr.backend,
        "device": mgr.device,
        "load_time_sec": mgr._load_duration_sec
    }


@router.post("/check-in", response_model=VoiceInteractionResult, summary="Execute Live Voice Check-In")
def execute_voice_check_in(payload: CheckInRequest = Body(...)):
    """
    Triggers microphone capture, Whisper speech recognition, and response safety analysis.
    """
    svc = get_voice_service()
    result = svc.run_check_in(
        elderly_id=payload.elderly_id,
        question=payload.question,
        max_duration_sec=payload.max_record_seconds,
        silence_timeout_sec=payload.silence_timeout_seconds,
        language=payload.language,
        room_id=payload.room_id,
        correlation_id=payload.incident_id
    )
    return result


@router.post("/analyze", response_model=VoiceAnalysisResult, summary="Analyze Verbal Transcript")
def analyze_spoken_response(payload: AnalyzeTranscriptRequest = Body(...)):
    """
    Evaluates transcript against clinical negation rules, emergency priorities, and risk patterns.
    """
    svc = get_voice_service()
    return svc.analyzer.analyze(payload.transcript)


@router.get("/history", response_model=List[Dict[str, Any]], summary="Get Recent Voice Interactions")
def get_voice_history(limit: int = Query(20, ge=1, le=100)):
    """Returns chronological log of recent senior voice interactions from database."""
    storage = VoiceStorage()
    return storage.get_recent_interactions(limit=limit)
