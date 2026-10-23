"""
Voice AI Test Harness for NIRA Live Voice Pipeline.
Amazon Developer Hackathon 2026.

Validates:
  - SAFE responses
  - EMERGENCY responses (calls for help, distress, falls)
  - RISK responses (dizziness, weakness, pain)
  - UNCERTAIN responses (mumbled, ambiguous, confusion)
  - SILENCE / timeout responses
  - Strict negation handling ("not okay", "not fine", "not feeling well")
  - Contradictory / mixed statements ("okay, but I fell down", "fine, but bleeding")
  - Graceful degradation when physical microphone is unavailable
  - Graceful handling when Whisper model is unavailable
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from Live.voice.response_analyzer import ResponseAnalyzer
from Live.voice.models import (
    VoiceInteractionStatus,
    VoiceUrgencyLevel,
    VoiceAction
)
from Live.voice.service import VoiceService
from Live.voice.microphone import (
    MicrophoneCapture,
    MicrophoneUnavailableError,
    MicrophonePermissionError
)
from Live.voice.whisper_engine import (
    WhisperSpeechToText,
    WhisperModelManager,
    WhisperModelUnavailableError
)
from Live.voice.speech_to_text import SpeechToText
from Live.voice.models import TranscriptionResult


@pytest.fixture
def analyzer():
    return ResponseAnalyzer(use_llm=False)


# ============================================================================
# 1. Semantic Categorization & Priority Tests
# ============================================================================

def test_safe_responses(analyzer):
    safe_samples = [
        "Yes, I am okay.",
        "I'm fine, thank you.",
        "Everything is alright here.",
        "No problem at all, just dropped my book.",
        "I am doing good, thanks for checking.",
        "All good.",
        "Got back up, no worries."
    ]
    for s in safe_samples:
        res = analyzer.analyze(s)
        assert res.status == VoiceInteractionStatus.SAFE, f"Failed for '{s}'"
        assert res.urgency == VoiceUrgencyLevel.LOW
        assert res.action == VoiceAction.LOG_ONLY


def test_emergency_responses(analyzer):
    emergency_samples = [
        "Help me!",
        "Please help, I fell down and cannot get up.",
        "I can't breathe, call 911!",
        "Call an ambulance immediately.",
        "I'm bleeding badly from my head.",
        "Broken my hip, cannot move at all.",
        "Call my son, this is an emergency.",
        "I need help right now."
    ]
    for s in emergency_samples:
        res = analyzer.analyze(s)
        assert res.status == VoiceInteractionStatus.EMERGENCY, f"Failed for '{s}'"
        assert res.urgency == VoiceUrgencyLevel.CRITICAL
        assert res.action == VoiceAction.ESCALATE_EMERGENCY_CAD


def test_risk_responses(analyzer):
    risk_samples = [
        "I'm feeling very dizzy right now.",
        "My chest feels a bit tight.",
        "I'm having a lot of pain in my back.",
        "Feeling very weak and shaky.",
        "I slipped and lost my balance.",
        "Feeling sick and nauseous."
    ]
    for s in risk_samples:
        res = analyzer.analyze(s)
        assert res.status == VoiceInteractionStatus.RISK, f"Failed for '{s}'"
        assert res.urgency == VoiceUrgencyLevel.HIGH
        assert res.action == VoiceAction.CREATE_INCIDENT


def test_uncertain_and_ambiguous_responses(analyzer):
    uncertain_samples = [
        "I don't know...",
        "Maybe, I'm not sure.",
        "Hard to say.",
        "What happened? Where am I?",
        "Hmm, who is talking?",
        "Confused."
    ]
    for s in uncertain_samples:
        res = analyzer.analyze(s)
        assert res.status == VoiceInteractionStatus.UNCERTAIN, f"Failed for '{s}'"
        assert res.urgency == VoiceUrgencyLevel.MEDIUM
        assert res.action == VoiceAction.REPEAT_CHECK_IN


def test_empty_or_silence_defaults_to_uncertain(analyzer):
    """Empty audio or blank transcript must default to UNCERTAIN, never SAFE."""
    res_empty = analyzer.analyze("")
    assert res_empty.status == VoiceInteractionStatus.UNCERTAIN

    res_spaces = analyzer.analyze("   ...   ")
    assert res_spaces.status == VoiceInteractionStatus.UNCERTAIN


# ============================================================================
# 2. Strict Negation Tests ("I am NOT okay")
# ============================================================================

def test_negated_positives_never_safe(analyzer):
    negated_samples = [
        "I am not okay.",
        "I'm not doing fine.",
        "No, I am not good.",
        "I'm not feeling well at all.",
        "Don't feel good today.",
        "Definitely not okay.",
        "Really not fine.",
        "No, I am not alright.",
        "Something is wrong."
    ]
    for s in negated_samples:
        res = analyzer.analyze(s)
        assert res.status != VoiceInteractionStatus.SAFE, f"Negation was mistakenly classified as SAFE: '{s}'"
        assert res.status in [VoiceInteractionStatus.RISK, VoiceInteractionStatus.EMERGENCY]
        assert res.is_negated is True


# ============================================================================
# 3. Contradictory and Mixed Utterance Tests
# ============================================================================

def test_contradictory_and_mixed_statements(analyzer):
    mixed_emergency_cases = [
        "Yes, I'm okay, but I fell down and I can't get up.",
        "I'm fine, but please call 911.",
        "I was fine, but now I'm bleeding.",
        "Everything is fine, actually no I can't move my leg.",
        "I'm alright, but I need immediate help."
    ]
    for s in mixed_emergency_cases:
        res = analyzer.analyze(s)
        assert res.status == VoiceInteractionStatus.EMERGENCY, f"Emergency priority failed for mixed: '{s}'"
        assert res.is_mixed is True

    mixed_risk_cases = [
        "I'm fine, but I feel very dizzy.",
        "I am okay, however my chest hurts.",
        "I'm doing good, except I have terrible pain."
    ]
    for s in mixed_risk_cases:
        res = analyzer.analyze(s)
        assert res.status == VoiceInteractionStatus.RISK, f"Risk priority failed for mixed: '{s}'"
        assert res.is_mixed is True


def test_contrast_clause_blocks_safe(analyzer):
    """A statement with 'but' or 'however' without clear affirmation must not be SAFE."""
    res = analyzer.analyze("I thought I was okay, but...")
    assert res.status != VoiceInteractionStatus.SAFE


# ============================================================================
# 4. Hardware Failure & Degradation Behavior
# ============================================================================

class MockFailingMic:
    def record_phrase(self, **kwargs):
        raise MicrophoneUnavailableError("No physical USB microphone found")


class MockFailingWhisper(SpeechToText):
    def transcribe(self, audio, **kwargs):
        raise WhisperModelUnavailableError("Whisper weights not loaded")

    def is_loaded(self):
        return False

    def get_hardware_info(self):
        return {"loaded": False}


class MockWorkingSTT(SpeechToText):
    def transcribe(self, audio, **kwargs):
        return TranscriptionResult(
            transcript="I am okay.",
            language="en",
            duration_sec=1.5,
            processing_time_sec=0.04,
            model="mock",
            transcription_quality="high"
        )

    def is_loaded(self):
        return True

    def get_hardware_info(self):
        return {"loaded": True}


def test_service_handles_microphone_unavailable():
    """VoiceService must return UNCERTAIN fallback when mic is disconnected, without crashing."""
    service = VoiceService(
        stt=MockWorkingSTT(),
        microphone=MockFailingMic(),
        analyzer=ResponseAnalyzer()
    )
    result = service.run_check_in(elderly_id="resident_test", question="Are you okay?")
    assert result is not None
    assert result.status == VoiceInteractionStatus.UNCERTAIN
    assert result.action == VoiceAction.REPEAT_CHECK_IN
    assert "Microphone unavailable" in result.reason
    assert result.metadata.get("error") == "MIC_UNAVAILABLE"


def test_service_handles_whisper_unavailable():
    """VoiceService must return UNCERTAIN fallback when Whisper fails, without crashing."""
    valid_audio = np.ones(16000, dtype=np.float32) * 0.1
    service = VoiceService(
        stt=MockFailingWhisper(),
        microphone=MicrophoneCapture(),
        analyzer=ResponseAnalyzer()
    )
    result = service.run_check_in(
        elderly_id="resident_test",
        question="Are you okay?",
        audio_data=valid_audio
    )
    assert result is not None
    assert result.status == VoiceInteractionStatus.UNCERTAIN
    assert result.action == VoiceAction.REPEAT_CHECK_IN
    assert result.metadata.get("error") == "ASR_FAILURE"
