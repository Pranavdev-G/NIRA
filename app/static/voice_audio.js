/**
 * Aegis Ambient Care - Voice Notes & Speech Synthesis Engine
 * Amazon Developer Hackathon 2026
 * 
 * Provides native text-to-speech audio for Alexa and Eleanor,
 * realistic Alexa chime sound effects, and voice note player controls.
 */

class VoiceAudioManager {
  constructor() {
    this.synth = (typeof window !== "undefined") ? window.speechSynthesis : null;
    this.isPlaying = false;
    this.audioCtx = null;
    this.currentUtterance = null;
  }

  getAudioContext() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    return this.audioCtx;
  }

  // Ensure AudioContext is resumed before playing notes (fixes suspended context bug)
  ensureAudioRunning(callback) {
    const ctx = this.getAudioContext();
    if (!ctx) return;
    if (ctx.state === "suspended") {
      ctx.resume().then(() => {
        if (callback) callback(ctx);
      }).catch(err => console.warn("AudioContext resume failed:", err));
    } else {
      if (callback) callback(ctx);
    }
  }

  // Alexa Wake & Confirmation Chime (Iconic 3-tone ascending chord: D5, A5, D6)
  playAlexaChime() {
    this.ensureAudioRunning((ctx) => {
      const tones = [587.33, 880.00, 1174.66];
      const startTime = ctx.currentTime + 0.05;

      tones.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, startTime + idx * 0.09);

        gain.gain.setValueAtTime(0.35, startTime + idx * 0.09);
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + idx * 0.09 + 0.22);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(startTime + idx * 0.09);
        osc.stop(startTime + idx * 0.09 + 0.25);
      });
    });
  }

  // Emergency Alert Siren Tone
  playEmergencyTone() {
    this.ensureAudioRunning((ctx) => {
      const startTime = ctx.currentTime + 0.05;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(800, startTime);
      osc.frequency.exponentialRampToValueAtTime(400, startTime + 0.4);

      gain.gain.setValueAtTime(0.30, startTime);
      gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.4);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(startTime + 0.42);
    });
  }

  // Phone Ring Tone (for calling Son David)
  playPhoneRing() {
    this.ensureAudioRunning((ctx) => {
      const startTime = ctx.currentTime + 0.05;
      const osc1 = ctx.createOscillator();
      const osc2 = ctx.createOscillator();
      const gain = ctx.createGain();

      osc1.frequency.setValueAtTime(440, startTime);
      osc2.frequency.setValueAtTime(480, startTime);

      gain.gain.setValueAtTime(0.25, startTime);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.85);

      osc1.connect(gain);
      osc2.connect(gain);
      gain.connect(ctx.destination);

      osc1.start(startTime);
      osc2.start(startTime);
      osc1.stop(startTime + 0.9);
      osc2.stop(startTime + 0.9);
    });
  }

  // Play pre-rendered studio WAV clip with automatic fallback to SpeechSynthesis
  playAudioClip(url, fallbackText = "", role = "alexa", onStart, onEnd) {
    this.ensureAudioRunning();
    this.stop();

    const audio = new Audio(url);
    this.activeAudio = audio;
    audio.volume = 1.0;

    audio.onplay = () => {
      this.isPlaying = true;
      this.setSoundwavesActive(true);
      if (onStart) onStart();
    };

    audio.onended = () => {
      this.isPlaying = false;
      this.setSoundwavesActive(false);
      this.activeAudio = null;
      if (onEnd) onEnd();
    };

    audio.onerror = (e) => {
      console.warn("Audio file error (" + url + "), falling back to SpeechSynthesis:", e);
      this.activeAudio = null;
      if (fallbackText) {
        this.speak(fallbackText, role, onStart, onEnd);
      } else {
        this.isPlaying = false;
        this.setSoundwavesActive(false);
        if (onEnd) onEnd();
      }
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch(err => {
        console.warn("audio.play() error, attempting speech synthesis fallback:", err);
        if (fallbackText) {
          this.speak(fallbackText, role, onStart, onEnd);
        } else {
          if (onEnd) onEnd();
        }
      });
    }
  }

  // Play Scene Narration with real WAV audio files
  playSceneNarration(sceneId, text, role = "alexa", onStart, onEnd) {
    const url = `/static/audio/scene_${sceneId}.wav`;
    this.playAudioClip(url, text, role, onStart, onEnd);
  }

  // Speak voice note using SpeechSynthesis with Chrome/Edge reliability enhancements
  speak(text, role = "alexa", onStart, onEnd) {
    this.ensureAudioRunning();

    if (!window.speechSynthesis) {
      console.warn("SpeechSynthesis not supported on this browser.");
      if (onEnd) onEnd();
      return;
    }

    try {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
      window.speechSynthesis.cancel();
    } catch (e) {
      console.warn("Error resetting speech synthesis:", e);
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.volume = 1.0;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pin utterance to window to prevent Chromium garbage collection bug mid-speech
    window._activeUtterance = utterance;

    const voices = window.speechSynthesis.getVoices() || [];
    if (voices.length > 0) {
      if (role === "alexa") {
        utterance.pitch = 1.15;
        const voice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Zira") || v.name.includes("Samantha") || v.name.includes("Google US English") || v.name.toLowerCase().includes("female")));
        if (voice) utterance.voice = voice;
      } else if (role === "senior") {
        utterance.pitch = 0.92;
        utterance.rate = 0.90;
      } else if (role === "son") {
        utterance.pitch = 1.0;
        utterance.rate = 1.05;
        const voice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("David") || v.name.toLowerCase().includes("male")));
        if (voice) utterance.voice = voice;
      }
    }

    utterance.onstart = () => {
      this.isPlaying = true;
      this.setSoundwavesActive(true);
      if (onStart) onStart();
    };

    utterance.onend = () => {
      this.isPlaying = false;
      this.setSoundwavesActive(false);
      window._activeUtterance = null;
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      console.warn("SpeechSynthesis error:", e);
      this.isPlaying = false;
      this.setSoundwavesActive(false);
      window._activeUtterance = null;
      if (onEnd) onEnd();
    };

    try {
      window.speechSynthesis.speak(utterance);
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    } catch (err) {
      console.warn("speechSynthesis.speak failed:", err);
      if (onEnd) onEnd();
    }
  }

  stop() {
    if (this.activeAudio) {
      try {
        this.activeAudio.pause();
        this.activeAudio.currentTime = 0;
      } catch (e) {}
      this.activeAudio = null;
    }
    if (window.speechSynthesis) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {}
    }
    this.isPlaying = false;
    this.setSoundwavesActive(false);
  }

  setSoundwavesActive(active) {
    const bars = document.querySelectorAll(".soundwave-bar");
    bars.forEach(bar => {
      if (active) {
        bar.style.animationPlayState = "running";
        bar.style.opacity = "1";
      } else {
        bar.style.animationPlayState = "paused";
        bar.style.opacity = "0.5";
      }
    });
  }

  // Interactive Test Audio method
  testAudio() {
    this.playAlexaChime();
    const testPhrase = "Aegis Ambient Care audio system is active. High fidelity voice narration is ready.";
    this.playAudioClip("/static/audio/test_audio.wav", testPhrase, "alexa", () => {
      if (typeof showToast === "function") {
        showToast("🔊 Playing Audio Test: Alexa Chime + High-Fidelity Voice");
      }
    });
  }
}

// Global Voice Manager Instance (Bound to both local scope and window)
const voiceAudio = new VoiceAudioManager();
window.voiceAudio = voiceAudio;

// Prime voices as soon as browser engine populates them
if (typeof window !== "undefined" && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
  };
}

// Helper to play Alexa voice note
function playAlexaVoiceNote() {
  voiceAudio.playAlexaChime();
  const text = document.getElementById("dialogAlexaText")?.textContent || "Eleanor, this is Aegis. I noticed a fall in the bathroom. Are you okay? Please tell me if you need help.";
  voiceAudio.playAudioClip("/static/audio/alexa_checkin.wav", text, "alexa", () => {
    const btn = document.getElementById("btnPlayAlexaVoice");
    if (btn) btn.innerHTML = "🔊 <em>Playing Alexa...</em>";
  }, () => {
    const btn = document.getElementById("btnPlayAlexaVoice");
    if (btn) btn.innerHTML = "▶️ Listen to Alexa Voice Note";
  });
}

// Helper to play Eleanor voice reply
function playSeniorVoiceNote() {
  const scenario = (typeof currentScenario !== "undefined") ? currentScenario : "silent";
  let url = "/static/audio/eleanor_reply.wav";
  let text = "I'm okay, Alexa! I just dropped my glasses.";
  if (scenario === "responsive") {
    url = "/static/audio/eleanor_distress.wav";
    text = "Help me, Alexa! I slipped and hurt my wrist, I can't get up!";
  } else if (scenario === "silent") {
    url = "/static/audio/eleanor_silent.wav";
    text = "No response for twenty seconds. Eleanor is presumed unconscious.";
  }

  voiceAudio.playAudioClip(url, text, "senior", () => {
    const btn = document.getElementById("btnPlaySeniorVoice");
    if (btn) btn.innerHTML = "🔊 <em>Playing Eleanor...</em>";
  }, () => {
    const btn = document.getElementById("btnPlaySeniorVoice");
    if (btn) btn.innerHTML = "▶️ Listen to Eleanor's Voice Reply";
  });
}

// Helper to play Son David's voice memo
function playSonVoiceMemo() {
  voiceAudio.playPhoneRing();
  voiceAudio.playAudioClip("/static/audio/son_memo.wav", "Mom! This is David. Aegis just alerted me on Alexa. I see your heart rate spiked. Are you okay? I'm rushing over right now!", "son", () => {
    if (typeof showToast === "function") {
      showToast("📞 Connected to Son David Vance: <em>\"Mom! I'm on my way!\"</em>");
    }
  });
}
