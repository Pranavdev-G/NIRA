"""
Unit and Integration Tests for Voice API Endpoints.
Amazon Developer Hackathon 2026.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from Live.api.voice_routes import router as voice_router, get_voice_service
from Live.voice.models import VoiceInteractionStatus
from Live.voice.service import VoiceService
from Live.voice.speech_to_text import SpeechToText
from Live.voice.models import TranscriptionResult


class MockAPI_STT(SpeechToText):
    def transcribe(self, audio, language=None, task="transcribe", **kwargs) -> TranscriptionResult:
        return TranscriptionResult(
            transcript="I am doing fine.",
            language="en",
            duration_sec=1.0,
            processing_time_sec=0.04,
            model="openai/whisper-large-v3-turbo",
            transcription_quality="high",
            metrics={}
        )

    def is_loaded(self) -> bool:
        return True

    def get_hardware_info(self):
        return {"device": "cpu"}


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(voice_router)
    return TestClient(app)


def test_api_status_endpoint(client):
    resp = client.get("/api/v1/live/voice/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "model" in data
    assert "device" in data
    assert "microphone_available" in data


def test_api_analyze_safe(client):
    resp = client.post("/api/v1/live/voice/analyze", json={
        "transcript": "I'm okay, false alarm.",
        "question": "Are you okay?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SAFE"
    assert data["urgency"] == "LOW"


def test_api_analyze_risk(client):
    resp = client.post("/api/v1/live/voice/analyze", json={
        "transcript": "I'm feeling dizzy and lightheaded.",
        "question": "Are you okay?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RISK"
    assert data["urgency"] == "HIGH"


def test_api_analyze_emergency(client):
    resp = client.post("/api/v1/live/voice/analyze", json={
        "transcript": "Help me! I fell down and cannot get up!",
        "question": "Are you okay?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "EMERGENCY"
    assert data["urgency"] == "CRITICAL"


def test_api_analyze_negation_not_safe(client):
    resp = client.post("/api/v1/live/voice/analyze", json={
        "transcript": "I am NOT okay.",
        "question": "Are you okay?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] != "SAFE"
    assert data["status"] in ["RISK", "EMERGENCY"]
    assert data["is_negated"] is True


def test_api_history_endpoint(client):
    resp = client.get("/api/v1/live/voice/history?limit=10")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
