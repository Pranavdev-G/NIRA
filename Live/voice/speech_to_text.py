"""
Abstract Speech-to-Text (ASR) Interface for NIRA.
Amazon Developer Hackathon 2026.

Isolates speech recognition from the rest of the NIRA pipeline so engines
can be replaced without impacting audio capture, orchestration, or clinical analyzers.
"""

from abc import ABC, abstractmethod
from typing import Optional, Union, Dict, Any
import numpy as np

from .models import TranscriptionResult


class SpeechToText(ABC):
    """
    Clean abstraction for Speech-To-Text engines in NIRA.
    Implementations must accept raw or preprocessed audio arrays and return standardized TranscriptionResult.
    """

    @abstractmethod
    def transcribe(
        self,
        audio: Union[np.ndarray, str],
        language: Optional[str] = None,
        task: str = "transcribe",
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribes the input audio.

        Args:
            audio: 1D numpy float32 array at 16,000 Hz, or path to audio file.
            language: Optional BCP-47 language code (e.g. 'en', 'es', 'hi') or None for auto-detection.
            task: 'transcribe' or 'translate' (Whisper native translation).

        Returns:
            TranscriptionResult with transcript, language, processing_time, and quality metrics.
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Returns True if the underlying model weights are loaded and ready."""
        pass

    @abstractmethod
    def get_hardware_info(self) -> Dict[str, Any]:
        """Returns hardware acceleration state (device, dtype, memory)."""
        pass
