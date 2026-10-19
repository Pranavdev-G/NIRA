/**
 * Aegis Ambient Care - Intuitive & User-Friendly Story Dashboard
 * Amazon Developer Hackathon 2026
 * 
 * Provides instant 1-click interactive scenarios and clear step-by-step
 * storytelling that anyone can understand immediately.
 */

// Global State
let currentScenario = "silent";
let isPlayingAnimation = false;

// Audio Chime Generator via Web Audio API (Zero external assets needed)
function playChime(type = "info") {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    let freq = 520;
    let dur = 0.25;

    if (type === "success") {
      freq = 659.25; // E5
      dur = 0.35;
    } else if (type === "warning") {
      freq = 440; // A4
      dur = 0.3;
    } else if (type === "alert") {
      freq = 880; // A5
      dur = 0.4;
    }

    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    if (type === "success") {
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + dur);
    } else if (type === "alert") {
      osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + dur);
    }

    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + dur);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + dur);
  } catch (e) {
    // Audio context may be restricted by browser until user gesture
  }
}

// Toast Notifications
function showToast(message) {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = "toast-pill";
  toast.innerHTML = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "all 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ---------------------------------------------------------------------------
// Scenario Data Model
// ---------------------------------------------------------------------------
const SCENARIOS = {
  false_alarm: {
    key: "false_alarm",
    badgeText: "🟢 ALL CLEAR & SAFE",
    room: "living",
    roomName: "🛋️ Living Room",
    floorplanSub: "Location: Living Room (Reading chair)",
    vitals: {
      hr: "72 BPM",
      hrSub: "Normal resting rhythm",
      hrColor: "var(--neon-green)",
      move: "Active",
      moveSub: "Normal posture & motion",
      moveColor: "var(--neon-green)"
    },
    door: {
      icon: "🔒",
      title: "Front Door Smart Lock: SECURELY LOCKED",
      sub: "Home is safe. Eleanor is resting comfortably.",
      color: "var(--neon-green)"
    },
    dialog: {
      alexa: '"Eleanor, this is Aegis. I noticed a sudden motion in the living room. Are you okay?"',
      senior: '<strong>"I\'m okay, Alexa! I just dropped my reading glasses."</strong>',
      seniorQuote: '"I\'m okay, Alexa! I just dropped my reading glasses."'
    },
    outcomes: {
      sarahTitle: "Son David Vance (Admin)",
      sarahDesc: "🟢 Notification: False alarm confirmed by Eleanor",
      sarahBorder: "rgba(16, 185, 129, 0.4)",
      emsTitle: "Boston EMS 911 Dispatch",
      emsDesc: "⚪ Standby &bull; No dispatch required",
      emsBorder: "rgba(255, 255, 255, 0.08)"
    }
  },

  responsive: {
    key: "responsive",
    badgeText: "🟡 CAREGIVER ASSIST",
    room: "kitchen",
    roomName: "🍳 Kitchen",
    floorplanSub: "Location: Kitchen (Near breakfast bar)",
    vitals: {
      hr: "104 BPM",
      hrSub: "Elevated (Distress)",
      hrColor: "var(--neon-amber)",
      move: "Sitting",
      moveSub: "Low movement near floor",
      moveColor: "var(--neon-amber)"
    },
    door: {
      icon: "🔒",
      title: "Front Door Smart Lock: LOCKED (Son has PIN)",
      sub: "Son David notified. Smart lock ready to auto-unlock on arrival.",
      color: "var(--neon-amber)"
    },
    dialog: {
      alexa: '"Eleanor, this is Aegis. I noticed a fall in the kitchen. Are you okay? Please tell me if you need help."',
      senior: '<strong>"Help me, Alexa! I slipped and hurt my wrist, I can\'t get up!"</strong>',
      seniorQuote: '"Help me, Alexa! I slipped and hurt my wrist, I can\'t get up!"'
    },
    outcomes: {
      sarahTitle: "Son David Vance (Admin)",
      sarahDesc: "📱 Echo Drop-In Connected & Live Voice Audio",
      sarahBorder: "rgba(245, 158, 11, 0.5)",
      emsTitle: "Boston EMS 911 Dispatch",
      emsDesc: "🟡 Standby &bull; Family caregiver attending call",
      emsBorder: "rgba(245, 158, 11, 0.2)"
    }
  },

  silent: {
    key: "silent",
    badgeText: "🔴 EMERGENCY DISPATCH ACTIVE",
    room: "bathroom",
    roomName: "🚿 Bathroom",
    floorplanSub: "Location: Bathroom (Wet tile floor)",
    vitals: {
      hr: "138 BPM",
      hrSub: "Acute tachycardia (Shock/Trauma)",
      hrColor: "var(--neon-red)",
      move: "None",
      moveSub: "Motionless on floor",
      moveColor: "var(--neon-red)"
    },
    door: {
      icon: "🔓",
      title: "Front Door Smart Lock: UNLOCKED FOR 911",
      sub: "Auto-unlocked for Boston EMS First Responders (PIN: 8492)",
      color: "var(--neon-red)"
    },
    dialog: {
      alexa: '"Eleanor, this is Aegis. I noticed a fall in the bathroom. Are you okay? Please tell me if you need help."',
      senior: '<em>&lt;No verbal response for 20 seconds &bull; Presumed unconscious&gt;</em>',
      seniorQuote: '"No response for 20 seconds. Presumed unconscious."'
    },
    outcomes: {
      sarahTitle: "Son David Vance (Admin)",
      sarahDesc: "🚨 Emergency Call Sent & 911 Dispatch Notification",
      sarahBorder: "rgba(239, 68, 68, 0.5)",
      emsTitle: "Boston EMS 911 Dispatch",
      emsDesc: "🚑 Medic-14 Dispatched &bull; Door Unlocked &bull; ETA 4 mins",
      emsBorder: "rgba(239, 68, 68, 0.6)"
    }
  }
};

// ---------------------------------------------------------------------------
// Switch Scenario Logic
// ---------------------------------------------------------------------------
function switchScenario(key) {
  const data = SCENARIOS[key];
  if (!data) return;

  currentScenario = key;
  playChime(key === "false_alarm" ? "success" : (key === "responsive" ? "warning" : "alert"));

  // 1. Update Scenario Pills
  const tab1 = document.getElementById("tabScenario1");
  const tab2 = document.getElementById("tabScenario2");
  const tab3 = document.getElementById("tabScenario3");
  if (tab1) tab1.className = "pill-scenario-btn btn-green" + (key === "false_alarm" ? " active" : "");
  if (tab2) tab2.className = "pill-scenario-btn btn-amber" + (key === "responsive" ? " active" : "");
  if (tab3) tab3.className = "pill-scenario-btn btn-red" + (key === "silent" ? " active" : "");

  // 2. Update 1-Glance Hero Ribbon
  const heroCard = document.getElementById("heroStatusCard");
  const heroIcon = document.getElementById("heroStatusIcon");
  const heroTitle = document.getElementById("heroStatusTitle");
  const heroSub = document.getElementById("heroStatusSub");

  if (heroCard && heroIcon && heroTitle && heroSub) {
    if (key === "false_alarm") {
      heroCard.className = "hero-ribbon is-safe";
      heroIcon.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
      heroTitle.textContent = "All Clear & Safe: Eleanor is Resting";
      heroTitle.style.color = "var(--neon-green)";
      heroSub.textContent = "Motion in Living Room. Answered 'I\\'m okay' to Alexa. No emergency.";
    } else if (key === "responsive") {
      heroCard.className = "hero-ribbon is-warning";
      heroIcon.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
      heroTitle.textContent = "Caregiver Alert: Son David Connected";
      heroTitle.style.color = "var(--neon-amber)";
      heroSub.textContent = "Eleanor slipped in Kitchen and requested help. Son David alerted on Alexa Drop-In.";
    } else if (key === "silent") {
      heroCard.className = "hero-ribbon is-critical";
      heroIcon.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#ff3b57" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
      heroTitle.textContent = "Emergency Action Active: Boston EMS 911 Dispatched";
      heroTitle.style.color = "var(--neon-red)";
      heroSub.textContent = "Bathroom fall at 2:14 AM. Eleanor is silent. Smart door lock is UNLOCKED for medics.";
    }
  }

  // 3. Animate Apple Health Activity Rings
  const ringHr = document.getElementById("ringHrFill");
  const ringMove = document.getElementById("ringMoveFill");
  if (ringHr && ringMove) {
    if (key === "false_alarm") {
      ringHr.style.strokeDashoffset = "50";
      ringHr.style.stroke = "var(--neon-green)";
      ringMove.style.strokeDashoffset = "25";
      ringMove.style.stroke = "var(--neon-green)";
    } else if (key === "responsive") {
      ringHr.style.strokeDashoffset = "32";
      ringHr.style.stroke = "var(--neon-amber)";
      ringMove.style.strokeDashoffset = "60";
      ringMove.style.stroke = "var(--neon-amber)";
    } else if (key === "silent") {
      ringHr.style.strokeDashoffset = "10";
      ringHr.style.stroke = "var(--neon-red)";
      ringMove.style.strokeDashoffset = "95";
      ringMove.style.stroke = "var(--neon-red)";
    }
  }

  // 4. Update Floorplan & Room Tiles
  const tileBath = document.getElementById("tileBathroom");
  const tileLiv = document.getElementById("tileLiving");
  const tileKit = document.getElementById("tileKitchen");
  const tileBed = document.getElementById("tileBedroom");

  const tagBath = document.getElementById("tagBathroom");
  const tagLiv = document.getElementById("tagLiving");
  const tagKit = document.getElementById("tagKitchen");
  const tagBed = document.getElementById("tagBedroom");

  [tileBath, tileLiv, tileKit, tileBed].forEach(t => {
    if (t) t.className = "room-visual-tile";
  });
  if (tagBath) tagBath.style.display = "none";
  if (tagLiv) tagLiv.style.display = "none";
  if (tagKit) tagKit.style.display = "none";
  if (tagBed) tagBed.style.display = "none";

  const camTitle = document.getElementById("camHeaderTitle");
  const hudPill = document.getElementById("camHudPill");
  const hudTag = document.getElementById("hudDetectionTag");

  if (key === "silent") {
    if (tileBath) tileBath.className = "room-visual-tile alert-active selected";
    if (tagBath) tagBath.style.display = "inline-flex";
    if (camTitle) camTitle.textContent = "Live Camera & Radar Feed: Bathroom";
    if (hudPill) hudPill.textContent = "CAM-01 BATHROOM • 1080p • CEILING RADAR";
    if (hudTag) {
      hudTag.style.display = "block";
      hudTag.textContent = "FALL DETECTED • CONF: 94%";
      hudTag.style.background = "rgba(255, 59, 87, 0.9)";
    }
    if (window.cameraSim) {
      window.cameraSim.setRoomAndState("bathroom", "critical");
    }
  } else if (key === "responsive") {
    if (tileKit) tileKit.className = "room-visual-tile selected";
    if (tagKit) tagKit.style.display = "inline-flex";
    if (camTitle) camTitle.textContent = "Live Camera & Radar Feed: Kitchen";
    if (hudPill) hudPill.textContent = "CAM-02 KITCHEN • 1080p • CEILING RADAR";
    if (hudTag) {
      hudTag.style.display = "block";
      hudTag.textContent = "DISTRESS / SITTING (CONF: 89%)";
      hudTag.style.background = "rgba(245, 158, 11, 0.9)";
    }
    if (window.cameraSim) {
      window.cameraSim.setRoomAndState("kitchen", "warning");
    }
  } else if (key === "false_alarm") {
    if (tileLiv) tileLiv.className = "room-visual-tile selected";
    if (tagLiv) tagLiv.style.display = "inline-flex";
    if (camTitle) camTitle.textContent = "Live Camera & Radar Feed: Living Room";
    if (hudPill) hudPill.textContent = "CAM-03 LIVING ROOM • 1080p • CEILING RADAR";
    if (hudTag) {
      hudTag.style.display = "none";
    }
    if (window.cameraSim) {
      window.cameraSim.setRoomAndState("living", "safe");
    }
  }

  // 5. Update Door Lock
  const doorIcon = document.getElementById("doorIcon");
  const doorTitle = document.getElementById("doorTitle");
  const doorSub = document.getElementById("doorSub");

  if (doorIcon) {
    if (key === "silent") {
      doorIcon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--neon-red)" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>`;
    } else {
      doorIcon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${data.door.color}" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`;
    }
  }
  if (doorTitle) {
    doorTitle.textContent = data.door.title;
    doorTitle.style.color = data.door.color;
  }
  if (doorSub) doorSub.textContent = data.door.sub;

  // 6. Update Vitals
  const hr = document.getElementById("vitalsHR");
  const hrSub = document.getElementById("vitalsHRSub");
  const move = document.getElementById("vitalsMove");
  const moveSub = document.getElementById("vitalsMoveSub");

  if (hr) {
    hr.textContent = data.vitals.hr;
    hr.style.color = data.vitals.hrColor;
  }
  if (hrSub) hrSub.textContent = data.vitals.hrSub;

  if (move) {
    move.textContent = data.vitals.move;
    move.style.color = data.vitals.moveColor;
  }
  if (moveSub) moveSub.textContent = data.vitals.moveSub;

  // 7. Update Alexa & Eleanor Dialogue
  const dAlexa = document.getElementById("dialogAlexaText");
  const dSenior = document.getElementById("dialogSeniorText");
  const qSenior = document.getElementById("quoteSeniorVoice");

  if (dAlexa) dAlexa.innerHTML = data.dialog.alexa;
  if (dSenior) dSenior.innerHTML = data.dialog.senior;
  if (qSenior) qSenior.textContent = data.dialog.seniorQuote;

  // 8. Update Caregiver & 911 Cards
  const cardSarah = document.getElementById("cardSarah");
  const titleSarah = document.getElementById("titleSarah");
  const descSarah = document.getElementById("descSarah");

  if (titleSarah) titleSarah.textContent = data.outcomes.sarahTitle;
  if (descSarah) descSarah.innerHTML = data.outcomes.sarahDesc;
  if (cardSarah) cardSarah.style.borderColor = data.outcomes.sarahBorder;

  const cardEms = document.getElementById("cardEms");
  const titleEms = document.getElementById("titleEms");
  const descEms = document.getElementById("descEms");

  if (titleEms) titleEms.textContent = data.outcomes.emsTitle;
  if (descEms) descEms.innerHTML = data.outcomes.emsDesc;
  if (cardEms) cardEms.style.borderColor = data.outcomes.emsBorder;
  if (main3DTwin) {
    main3DTwin.updateState(key);
  }

  showToast(`Switched to <strong>${data.badgeText}</strong>`);
}

// ---------------------------------------------------------------------------
// Interactive Room Tile Selection (Click room to switch live camera feed)
// ---------------------------------------------------------------------------
function selectRoomTile(roomName) {
  playChime("info");
  const tileBath = document.getElementById("tileBathroom");
  const tileLiv = document.getElementById("tileLiving");
  const tileKit = document.getElementById("tileKitchen");
  const tileBed = document.getElementById("tileBedroom");

  [tileBath, tileLiv, tileKit, tileBed].forEach(t => {
    if (t) t.classList.remove("selected");
  });

  const mapName = roomName === "living" ? "Living" : (roomName === "bathroom" ? "Bathroom" : (roomName === "kitchen" ? "Kitchen" : "Bedroom"));
  const targetTile = document.getElementById(`tile${mapName}`);
  if (targetTile) targetTile.classList.add("selected");

  const camTitle = document.getElementById("camHeaderTitle");
  const hudPill = document.getElementById("camHudPill");
  if (camTitle) camTitle.textContent = `Live Camera & Radar Feed: ${capitalize(roomName)}`;
  if (hudPill) hudPill.textContent = `CAM-${roomName === 'bathroom' ? '01' : (roomName === 'kitchen' ? '02' : '03')} ${roomName.toUpperCase()} • 1080p • CEILING RADAR`;

  if (window.cameraSim) {
    const isRoomAlert = (currentScenario === 'silent' && roomName === 'bathroom') || (currentScenario === 'responsive' && roomName === 'kitchen');
    window.cameraSim.setRoomAndState(roomName, isRoomAlert ? (currentScenario === 'silent' ? 'critical' : 'warning') : 'safe');
  }

  if (main3DTwin) {
    main3DTwin.setRoomFocus(roomName);
  }

  showToast(`Switched Camera View to <strong>${capitalize(roomName)}</strong>`);
}

function capitalize(s) {
  if (!s) return "";
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// ---------------------------------------------------------------------------
// Interactive User Voice Answer ("I'm okay", "Help me!", "<Silence>")
// ---------------------------------------------------------------------------
function userAnswer(choice) {
  if (choice === "ok") {
    switchScenario("false_alarm");
    showToast("🗣️ Eleanor replied: <em>\"I'm okay!\"</em> ➔ Alert cancelled.");
    if (window.voiceAudio) {
      window.voiceAudio.playAlexaChime();
      setTimeout(() => {
        window.voiceAudio.speak("I'm okay, Alexa! I just dropped my glasses.", "senior");
      }, 500);
    }
  } else if (choice === "help") {
    switchScenario("responsive");
    showToast("🗣️ Eleanor replied: <em>\"Help me!\"</em> ➔ Son David alerted.");
    if (window.voiceAudio) {
      window.voiceAudio.speak("Help me, Alexa! I slipped and hurt my wrist, I can't get up!", "senior");
    }
  } else if (choice === "timeout") {
    switchScenario("silent");
    showToast("⏱️ 20s Silence Elapsed ➔ Boston EMS 911 Dispatched!");
    if (window.voiceAudio) {
      window.voiceAudio.playEmergencyTone();
      setTimeout(() => {
        window.voiceAudio.speak("No verbal response detected for twenty seconds. Initiating emergency dispatch.", "alexa");
      }, 600);
    }
  }
}

// ---------------------------------------------------------------------------
// Play Step-by-Step Story Animation
// ---------------------------------------------------------------------------
async function playStepByStepStory() {
  if (isPlayingAnimation) return;
  isPlayingAnimation = true;

  const btn = document.getElementById("btnPlayStory");
  if (btn) {
    btn.textContent = "⏳ Playing Story...";
    btn.style.opacity = "0.7";
  }

  // Step 1: Drop
  playChime("warning");
  showToast("👁️ <strong>Step 1:</strong> Ambient Camera/Radar detects sudden drop in Bathroom.");
  selectRoomTile("bathroom");
  await sleep(1800);

  // Step 2: Risk assessment
  playChime("warning");
  showToast("🧠 <strong>Step 2:</strong> Risk Engine checks wet tile + tachycardia (138 BPM) ➔ HIGH RISK.");
  await sleep(1800);

  // Step 3: Alexa Check-In
  playChime("info");
  showToast("🎙️ <strong>Step 3:</strong> Alexa Echo Show speaks: <em>\"Eleanor, are you okay?\"</em>");
  if (window.voiceAudio) {
    window.voiceAudio.playAlexaChime();
    setTimeout(() => {
      window.voiceAudio.speak("Eleanor, this is Aegis. I noticed a fall in the bathroom. Are you okay?", "alexa");
    }, 400);
  }
  await sleep(3000);

  // Step 4: Dispatch & Unlock
  playChime("alert");
  showToast("🛡️ <strong>Step 4:</strong> 20s Silence. Boston EMS 911 dispatched, Front Door UNLOCKED.");
  switchScenario("silent");
  await sleep(2000);

  if (btn) {
    btn.textContent = "▶️ Play Story Walkthrough Animation";
    btn.style.opacity = "1";
  }
  isPlayingAnimation = false;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Multi-View Tab Navigation (Overview, Vision & Floorplan, Voice AI, Dispatch)
// ---------------------------------------------------------------------------
function switchTab(tabId) {
  playChime("info");
  const tabs = ['overview', 'vision', 'voice', 'dispatch'];
  tabs.forEach(t => {
    const btn = document.getElementById('tabBtn' + capitalize(t));
    const panel = document.getElementById('panel' + capitalize(t));
    if (btn) {
      if (t === tabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    }
    if (panel) {
      if (t === tabId) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    }
  });

  // If switched to vision tab, trigger camera canvas resize to fit viewport
  if (tabId === 'vision' && window.cameraSim) {
    setTimeout(() => {
      window.cameraSim.resizeCanvas();
    }, 60);
  }
}

// ---------------------------------------------------------------------------
// User Session Management
// ---------------------------------------------------------------------------
function initUserSession() {
  const sessionStr = localStorage.getItem("aegis_auth_user");
  let user = null;
  if (sessionStr) {
    try {
      user = JSON.parse(sessionStr);
    } catch(e) {}
  }

  if (!user) {
    user = {
      name: "David Vance (Son)",
      role: "Primary Guardian",
      email: "david.vance@example.com",
      avatar: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
      patient: "Eleanor Vance (Age 79)"
    };
    localStorage.setItem("aegis_auth_user", JSON.stringify(user));
  }

  const nameEl = document.getElementById("userName");
  const roleEl = document.getElementById("userRole");
  const avatarEl = document.getElementById("userAvatar");

  if (nameEl) nameEl.textContent = user.name || "David Vance";
  if (roleEl) roleEl.textContent = user.role || "Primary Guardian";
  if (avatarEl) {
    if (user.avatar && user.avatar.includes("<svg")) {
      avatarEl.innerHTML = user.avatar;
    } else {
      avatarEl.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>`;
    }
  }
}

function logoutUser() {
  localStorage.removeItem("aegis_auth_user");
  window.location.href = "/login";
}

// ---------------------------------------------------------------------------
// Video Guide Modal Functions
// ---------------------------------------------------------------------------
function openVideoGuideModal() {
  playChime("info");
  const modal = document.getElementById("videoGuideModal");
  if (modal) modal.style.display = "flex";
}

function closeVideoGuideModal() {
  const modal = document.getElementById("videoGuideModal");
  if (modal) modal.style.display = "none";
}

// Close modal when clicking outside
window.addEventListener("click", (e) => {
  const modal = document.getElementById("videoGuideModal");
  if (e.target === modal) {
    closeVideoGuideModal();
  }
  const videoModal = document.getElementById("videoDemoModal");
  if (e.target === videoModal) {
    closeVideoDemoModal();
  }
});

// ---------------------------------------------------------------------------
// Interactive 3D Digital Twin Apartment Model (Three.js WebGL)
// ---------------------------------------------------------------------------
let is3DModeActive = false;
let main3DTwin = null;

class Main3DDigitalTwin {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas || typeof THREE === "undefined") return;

    const w = this.canvas.parentElement.clientWidth;
    const h = 330;

    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x060913);
    this.scene.fog = new THREE.FogExp2(0x060913, 0.03);

    // Camera
    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    this.camera.position.set(0, 12, 16);
    this.targetLook = new THREE.Vector3(0, 1, 0);
    this.camera.lookAt(this.targetLook);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Lights
    const amb = new THREE.AmbientLight(0x223355, 1.4);
    this.scene.add(amb);

    this.dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    this.dirLight.position.set(10, 20, 10);
    this.scene.add(this.dirLight);

    this.statusLight = new THREE.PointLight(0xef4444, 2, 20);
    this.statusLight.position.set(-5, 4, 0);
    this.scene.add(this.statusLight);

    // Build Model
    this.buildApartment();
    this.buildEleanor();
    this.setupOrbitControls();

    this.isAnimating = true;
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  buildApartment() {
    this.modelGroup = new THREE.Group();

    // 3D Grid Floor
    const grid = new THREE.GridHelper(28, 28, 0x00cae0, 0x1e293b);
    this.modelGroup.add(grid);

    // Room Floors
    const roomMat = new THREE.MeshStandardMaterial({ color: 0x0d1527, roughness: 0.7 });
    const bathMat = new THREE.MeshStandardMaterial({ color: 0x0a2a38, roughness: 0.2, metalness: 0.3 });

    // Living Room (Center)
    const living = new THREE.Mesh(new THREE.BoxGeometry(8, 0.2, 8), roomMat);
    living.position.set(0, -0.1, 0);
    this.modelGroup.add(living);

    // Bathroom (Left)
    const bath = new THREE.Mesh(new THREE.BoxGeometry(6, 0.2, 6), bathMat);
    bath.position.set(-6, -0.1, 0);
    this.modelGroup.add(bath);

    // Kitchen (Right)
    const kitchen = new THREE.Mesh(new THREE.BoxGeometry(6, 0.2, 6), roomMat);
    kitchen.position.set(6, -0.1, 0);
    this.modelGroup.add(kitchen);

    // Translucent Walls
    const wallMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.22,
      roughness: 0.1
    });

    const wall1 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3, 6), wallMat);
    wall1.position.set(-3, 1.5, 0);
    this.modelGroup.add(wall1);

    const wall2 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3, 6), wallMat);
    wall2.position.set(3, 1.5, 0);
    this.modelGroup.add(wall2);

    // Radar Pod & Rings
    const radarGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.2, 32);
    const radarMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.8 });
    const pod = new THREE.Mesh(radarGeo, radarMat);
    pod.position.set(0, 4.2, 0);
    this.modelGroup.add(pod);

    this.radarRing = new THREE.Mesh(
      new THREE.RingGeometry(0.5, 0.8, 32),
      new THREE.MeshBasicMaterial({ color: 0x10b981, side: THREE.DoubleSide, transparent: true, opacity: 0.7 })
    );
    this.radarRing.rotation.x = Math.PI / 2;
    this.radarRing.position.set(0, 4.0, 0);
    this.modelGroup.add(this.radarRing);

    this.scene.add(this.modelGroup);
  }

  buildEleanor() {
    this.eleanor = new THREE.Group();
    const clothesMat = new THREE.MeshStandardMaterial({ color: 0x0284c7 });
    const skinMat = new THREE.MeshStandardMaterial({ color: 0xfbd0b8 });

    // Head
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 16), skinMat);
    head.position.y = 2.4;
    this.eleanor.add(head);

    // Torso
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.32, 1.1, 16), clothesMat);
    body.position.y = 1.6;
    this.eleanor.add(body);

    // Limbs
    const legGeo = new THREE.CylinderGeometry(0.12, 0.1, 1.0, 12);
    const legMat = new THREE.MeshStandardMaterial({ color: 0x475569 });
    this.leftLeg = new THREE.Mesh(legGeo, legMat);
    this.leftLeg.position.set(-0.2, 0.5, 0);
    this.eleanor.add(this.leftLeg);

    this.rightLeg = new THREE.Mesh(legGeo, legMat);
    this.rightLeg.position.set(0.2, 0.5, 0);
    this.eleanor.add(this.rightLeg);

    // Cane
    const cane = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.3, 8), new THREE.MeshStandardMaterial({ color: 0x94a3b8 }));
    cane.position.set(0.55, 0.65, 0.3);
    this.eleanor.add(cane);

    this.eleanor.position.set(-5, 0.3, 0);
    this.eleanor.rotation.x = -Math.PI / 2; // Default fallen in bathroom
    this.scene.add(this.eleanor);
  }

  setupOrbitControls() {
    let isDown = false;
    let prevX = 0, prevY = 0;

    this.canvas.addEventListener("mousedown", (e) => {
      isDown = true;
      prevX = e.clientX;
      prevY = e.clientY;
    });

    window.addEventListener("mouseup", () => isDown = false);

    window.addEventListener("mousemove", (e) => {
      if (!isDown || !is3DModeActive) return;
      const dx = (e.clientX - prevX) * 0.008;
      const dy = (e.clientY - prevY) * 0.008;
      prevX = e.clientX;
      prevY = e.clientY;

      const radius = this.camera.position.length();
      let theta = Math.atan2(this.camera.position.x, this.camera.position.z) - dx;
      let phi = Math.acos(this.camera.position.y / radius) + dy;
      phi = Math.max(0.2, Math.min(Math.PI / 2 - 0.05, phi));

      this.camera.position.x = radius * Math.sin(phi) * Math.sin(theta);
      this.camera.position.y = radius * Math.cos(phi);
      this.camera.position.z = radius * Math.sin(phi) * Math.cos(theta);
      this.camera.lookAt(this.targetLook);
    });

    this.canvas.addEventListener("wheel", (e) => {
      if (!is3DModeActive) return;
      e.preventDefault();
      const zoom = e.deltaY * 0.01;
      this.camera.position.multiplyScalar(1 + zoom * 0.08);
      this.camera.position.clampLength(6, 32);
      this.camera.lookAt(this.targetLook);
    });
  }

  setRoomFocus(room) {
    if (room === "bathroom") {
      this.targetLook.set(-5, 1, 0);
    } else if (room === "kitchen") {
      this.targetLook.set(5, 1, 0);
    } else {
      this.targetLook.set(0, 1, 0);
    }
  }

  updateState(scenarioKey) {
    if (scenarioKey === "silent") {
      this.eleanor.position.set(-5, 0.3, 0);
      this.eleanor.rotation.x = -Math.PI / 2; // Fallen on floor
      this.statusLight.color.setHex(0xef4444);
      this.statusLight.position.set(-5, 3, 0);
      this.targetLook.set(-5, 1, 0);
    } else if (scenarioKey === "responsive") {
      this.eleanor.position.set(5, 0.6, 0);
      this.eleanor.rotation.x = -Math.PI / 4; // Slumped/sitting
      this.statusLight.color.setHex(0xf59e0b);
      this.statusLight.position.set(5, 3, 0);
      this.targetLook.set(5, 1, 0);
    } else if (scenarioKey === "false_alarm") {
      this.eleanor.position.set(0, 0, 0);
      this.eleanor.rotation.x = 0; // Upright standing
      this.statusLight.color.setHex(0x10b981);
      this.statusLight.position.set(0, 3, 0);
      this.targetLook.set(0, 1, 0);
    }
  }

  animate() {
    if (!this.isAnimating) return;
    const t = performance.now() * 0.002;

    // Pulse radar ring
    if (this.radarRing) {
      const scale = ((t * 1.5) % 4) + 0.5;
      this.radarRing.scale.set(scale, scale, 1);
      this.radarRing.material.opacity = Math.max(0, 0.7 - scale / 4.5);
    }

    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(this.animate);
  }

  resize() {
    if (!this.renderer || !this.camera || !this.canvas) return;
    const w = this.canvas.parentElement.clientWidth;
    const h = 330;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }
}

function toggleMain3DMode() {
  const cam2D = document.getElementById("cameraCanvas");
  const cam3D = document.getElementById("threeDCanvas");
  const btn = document.getElementById("btnToggle3DMode");

  is3DModeActive = !is3DModeActive;

  if (is3DModeActive) {
    if (cam2D) cam2D.style.display = "none";
    if (cam3D) cam3D.style.display = "block";
    if (btn) {
      btn.innerHTML = "📹 2D Camera View";
      btn.style.color = "#fff";
      btn.style.background = "linear-gradient(135deg, #0284c7, #38bdf8)";
    }

    if (!main3DTwin) {
      main3DTwin = new Main3DDigitalTwin("threeDCanvas");
    }
    if (main3DTwin) {
      main3DTwin.resize();
      main3DTwin.updateState(currentScenario);
    }
    showToast("🌐 <strong>Interactive 3D Digital Twin Active:</strong> Click & drag to rotate in 360°!");
  } else {
    if (cam2D) cam2D.style.display = "block";
    if (cam3D) cam3D.style.display = "none";
    if (btn) {
      btn.innerHTML = "🌐 3D Model View";
      btn.style.color = "var(--neon-cyan)";
      btn.style.background = "rgba(0, 202, 224, 0.12)";
    }
    showToast("📹 Switched back to <strong>2D Edge Camera & YOLO Skeleton</strong>.");
  }
}

// ---------------------------------------------------------------------------
// Initialization on Page Load
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initUserSession();
  switchScenario("silent");
  console.log("Aegis Ambient Care Story Dashboard & 3D Digital Twin ready.");
});

