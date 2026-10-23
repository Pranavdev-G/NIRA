"""
Continuous Microphone Voice Monitor and Spontaneous Help Engine (Phases 28-36, 53-55).
Amazon Developer Hackathon 2026.

Key Guarantees:
  1. Long-running stream listening whenever LIVE MONITORING = ON (Phase 28).
  2. Does NOT run Whisper on silence: VAD buffers speech before calling ASR (Phase 29).
  3. Seamless transitions between PASSIVE_MONITORING and PRIORITY_WELLNESS_CHECK without restarting mic (Phase 30).
  4. Spontaneous emergency detection: "Help me" triggers immediate Core emergency incident (Phase 31).
  5. Authoritative classification using ResponseAnalyzer (Phase 32).
  6. Audio echo suppression via SYSTEM_SPEECH_ACTIVE flag (Phase 36).
  7. Automatic device recovery without crashing: MIC_OFFLINE -> MIC_RECOVERED (Phase 54).
  8. Room-specific voice association (Phase 55).
  9. Zero persistent raw audio recording by default (Phase 72).
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable
import numpy as np

from Live.core.models import EventType, EventSource, ZoneType
from Live.core.time_provider import get_time_provider
from Live.voice.audio import AudioPreprocessor, TARGET_SAMPLE_RATE
from Live.voice.response_analyzer import ResponseAnalyzer
from Live.voice.models import VoiceInteractionStatus, VoiceUrgencyLevel
from Live.app.config import settings

logger = logging.getLogger("NIRA.LiveVoice.ContinuousMonitor")

try:
    import sounddevice as sd
except ImportError:
    sd = None


class MicrophoneMode:
    PASSIVE_MONITORING = "PASSIVE_MONITORING"
    PRIORITY_WELLNESS_CHECK = "PRIORITY_WELLNESS_CHECK"


class ContinuousMicrophoneMonitor:
    """
    Long-running ambient audio supervisor with local Voice Activity Detection (VAD).
    """

    def __init__(
        self,
        core_service: Optional[Any] = None,
        camera_manager: Optional[Any] = None,
        whisper_transcriber: Optional[Callable[[np.ndarray], Tuple[str, Dict[str, Any]]]] = None,
        sample_rate: int = TARGET_SAMPLE_RATE,
        device_index: Optional[int] = None
    ):
        self.core_service = core_service
        self.camera_manager = camera_manager
        self._whisper_transcriber = whisper_transcriber
        self.sample_rate = sample_rate
        self.device_index = device_index

        self.mode = MicrophoneMode.PASSIVE_MONITORING
        self.system_speech_active: bool = False  # Echo suppression flag (Phase 36)
        self.is_online: bool = False
        self._stop_requested = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._active_incident_id: Optional[str] = None
        self._active_correlation_id: Optional[str] = None

        # VAD Parameters
        self.energy_threshold: float = 0.015
        self.silence_timeout_sec: float = 1.4
        self.min_speech_sec: float = getattr(settings, "VOICE_MIN_SPEECH_SECONDS", 0.5)
        self.max_segment_sec: float = getattr(settings, "VOICE_MAX_SEGMENT_SECONDS", 10.0)

        # Rolling Pre-buffer (300ms) to preserve onset consonants
        self._pre_buffer_blocks: List[np.ndarray] = []
        self._max_pre_buffer_blocks: int = 6  # 6 * 50ms = 300ms

        logger.info("[ContinuousMicrophoneMonitor] Initialized continuous ambient microphone supervisor.")

    def set_system_speech_active(self, active: bool):
        """Notifies VAD whether NIRA TTS vocalization is actively playing (Phase 36)."""
        self.system_speech_active = active
        if active:
            logger.debug("[ContinuousMicrophoneMonitor] Echo suppression: NIRA TTS active.")

    def set_priority_wellness_mode(self, incident_id: str, correlation_id: Optional[str] = None):
        """Switches operating mode to PRIORITY_WELLNESS_CHECK without restarting audio stream (Phase 30)."""
        self.mode = MicrophoneMode.PRIORITY_WELLNESS_CHECK
        self._active_incident_id = incident_id
        self._active_correlation_id = correlation_id
        logger.info(f"[ContinuousMicrophoneMonitor] Switched to PRIORITY_WELLNESS_CHECK for incident {incident_id}")

    def reset_to_passive_mode(self):
        """Returns to passive ambient monitoring mode (Phase 30)."""
        self.mode = MicrophoneMode.PASSIVE_MONITORING
        self._active_incident_id = None
        self._active_correlation_id = None
        logger.debug("[ContinuousMicrophoneMonitor] Returned to PASSIVE_MONITORING mode.")

    def start(self):
        """Launches continuous background listening thread."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            return
        self._stop_requested.clear()
        self._monitor_thread = threading.Thread(target=self._run_loop, daemon=True, name="NIRAMicMonitor")
        self._monitor_thread.start()

    def stop(self):
        """Stops background monitor gracefully."""
        self._stop_requested.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        self.is_online = False

    def _run_loop(self):
        """Main listening loop with auto-recovery on device errors (Phase 54)."""
        retry_delay = getattr(settings, "VOICE_RETRY_SECONDS", 5.0)

        while not self._stop_requested.is_set():
            if sd is None:
                logger.warning("[ContinuousMicrophoneMonitor] sounddevice not available. Mic simulation standby.")
                self.is_online = False
                time.sleep(retry_delay)
                continue

            try:
                self._stream_and_process()
            except Exception as e:
                logger.warning(f"[ContinuousMicrophoneMonitor] Audio stream error: {e}. Emitting MIC_OFFLINE...")
                self.is_online = False
                self._dispatch_mic_event(EventType.MIC_OFFLINE, {"error": str(e)})

                # Auto-retry loop (Phase 54)
                time.sleep(retry_delay)

    def _stream_and_process(self):
        """Opens InputStream once and streams audio blocks through VAD."""
        block_size = int(self.sample_rate * 0.05)  # 50ms blocks
        audio_queue = []
        speech_active = False
        speech_start_time = 0.0
        silence_start_time = 0.0

        def callback(indata, frames, time_info, status):
            if not self.system_speech_active:
                mono = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
                audio_queue.append(mono)

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            device=self.device_index,
            callback=callback
        ):
            self.is_online = True
            logger.info("[ContinuousMicrophoneMonitor] Microphone stream established (ONLINE).")
            self._dispatch_mic_event(EventType.MIC_ONLINE, {"status": "ONLINE"})

            speech_blocks: List[np.ndarray] = []

            while not self._stop_requested.is_set():
                if not audio_queue:
                    time.sleep(0.02)
                    continue

                chunk = audio_queue.pop(0)
                now = get_time_provider().time()
                rms = AudioPreprocessor.calculate_rms(chunk)

                # Maintain rolling pre-buffer
                self._pre_buffer_blocks.append(chunk)
                if len(self._pre_buffer_blocks) > self._max_pre_buffer_blocks:
                    self._pre_buffer_blocks.pop(0)

                # VAD: Check for speech onset
                if not speech_active:
                    if rms >= self.energy_threshold:
                        speech_active = True
                        speech_start_time = now
                        silence_start_time = 0.0
                        speech_blocks = list(self._pre_buffer_blocks)
                        logger.info("[ContinuousMicrophoneMonitor] Speech onset detected by VAD.")
                else:
                    # Speech in progress
                    speech_blocks.append(chunk)
                    elapsed = now - speech_start_time

                    if rms < self.energy_threshold:
                        if silence_start_time == 0.0:
                            silence_start_time = now
                        elif (now - silence_start_time) >= self.silence_timeout_sec:
                            # Speech completed!
                            logger.info(f"[ContinuousMicrophoneMonitor] Speech segment ended ({elapsed:.1f}s).")
                            full_speech = np.concatenate(speech_blocks, axis=0)
                            self._process_completed_speech_segment(full_speech)

                            speech_active = False
                            speech_blocks = []
                            silence_start_time = 0.0
                    else:
                        silence_start_time = 0.0

                    if elapsed >= self.max_segment_sec:
                        # Max segment duration reached
                        full_speech = np.concatenate(speech_blocks, axis=0)
                        self._process_completed_speech_segment(full_speech)
                        speech_active = False
                        speech_blocks = []

    def _process_completed_speech_segment(self, audio: np.ndarray):
        """
        Transcribes speech segment with Whisper and classifies with authoritative ResponseAnalyzer.
        NEVER runs on silence (Phase 29).
        """
        duration_sec = len(audio) / float(self.sample_rate)
        if duration_sec < self.min_speech_sec:
            logger.debug(f"[ContinuousMicrophoneMonitor] Ignoring sub-second click/pop ({duration_sec:.2f}s).")
            return

        # 1. Transcribe with Whisper (Phase 53)
        transcript = ""
        whisper_meta = {}
        if self._whisper_transcriber is not None:
            try:
                transcript, whisper_meta = self._whisper_transcriber(audio)
            except Exception as e:
                logger.error(f"[ContinuousMicrophoneMonitor] Whisper transcription exception: {e}")
        else:
            try:
                from Live.voice.service import get_voice_service
                svc = get_voice_service()
                res = svc.whisper_engine.transcribe_audio(audio, sample_rate=self.sample_rate)
                transcript = res.get("text", "")
                whisper_meta = res
            except Exception as e:
                logger.warning(f"[ContinuousMicrophoneMonitor] Whisper engine fallback note: {e}")

        clean_text = transcript.strip()
        if not clean_text:
            logger.info("[ContinuousMicrophoneMonitor] Speech segment produced empty transcript.")
            return

        logger.info(f"[ContinuousMicrophoneMonitor] Spoken input transcribed: '{clean_text}'")

        # 2. Authoritative Classification using ResponseAnalyzer (Phase 32)
        analysis = ResponseAnalyzer.analyze_response(clean_text)

        # 3. Associate with most probable current room (Phase 55)
        associated_room = ZoneType.UNKNOWN
        if self.camera_manager:
            associated_room = self.camera_manager.current_resident_room
        elif self.core_service:
            associated_room = self.core_service._current_zone

        # 4. Handle based on mode
        if self.mode == MicrophoneMode.PRIORITY_WELLNESS_CHECK:
            # Wellness reply correlation
            if self.core_service:
                self.core_service.process_wellness_response(
                    response_text=clean_text,
                    incident_id=self._active_incident_id,
                    duration_sec=duration_sec
                )
            self.reset_to_passive_mode()
        else:
            # PASSIVE_MONITORING (Phase 31: Spontaneous Help at Any Time)
            self._handle_passive_utterance(clean_text, analysis, associated_room, duration_sec)

    def _handle_passive_utterance(
        self,
        transcript: str,
        analysis: Any,
        room: ZoneType,
        duration_sec: float
    ):
        """
        Processes spontaneous speech in passive mode (Phase 31).
        If resident says "Help me" / EMERGENCY: creates incident & emergency workflow immediately!
        """
        is_emergency = (analysis.status == VoiceInteractionStatus.EMERGENCY)
        is_risk = (analysis.status == VoiceInteractionStatus.RISK)

        logger.info(
            f"[ContinuousMicrophoneMonitor] Passive speech classified: {analysis.status.value} "
            f"(Urgency: {analysis.urgency.value}, Negated: {analysis.is_negated})"
        )

        if not self.core_service:
            return

        if is_emergency:
            # Immediate Emergency Voice Event (Phase 31)
            raw_event = {
                "event_type": EventType.VOICE_HELP_REQUEST.value,
                "source": EventSource.CONTINUOUS_MIC.value,
                "confidence": 0.98,
                "timestamp": get_time_provider().now_iso(),
                "location": {"zone": room.value},
                "payload": {
                    "transcript": transcript,
                    "classification": "EMERGENCY",
                    "reason": analysis.reason,
                    "action": analysis.action.value,
                    "spontaneous": True,
                    "duration_sec": round(duration_sec, 2)
                }
            }
            logger.warning(f"[ContinuousMicrophoneMonitor] SPONTANEOUS HELP DETECTED: '{transcript}'! Ingesting to Core.")
            self.core_service.ingest_event(raw_event)

        elif is_risk:
            # Spontaneous mild distress (e.g. "I'm dizzy")
            raw_event = {
                "event_type": EventType.VOICE_AMBIENT_DISTRESS.value,
                "source": EventSource.CONTINUOUS_MIC.value,
                "confidence": 0.88,
                "timestamp": get_time_provider().now_iso(),
                "location": {"zone": room.value},
                "payload": {
                    "transcript": transcript,
                    "classification": "RISK",
                    "reason": analysis.reason,
                    "spontaneous": True,
                    "duration_sec": round(duration_sec, 2)
                }
            }
            self.core_service.ingest_event(raw_event)

    def _dispatch_mic_event(self, event_type: EventType, payload: Dict[str, Any]):
        """Dispatches microphone health events into CoreService."""
        if self.core_service and hasattr(self.core_service, "ingest_event"):
            raw = {
                "event_type": event_type.value,
                "source": EventSource.CONTINUOUS_MIC.value,
                "timestamp": get_time_provider().now_iso(),
                "confidence": 1.0,
                "location": {"zone": ZoneType.UNKNOWN.value},
                "payload": payload
            }
            try:
                self.core_service.ingest_event(raw)
            except Exception as e:
                logger.error(f"[ContinuousMicrophoneMonitor] Core mic event error: {e}")

    # Synchronous simulation helper for unit testing (Phase 66)
    def simulate_speech_utterance(self, transcript: str, room: Optional[ZoneType] = None):
        """Simulates speech input directly into the VAD pipeline for tests without sound hardware."""
        analysis = ResponseAnalyzer.analyze_response(transcript)
        target_room = room or (self.camera_manager.current_resident_room if self.camera_manager else ZoneType.LIVING_ROOM)
        if self.mode == MicrophoneMode.PRIORITY_WELLNESS_CHECK:
            if self.core_service:
                self.core_service.process_wellness_response(
                    response_text=transcript,
                    incident_id=self._active_incident_id,
                    duration_sec=2.0
                )
            self.reset_to_passive_mode()
        else:
            self._handle_passive_utterance(transcript, analysis, target_room, 2.0)


# Global singleton
_continuous_monitor: Optional[ContinuousMicrophoneMonitor] = None


def get_continuous_mic_monitor(core_service: Optional[Any] = None, camera_manager: Optional[Any] = None) -> ContinuousMicrophoneMonitor:
    global _continuous_monitor
    if _continuous_monitor is None:
        _continuous_monitor = ContinuousMicrophoneMonitor(core_service=core_service, camera_manager=camera_manager)
    else:
        if core_service and _continuous_monitor.core_service is None:
            _continuous_monitor.core_service = core_service
        if camera_manager and _continuous_monitor.camera_manager is None:
            _continuous_monitor.camera_manager = camera_manager
    return _continuous_monitor
