"""
Whisper Speech-to-Text Engine for NIRA.
Amazon Developer Hackathon 2026.

Primary Model: openai/whisper-large-v3-turbo
Features:
  - Hardware selection (Configurable: CPU, CUDA/GPU, MPS, or auto-detect)
  - Singleton Model Lifecycle Manager (loads once, reuses across requests)
  - Lazy loading, error recovery, clean shutdown, and availability status
  - Authentic transcription quality metrics (no fabricated confidence scores)
  - Multilingual speech recognition & separate translation capabilities
"""

import os
import time
import logging
import threading
from typing import Optional, Union, Dict, Any, Tuple
import numpy as np
import torch

HAS_TRANSFORMERS = None
HAS_OPENAI_WHISPER = None

from .speech_to_text import SpeechToText
from .models import TranscriptionResult
from .audio import AudioPreprocessor, TARGET_SAMPLE_RATE

logger = logging.getLogger("NIRA.WhisperEngine")

DEFAULT_MODEL_ID = "openai/whisper-large-v3-turbo"


class WhisperModelUnavailableError(Exception):
    """Raised when Whisper models or dependencies cannot be loaded."""
    pass


def detect_optimal_hardware(requested_device: Optional[str] = None) -> Tuple[str, torch.dtype]:
    """
    Detects or configures hardware acceleration device:
      - 'cuda' / 'gpu': FP16 on CUDA device (falls back to CPU if unavailable)
      - 'mps': FP16 on Apple Silicon MPS (falls back to CPU if unavailable)
      - 'cpu': FP32 with multi-threaded optimizations
      - 'auto' / None: Checks environment (NIRA_WHISPER_DEVICE) then auto-detects
    """
    req = (requested_device or os.getenv("NIRA_WHISPER_DEVICE", "auto")).lower().strip()

    if req in ["cuda", "cuda:0", "gpu"]:
        if torch.cuda.is_available():
            logger.info(f"Hardware acceleration: CUDA requested and active ({torch.cuda.get_device_name(0)})")
            return "cuda:0", torch.float16
        logger.warning("CUDA requested but not available. Falling back to CPU.")

    elif req == "mps":
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("Hardware acceleration: Apple Silicon (MPS) active")
            return "mps", torch.float16
        logger.warning("MPS requested but not available. Falling back to CPU.")

    elif req == "cpu":
        try:
            num_cores = os.cpu_count() or 4
            torch.set_num_threads(max(1, min(num_cores, 8)))
        except Exception:
            pass
        return "cpu", torch.float32

    # Auto-detection
    if torch.cuda.is_available():
        logger.info(f"Hardware acceleration: Auto-detected CUDA GPU ({torch.cuda.get_device_name(0)})")
        return "cuda:0", torch.float16
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("Hardware acceleration: Auto-detected Apple Silicon (MPS)")
        return "mps", torch.float16
    else:
        try:
            num_cores = os.cpu_count() or 4
            torch.set_num_threads(max(1, min(num_cores, 8)))
        except Exception:
            pass
        logger.info(f"Hardware acceleration: CPU inference active (threads: {torch.get_num_threads()})")
        return "cpu", torch.float32


class WhisperModelManager:
    """
    Thread-safe Singleton Lifecycle Manager for Whisper large-v3-turbo.
    Ensures model weights are loaded ONCE into memory, supports clean shutdown,
    and reports live availability status without crashing on unavailable hardware.
    """
    _instance: Optional["WhisperModelManager"] = None
    _lock = threading.Lock()

    def __init__(self, model_id: str = DEFAULT_MODEL_ID, device: Optional[str] = None):
        self.model_id = model_id
        self.device, self.torch_dtype = detect_optimal_hardware(requested_device=device)
        self.hf_pipeline = None
        self.whisper_model = None
        self.backend = "none"
        self._load_lock = threading.Lock()
        self._is_loaded = False
        self._load_duration_sec = 0.0
        self._last_error: Optional[str] = None

    @classmethod
    def get_instance(
        cls,
        model_id: str = DEFAULT_MODEL_ID,
        device: Optional[str] = None
    ) -> "WhisperModelManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(model_id=model_id, device=device)
            return cls._instance

    @classmethod
    def reset_instance(cls):
        """Resets the singleton instance (primarily used in testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.unload_model()
                cls._instance = None

    def is_available(self) -> bool:
        """Checks if inference backend is currently loaded and ready."""
        return self._is_loaded and (self.hf_pipeline is not None or self.whisper_model is not None)

    def get_status(self) -> Dict[str, Any]:
        """Returns structured lifecycle and availability metadata."""
        return {
            "model_id": self.model_id,
            "device": self.device,
            "torch_dtype": str(self.torch_dtype),
            "backend": self.backend,
            "is_loaded": self._is_loaded,
            "is_available": self.is_available(),
            "load_duration_sec": self._load_duration_sec,
            "last_error": self._last_error,
            "cuda_available": torch.cuda.is_available()
        }

    def load_model(self, force_reload: bool = False) -> bool:
        """
        Loads Whisper large-v3-turbo into memory once.
        Returns True if successfully loaded, raises WhisperModelUnavailableError on failure.
        """
        global HAS_TRANSFORMERS, HAS_OPENAI_WHISPER

        with self._load_lock:
            if self._is_loaded and not force_reload:
                return True

            t0 = time.perf_counter()
            logger.info(f"Loading Whisper model '{self.model_id}' on {self.device}...")

            # Lazy import transformers
            if HAS_TRANSFORMERS is None:
                try:
                    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
                    HAS_TRANSFORMERS = True
                except ImportError:
                    HAS_TRANSFORMERS = False

            # Strategy 1: Try Hugging Face Transformers pipeline
            if HAS_TRANSFORMERS:
                try:
                    logger.info(f"Initializing Transformers ASR pipeline for {self.model_id}...")
                    model = AutoModelForSpeechSeq2Seq.from_pretrained(
                        self.model_id,
                        torch_dtype=self.torch_dtype,
                        low_cpu_mem_usage=True,
                        use_safetensors=True
                    )
                    model.to(self.device)

                    processor = AutoProcessor.from_pretrained(self.model_id)

                    self.hf_pipeline = pipeline(
                        "automatic-speech-recognition",
                        model=model,
                        tokenizer=processor.tokenizer,
                        feature_extractor=processor.feature_extractor,
                        torch_dtype=self.torch_dtype,
                        device=self.device,
                        return_timestamps=True
                    )
                    self.backend = "transformers"
                    self._is_loaded = True
                    self._last_error = None
                    self._load_duration_sec = round(time.perf_counter() - t0, 2)
                    logger.info(f"Whisper large-v3-turbo loaded successfully via Transformers in {self._load_duration_sec}s.")
                    return True
                except Exception as e:
                    self._last_error = f"Transformers loading error: {e}"
                    logger.warning(f"Transformers loading error ({e}). Attempting openai-whisper fallback...")

            # Strategy 2: Fallback to official openai-whisper library
            if HAS_OPENAI_WHISPER is None:
                try:
                    import whisper as openai_whisper
                    HAS_OPENAI_WHISPER = True
                except ImportError:
                    openai_whisper = None
                    HAS_OPENAI_WHISPER = False

            if HAS_OPENAI_WHISPER:
                try:
                    import whisper as openai_whisper
                    model_name = "large-v3-turbo" if "turbo" in self.model_id.lower() else "large-v3"
                    logger.info(f"Loading {model_name} via openai-whisper on {self.device}...")
                    self.whisper_model = openai_whisper.load_model(model_name, device=self.device)
                    self.backend = "openai-whisper"
                    self._is_loaded = True
                    self._last_error = None
                    self._load_duration_sec = round(time.perf_counter() - t0, 2)
                    logger.info(f"Whisper large-v3-turbo loaded successfully via openai-whisper in {self._load_duration_sec}s.")
                    return True
                except Exception as e:
                    self._last_error = f"openai-whisper loading failed: {e}"
                    logger.error(f"openai-whisper loading failed: {e}")

            err_msg = (
                f"Could not load Whisper model '{self.model_id}'. "
                f"Ensure transformers or openai-whisper is installed. Detail: {self._last_error}"
            )
            self._is_loaded = False
            raise WhisperModelUnavailableError(err_msg)

    def unload_model(self):
        """Clean shutdown and memory release of Whisper weights."""
        with self._load_lock:
            self.hf_pipeline = None
            self.whisper_model = None
            self.backend = "none"
            self._is_loaded = False
            self._load_duration_sec = 0.0
            if torch.cuda.is_available():
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass
            logger.info("Whisper model unloaded from memory.")


class WhisperSpeechToText(SpeechToText):
    """
    High-accuracy real-time Speech-to-Text implementation using openai/whisper-large-v3-turbo.
    """

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        device: Optional[str] = None,
        auto_load: bool = True
    ):
        self.model_id = model_id
        self.manager = WhisperModelManager.get_instance(model_id=model_id, device=device)
        if auto_load:
            try:
                self.manager.load_model()
            except WhisperModelUnavailableError as e:
                logger.warning(f"Whisper auto-load failed: {e}")

    def is_loaded(self) -> bool:
        return self.manager.is_available()

    def get_hardware_info(self) -> Dict[str, Any]:
        return self.manager.get_status()

    def transcribe(
        self,
        audio: Union[np.ndarray, str],
        language: Optional[str] = None,
        task: str = "transcribe",
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribes audio using the persistent Whisper large-v3-turbo model.
        Handles empty or invalid audio gracefully before model invocation.
        """
        t_start = time.perf_counter()

        # Handle empty or invalid audio array before loading heavy model weights
        if isinstance(audio, np.ndarray):
            if audio.size == 0 or np.all(np.abs(audio) < 1e-4):
                return TranscriptionResult(
                    transcript="",
                    language=language or "en",
                    duration_sec=0.0,
                    processing_time_sec=0.0,
                    model=self.model_id,
                    transcription_quality="empty",
                    metrics={"no_speech_prob": 1.0, "reason": "Silence or empty audio buffer"}
                )

            # Ensure float32 mono 16kHz
            processed, is_valid, msg = AudioPreprocessor.preprocess(audio, target_sample_rate=TARGET_SAMPLE_RATE)
            if not is_valid:
                return TranscriptionResult(
                    transcript="",
                    language=language or "en",
                    duration_sec=round(len(audio) / TARGET_SAMPLE_RATE, 2),
                    processing_time_sec=0.0,
                    model=self.model_id,
                    transcription_quality="invalid",
                    metrics={"reason": msg}
                )
            audio_input = processed
            audio_duration = round(len(processed) / float(TARGET_SAMPLE_RATE), 3)
        else:
            audio_input = audio
            audio_duration = 0.0

        # Ensure model is loaded
        if not self.is_loaded():
            self.manager.load_model()

        # Run inference using loaded backend
        transcript_text = ""
        detected_language = language or "en"
        metrics: Dict[str, Any] = {}
        quality = "good"

        if self.manager.backend == "transformers" and self.manager.hf_pipeline is not None:
            gen_kwargs = {"task": task}
            if language:
                gen_kwargs["language"] = language

            result = self.manager.hf_pipeline(
                audio_input,
                generate_kwargs=gen_kwargs,
                batch_size=1
            )
            transcript_text = result.get("text", "").strip()
            chunks = result.get("chunks", [])
            metrics["chunks_count"] = len(chunks)
            metrics["backend"] = "transformers"

        elif self.manager.backend == "openai-whisper" and self.manager.whisper_model is not None:
            options: Dict[str, Any] = {"task": task, "fp16": (self.manager.device != "cpu")}
            if language:
                options["language"] = language

            result = self.manager.whisper_model.transcribe(audio_input, **options)
            transcript_text = result.get("text", "").strip()
            detected_language = result.get("language", detected_language)

            segments = result.get("segments", [])
            if segments:
                avg_logprob = float(np.mean([s.get("avg_logprob", 0.0) for s in segments]))
                no_speech_probs = [s.get("no_speech_prob", 0.0) for s in segments]
                avg_no_speech = float(np.mean(no_speech_probs))
                compression_ratios = [s.get("compression_ratio", 1.0) for s in segments]
                avg_comp = float(np.mean(compression_ratios))

                metrics["avg_logprob"] = round(avg_logprob, 3)
                metrics["avg_no_speech_prob"] = round(avg_no_speech, 3)
                metrics["compression_ratio"] = round(avg_comp, 3)

                if avg_no_speech > 0.6:
                    quality = "low_speech_detected"
                elif avg_logprob > -0.5:
                    quality = "high"
                elif avg_logprob > -1.0:
                    quality = "good"
                else:
                    quality = "low_confidence"

            metrics["backend"] = "openai-whisper"
        else:
            raise WhisperModelUnavailableError("No active Whisper backend ready for inference.")

        t_elapsed = round(time.perf_counter() - t_start, 3)

        return TranscriptionResult(
            transcript=transcript_text,
            language=detected_language,
            duration_sec=audio_duration,
            processing_time_sec=t_elapsed,
            model=self.model_id,
            transcription_quality=quality,
            metrics=metrics
        )
