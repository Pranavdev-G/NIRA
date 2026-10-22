# NIRA Live Speech Interaction Module
**Amazon Developer Hackathon 2026 | Ambient AI Safety Agent Track**

High-accuracy real-time speech interaction and conversational wellness verification system for the NIRA elderly care platform.

---

## 🎙️ Core Objectives & Capabilities

1. **Controlled On-Demand Microphone Capture**: Captures senior resident speech without permanent recording or privacy intrusion. Automatically detects speech onset and terminates upon silence timeout.
2. **Standardized Audio Conditioning**: Resamples audio to 16,000 Hz float32 mono, eliminates DC offsets, applies gentle peak normalization, and filters short noise bursts.
3. **Primary ASR Engine**: Uses **Whisper large-v3-turbo (`openai/whisper-large-v3-turbo`)** loaded once via a singleton lifecycle manager with automatic hardware acceleration detection.
4. **Clinical Response Analyzer**: Evaluates conversational meaning and classifies responses into `SAFE`, `UNCERTAIN`, `RISK`, or `EMERGENCY`.
5. **Strict Negation Handling**: Explicitly prevents phrases like `"I am NOT okay"` or `"I'm not feeling well"` from ever resolving to `SAFE`.
6. **Emergency Priority Hierarchy**: `EMERGENCY > RISK > UNCERTAIN > SAFE`. Contradictory phrases like `"Yes, I'm okay, but I fell down and I can't get up"` immediately trigger `EMERGENCY`.
7. **Safety Fallback Guarantees**: Any transcription failure, ambiguous input, or microphone hardware issue defaults to `UNCERTAIN` (never silently `SAFE`).
8. **Downstream Integration**: Emits clean structured contracts (`VoiceInteractionResult`) and persists records to `aegis_care.db`.

---

## 🏗️ Architecture Pipeline

```text
NIRA Prompt: "Are you okay?"
       ↓
🎙️ Controlled Microphone Capture (sounddevice)
       ↓
Audio Conditioning (16kHz float32 mono, DC filter, peak norm)
       ↓
openai/whisper-large-v3-turbo (Singleton Lifecycle Manager)
       ↓
Verbal Transcript + Authentic ASR Quality Metrics
       ↓
Clinical Response Analyzer (Negation + Priority Engine)
       ↓
Structured Output: VoiceInteractionResult
       ├── SAFE      → Action: LOG_ONLY
       ├── RISK      → Action: CREATE_INCIDENT
       ├── EMERGENCY → Action: ESCALATE_EMERGENCY_CAD
       └── UNCERTAIN → Action: REPEAT_CHECK_IN
       ↓
Persisted to aegis_care.db & Streamed to NIRA Event Pipeline
```

---

## 📂 File Structure

All implementation files remain strictly inside `Live/`:

```text
Live/
│
├── voice/
│   ├── __init__.py                # Module exports
│   ├── models.py                  # Pydantic data contracts & enums
│   ├── audio.py                   # 16kHz mono audio preprocessing & RMS VAD
│   ├── microphone.py              # Controlled on-demand microphone capture
│   ├── speech_to_text.py          # Clean abstract ASR interface
│   ├── whisper_engine.py          # Whisper large-v3-turbo implementation & lifecycle manager
│   ├── response_analyzer.py       # Clinical semantic analyzer with negation handling
│   ├── storage.py                 # SQLite database logging (telemetry_events & audit table)
│   ├── conversation.py            # Multi-turn check-in dialogue manager
│   ├── service.py                 # Central VoiceService coordinator
│   └── test_mic.py                # Standalone CLI microphone test tool
│
├── api/
│   ├── __init__.py
│   └── voice_routes.py            # FastAPI REST endpoints (/api/v1/live/voice/*)
│
├── tests/
│   ├── __init__.py
│   ├── test_speech_to_text.py     # ASR abstraction & engine tests
│   ├── test_response_analyzer.py  # SAFE, RISK, EMERGENCY, NEGATION & Mixed tests
│   ├── test_voice_service.py      # End-to-end integration flow tests
│   └── test_voice_api.py          # FastAPI endpoint tests
│
├── verify_whisper_transcription.py# Real inference test on synthesized audio waveforms
├── generate_test_audio.py         # Audio generator for benchmark test suite
├── .env.example                   # Environment configuration template
└── README.md                      # This documentation
```

---

## 🚀 Quick Start & Installation

### 1. Dependencies
The system utilizes:
- `torch` (PyTorch 2.x)
- `transformers` (Hugging Face)
- `sounddevice` (Audio I/O)
- `scipy` & `numpy` (Signal processing)
- `fastapi` & `pydantic` (Data schemas and REST endpoints)

Install with:
```bash
pip install torch transformers sounddevice soundfile scipy numpy fastapi pydantic pytest
```

### 2. Configuration
Copy the template configuration:
```bash
cp Live/.env.example Live/.env
```

Key environment variables:
- `WHISPER_MODEL_ID`: `openai/whisper-large-v3-turbo` (default)
- `WHISPER_DEVICE`: `auto` (auto-selects CUDA GPU, Apple Silicon MPS, or multi-threaded CPU)
- `MIC_SAMPLE_RATE`: `16000`
- `MIC_MAX_RECORD_SECONDS`: `10.0`
- `MIC_SILENCE_TIMEOUT_SECONDS`: `2.2`
- `DATABASE_URL`: `sqlite:///./aegis_care.db`
- `OPENAI_API_KEY`: (Optional) for secondary LLM semantic evaluation

---

## 🎤 Running the Live Microphone Test

Run the interactive test command in your terminal and speak into your microphone:

```bash
python Live/voice/test_mic.py
```
Or with specific parameters:
```bash
python Live/voice/test_mic.py --question "Are you okay?" --max-duration 10.0 --silence-timeout 2.2
```

To list all detected audio hardware:
```bash
python Live/voice/test_mic.py --list-devices
```

### Example Terminal Output:
```text
==================================================================
 [NIRA] AEGIS AMBIENT CARE — LIVE VOICE INTERACTION SYSTEM
 Amazon Developer Hackathon 2026
==================================================================

[Hardware] Accelerator: CPU | Precision: torch.float32
[Microphone] Status: ACTIVE | Device: Microphone Array (AMD Audio Device)
[ASR Engine] Loading openai/whisper-large-v3-turbo into memory...
[ASR Engine] Model ready (transformers backend)

------------------------------------------------------------------
NIRA: Are you okay?
------------------------------------------------------------------

Listening... (Please speak into your microphone now)

Transcribing...

==================================================================
Transcript:
"I am feeling dizzy."

Status:
RISK

Urgency:
HIGH

Reason:
Resident reported experiencing dizziness (feeling dizzy).

Action:
CREATE_INCIDENT
------------------------------------------------------------------
Metadata:
  • Spoken Language : en
  • Quality Metric  : good
  • Audio Duration  : 2.14s
  • Total Latency   : 14.82s
  • Interaction ID  : vox-686cdc186b
==================================================================
```

---

## 🧪 Automated Test Suite

Run the full 70-test test suite:
```bash
python -m pytest Live/tests/ -v
```

### Verified Test Categories:
- **`test_response_analyzer.py`**:
  - Safe affirmations (`"I'm okay"`, `"Yes, I'm fine"`, `"Everything is alright"`)
  - Risk indicators (`"I'm feeling dizzy"`, `"I feel weak"`, `"I fell down"`)
  - Emergency declarations (`"Help me"`, `"I fell and can't get up"`, `"I can't breathe"`)
  - Critical Negations (`"I am NOT okay"`, `"I'm not feeling well"`, `"No, not alright"` -> **Never SAFE**)
  - Mixed Contradictions (`"Yes, I'm okay, but I fell down and I can't get up"` -> **EMERGENCY**)
  - Ambiguity & Silence (`"I don't know"`, `""`, mumbling -> **UNCERTAIN**)
- **`test_speech_to_text.py`**: Clean abstraction interface, hardware auto-detection, mono downmixing, resampling, silence handling.
- **`test_voice_service.py`**: Complete workflow, risk/emergency/safe handling, database audit persistence.
- **`test_voice_api.py`**: REST endpoints (`/status`, `/analyze`, `/check-in`, `/history`).

---

## 🔬 Benchmark Verification on Real Audio Waveforms

To run real Whisper inference on generated audio waveforms:
```bash
python Live/verify_whisper_transcription.py
```
This tests the actual `openai/whisper-large-v3-turbo` model against 5 real audio files:
1. `test_speech_safe.wav`: "Yes, I am okay." -> `SAFE`
2. `test_speech_dizzy.wav`: "I am feeling dizzy." -> `RISK`
3. `test_speech_emergency.wav`: "Help me. I fell down and cannot get up." -> `EMERGENCY`
4. `test_speech_negated.wav`: "I am not okay." -> `RISK`
5. `test_speech_mixed.wav`: "Yes, I am OK, but I fell down and I cannot get up." -> `EMERGENCY`

---

## 🤝 Clean Integration Contract

Other LIVE system teammates (incident management, caregiver hub, 911 CAD dispatch) interface with `VoiceService` cleanly without tightly coupling audio dependencies:

```python
from Live.voice import VoiceService, VoiceInteractionStatus

voice_service = VoiceService()

# Trigger conversational check-in
result = voice_service.run_check_in(
    elderly_id="user_eleanor_vance",
    question="Are you okay?"
)

# Consume result by safety status
if result.status == VoiceInteractionStatus.EMERGENCY:
    emergency_service.handle(result)

elif result.status == VoiceInteractionStatus.RISK:
    incident_service.create(result)

elif result.status == VoiceInteractionStatus.UNCERTAIN:
    repeat_check_in_timer.schedule(result)
```

---

## ⚡ Hardware Awareness & Known Performance Characteristics

1. **Hardware Acceleration**:
   - **CUDA GPU**: Precision `FP16`. Latency is typically **`250ms – 600ms`**.
   - **Apple Silicon (MPS)**: Precision `FP16`. Latency is typically **`400ms – 900ms`**.
   - **CPU**: Precision `FP32` with automatic thread optimization. Latency is typically **`15s – 30s`** on consumer multi-core CPUs due to the 800M parameter model size.
2. **Model Lifecycle**:
   - The model is loaded **once** into memory via `WhisperModelManager` and kept hot.
   - It is never re-downloaded or re-initialized on subsequent speech turns.
3. **No Fabricated Confidence Numbers**:
   - The system exposes genuine token metrics (`avg_logprob`, `no_speech_prob`, `compression_ratio`) and derives qualitative indicators (`high`, `good`, `low_confidence`, `empty`) rather than fabricating arbitrary percentages.
