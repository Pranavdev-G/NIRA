"""
NIRA Live Processing Package.
Contains live models, real-time camera pipelines, and physical sensor ingestion streams.
"""

try:
    from .live_vision_tracker import LiveVisionTracker
    from .live_ingest_stream import LiveIngestStream
    from .voice import (
        VoiceService,
        SpeechToText,
        WhisperSpeechToText,
        MicrophoneCapture,
        AudioPreprocessor,
        ResponseAnalyzer,
        VoiceInteractionResult,
        VoiceInteractionStatus,
        VoiceUrgencyLevel,
        VoiceAction,
        WellnessConversationManager
    )
    from .api import voice_router
except ImportError:
    from live_vision_tracker import LiveVisionTracker
    from live_ingest_stream import LiveIngestStream
    from voice import (
        VoiceService,
        SpeechToText,
        WhisperSpeechToText,
        MicrophoneCapture,
        AudioPreprocessor,
        ResponseAnalyzer,
        VoiceInteractionResult,
        VoiceInteractionStatus,
        VoiceUrgencyLevel,
        VoiceAction,
        WellnessConversationManager
    )
    from api import voice_router

__all__ = [
    "LiveVisionTracker",
    "LiveIngestStream",
    "VoiceService",
    "SpeechToText",
    "WhisperSpeechToText",
    "MicrophoneCapture",
    "AudioPreprocessor",
    "ResponseAnalyzer",
    "VoiceInteractionResult",
    "VoiceInteractionStatus",
    "VoiceUrgencyLevel",
    "VoiceAction",
    "WellnessConversationManager",
    "voice_router",
]
