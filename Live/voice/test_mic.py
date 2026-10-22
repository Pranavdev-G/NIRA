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

# Print initial banner immediately before any module imports
print("\n==================================================================", flush=True)
print(" [NIRA] AEGIS AMBIENT CARE — LIVE VOICE INTERACTION SYSTEM", flush=True)
print(" Amazon Developer Hackathon 2026", flush=True)
print("==================================================================", flush=True)

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


def main():
    parser = argparse.ArgumentParser(description="NIRA Live Voice Interaction - Real Microphone Test")
    parser.add_argument("--question", type=str, default="Are you okay?", help="Check-in prompt question")
    parser.add_argument("--elderly-id", type=str, default="user_eleanor_vance", help="Resident identifier")
    parser.add_argument("--max-duration", type=float, default=10.0, help="Max recording duration (seconds)")
    parser.add_argument("--silence-timeout", type=float, default=2.2, help="Silence timeout after speech (seconds)")
    parser.add_argument("--list-devices", action="store_true", help="List all available audio input devices and exit")
    parser.add_argument("--device", type=int, default=None, help="Audio input device index")
    args = parser.parse_args()

    # Fast path for device listing: Avoid loading heavy ML libraries if only querying hardware
    if args.list_devices:
        from Live.voice.microphone import MicrophoneCapture
        devices = MicrophoneCapture.list_input_devices()
        print("\nAvailable Audio Input Devices:", flush=True)
        for d in devices:
            default_tag = " [DEFAULT]" if d["is_default"] else ""
            print(f"  [{d['index']}] {d['name']} (channels: {d['channels']}, rate: {d['default_samplerate']}Hz){default_tag}", flush=True)
        print("==================================================================\n", flush=True)
        return

    # Step 1: Hardware detection
    print("\n[1/4] Detecting hardware accelerators...", flush=True)
    from Live.voice.whisper_engine import detect_optimal_hardware, DEFAULT_MODEL_ID
    device, dtype = detect_optimal_hardware()
    print(f"      • Hardware: {device.upper()} | Precision: {dtype}", flush=True)

    # Step 2: Check Microphone
    print("[2/4] Checking audio input hardware...", flush=True)
    from Live.voice.microphone import MicrophoneCapture
    mic_available = MicrophoneCapture.is_available()
    default_dev = MicrophoneCapture.get_default_device_info()
    dev_name = default_dev['name'] if default_dev else "None"
    dev_idx = default_dev['index'] if default_dev else -1
    print(f"      • Microphone Status : {'ACTIVE' if mic_available else 'NOT DETECTED'}", flush=True)
    print(f"      • Selected Device   : [{dev_idx}] {dev_name}", flush=True)

    if not mic_available:
        print("\n[ERROR] No active microphone detected on this system.", flush=True)
        print("Please connect a microphone or use an audio input device to run live speech recognition.", flush=True)
        print("==================================================================\n", flush=True)
        return

    # Step 3: Model Initialization
    print(f"[3/4] Initializing {DEFAULT_MODEL_ID} from local cache...", flush=True)
    t_load_start = time.perf_counter()
    from Live.voice.whisper_engine import WhisperSpeechToText
    stt = WhisperSpeechToText(model_id=DEFAULT_MODEL_ID, auto_load=True)
    load_time = time.perf_counter() - t_load_start
    print(f"      • Model Ready in {load_time:.2f}s ({stt.manager.backend} backend)", flush=True)

    # Step 4: Live Check-In Service
    print("[4/4] Starting live check-in interaction...", flush=True)
    from Live.voice.service import VoiceService
    voice_service = VoiceService(stt=stt)

    print("\n------------------------------------------------------------------", flush=True)
    print(f"NIRA: \"{args.question}\"", flush=True)
    print("------------------------------------------------------------------", flush=True)
    print("\n🎙️  LISTENING... (Please speak your answer into your microphone now)", flush=True)
    print("   [Speak normally, e.g. 'I am okay' or 'I feel dizzy'. Recording stops automatically when you finish speaking]\n", flush=True)

    result = voice_service.run_check_in(
        elderly_id=args.elderly_id,
        question=args.question,
        max_duration_sec=args.max_duration,
        silence_timeout_sec=args.silence_timeout
    )

    print("🤖 Transcribing and analyzing speech response...\n", flush=True)
    time.sleep(0.1)

    print("==================================================================", flush=True)
    print(f"Transcript:\n\"{result.transcript}\"", flush=True)
    print(f"\nStatus:\n{result.status.value}", flush=True)
    print(f"\nUrgency:\n{result.urgency.value}", flush=True)
    print(f"\nReason:\n{result.reason}", flush=True)
    print(f"\nAction:\n{result.action.value}", flush=True)
    print("------------------------------------------------------------------", flush=True)
    print(f"Metadata:")
    print(f"  • Spoken Language : {result.language}", flush=True)
    print(f"  • Quality Metric  : {result.transcription_quality}", flush=True)
    print(f"  • Audio Duration  : {result.duration_sec:.2f}s", flush=True)
    print(f"  • Pipeline Latency: {result.processing_time_sec:.2f}s", flush=True)
    print(f"  • Model Used      : {result.model}", flush=True)
    print(f"  • Interaction ID  : {result.interaction_id}", flush=True)
    print("==================================================================\n", flush=True)


if __name__ == "__main__":
    main()
