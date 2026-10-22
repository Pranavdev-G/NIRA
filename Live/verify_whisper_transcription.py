"""
Direct Verification of Whisper large-v3-turbo Speech Recognition on Real Audio Files.
Amazon Developer Hackathon 2026.
"""

import os
import sys
import time
import numpy as np

# Ensure path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
for p in [ROOT_DIR, CURRENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from Live.voice.whisper_engine import WhisperSpeechToText, DEFAULT_MODEL_ID, detect_optimal_hardware
from Live.voice.audio import AudioPreprocessor, TARGET_SAMPLE_RATE
from Live.voice.response_analyzer import ResponseAnalyzer
from Live.voice.models import VoiceInteractionStatus

try:
    import soundfile as sf
except ImportError:
    import scipy.io.wavfile as sf_wav
    sf = None


def read_wav_16k(file_path: str) -> np.ndarray:
    if sf:
        audio, sr = sf.read(file_path)
    else:
        sr, audio = sf_wav.read(file_path)
    processed, is_valid, reason = AudioPreprocessor.preprocess(audio, sample_rate=sr, target_sample_rate=TARGET_SAMPLE_RATE)
    if not is_valid:
        raise ValueError(f"Failed to preprocess {file_path}: {reason}")
    return processed


def main():
    print("\n==================================================================")
    print(" [NIRA] VERIFYING REAL WHISPER large-v3-turbo TRANSCRIPTION")
    print(" Model: openai/whisper-large-v3-turbo")
    device, dtype = detect_optimal_hardware()
    print(f" Hardware: {device.upper()} | Precision: {dtype}")
    print("==================================================================\n")

    t0 = time.perf_counter()
    stt = WhisperSpeechToText(model_id=DEFAULT_MODEL_ID, auto_load=True)
    analyzer = ResponseAnalyzer()
    print(f"Model loaded in {time.perf_counter() - t0:.2f}s\n")

    test_cases = [
        ("Live/test_speech_safe.wav", "Safe Confirmation", "Are you okay?"),
        ("Live/test_speech_dizzy.wav", "Dizziness / Risk", "Are you okay?"),
        ("Live/test_speech_emergency.wav", "Emergency Assistance", "Are you okay?"),
        ("Live/test_speech_negated.wav", "Negation (NOT okay)", "Are you okay?"),
        ("Live/test_speech_mixed.wav", "Mixed / Emergency Override", "Are you okay?")
    ]

    all_passed = True
    for wav_path, label, question in test_cases:
        if not os.path.exists(wav_path):
            print(f"[SKIP] {wav_path} not found.")
            continue

        print("------------------------------------------------------------------")
        print(f"TEST CASE: {label}")
        print(f"NIRA: {question}")
        print("Listening...")
        print("Transcribing...")

        audio_16k = read_wav_16k(wav_path)
        t_trans = time.perf_counter()
        res = stt.transcribe(audio_16k)
        trans_time = time.perf_counter() - t_trans

        analysis = analyzer.analyze(res.transcript)

        print(f"\nTranscript:\n\"{res.transcript}\"")
        print(f"\nStatus:\n{analysis.status.value}")
        print(f"\nUrgency:\n{analysis.urgency.value}")
        print(f"\nReason:\n{analysis.reason}")
        print(f"Action: {analysis.action.value}")
        print(f"Latency: {trans_time:.2f}s | Language: {res.language} | Quality: {res.transcription_quality}")

        # Verification asserts
        if "Safe" in label and analysis.status != VoiceInteractionStatus.SAFE:
            all_passed = False
            print("[FAIL] Expected SAFE status")
        elif "Risk" in label and analysis.status != VoiceInteractionStatus.RISK:
            all_passed = False
            print("[FAIL] Expected RISK status")
        elif "Emergency" in label and analysis.status != VoiceInteractionStatus.EMERGENCY:
            all_passed = False
            print("[FAIL] Expected EMERGENCY status")
        elif "Negation" in label and analysis.status == VoiceInteractionStatus.SAFE:
            all_passed = False
            print("[FAIL] Critical violation: Negation became SAFE!")
        else:
            print("[VERIFIED SUCCESS]")

    print("\n==================================================================")
    if all_passed:
        print(" ALL REAL WHISPER large-v3-turbo INFERENCE TESTS PASSED!")
    else:
        print(" SOME INFERENCE TESTS FAILED.")
    print("==================================================================\n")


if __name__ == "__main__":
    main()
