"""
Audio Preprocessing and Signal Conditioning for NIRA Speech Interaction.
Amazon Developer Hackathon 2026.
"""

import math
import logging
from typing import Tuple, Optional, Union
import numpy as np

try:
    from scipy import signal
except ImportError:
    signal = None

logger = logging.getLogger("NIRA.LiveAudio")

TARGET_SAMPLE_RATE = 16000  # Whisper requires 16,000 Hz single-channel audio


class AudioPreprocessor:
    """
    Standardizes, validates, and normalizes audio data before Whisper transcription.
    Preserves speaker voice characteristics without destructive modifications.
    """

    @staticmethod
    def ensure_mono(audio: np.ndarray) -> np.ndarray:
        """
        Converts multi-channel (stereo) audio to single-channel (mono) by averaging channels.
        """
        if audio is None or audio.size == 0:
            return np.array([], dtype=np.float32)

        if audio.ndim == 1:
            return audio.astype(np.float32, copy=False)
        elif audio.ndim == 2:
            # Average across channels (shape: [samples, channels] or [channels, samples])
            if audio.shape[1] <= 4:
                return np.mean(audio, axis=1).astype(np.float32)
            else:
                return np.mean(audio, axis=0).astype(np.float32)
        else:
            flat = audio.reshape(-1, audio.shape[-1])
            return np.mean(flat, axis=-1).astype(np.float32)

    @staticmethod
    def convert_to_float32(audio: np.ndarray) -> np.ndarray:
        """
        Converts integer PCM audio (int16, int32) or float64 to float32 normalized in [-1.0, 1.0].
        """
        if audio is None or audio.size == 0:
            return np.array([], dtype=np.float32)

        if np.issubdtype(audio.dtype, np.floating):
            audio_f = audio.astype(np.float32, copy=False)
        elif audio.dtype == np.int16:
            audio_f = audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            audio_f = audio.astype(np.float32) / 2147483648.0
        elif audio.dtype == np.uint8:
            audio_f = (audio.astype(np.float32) - 128.0) / 128.0
        else:
            audio_f = audio.astype(np.float32)

        # Replace NaNs and Infs with 0.0
        if not np.isfinite(audio_f).all():
            audio_f = np.nan_to_num(audio_f, nan=0.0, posinf=1.0, neginf=-1.0)

        return audio_f

    @staticmethod
    def resample(audio: np.ndarray, orig_sr: int, target_sr: int = TARGET_SAMPLE_RATE) -> np.ndarray:
        """
        Resamples audio from orig_sr to target_sr using polyphase filtering or linear interpolation.
        """
        if audio is None or audio.size == 0:
            return np.array([], dtype=np.float32)

        if orig_sr == target_sr:
            return audio.astype(np.float32, copy=False)

        num_target_samples = int(round(len(audio) * float(target_sr) / float(orig_sr)))
        if num_target_samples <= 0:
            return np.array([], dtype=np.float32)

        if signal and hasattr(signal, "resample_poly"):
            gcd = math.gcd(orig_sr, target_sr)
            up = target_sr // gcd
            down = orig_sr // gcd
            resampled = signal.resample_poly(audio, up, down).astype(np.float32)
        elif signal and hasattr(signal, "resample"):
            resampled = signal.resample(audio, num_target_samples).astype(np.float32)
        else:
            # Fallback linear interpolation
            orig_indices = np.linspace(0, len(audio) - 1, num=len(audio))
            target_indices = np.linspace(0, len(audio) - 1, num=num_target_samples)
            resampled = np.interp(target_indices, orig_indices, audio).astype(np.float32)

        return resampled

    @staticmethod
    def remove_dc_offset(audio: np.ndarray) -> np.ndarray:
        """
        Removes DC offset bias by subtracting the mean of the signal.
        """
        if audio.size == 0:
            return audio
        mean_val = float(np.mean(audio))
        return audio - mean_val

    @staticmethod
    def normalize_peak(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
        """
        Applies gentle peak normalization to avoid clipping while preserving speech dynamics.
        If audio is silence or nearly zero, leaves it unchanged.
        """
        if audio.size == 0:
            return audio

        peak = float(np.max(np.abs(audio)))
        if peak > 1e-4:
            scale = target_peak / peak
            # Only amplify if peak is small, or attenuate if clipping (> 1.0)
            if peak > 1.0 or scale < 3.0:
                return np.clip(audio * min(scale, 2.5), -1.0, 1.0).astype(np.float32)

        return np.clip(audio, -1.0, 1.0).astype(np.float32)

    @classmethod
    def preprocess(
        cls,
        audio: np.ndarray,
        sample_rate: int = TARGET_SAMPLE_RATE,
        min_duration_sec: float = 0.25,
        target_sample_rate: int = TARGET_SAMPLE_RATE
    ) -> Tuple[np.ndarray, bool, str]:
        """
        Full preprocessing pipeline for Whisper speech recognition.
        Returns:
            (processed_audio_16khz_mono, is_valid, reason)
        """
        if audio is None or audio.size == 0:
            return np.array([], dtype=np.float32), False, "Empty audio buffer"

        # 1. Convert to float32 in [-1, 1]
        audio_f = cls.convert_to_float32(audio)

        # 2. Downmix multi-channel to mono
        mono_audio = cls.ensure_mono(audio_f)

        # 3. Resample to 16 kHz if necessary
        if sample_rate != target_sample_rate:
            mono_audio = cls.resample(mono_audio, sample_rate, target_sample_rate)

        # 4. Check duration
        duration_sec = len(mono_audio) / float(target_sample_rate)
        if duration_sec < min_duration_sec:
            return mono_audio, False, f"Audio duration too short ({duration_sec:.2f}s < {min_duration_sec}s)"

        # 5. Remove DC offset
        cleaned = cls.remove_dc_offset(mono_audio)

        # 6. Peak normalize
        normalized = cls.normalize_peak(cleaned)

        return normalized, True, "OK"

    @staticmethod
    def calculate_rms(audio: np.ndarray) -> float:
        """Calculates Root-Mean-Square energy of audio frame."""
        if audio is None or audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio))))

    @staticmethod
    def is_speech_detected(frame: np.ndarray, threshold_rms: float = 0.012) -> bool:
        """Simple energy-based Voice Activity Detection frame check."""
        return AudioPreprocessor.calculate_rms(frame) >= threshold_rms
