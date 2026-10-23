"""
Live Voice Interaction Service & Pipeline Coordinator for NIRA.
Amazon Developer Hackathon 2026.

Integrates:
  Microphone Capture -> Audio Preprocessing -> Whisper large-v3-turbo ->
  Response Analyzer -> Structured Result & Event Ingestion
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Union, Dict, Any
import numpy as np

from .models import (
    VoiceInteractionStatus,
    VoiceUrgencyLevel,
    VoiceAction,
    VoiceInteractionResult,
    TranscriptionResult
)
from .audio import AudioPreprocessor, TARGET_SAMPLE_RATE
from .microphone import (
    MicrophoneCapture,
    MicrophoneCaptureError,
    MicrophoneUnavailableError,
    MicrophonePermissionError
)
from .speech_to_text import SpeechToText
from .whisper_engine import WhisperSpeechToText, DEFAULT_MODEL_ID
from .response_analyzer import ResponseAnalyzer
from .storage import VoiceStorage

try:
    from Live.live_ingest_stream import LiveIngestStream, build_live_event
except ImportError:
    try:
        from live_ingest_stream import LiveIngestStream, build_live_event
    except ImportError:
        LiveIngestStream = None
        build_live_event = None

logger = logging.getLogger("NIRA.VoiceService")


class VoiceService:
    """
    Central orchestration service for NIRA live vocal interactions.
    Exposes clean programmatic API contracts to other live modules.
    """

    def __init__(
        self,
        stt: Optional[SpeechToText] = None,
        microphone: Optional[MicrophoneCapture] = None,
        analyzer: Optional[ResponseAnalyzer] = None,
        storage: Optional[VoiceStorage] = None,
        backend_url: str = "http://localhost:8000",
        auto_load_model: bool = False
    ):
        self.stt = stt or WhisperSpeechToText(auto_load=auto_load_model)
        self.microphone = microphone or MicrophoneCapture(sample_rate=TARGET_SAMPLE_RATE)
        self.analyzer = analyzer or ResponseAnalyzer()
        self.storage = storage or VoiceStorage()
        self.live_stream = LiveIngestStream(backend_url=backend_url) if LiveIngestStream else None

    def run_check_in(
        self,
        elderly_id: str = "PT-84920",
        question: str = "Are you okay?",
        audio_data: Optional[np.ndarray] = None,
        max_duration_sec: float = 10.0,
        silence_timeout_sec: float = 2.2,
        initial_timeout_sec: float = 5.0,
        language: Optional[str] = None,
        room_id: str = "living_room",
        correlation_id: Optional[str] = None
    ) -> VoiceInteractionResult:
        """
        Executes a complete wellness check-in turn:
          1. Activates microphone (or uses supplied audio buffer)
          2. Listens and records speech response
          3. Transcribes using Whisper large-v3-turbo
          4. Evaluates clinical safety (SAFE / UNCERTAIN / RISK / EMERGENCY)
          5. Constructs authoritative VoiceInteractionResult
          6. Persists interaction and publishes telemetry event
        """
        t_start = time.perf_counter()
        interaction_id = f"vox-{uuid.uuid4().hex[:10]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        corr_id = correlation_id or f"corr-{interaction_id}"

        raw_audio: Optional[np.ndarray] = audio_data
        mic_metadata: Dict[str, Any] = {}

        # -------------------------------------------------------------------
        # Step 1: Microphone Capture (if raw audio not explicitly passed in)
        # -------------------------------------------------------------------
        if raw_audio is None:
            try:
                logger.info(f"NIRA checking in with resident [{elderly_id}]: '{question}'")
                raw_audio, mic_metadata = self.microphone.record_phrase(
                    max_duration_sec=max_duration_sec,
                    silence_timeout_sec=silence_timeout_sec,
                    initial_speech_timeout_sec=initial_timeout_sec
                )
            except MicrophoneUnavailableError as mue:
                logger.warning(f"Microphone unavailable during check-in: {mue}")
                return self._build_safety_fallback_result(
                    interaction_id=interaction_id,
                    elderly_id=elderly_id,
                    question=question,
                    status=VoiceInteractionStatus.UNCERTAIN,
                    urgency=VoiceUrgencyLevel.HIGH,
                    reason=f"Microphone unavailable or disconnected: {mue}",
                    action=VoiceAction.REPEAT_CHECK_IN,
                    elapsed_sec=time.perf_counter() - t_start,
                    metadata={"error": "MIC_UNAVAILABLE", "detail": str(mue)}
                )
            except MicrophonePermissionError as mpe:
                logger.error(f"Microphone permission denied: {mpe}")
                return self._build_safety_fallback_result(
                    interaction_id=interaction_id,
                    elderly_id=elderly_id,
                    question=question,
                    status=VoiceInteractionStatus.UNCERTAIN,
                    urgency=VoiceUrgencyLevel.HIGH,
                    reason=f"Microphone permission denied by host operating system: {mpe}",
                    action=VoiceAction.REPEAT_CHECK_IN,
                    elapsed_sec=time.perf_counter() - t_start,
                    metadata={"error": "MIC_PERMISSION_DENIED", "detail": str(mpe)}
                )
            except Exception as e:
                logger.error(f"Unexpected audio recording failure: {e}")
                return self._build_safety_fallback_result(
                    interaction_id=interaction_id,
                    elderly_id=elderly_id,
                    question=question,
                    status=VoiceInteractionStatus.UNCERTAIN,
                    urgency=VoiceUrgencyLevel.HIGH,
                    reason=f"Audio hardware error: {e}",
                    action=VoiceAction.REPEAT_CHECK_IN,
                    elapsed_sec=time.perf_counter() - t_start,
                    metadata={"error": "AUDIO_CAPTURE_EXCEPTION", "detail": str(e)}
                )

        # Handle silence or timeout without speech
        if mic_metadata.get("status") == "TIMEOUT_NO_SPEECH" or (raw_audio is not None and raw_audio.size == 0):
            logger.info(f"Check-in timed out with complete silence for resident [{elderly_id}].")
            return self._build_safety_fallback_result(
                interaction_id=interaction_id,
                elderly_id=elderly_id,
                question=question,
                status=VoiceInteractionStatus.UNCERTAIN,
                urgency=VoiceUrgencyLevel.HIGH,
                reason="Resident remained completely silent following verbal prompt; no speech detected.",
                action=VoiceAction.REPEAT_CHECK_IN,
                elapsed_sec=time.perf_counter() - t_start,
                metadata=mic_metadata
            )

        # -------------------------------------------------------------------
        # Step 2: Audio Preprocessing & Validation
        # -------------------------------------------------------------------
        processed_audio, is_valid, prep_reason = AudioPreprocessor.preprocess(
            raw_audio,
            target_sample_rate=TARGET_SAMPLE_RATE
        )

        if not is_valid:
            logger.info(f"Preprocessed audio invalid: {prep_reason}")
            return self._build_safety_fallback_result(
                interaction_id=interaction_id,
                elderly_id=elderly_id,
                question=question,
                status=VoiceInteractionStatus.UNCERTAIN,
                urgency=VoiceUrgencyLevel.MEDIUM,
                reason=f"Audio signal unusable ({prep_reason}).",
                action=VoiceAction.REPEAT_CHECK_IN,
                elapsed_sec=time.perf_counter() - t_start,
                metadata={"preprocessing_reason": prep_reason}
            )

        # -------------------------------------------------------------------
        # Step 3: Whisper Speech-to-Text Transcription
        # -------------------------------------------------------------------
        try:
            trans_result = self.stt.transcribe(processed_audio, language=language)
        except Exception as e:
            logger.error(f"Speech-to-text inference failure: {e}")
            return self._build_safety_fallback_result(
                interaction_id=interaction_id,
                elderly_id=elderly_id,
                question=question,
                status=VoiceInteractionStatus.UNCERTAIN,
                urgency=VoiceUrgencyLevel.HIGH,
                reason=f"Speech-to-text inference failure: {e}",
                action=VoiceAction.REPEAT_CHECK_IN,
                elapsed_sec=time.perf_counter() - t_start,
                metadata={"error": "ASR_FAILURE", "detail": str(e)}
            )

        # -------------------------------------------------------------------
        # Step 4: Clinical Response Analysis
        # -------------------------------------------------------------------
        try:
            analysis = self.analyzer.analyze(trans_result.transcript)
        except Exception as e:
            logger.error(f"Response analyzer failure: {e}")
            # SAFETY FALLBACK: Never silently become SAFE on analyzer failure
            analysis = self.analyzer.analyze_deterministic(trans_result.transcript)

        # -------------------------------------------------------------------
        # Step 5: Construct Structured VoiceInteractionResult
        # -------------------------------------------------------------------
        audio_dur = round(len(processed_audio) / float(TARGET_SAMPLE_RATE), 3)
        total_latency = round(time.perf_counter() - t_start, 3)

        result = VoiceInteractionResult(
            interaction_id=interaction_id,
            elderly_id=elderly_id,
            question=question,
            transcript=trans_result.transcript,
            language=trans_result.language,
            translated_transcript=None,
            status=analysis.status,
            urgency=analysis.urgency,
            reason=analysis.reason,
            action=analysis.action,
            model=trans_result.model,
            timestamp=now_iso,
            duration_sec=audio_dur,
            processing_time_sec=total_latency,
            transcription_quality=trans_result.transcription_quality,
            metadata={
                "mic": mic_metadata,
                "asr_metrics": trans_result.metrics,
                "is_negated": analysis.is_negated,
                "is_mixed": analysis.is_mixed,
                "correlation_id": corr_id,
                "room_id": room_id
            }
        )

        # -------------------------------------------------------------------
        # Step 6: Database Logging & Event Streaming
        # -------------------------------------------------------------------
        try:
            self.storage.log_interaction(result, room_id=room_id)
        except Exception as e:
            logger.warning(f"Could not persist voice interaction to database: {e}")

        # Stream event into live event pipeline if available
        if self.live_stream:
            try:
                if build_live_event:
                    evt = build_live_event(
                        event_type=f"voice_check_in_{result.status.value.lower()}",
                        source="live_voice",
                        zone=room_id,
                        confidence=1.0,
                        correlation_id=corr_id,
                        resident_id=elderly_id,
                        payload={
                            "transcript": result.transcript,
                            "safety_state": result.status.value,
                            "urgency": result.urgency.value,
                            "reason": result.reason,
                            "action": result.action.value,
                            "interaction_id": result.interaction_id,
                            "is_negated": analysis.is_negated,
                            "is_mixed": analysis.is_mixed
                        },
                        metadata={
                            "model": result.model,
                            "audio_duration_sec": audio_dur,
                            "latency_sec": total_latency
                        }
                    )
                    self.live_stream.publish_event(evt, blocking=False)
                else:
                    self.live_stream.ingest_live_sensor("voice", {
                        "event_type": f"voice_check_in_{result.status.value.lower()}",
                        "confidence": 1.0,
                        "location": room_id,
                        "transcript": result.transcript,
                        "safety_state": result.status.value,
                        "urgency": result.urgency.value,
                        "reason": result.reason,
                        "interaction_id": result.interaction_id
                    })
            except Exception as e:
                logger.debug(f"Event streaming to NIRA pipeline failed: {e}")

        return result

    def _build_safety_fallback_result(
        self,
        interaction_id: str,
        elderly_id: str,
        question: str,
        status: VoiceInteractionStatus,
        urgency: VoiceUrgencyLevel,
        reason: str,
        action: VoiceAction,
        elapsed_sec: float,
        metadata: Dict[str, Any]
    ) -> VoiceInteractionResult:
        """Constructs an UNCERTAIN result safely guaranteeing non-silent degradation."""
        result = VoiceInteractionResult(
            interaction_id=interaction_id,
            elderly_id=elderly_id,
            question=question,
            transcript="",
            language="en",
            status=status,
            urgency=urgency,
            reason=reason,
            action=action,
            model=DEFAULT_MODEL_ID,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_sec=0.0,
            processing_time_sec=round(elapsed_sec, 3),
            transcription_quality="unavailable",
            metadata=metadata
        )
        try:
            self.storage.log_interaction(result)
        except Exception:
            pass

        # Publish voice fallback / sensor health event
        if self.live_stream:
            try:
                if build_live_event:
                    fallback_evt = build_live_event(
                        event_type="voice_check_in_uncertain",
                        source="live_voice",
                        zone=metadata.get("room_id", "living_room"),
                        confidence=0.5,
                        correlation_id=metadata.get("correlation_id"),
                        resident_id=elderly_id,
                        payload={
                            "status": status.value,
                            "reason": reason,
                            "action": action.value,
                            "interaction_id": interaction_id,
                            "metadata": metadata
                        }
                    )
                    self.live_stream.publish_event(fallback_evt, blocking=False)
            except Exception as e:
                logger.debug(f"Failed to stream fallback voice event: {e}")

        return result
