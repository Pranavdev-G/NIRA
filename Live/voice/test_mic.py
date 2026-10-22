"""
Interactive Real Microphone Test for NIRA Live Speech Interaction.
Amazon Developer Hackathon 2026.

Run with:
    python Live/voice/test_mic.py
or:
    python -m Live.voice.test_mic
"""

import sys
import os
import time
import argparse

# Ensure parent path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LIVE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
ROOT_DIR = os.path.abspath(os.path.join(LIVE_DIR, ".."))

for p in [ROOT_DIR, LIVE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from Live.voice.whisper_engine import WhisperSpeechToText, detect_optimal_hardware, DEFAULT_MODEL_ID
from Live.voice.microphone import MicrophoneCapture
from Live.voice.response_analyzer import ResponseAnalyzer
from Live.voice.service import VoiceService
from Live.voice.models import VoiceInteractionStatus


def main():
    parser = argparse.ArgumentParser(description="NIRA Live Voice Interaction - Real Microphone Test")
    parser.add_argument("--question", type=str, default="Are you okay?", help="Check-in prompt question")
    parser.add_argument("--elderly-id", type=str, default="user_eleanor_vance", help="Resident identifier")
    parser.add_argument("--max-duration", type=float, default=10.0, help="Max recording duration (seconds)")
    parser.add_argument("--silence-timeout", type=float, default=2.2, help="Silence timeout after speech (seconds)")
    parser.add_argument("--list-devices", action="store_true", help="List all available audio input devices and exit")
    parser.add_argument("--device", type=int, default=None, help="Audio input device index")
    args = parser.parse_args()

    print("\n==================================================================")
    print(" [NIRA] AEGIS AMBIENT CARE — LIVE VOICE INTERACTION SYSTEM")
    print(" Amazon Developer Hackathon 2026")
    print("==================================================================")

    if args.list_devices:
        devices = MicrophoneCapture.list_input_devices()
        print("\nAvailable Audio Input Devices:")
        for d in devices:
            default_tag = " [DEFAULT]" if d["is_default"] else ""
            print(f"  [{d['index']}] {d['name']} (channels: {d['channels']}, rate: {d['default_samplerate']}Hz){default_tag}")
        return

    # 1. Hardware Detection
    device, dtype = detect_optimal_hardware()
    print(f"\n[Hardware] Accelerator: {device.upper()} | Precision: {dtype}")

    # 2. Check Microphone
    mic_available = MicrophoneCapture.is_available()
    default_dev = MicrophoneCapture.get_default_device_info()
    dev_name = default_dev['name'] if default_dev else "None"
    print(f"[Microphone] Status: {'ACTIVE' if mic_available else 'NOT DETECTED'} | Device: {dev_name}")

    if not mic_available:
        print("\n[ERROR] No active microphone detected on this system.")
        print("Please connect a microphone or use an audio input device to run live speech recognition.")
        return

    # 3. Model Initialization (Singleton load)
    print(f"[ASR Engine] Loading {DEFAULT_MODEL_ID} into memory...")
    t_load_start = time.perf_counter()
    stt = WhisperSpeechToText(model_id=DEFAULT_MODEL_ID, auto_load=True)
    load_time = time.perf_counter() - t_load_start
    print(f"[ASR Engine] Model ready in {load_time:.2f}s ({stt.manager.backend} backend)")

    # 4. Service Setup
    voice_service = VoiceService(stt=stt)

    # 5. Live Speech Interaction Turn
    print("\n------------------------------------------------------------------")
    print(f"NIRA: {args.question}")
    print("------------------------------------------------------------------")
    print("\nListening... (Please speak into your microphone now)")

    result = voice_service.run_check_in(
        elderly_id=args.elderly_id,
        question=args.question,
        max_duration_sec=args.max_duration,
        silence_timeout_sec=args.silence_timeout
    )

    print("\nTranscribing...")
    time.sleep(0.1)

    print("\n==================================================================")
    print(f"Transcript:\n\"{result.transcript}\"")
    print(f"\nStatus:\n{result.status.value}")
    print(f"\nUrgency:\n{result.urgency.value}")
    print(f"\nReason:\n{result.reason}")
    print(f"\nAction:\n{result.action.value}")
    print("------------------------------------------------------------------")
    print(f"Metadata:")
    print(f"  • Spoken Language : {result.language}")
    print(f"  • Quality Metric  : {result.transcription_quality}")
    print(f"  • Audio Duration  : {result.duration_sec:.2f}s")
    print(f"  • Total Latency   : {result.processing_time_sec:.2f}s")
    print(f"  • Interaction ID  : {result.interaction_id}")
    print("==================================================================\n")


if __name__ == "__main__":
    main()
