"""
Controlled Microphone Audio Capture for NIRA Live Voice Interaction.
Amazon Developer Hackathon 2026.
"""

import time
import logging
import threading
from typing import Optional, Tuple, Dict, Any, List
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from .audio import AudioPreprocessor, TARGET_SAMPLE_RATE

logger = logging.getLogger("NIRA.LiveMicrophone")


class MicrophoneCaptureError(Exception):
    """Base exception for microphone errors."""
    pass


class MicrophoneUnavailableError(MicrophoneCaptureError):
    """Raised when no operational audio input device is found."""
    pass


class MicrophonePermissionError(MicrophoneCaptureError):
    """Raised when access to the audio input device is denied."""
    pass


class MicrophoneCapture:
    """
    Manages controlled, on-demand microphone capture for senior check-in interactions.
    Does NOT permanently record the resident; records strictly upon request until silence or timeout.
    """

    def __init__(
        self,
        sample_rate: int = TARGET_SAMPLE_RATE,
        device_index: Optional[int] = None,
        channels: int = 1
    ):
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.channels = channels
        self._is_recording = False
        self._stop_requested = threading.Event()

    @classmethod
    def is_available(cls) -> bool:
        """Checks if sounddevice is installed and an input device exists."""
        if sd is None:
            return False
        try:
            devices = sd.query_devices()
            input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
            return len(input_devices) > 0
        except Exception as e:
            logger.warning(f"Error querying audio devices: {e}")
            return False

    @classmethod
    def list_input_devices(cls) -> List[Dict[str, Any]]:
        """Lists all physical and virtual audio input devices."""
        if sd is None:
            return []
        try:
            devices = sd.query_devices()
            inputs = []
            for idx, d in enumerate(devices):
                if d.get("max_input_channels", 0) > 0:
                    inputs.append({
                        "index": idx,
                        "name": d.get("name"),
                        "channels": d.get("max_input_channels"),
                        "default_samplerate": d.get("default_samplerate"),
                        "is_default": idx == sd.default.device[0]
                    })
            return inputs
        except Exception as e:
            logger.error(f"Failed to list input devices: {e}")
            return []

    @classmethod
    def get_default_device_info(cls) -> Optional[Dict[str, Any]]:
        """Returns metadata for the default system audio input device."""
        if sd is None:
            return None
        try:
            def_idx = sd.default.device[0]
            if def_idx is not None and def_idx >= 0:
                dev = sd.query_devices(def_idx)
                return {
                    "index": def_idx,
                    "name": dev.get("name"),
                    "channels": dev.get("max_input_channels"),
                    "sample_rate": dev.get("default_samplerate")
                }
        except Exception:
            pass
        return None

    def abort(self):
        """Signals active recording session to abort immediately."""
        self._stop_requested.set()

    def record_phrase(
        self,
        max_duration_sec: float = 12.0,
        silence_timeout_sec: float = 2.2,
        initial_speech_timeout_sec: float = 5.0,
        energy_threshold: float = 0.015,
        block_size_ms: int = 50
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Controlled conversational recording turn:
          1. Activates microphone
          2. Waits up to `initial_speech_timeout_sec` for user to begin speaking
          3. Once speech detected, records until `silence_timeout_sec` of silence or `max_duration_sec`
          4. Immediately disengages microphone
        Returns:
          (audio_numpy_float32, metadata_dict)
        """
        if sd is None:
            raise MicrophoneUnavailableError("sounddevice library is not installed or available.")

        if not self.is_available():
            raise MicrophoneUnavailableError("No active microphone or audio input hardware detected.")

        self._stop_requested.clear()
        self._is_recording = True

        block_size = int(self.sample_rate * (block_size_ms / 1000.0))
        collected_blocks: List[np.ndarray] = []

        speech_started = False
        speech_start_time: Optional[float] = None
        silence_start_time: Optional[float] = None
        start_time = time.perf_counter()

        capture_status = "OK"
        peak_energy = 0.0

        def audio_callback(indata, frames, time_info, status):
            nonlocal peak_energy
            if status:
                logger.debug(f"Audio stream status: {status}")
            # indata shape: [frames, channels]
            frame_mono = indata[:, 0].copy() if indata.ndim > 1 else indata.copy()
            collected_blocks.append(frame_mono)

            frame_rms = AudioPreprocessor.calculate_rms(frame_mono)
            if frame_rms > peak_energy:
                peak_energy = frame_rms

        try:
            # Open stream
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=block_size,
                device=self.device_index,
                callback=audio_callback
            ):
                while True:
                    now = time.perf_counter()
                    elapsed = now - start_time

                    if self._stop_requested.is_set():
                        capture_status = "ABORTED"
                        break

                    # Check current audio blocks for speech onset and silence
                    if len(collected_blocks) > 0:
                        recent_block = collected_blocks[-1]
                        current_rms = AudioPreprocessor.calculate_rms(recent_block)

                        if not speech_started:
                            if current_rms >= energy_threshold:
                                speech_started = True
                                speech_start_time = now
                                silence_start_time = None
                                logger.info("User speech onset detected.")
                            elif elapsed > initial_speech_timeout_sec:
                                capture_status = "TIMEOUT_NO_SPEECH"
                                logger.info(f"Initial speech timeout ({initial_speech_timeout_sec}s) reached without speech.")
                                break
                        else:
                            # Speech was already active; monitor for subsequent silence
                            if current_rms < energy_threshold:
                                if silence_start_time is None:
                                    silence_start_time = now
                                elif (now - silence_start_time) >= silence_timeout_sec:
                                    capture_status = "SILENCE_DETECTED"
                                    logger.info(f"End of speech detected after {silence_timeout_sec}s of silence.")
                                    break
                            else:
                                silence_start_time = None  # Reset silence timer on new utterance

                    if elapsed >= max_duration_sec:
                        capture_status = "MAX_DURATION_REACHED"
                        logger.info(f"Max recording window ({max_duration_sec}s) reached.")
                        break

                    time.sleep(0.04)

        except sd.PortAudioError as pae:
            err_msg = str(pae).lower()
            if "permission" in err_msg or "access" in err_msg:
                raise MicrophonePermissionError(f"Microphone permission denied: {pae}")
            raise MicrophoneUnavailableError(f"Microphone PortAudio failure: {pae}")
        except Exception as e:
            logger.error(f"Unexpected audio recording exception: {e}")
            raise MicrophoneCaptureError(f"Recording error: {e}")
        finally:
            self._is_recording = False

        total_elapsed = time.perf_counter() - start_time

        if collected_blocks:
            full_audio = np.concatenate(collected_blocks, axis=0)
        else:
            full_audio = np.array([], dtype=np.float32)

        meta = {
            "status": capture_status,
            "duration_sec": round(len(full_audio) / float(self.sample_rate), 3),
            "elapsed_sec": round(total_elapsed, 3),
            "speech_detected": speech_started,
            "peak_rms": round(peak_energy, 5),
            "sample_rate": self.sample_rate,
            "device": self.device_index if self.device_index is not None else "default"
        }

        return full_audio, meta
