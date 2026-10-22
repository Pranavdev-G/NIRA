"""
Unit Tests for Speech-to-Text Abstraction and Whisper Engine.
Amazon Developer Hackathon 2026.
"""

import pytest
import numpy as np
from Live.voice.speech_to_text import SpeechToText
from Live.voice.whisper_engine import (
    WhisperSpeechToText,
    WhisperModelManager,
    detect_optimal_hardware,
    DEFAULT_MODEL_ID
)
from Live.voice.audio import AudioPreprocessor, TARGET_SAMPLE_RATE
from Live.voice.models import TranscriptionResult


class MockCustomSTT(SpeechToText):
    """Verifies that the SpeechToText interface can be cleanly implemented by any engine."""
    def __init__(self):
        self._loaded = True

    def transcribe(self, audio, language=None, task="transcribe", **kwargs) -> TranscriptionResult:
        return TranscriptionResult(
            transcript="I am okay.",
            language=language or "en",
            duration_sec=1.5,
            processing_time_sec=0.05,
            model="mock-custom-asr",
            transcription_quality="high",
            metrics={"mock": True}
        )

    def is_loaded(self) -> bool:
        return self._loaded

    def get_hardware_info(self):
        return {"device": "cpu", "model": "mock-custom-asr"}


def test_speech_to_text_clean_abstraction():
    mock_engine = MockCustomSTT()
    assert isinstance(mock_engine, SpeechToText)
    res = mock_engine.transcribe(np.zeros(16000, dtype=np.float32))
    assert res.transcript == "I am okay."
    assert res.model == "mock-custom-asr"
    assert res.transcription_quality == "high"


def test_hardware_detection():
    device, dtype = detect_optimal_hardware()
    assert device in ["cuda:0", "mps", "cpu"]
    assert dtype is not None


def test_audio_preprocessor_mono_conversion():
    # Stereo input (2 channels, 16000 samples)
    stereo = np.ones((16000, 2), dtype=np.float32)
    mono = AudioPreprocessor.ensure_mono(stereo)
    assert mono.ndim == 1
    assert len(mono) == 16000


def test_audio_preprocessor_resampling():
    # 48,000 Hz 1-second sine wave
    orig_sr = 48000
    t = np.linspace(0, 1.0, orig_sr, endpoint=False)
    sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)

    resampled = AudioPreprocessor.resample(sine, orig_sr=orig_sr, target_sr=16000)
    assert len(resampled) == 16000


def test_audio_preprocessor_rejects_empty():
    empty_arr = np.array([], dtype=np.float32)
    processed, is_valid, reason = AudioPreprocessor.preprocess(empty_arr)
    assert not is_valid
    assert "Empty" in reason


def test_audio_preprocessor_rejects_extremely_short():
    short_arr = np.zeros(800, dtype=np.float32)  # 0.05 seconds at 16kHz
    processed, is_valid, reason = AudioPreprocessor.preprocess(short_arr, min_duration_sec=0.25)
    assert not is_valid
    assert "short" in reason.lower()


def test_whisper_engine_hardware_info():
    manager = WhisperModelManager.get_instance(model_id=DEFAULT_MODEL_ID)
    info = manager.device
    assert info in ["cuda:0", "mps", "cpu"]


def test_whisper_handles_empty_audio_gracefully():
    # Whisper engine must handle empty array without crashing
    stt = WhisperSpeechToText(auto_load=False)
    empty_audio = np.array([], dtype=np.float32)
    res = stt.transcribe(empty_audio)
    assert res.transcript == ""
    assert res.transcription_quality in ["empty", "invalid"]
