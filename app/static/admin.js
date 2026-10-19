/**
 * Aegis Ambient Care - Family Admin Guardian Console Logic
 * Dedicated to Eleanor's son / primary family administrator
 */

let isDoorUnlocked = true;

function playAdminChime(freq = 600, dur = 0.25) {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + dur);

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + dur);
  } catch(e) {}
}

function showToast(msg) {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const pill = document.createElement("div");
  pill.className = "toast-pill";
  pill.innerHTML = msg;
  container.appendChild(pill);
  setTimeout(() => {
    pill.style.opacity = "0";
    pill.style.transition = "all 0.3s";
    setTimeout(() => pill.remove(), 300);
  }, 3500);
}

function toggleDoorOverride() {
  isDoorUnlocked = !isDoorUnlocked;
  playAdminChime(isDoorUnlocked ? 880 : 440);

  const valEl = document.getElementById("adminDoorVal");
  const btnEl = document.getElementById("btnToggleDoor");

  if (isDoorUnlocked) {
    valEl.textContent = "UNLOCKED";
    valEl.style.color = "#ef4444";
    btnEl.textContent = "🔒 Remote Lock Door";
    btnEl.className = "btn-action-admin";
    showToast("🔓 Front Door <strong>UNLOCKED</strong> remotely for first responders.");
    addTimelineEvent("critical", "Admin Remote Door Unlock Override", "Son David Vance remotely unlocked front door (Emergency PIN: 8492 active).");
  } else {
    valEl.textContent = "LOCKED";
    valEl.style.color = "#10b981";
    btnEl.textContent = "🔓 Override Door Lock";
    btnEl.className = "btn-action-admin btn-danger-admin";
    showToast("🔒 Front Door <strong>SECURELY LOCKED</strong>.");
    addTimelineEvent("safe", "Admin Remote Door Lock", "Son David Vance verified residence safe and restored door deadbolt lock.");
  }
}

function triggerEchoDropIn() {
  playAdminChime(580);
  showToast("🎙️ Connecting live <strong>Echo Drop-In Audio Call</strong> to Beacon Hill Unit 4B...");
  addTimelineEvent("warning", "Echo Drop-In Call Initiated", "Son David Vance connected live two-way audio to Eleanor's living room Echo Show.");
}

function addTimelineEvent(type, title, desc) {
  const list = document.getElementById("timelineList");
  if (!list) return;

  const item = document.createElement("div");
  item.className = `timeline-item ${type}`;
  const now = new Date().toLocaleTimeString();
  item.innerHTML = `
    <div class="timeline-time">Just now &bull; ${now}</div>
    <div class="timeline-title">${title}</div>
    <div class="timeline-desc">${desc}</div>
  `;
  list.insertBefore(item, list.firstChild);
}

function triggerTestSimulation(scenario) {
  playAdminChime(scenario === "false_alarm" ? 660 : (scenario === "responsive" ? 500 : 880));

  const riskVal = document.getElementById("adminRiskVal");
  const riskSub = document.getElementById("adminRiskSub");
  const hrVal = document.getElementById("adminHrVal");
  const gaitVal = document.getElementById("adminGaitVal");
  const doorVal = document.getElementById("adminDoorVal");
  const jsonBox = document.getElementById("rawJsonBox");

  window.currentScenario = scenario;
  const bathRoom = document.getElementById("adminRoomBath");
  const livingRoom = document.getElementById("adminRoomLiving");
  const kitchenRoom = document.getElementById("adminRoomKitchen");
  const bedRoom = document.getElementById("adminRoomBed");

  // Reset rooms
  [bathRoom, livingRoom, kitchenRoom, bedRoom].forEach(r => {
    if (r) r.className = "room-box";
  });

  if (scenario === "false_alarm") {
    riskVal.textContent = "LOW";
    riskVal.style.color = "#10b981";
    riskSub.textContent = "Score: 0.12 • Verified Safe via Alexa";
    hrVal.textContent = "72 BPM";
    hrVal.style.color = "#10b981";
    gaitVal.textContent = "0.05 / 1.0";
    doorVal.textContent = "LOCKED";
    doorVal.style.color = "#10b981";

    livingRoom.className = "room-box is-safe";
    showToast("🟢 Simulation: <strong>False Alarm</strong> active.");
    addTimelineEvent("safe", "False Alarm Resolved", "Eleanor dropped book in living room, answered 'I'm okay' to Alexa. No siren dispatched.");

    jsonBox.textContent = JSON.stringify({
      event_type: "dropped_object_reach",
      confidence: 0.88,
      location: "living_room",
      timestamp: new Date().toISOString(),
      movement_after_event: "normal",
      vitals: { heart_rate_bpm: 72, normal: true },
      alexa_voice_verification: { prompt: "Eleanor, are you okay?", response: "im_okay", safe: true },
      escalation: { status: "DISMISSED", alert_sent: false }
    }, null, 2);

  } else if (scenario === "responsive") {
    riskVal.textContent = "MODERATE";
    riskVal.style.color = "#f59e0b";
    riskSub.textContent = "Score: 0.65 • Caregiver Alert Active";
    hrVal.textContent = "98 BPM";
    hrVal.style.color = "#f59e0b";
    gaitVal.textContent = "0.45 / 1.0";
    doorVal.textContent = "LOCKED";
    doorVal.style.color = "#f59e0b";

    kitchenRoom.className = "room-box has-mild-alert";
    showToast("🟡 Simulation: <strong>Calls for Help</strong> active.");
    addTimelineEvent("warning", "Caregiver Alert Dispatched", "Eleanor slipped in kitchen and called 'Help me!'. Son David notified via Alexa Drop-In.");

    jsonBox.textContent = JSON.stringify({
      event_type: "slip_and_fall",
      confidence: 0.91,
      location: "kitchen",
      timestamp: new Date().toISOString(),
      movement_after_event: "limited",
      vitals: { heart_rate_bpm: 98, elevated: true },
      alexa_voice_verification: { prompt: "Eleanor, are you okay?", response: "help_me", assistance_requested: true },
      escalation: { status: "CAREGIVER_ALERTED", drop_in_active: true, primary_guardian: "David Vance (Son)" }
    }, null, 2);

  } else if (scenario === "silent") {
    riskVal.textContent = "CRITICAL";
    riskVal.style.color = "#ef4444";
    riskSub.textContent = "Score: 0.94 • 911 Dispatched";
    hrVal.textContent = "138 BPM";
    hrVal.style.color = "#ef4444";
    gaitVal.textContent = "0.88 / 1.0";
    doorVal.textContent = "UNLOCKED";
    doorVal.style.color = "#ef4444";

    bathRoom.className = "room-box has-alert";
    showToast("🔴 Simulation: <strong>Silent Emergency</strong> active!");
    addTimelineEvent("critical", "Boston EMS 911 Dispatched", "Nocturnal bathroom fall detected with 20s voice timeout. Door unlocked for first responders.");

    jsonBox.textContent = JSON.stringify({
      event_type: "possible_fall",
      confidence: 0.94,
      location: "bathroom",
      timestamp: new Date().toISOString(),
      movement_after_event: "none",
      vitals: { heart_rate_bpm: 138, tachycardia: true },
      alexa_voice_verification: { prompt: "Eleanor, are you okay?", response: "timeout_20s", presumed_unconscious: true },
      escalation: { status: "EMS_DISPATCHED", unit: "Medic-14", front_door_smart_lock: "UNLOCKED", pin: 8492 }
    }, null, 2);
  }
}

function switchPayloadView(viewMode) {
  const visualBanner = document.getElementById("visualFormulaBanner");
  const visualGrid = document.getElementById("visualFactorsGrid");
  const jsonWrapper = document.getElementById("jsonPayloadWrapper");
  const btnVisual = document.getElementById("btnViewVisual");
  const btnJson = document.getElementById("btnViewJson");

  if (viewMode === "visual") {
    if (visualBanner) visualBanner.style.display = "block";
    if (visualGrid) visualGrid.style.display = "grid";
    if (jsonWrapper) jsonWrapper.style.display = "none";
    if (btnVisual) btnVisual.className = "btn-view-toggle active";
    if (btnJson) btnJson.className = "btn-view-toggle";
  } else {
    if (visualBanner) visualBanner.style.display = "none";
    if (visualGrid) visualGrid.style.display = "none";
    if (jsonWrapper) jsonWrapper.style.display = "block";
    if (btnVisual) btnVisual.className = "btn-view-toggle";
    if (btnJson) btnJson.className = "btn-view-toggle active";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("Aegis Family Admin Guardian Console ready.");
});
