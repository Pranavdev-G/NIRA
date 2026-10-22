"""
NIRA Live Voice Package.
Amazon Developer Hackathon 2026.

High-accuracy real-time speech interaction system using Whisper large-v3-turbo.
"""

from .models import (
    VoiceInteractionStatus,
    VoiceUrgencyLevel,
    VoiceAction,
    TranscriptionResult,
    VoiceAnalysisResult,
    VoiceInteractionResult,
    CheckInRequest
)
from .audio import AudioPreprocessor, TARGET_SAMPLE_RATE
from .microphone import (
    MicrophoneCapture,
    MicrophoneCaptureError,
    MicrophoneUnavailableError,
    MicrophonePermissionError
)
from .speech_to_text import SpeechToText
from .whisper_engine import (
    WhisperSpeechToText,
    WhisperModelManager,
    detect_optimal_hardware,
    DEFAULT_MODEL_ID
)
from .response_analyzer import ResponseAnalyzer
from .storage import VoiceStorage
from .service import VoiceService
from .conversation import WellnessConversationManager

__all__ = [
    "VoiceInteractionStatus",
    "VoiceUrgencyLevel",
    "VoiceAction",
    "TranscriptionResult",
    "VoiceAnalysisResult",
    "VoiceInteractionResult",
    "CheckInRequest",
    "AudioPreprocessor",
    "TARGET_SAMPLE_RATE",
    "MicrophoneCapture",
    "MicrophoneCaptureError",
    "MicrophoneUnavailableError",
    "MicrophonePermissionError",
    "SpeechToText",
    "WhisperSpeechToText",
    "WhisperModelManager",
    "detect_optimal_hardware",
    "DEFAULT_MODEL_ID",
    "ResponseAnalyzer",
    "VoiceStorage",
    "VoiceService",
    "WellnessConversationManager",
]
