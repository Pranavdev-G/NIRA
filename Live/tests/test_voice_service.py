"""
Unit and Integration Tests for VoiceService Pipeline.
Amazon Developer Hackathon 2026.
"""

import pytest
import numpy as np
from Live.voice.models import (
    VoiceInteractionResult,
    VoiceInteractionStatus,
    VoiceUrgencyLevel,
    VoiceAction,
    TranscriptionResult
)
from Live.voice.speech_to_text import SpeechToText
from Live.voice.response_analyzer import ResponseAnalyzer
from Live.voice.service import VoiceService
from Live.voice.storage import VoiceStorage


class MockConfigurableSTT(SpeechToText):
    """Mock ASR engine that returns pre-configured transcripts for controlled pipeline testing."""
    def __init__(self, transcript_to_return: str = "Yes, I am okay."):
        self.transcript_to_return = transcript_to_return
        self._loaded = True

    def transcribe(self, audio, language=None, task="transcribe", **kwargs) -> TranscriptionResult:
        return TranscriptionResult(
            transcript=self.transcript_to_return,
            language=language or "en",
            duration_sec=1.5,
            processing_time_sec=0.08,
            model="openai/whisper-large-v3-turbo",
            transcription_quality="high",
            metrics={"avg_logprob": -0.22, "mock": True}
        )

    def is_loaded(self) -> bool:
        return self._loaded

    def get_hardware_info(self):
        return {"device": "cpu", "model": "mock-whisper-test"}


@pytest.fixture
def mock_audio():
    # 1 second 16kHz float32 audio
    return np.random.uniform(-0.1, 0.1, 16000).astype(np.float32)


def test_voice_service_safe_flow(mock_audio):
    stt = MockConfigurableSTT("Yes, I am okay.")
    service = VoiceService(stt=stt, auto_load_model=False)

    result = service.run_check_in(
        elderly_id="PT-84920",
        question="Are you okay?",
        audio_data=mock_audio
    )

    assert isinstance(result, VoiceInteractionResult)
    assert result.status == VoiceInteractionStatus.SAFE
    assert result.urgency == VoiceUrgencyLevel.LOW
    assert result.action == VoiceAction.LOG_ONLY
    assert result.elderly_id == "PT-84920"
    assert result.transcript == "Yes, I am okay."


def test_voice_service_risk_flow(mock_audio):
    stt = MockConfigurableSTT("I'm feeling dizzy.")
    service = VoiceService(stt=stt, auto_load_model=False)

    result = service.run_check_in(
        elderly_id="PT-84920",
        question="Are you okay?",
        audio_data=mock_audio
    )

    assert result.status == VoiceInteractionStatus.RISK
    assert result.urgency == VoiceUrgencyLevel.HIGH
    assert result.action == VoiceAction.CREATE_INCIDENT
    assert "dizzy" in result.reason.lower()


def test_voice_service_emergency_flow(mock_audio):
    stt = MockConfigurableSTT("I fell down and can't get up.")
    service = VoiceService(stt=stt, auto_load_model=False)

    result = service.run_check_in(
        elderly_id="PT-84920",
        question="Are you okay?",
        audio_data=mock_audio
    )

    assert result.status == VoiceInteractionStatus.EMERGENCY
    assert result.urgency == VoiceUrgencyLevel.CRITICAL
    assert result.action == VoiceAction.ESCALATE_EMERGENCY_CAD


def test_voice_service_negation_not_safe(mock_audio):
    stt = MockConfigurableSTT("I am NOT okay.")
    service = VoiceService(stt=stt, auto_load_model=False)

    result = service.run_check_in(
        elderly_id="PT-84920",
        question="Are you okay?",
        audio_data=mock_audio
    )

    assert result.status != VoiceInteractionStatus.SAFE
    assert result.status in [VoiceInteractionStatus.RISK, VoiceInteractionStatus.EMERGENCY]
    assert result.metadata["is_negated"] is True


def test_voice_service_mixed_emergency_overrides(mock_audio):
    stt = MockConfigurableSTT("Yes, I'm okay, but I fell down and I can't get up.")
    service = VoiceService(stt=stt, auto_load_model=False)

    result = service.run_check_in(
        elderly_id="PT-84920",
        question="Are you okay?",
        audio_data=mock_audio
    )

    assert result.status == VoiceInteractionStatus.EMERGENCY
    assert result.urgency == VoiceUrgencyLevel.CRITICAL
    assert result.metadata["is_mixed"] is True


def test_voice_service_silence_timeout_safety_fallback():
    # Pass empty array to simulate complete silence / timeout
    stt = MockConfigurableSTT("")
    service = VoiceService(stt=stt, auto_load_model=False)

    result = service.run_check_in(
        elderly_id="PT-84920",
        question="Are you okay?",
        audio_data=np.array([], dtype=np.float32)
    )

    # MUST be UNCERTAIN, never SAFE
    assert result.status == VoiceInteractionStatus.UNCERTAIN
    assert result.status != VoiceInteractionStatus.SAFE


def test_voice_service_storage_logging(mock_audio):
    stt = MockConfigurableSTT("I'm fine.")
    storage = VoiceStorage()
    service = VoiceService(stt=stt, storage=storage, auto_load_model=False)

    result = service.run_check_in(
        elderly_id="PT-84920",
        question="Are you okay?",
        audio_data=mock_audio
    )

    recent = storage.get_recent_interactions(limit=5)
    matched = [r for r in recent if r["id"] == result.interaction_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "SAFE"
    assert matched[0]["elderly_id"] == "PT-84920"
