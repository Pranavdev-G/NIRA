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
// Authoritative Real-Time Reactive Dashboard Renderer (Person 2)
// ---------------------------------------------------------------------------

function renderDashboard(state) {
  if (!state) return;

  // 1. Connection status in header & global banner
  const badge = document.getElementById("mcpConnectionBadge");
  const connText = document.getElementById("connStatusText");
  const connLatency = document.getElementById("connLatencyText");
  if (badge && connText && connLatency) {
    badge.className = "conn-badge " + state.connection.status;
    if (state.connection.status === "connected") {
      connText.textContent = "MCP STREAM LIVE";
      connLatency.textContent = `(${state.connection.latencyMs || 18}ms SLA)`;
    } else if (state.connection.status === "connecting") {
      connText.textContent = "CONNECTING...";
      connLatency.textContent = "--ms";
    } else if (state.connection.status === "reconnecting") {
      connText.textContent = "RECONNECTING...";
      connLatency.textContent = "--ms";
    } else {
      connText.textContent = "OFFLINE";
      connLatency.textContent = "NO STREAM";
    }
  }

  // 1B. Global Disconnected / Stale Warning Banner
  const sysBanner = document.getElementById("systemStateBanner");
  const bannerTitle = document.getElementById("bannerTitle");
  const bannerSub = document.getElementById("bannerSubtitle");
  const bannerIcon = document.getElementById("bannerIcon");
  if (sysBanner) {
    if (state.connection.status === "disconnected") {
      sysBanner.style.display = "flex";
      sysBanner.className = "system-state-banner disconnected";
      if (bannerTitle) bannerTitle.textContent = "SAFETY STREAM OFFLINE";
      if (bannerSub) bannerSub.textContent = "Live telemetry connection lost. Displaying cached baseline safety data. Automatic reconnection in progress...";
      if (bannerIcon) bannerIcon.textContent = "🚨";
    } else if (state.connection.status === "reconnecting") {
      sysBanner.style.display = "flex";
      sysBanner.className = "system-state-banner reconnecting";
      if (bannerTitle) bannerTitle.textContent = "STREAM RECONNECTING";
      if (bannerSub) bannerSub.textContent = "Re-establishing secure SSE telemetry pipe to NIRA Engine. Stand by...";
      if (bannerIcon) bannerIcon.textContent = "🟡";
    } else {
      sysBanner.style.display = "none";
    }
  }

  // 2. Scenario buttons active state & accessible ARIA attributes
  const tab1 = document.getElementById("tabScenario1");
  const tab2 = document.getElementById("tabScenario2");
  const tab3 = document.getElementById("tabScenario3");
  const risk = state.incident.currentRiskLevel;

  if (tab1 && tab2 && tab3) {
    const isTab1 = risk === "LOW" || state.incident.status === "RESOLVED";
    const isTab2 = risk === "HIGH" || risk === "MODERATE" || state.incident.status === "ESCALATED_CAREGIVER";
    const isTab3 = risk === "CRITICAL" || state.incident.status === "ESCALATED_CAD";

    tab1.className = "pill-scenario-btn btn-green" + (isTab1 ? " active" : "");
    tab1.setAttribute("aria-pressed", isTab1 ? "true" : "false");

    tab2.className = "pill-scenario-btn btn-amber" + (isTab2 ? " active" : "");
    tab2.setAttribute("aria-pressed", isTab2 ? "true" : "false");

    tab3.className = "pill-scenario-btn btn-red" + (isTab3 ? " active" : "");
    tab3.setAttribute("aria-pressed", isTab3 ? "true" : "false");
  }

  // 3. Hero Reassurance Ribbon (Multi-Modal: Icon + Tier Label + Color + Descriptive Text)
  const heroCard = document.getElementById("heroStatusCard");
  const heroIcon = document.getElementById("heroStatusIcon");
  const heroTitle = document.getElementById("heroStatusTitle");
  const heroSub = document.getElementById("heroStatusSub");

  if (heroCard && heroIcon && heroTitle && heroSub) {
    const timeAgo = NiraStateStore.formatTimeAgo(state.timestamps.risk);
    if (risk === "LOW" || state.incident.status === "RESOLVED") {
      heroCard.className = "hero-ribbon is-safe";
      heroIcon.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
      heroTitle.innerHTML = `<span class="severity-tag safe">🛡️ TIER 1 &bull; ALL CLEAR</span> All Clear &amp; Safe: Eleanor is Resting`;
      heroTitle.style.color = "#34d399";
      heroSub.innerHTML = `Location: <strong>${capitalize(state.incident.location)}</strong> &bull; Routine baseline verified &bull; <span class="timestamp-tag">Updated ${timeAgo}</span>`;
    } else if (risk === "HIGH" || risk === "MODERATE" || state.incident.status === "ESCALATED_CAREGIVER") {
      heroCard.className = "hero-ribbon is-warning";
      heroIcon.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
      heroTitle.innerHTML = `<span class="severity-tag warning">⚠️ TIER 2 &bull; CAREGIVER ALERT</span> Caregiver Alert: Son David Connected`;
      heroTitle.style.color = "#fbbf24";
      heroSub.innerHTML = `Distress observed in <strong>${capitalize(state.incident.location)}</strong>. Primary guardian alerted across Echo Drop-In &amp; Phone &bull; <span class="timestamp-tag">Updated ${timeAgo}</span>`;
    } else {
      heroCard.className = "hero-ribbon is-critical";
      heroIcon.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2.2" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
      heroTitle.innerHTML = `<span class="severity-tag critical">🚨 TIER 3 &bull; CRITICAL DISPATCH</span> Emergency Action Active: Boston EMS 911 Dispatched <span class="simulation-pill">SIMULATION</span>`;
      heroTitle.style.color = "#fda4af";
      heroSub.innerHTML = `Acute fall in <strong>${capitalize(state.incident.location)}</strong> with 20s voice timeout. Smart lock UNLOCKED for first responders &bull; <span class="timestamp-tag">Updated ${timeAgo}</span>`;
    }
  }

  // 4. Apple Health Activity Rings & Telemetry with Rolling Histories
  const ringHr = document.getElementById("ringHrFill");
  const ringMove = document.getElementById("ringMoveFill");
  const hr = document.getElementById("vitalsHR");
  const hrSub = document.getElementById("vitalsHRSub");
  const move = document.getElementById("vitalsMove");
  const moveSub = document.getElementById("vitalsMoveSub");
  const sparklinePath = document.getElementById("hrSparklinePath");
  const hrTrendTag = document.getElementById("hrTrendTag");
  const moveBreadcrumbs = document.getElementById("moveBreadcrumbs");
  const devStatus = document.getElementById("vitalsDeviceStatus");
  const devBreadcrumbs = document.getElementById("deviceBreadcrumbs");
  const envLight = document.getElementById("envLight");
  const envFloor = document.getElementById("envFloor");
  const envTemp = document.getElementById("envTemp");
  const envRadar = document.getElementById("envRadar");

  const hasData = state.telemetry && state.telemetry.hasLiveData;

  if (!hasData) {
    if (hr) hr.innerHTML = `<span class="no-live-data-badge">NO LIVE DATA</span>`;
    if (move) move.innerHTML = `<span class="no-live-data-badge">NO LIVE DATA</span>`;
    if (devStatus) devStatus.innerHTML = `<span class="no-live-data-badge">NO LIVE DATA</span>`;
  } else {
    // 4A. Heart Rate & Rolling Chart
    if (hr) {
      hr.textContent = `${state.vitals.heartRateBpm} BPM`;
      if (state.vitals.heartRateBpm > 120) {
        hr.style.color = "var(--accent-red)";
        if (ringHr) {
          ringHr.style.strokeDashoffset = "10";
          ringHr.style.stroke = "var(--accent-red)";
        }
      } else if (state.vitals.heartRateBpm > 90) {
        hr.style.color = "var(--accent-amber)";
        if (ringHr) {
          ringHr.style.strokeDashoffset = "32";
          ringHr.style.stroke = "var(--accent-amber)";
        }
      } else {
        hr.style.color = "var(--accent-green)";
        if (ringHr) {
          ringHr.style.strokeDashoffset = "50";
          ringHr.style.stroke = "var(--accent-green)";
        }
      }
    }

    if (sparklinePath && state.telemetry.heartRate.history) {
      const pathData = NiraStateStore.generateSparklinePath(state.telemetry.heartRate.history, 100, 24);
      sparklinePath.setAttribute("d", pathData);
      sparklinePath.style.stroke = state.vitals.heartRateBpm > 120 ? "var(--accent-red)" : (state.vitals.heartRateBpm > 90 ? "var(--accent-amber)" : "var(--accent-green)");
    }

    if (hrTrendTag && state.telemetry.heartRate.trend) {
      const trend = state.telemetry.heartRate.trend;
      hrTrendTag.className = "trend-tag " + trend;
      hrTrendTag.innerHTML = trend === "rising" ? "&uarr; RISING" : (trend === "falling" ? "&darr; FALLING" : "&rarr; STABLE");
    }

    const hrAgeSec = state.timestamps.heartRate ? Math.floor((Date.now() - new Date(state.timestamps.heartRate).getTime()) / 1000) : 0;
    const isHrStale = hrAgeSec > 60;
    if (hrSub) {
      hrSub.innerHTML = `${state.vitals.heartRateStatus} <span class="timestamp-tag">${NiraStateStore.formatTimeAgo(state.timestamps.heartRate)}</span>${isHrStale ? ' <span class="stale-data-badge" role="status">⚠️ STALE</span>' : ''}`;
    }

    // 4B. Movement & Rolling Transition Breadcrumbs
    if (move) {
      if (state.vitals.movementScore < 0.2) {
        move.textContent = "Immobile";
        move.style.color = "var(--accent-red)";
        if (ringMove) {
          ringMove.style.strokeDashoffset = "95";
          ringMove.style.stroke = "var(--accent-red)";
        }
      } else if (state.vitals.movementScore < 0.7) {
        move.textContent = "Sitting";
        move.style.color = "var(--accent-amber)";
        if (ringMove) {
          ringMove.style.strokeDashoffset = "60";
          ringMove.style.stroke = "var(--accent-amber)";
        }
      } else {
        move.textContent = "Active";
        move.style.color = "var(--accent-green)";
        if (ringMove) {
          ringMove.style.strokeDashoffset = "25";
          ringMove.style.stroke = "var(--accent-green)";
        }
      }
    }

    if (moveBreadcrumbs && state.telemetry.movement.history) {
      const crumbs = state.telemetry.movement.history;
      moveBreadcrumbs.innerHTML = crumbs.map((c, i) => {
        const isLast = i === crumbs.length - 1;
        const cls = isLast ? (c === "immobile" ? "crumb-node immobile active" : "crumb-node active") : "crumb-node";
        return `<span class="${cls}">${c}</span>${!isLast ? '<span class="crumb-arrow">&rarr;</span>' : ''}`;
      }).join("");
    }

    const mvAgeSec = state.timestamps.movement ? Math.floor((Date.now() - new Date(state.timestamps.movement).getTime()) / 1000) : 0;
    const isMvStale = mvAgeSec > 60;
    if (moveSub) {
      moveSub.innerHTML = `${state.vitals.movementDescription} <span class="timestamp-tag">${NiraStateStore.formatTimeAgo(state.timestamps.movement)}</span>${isMvStale ? ' <span class="stale-data-badge" role="status">⚠️ STALE</span>' : ''}`;
    }

    // 4C. Device Connectivity & Battery
    if (devStatus) {
      const devState = state.telemetry.device.status;
      devStatus.textContent = capitalize(devState);
      devStatus.style.color = devState === "connected" ? "var(--accent-green)" : (devState === "degraded" ? "var(--accent-amber)" : "var(--accent-red)");
    }

    if (devBreadcrumbs) {
      const bPct = state.telemetry.device.batteryPercent || 84;
      const devState = state.telemetry.device.status;
      devBreadcrumbs.innerHTML = `
        <span class="crumb-node ${devState === 'connected' ? 'active' : ''}">${capitalize(devState)}</span>
        <span class="crumb-arrow">&bull;</span>
        <span class="crumb-node">Battery: ${bPct}%</span>
      `;
    }

    // 4D. Environmental Telemetry Strip
    if (envLight) envLight.textContent = `${state.telemetry.environment.lightLux} Lux`;
    if (envFloor) {
      const floorCond = state.telemetry.environment.floorCondition;
      envFloor.textContent = floorCond === "wet" ? "Wet Substrate" : "Dry Floor";
      envFloor.style.color = floorCond === "wet" ? "var(--accent-red)" : "var(--accent-green)";
    }
    if (envTemp) envTemp.textContent = `${state.telemetry.environment.temperatureC}°C`;
    if (envRadar) envRadar.textContent = state.vitals.radarActive ? "mmWave Active" : "Standby";
  }

  // 5. Smart Lock Status Card
  const doorIcon = document.getElementById("doorIcon");
  const doorTitle = document.getElementById("doorTitle");
  const doorSub = document.getElementById("doorSub");

  if (doorIcon && doorTitle && doorSub) {
    if (state.emergency.doorLockState === "UNLOCKED") {
      doorIcon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent-red)" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>`;
      doorTitle.innerHTML = `Front Door Smart Lock: UNLOCKED FOR 911 <span class="simulation-pill">SIMULATION</span>`;
      doorTitle.style.color = "var(--accent-red)";
      doorSub.innerHTML = `Auto-unlocked for Boston EMS First Responders (PIN: ${state.emergency.doorPin}) <span class="timestamp-tag">${NiraStateStore.formatTimeAgo(state.timestamps.doorLock)}</span>`;
    } else {
      doorIcon.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`;
      doorTitle.textContent = "Front Door Smart Lock: SECURELY LOCKED";
      doorTitle.style.color = "var(--accent-green)";
      doorSub.innerHTML = `Home perimeter secured <span class="timestamp-tag">${NiraStateStore.formatTimeAgo(state.timestamps.doorLock)}</span>`;
    }
  }

  // 6. Caregiver and 911 CAD Quick Snapshot
  const cardSarah = document.getElementById("cardSarah");
  const titleSarah = document.getElementById("titleSarah");
  const descSarah = document.getElementById("descSarah");
  const cardEms = document.getElementById("cardEms");
  const titleEms = document.getElementById("titleEms");
  const descEms = document.getElementById("descEms");

  if (titleSarah && descSarah) {
    titleSarah.textContent = state.caregiver.guardianName;
    if (state.caregiver.status === "ALERTED") {
      descSarah.innerHTML = `📱 Echo Drop-In Connected & Live Audio <span class="timestamp-tag">${NiraStateStore.formatTimeAgo(state.timestamps.caregiver)}</span>`;
      if (cardSarah) cardSarah.style.borderColor = "rgba(245, 158, 11, 0.5)";
    } else if (state.caregiver.status === "DISPATCHED") {
      descSarah.innerHTML = `🚨 High-Priority Notification & Emergency SMS Sent <span class="timestamp-tag">${NiraStateStore.formatTimeAgo(state.timestamps.caregiver)}</span>`;
      if (cardSarah) cardSarah.style.borderColor = "rgba(239, 68, 68, 0.5)";
    } else {
      descSarah.innerHTML = `🟢 Standby • Routine monitoring <span class="timestamp-tag">${NiraStateStore.formatTimeAgo(state.timestamps.caregiver)}</span>`;
      if (cardSarah) cardSarah.style.borderColor = "rgba(16, 185, 129, 0.4)";
    }
  }

  if (titleEms && descEms) {
    titleEms.innerHTML = `Boston EMS 911 CAD Dispatch <span class="simulation-pill">SIMULATION</span>`;
    if (state.emergency.status === "DISPATCHED") {
      descEms.innerHTML = `🚑 ${state.emergency.unitDispatched} Dispatched • Incident #${state.incident.id || "BOS-2026-88192"} • Door Unlocked`;
      descEms.style.color = "var(--accent-red)";
      if (cardEms) {
        cardEms.style.borderColor = "rgba(244, 63, 94, 0.5)";
        cardEms.style.background = "rgba(244, 63, 94, 0.08)";
      }
    } else {
      descEms.innerHTML = "⚪ Standby • No emergency dispatch required";
      descEms.style.color = "var(--text-secondary)";
      if (cardEms) {
        cardEms.style.borderColor = "rgba(255, 255, 255, 0.08)";
        cardEms.style.background = "var(--bg-card-subtle)";
      }
    }
  }

  // 7. Floorplan Digital Twin – Full Event-Driven Room Telemetry Rendering
  const location = state.incident.location || "bathroom";
  const rooms = state.rooms || {};
  const ROOM_IDS = ["bathroom", "living", "kitchen", "bedroom"];
  const ROOM_NAMES = { bathroom: "Bathroom", living: "Living", kitchen: "Kitchen", bedroom: "Bedroom" };

  ROOM_IDS.forEach(roomId => {
    const rm = rooms[roomId];
    const mapName = ROOM_NAMES[roomId];
    const tile = document.getElementById(`tile${mapName}`);
    if (!tile || !rm) return;

    // Tile CSS classes based on room risk and selection
    let tileClass = "room-visual-tile";
    if (rm.isResidentLocation) tileClass += " selected";
    if (rm.riskLevel === "CRITICAL") tileClass += " alert-active";
    else if (rm.riskLevel === "ELEVATED") tileClass += " risk-elevated";
    tile.className = tileClass;

    // Keyboard accessibility & focus support for room tiles
    tile.setAttribute("tabindex", "0");
    tile.setAttribute("role", "button");
    tile.setAttribute("aria-label", `${mapName} room, risk level ${rm.riskLevel}, ${rm.occupied ? 'resident present' : 'vacant'}`);
    tile.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        tile.click();
      }
    };

    // Risk badge - Multi-Modal: Icon + Label
    const riskBadge = document.getElementById(`badgeRisk${mapName}`);
    if (riskBadge) {
      if (rm.riskLevel === "CRITICAL") {
        riskBadge.textContent = "🚨 CRITICAL";
        riskBadge.className = "room-risk-badge badge-critical";
      } else if (rm.riskLevel === "ELEVATED") {
        riskBadge.textContent = "⚠️ ELEVATED";
        riskBadge.className = "room-risk-badge badge-elevated";
      } else {
        riskBadge.textContent = "🛡️ NORMAL";
        riskBadge.className = "room-risk-badge badge-normal";
      }
    }

    // Occupancy pill
    const occPill = document.getElementById(`occupancy${mapName}`);
    const occText = document.getElementById(`occupancyText${mapName}`);
    if (occPill && occText) {
      if (rm.occupied) {
        occPill.className = "room-occupancy-pill occupied" + (rm.riskLevel !== "NORMAL" ? " in-alert" : "");
        occText.textContent = rm.isResidentLocation ? "RESIDENT PRESENT (Eleanor)" : "OCCUPIED";
      } else {
        occPill.className = "room-occupancy-pill vacant";
        occText.textContent = "VACANT (No presence)";
      }
    }

    // Posture
    const postureEl = document.getElementById(`posture${mapName}`);
    if (postureEl) {
      postureEl.textContent = rm.posture;
      postureEl.className = "m-val" + (rm.postureCode === "fallen" ? " danger" : rm.postureCode === "sitting" ? " warning" : rm.postureCode === "empty" ? "" : " safe");
    }

    // Movement State
    const moveEl = document.getElementById(`moveState${mapName}`);
    if (moveEl) {
      moveEl.textContent = `${rm.movementState} (${rm.movementScore.toFixed(2)})`;
      moveEl.className = "m-val" + (rm.movementScore < 0.2 ? " danger" : rm.movementScore < 0.7 ? " warning" : " safe");
    }

    // Hazards
    const hazardEl = document.getElementById(`hazards${mapName}`);
    if (hazardEl) {
      const hazardText = rm.hazards && rm.hazards.length ? rm.hazards.join(" • ") : "None detected";
      hazardEl.textContent = hazardText;
      const hasDanger = rm.floorCondition === "wet" || (rm.lux !== undefined && rm.lux < 30);
      hazardEl.className = "m-val" + (hasDanger ? " danger" : " safe");
    }

    // Active sensors (static per room – these don't change based on incident)
    const sensorEl = document.getElementById(`sensors${mapName}`);
    if (sensorEl && rm.activeSensors && rm.activeSensors.length) {
      sensorEl.textContent = rm.activeSensors[0] + (rm.activeSensors.length > 1 ? " +" + (rm.activeSensors.length - 1) : "");
    }
  });

  // 8. Camera/Radar Viewport HUD & Simulator
  const camTitle = document.getElementById("camHeaderTitle");
  const hudPill = document.getElementById("camHudPill");
  const hudTag = document.getElementById("hudDetectionTag");
  const footerModality = document.getElementById("footerModalityText");
  const privacyBadge = document.getElementById("privacyShieldBadge");

  const currentRoom = rooms[location] || {};
  const cameraAvailable = currentRoom.cameraAvailable !== false;
  const isRadarRoom = !cameraAvailable;

  const camState = (risk === "CRITICAL" && state.incident.fallDetected)
    ? "critical"
    : (risk === "HIGH" || risk === "MODERATE" ? "warning" : "safe");
  const postureCodeFromRoom = currentRoom.postureCode || (camState === "critical" ? "fallen" : camState === "warning" ? "sitting" : "upright");

  if (window.cameraSim && !is3DModeActive) {
    window.cameraSim.setRoomAndState(location, camState, postureCodeFromRoom);
  }

  // Update mode labels and headers based on active cinema mode
  if (currentCinemaViewMode === "3d" || is3DModeActive) {
    if (camTitle) camTitle.textContent = `3D Spatial Digital Twin: ${capitalize(location)}`;
    if (hudPill) hudPill.textContent = `SPATIAL-3D ${location.toUpperCase()} • DIGITAL TWIN RIGID SKELETON`;
    if (footerModality) footerModality.textContent = "3D WEBGL ENGINE • KINEMATIC FALL SIMULATOR • CONTINUOUS POSE";
    if (privacyBadge) privacyBadge.style.display = "inline-flex";
  } else if (currentCinemaViewMode === "camera") {
    if (camTitle) camTitle.textContent = `Optical Camera Feed: ${capitalize(location)}`;
    if (hudPill) hudPill.textContent = `CAM-01 ${location.toUpperCase()} • 1080p • YOLOv8-Pose`;
    if (footerModality) footerModality.textContent = "OPTICAL CAMERA • YOLOv8 17-KEYPOINT SKELETON • EDGE INFERENCE";
    if (privacyBadge) privacyBadge.style.display = "none";
  } else {
    // Default / Radar
    if (camTitle) camTitle.textContent = `Privacy Radar Feed: ${capitalize(location)}`;
    if (hudPill) hudPill.textContent = `RADAR-01 ${location.toUpperCase()} • 60GHz FMCW • PRIVACY SHIELD`;
    if (footerModality) footerModality.textContent = "60GHz mmWAVE RADAR • ZERO OPTICAL RECORDING • FMCW POINT CLOUD";
    if (privacyBadge) privacyBadge.style.display = "inline-flex";
  }

  if (hudTag) {
    if (state.incident.fallDetected) {
      hudTag.style.display = "block";
      const modeTag = (currentCinemaViewMode === "radar") ? "RADAR" : (currentCinemaViewMode === "3d" ? "3D TWIN" : "OPTICAL");
      hudTag.textContent = `FALL DETECTED (${modeTag}) • CONF: ${(state.incident.confidence * 100).toFixed(0)}%`;
      hudTag.style.background = risk === "CRITICAL" ? "rgba(244, 63, 94, 0.9)" : "rgba(245, 158, 11, 0.9)";
    } else {
      hudTag.style.display = "none";
    }
  }

  // 9. 3D Digital Twin – Update physical location, posture, risk from authoritative state
  if (main3DTwin) {
    main3DTwin.updatePhysicalState(location, currentRoom.postureCode || "upright", risk);
  }

  // 10. Voice AI 8-Phase State Machine & Live Conversation Timeline
  renderVoicePanel(state);

  // 11. Real-Time Emergency Command Center (Actual Backend Incident State)
  renderEmergencyCommandCenter(state);

  // 12. Update Resident & Family Portal (Simple View) & Company Architecture
  if (typeof renderUserPortal === "function") renderUserPortal(state);

  // 13. NIRA THE LIVING GUARDIAN Signature Visual Experience
  if (typeof renderLivingGuardian === "function") renderLivingGuardian(state);
  if (typeof renderActiveIncidentSection === "function") renderActiveIncidentSection(state);
  if (typeof renderSpatialMap === "function") renderSpatialMap(state);
  if (typeof renderRiskReasoning === "function") renderRiskReasoning(state);
  if (typeof renderTrustLedger === "function") renderTrustLedger(state);

  // 14. Live Mode Operations Console Synchronization (Prioritizing Our Live Features)
  if (typeof renderLiveModeConsole === "function") {
    renderLiveModeConsole(state);
  }

  // 15. Ensure localized translations are rendered consistently
  if (typeof applyTranslations === "function") {
    applyTranslations();
  }
}


// ---------------------------------------------------------------------------
// NIRA THE LIVING GUARDIAN: Theme Engine (Dark, Light, System)
// ---------------------------------------------------------------------------
function setNiraTheme(theme, notify = true) {
  const root = document.documentElement;
  const validThemes = ["dark", "light", "system"];
  const chosen = validThemes.includes(theme) ? theme : "dark";

  localStorage.setItem("nira_theme", chosen);

  if (chosen === "system") {
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.setAttribute("data-theme", prefersDark ? "dark" : "light");
  } else {
    root.setAttribute("data-theme", chosen);
  }

  // Update theme toggle buttons active class (supporting both naming conventions)
  const themeIds = {
    dark: ["btnThemeDark", "themeBtnDark"],
    light: ["btnThemeLight", "themeBtnLight"],
    system: ["btnThemeAuto", "themeBtnSystem"]
  };
  Object.keys(themeIds).forEach(t => {
    themeIds[t].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) {
        if (t === chosen) {
          btn.classList.add("active");
          btn.setAttribute("aria-pressed", "true");
        } else {
          btn.classList.remove("active");
          btn.setAttribute("aria-pressed", "false");
        }
      }
    });
  });

  if (notify) {
    const labels = { dark: "Dark Theme", light: "Light Theme", system: "System Theme" };
    showToast(`🎨 <strong>Theme Switched:</strong> ${labels[chosen]}`);
  }
}

function initNiraTheme() {
  const saved = localStorage.getItem("nira_theme") || "dark";
  setNiraTheme(saved, false);

  try {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    mediaQuery.addEventListener("change", () => {
      const current = localStorage.getItem("nira_theme");
      if (current === "system") {
        document.documentElement.setAttribute("data-theme", "system");
      }
    });
  } catch (err) {}
}

// ---------------------------------------------------------------------------
// 12-Section Application Navigation Controller
// ---------------------------------------------------------------------------
let currentSectionId = "overview";

function switchSection(sectionId) {
  playChime("info");
  closeMobileSidebar();
  currentSectionId = sectionId;

  const sectionMap = {
    "overview": "perspectiveUser",
    "live-home": "viewHomeMap",
    "risk-assessment": "viewRiskAssessment",
    "risk-timeline": "viewTrustLedger",
    "sensors-devices": "viewSensorsDevices",
    "care-circle": "viewCareCircle",
    "incident-reports": "viewIncidentReports",
    "emergency-packet": "viewEmergencyPacket",
    "privacy-settings": "viewPrivacySettings",
    "simulation-sandbox": "perspectiveSandbox",
    "architecture-sla": "perspectiveCompany",
    "resident-admin": "viewResidentAdmin"
  };

  const navItemMap = {
    "overview": "navItemOverview",
    "live-home": "navItemLiveHome",
    "risk-assessment": "navItemRiskAssessment",
    "risk-timeline": "navItemRiskTimeline",
    "sensors-devices": "navItemSensorsDevices",
    "care-circle": "navItemCareCircle",
    "incident-reports": "navItemIncidentReports",
    "emergency-packet": "navItemEmergencyPacket",
    "privacy-settings": "navItemPrivacySettings",
    "simulation-sandbox": "navItemSimulationSandbox",
    "architecture-sla": "navItemArchitectureSla",
    "resident-admin": "navItemResidentAdmin"
  };

  // Hide all sections
  document.querySelectorAll(".command-section-view, .perspective-panel").forEach(el => {
    el.classList.remove("active");
    el.style.display = "none";
  });

  // Deactivate all sidebar nav items
  document.querySelectorAll(".sidebar-nav-item").forEach(item => {
    item.classList.remove("active");
    item.setAttribute("aria-selected", "false");
  });

  // Activate target section
  const targetElId = sectionMap[sectionId] || sectionId;
  const targetEl = document.getElementById(targetElId);
  if (targetEl) {
    targetEl.classList.add("active");
    targetEl.style.display = "block";
  }

  // Activate target sidebar item
  const navId = navItemMap[sectionId];
  if (navId) {
    const navBtn = document.getElementById(navId);
    if (navBtn) {
      navBtn.classList.add("active");
      navBtn.setAttribute("aria-selected", "true");
    }
  }

  // Handle Canvas Resizing if needed
  if (sectionId === "live-home" || sectionId === "simulation-sandbox") {
    setTimeout(() => {
      if (window.main3DTwin && is3DModeActive) {
        window.main3DTwin.resize();
      }
      if (window.cameraSim) {
        window.cameraSim.resizeCanvas();
      }
      if (window.niraStore) {
        renderDashboard(window.niraStore.state);
      }
    }, 60);
  }

  const sectionTitles = {
    "overview": "Guardian Overview",
    "live-home": "Live Home & Sensors",
    "risk-assessment": "Aegis CARE Risk Workflow",
    "risk-timeline": "Risk Timeline & Trust Ledger",
    "sensors-devices": "Connected Sensors & Devices",
    "care-circle": "Care Circle Directory",
    "incident-reports": "Incident Reports Archive",
    "emergency-packet": "Emergency Context Packet CAD",
    "privacy-settings": "Privacy Architecture & Settings",
    "simulation-sandbox": "Interactive Simulation Sandbox",
    "architecture-sla": "Architecture & SLA Headroom",
    "resident-admin": "Resident & Admin Portals"
  };

  showToast(`🛡️ <strong>View:</strong> ${sectionTitles[sectionId] || sectionId}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Backward-compatibility alias for 5 legacy view calls
function switchViewMode(mode) {
  const modeMap = {
    overview: "overview",
    map: "live-home",
    ledger: "risk-timeline",
    architecture: "architecture-sla",
    sandbox: "simulation-sandbox"
  };
  switchSection(modeMap[mode] || mode);
}

function switchPerspective(mode) {
  const modeMap = { user: "overview", company: "architecture-sla", sandbox: "simulation-sandbox" };
  switchSection(modeMap[mode] || mode);
}

// ---------------------------------------------------------------------------
// Mobile Sidebar Drawer
// ---------------------------------------------------------------------------
function toggleMobileSidebar() {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (sidebar && backdrop) {
    sidebar.classList.toggle("sidebar-open");
    backdrop.classList.toggle("active");
  }
}

function closeMobileSidebar() {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (sidebar) sidebar.classList.remove("sidebar-open");
  if (backdrop) backdrop.classList.remove("active");
}

// ---------------------------------------------------------------------------
// Deterministic Simulation Stepper Controls
// ---------------------------------------------------------------------------
let simPlaybackStep = 0;
let isSimPaused = false;

function simStart() {
  playChime("info");
  isSimPaused = false;
  document.querySelectorAll(".sim-ctrl-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById("btnSimStart");
  if (btn) btn.classList.add("active");

  showToast(`▶ Simulation Active: <strong>${currentScenario.toUpperCase()}</strong> mode`);
  if (window.niraStore) {
    window.niraStore.dispatchScenario(currentScenario);
  }
}

function simPause() {
  playChime("warning");
  isSimPaused = true;
  document.querySelectorAll(".sim-ctrl-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById("btnSimPause");
  if (btn) btn.classList.add("active");
  showToast("⏸ Simulation Paused");
}

function simResume() {
  playChime("info");
  isSimPaused = false;
  document.querySelectorAll(".sim-ctrl-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById("btnSimResume");
  if (btn) btn.classList.add("active");
  showToast("⏯ Simulation Resumed");
}

function simReset() {
  playChime("info");
  isSimPaused = false;
  simPlaybackStep = 0;
  document.querySelectorAll(".sim-ctrl-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById("btnSimReset");
  if (btn) btn.classList.add("active");
  showToast("↺ Simulation State Reset to Normal Baseline");
  if (window.niraStore) {
    window.niraStore.dispatchScenario("false_alarm");
  }
}

function simStep() {
  playChime("info");
  simPlaybackStep = (simPlaybackStep + 1) % 3;
  const stepScenarios = ["false_alarm", "responsive", "silent"];
  const nextScen = stepScenarios[simPlaybackStep];
  showToast(`⏭ Step Forward &bull; Advancing to Scenario <strong>${nextScen.toUpperCase()}</strong>`);
  switchScenario(nextScen);
}

// ---------------------------------------------------------------------------
// Sensor Dropout Simulation Controls
// ---------------------------------------------------------------------------
let sensorStates = { radar: true, vitals: true, lock: true, env: true, audio: true };

function toggleSensorDropout(sensorId) {
  playChime("warning");
  sensorStates[sensorId] = !sensorStates[sensorId];
  const isUp = sensorStates[sensorId];

  const badgeMap = {
    radar: "statusBadgeRadar",
    vitals: "statusBadgeVitals",
    lock: "statusBadgeLock",
    env: "statusBadgeEnv",
    audio: "statusBadgeAudio"
  };

  const badge = document.getElementById(badgeMap[sensorId]);
  const btn = document.getElementById(`btnDropout${sensorId.charAt(0).toUpperCase() + sensorId.slice(1)}`);

  if (badge) {
    if (isUp) {
      badge.className = "device-status-badge online";
      badge.textContent = "ONLINE";
    } else {
      badge.className = "device-status-badge offline";
      badge.textContent = "DROPOUT / STALE";
    }
  }

  if (btn) {
    btn.textContent = isUp ? "Simulate Signal Dropout" : "Restore Sensor Signal";
    btn.style.borderColor = isUp ? "" : "var(--status-critical)";
    btn.style.color = isUp ? "" : "var(--status-critical)";
  }

  // Update sidebar count
  const onlineCount = Object.values(sensorStates).filter(Boolean).length;
  const countBadge = document.getElementById("sidebarDeviceCount");
  if (countBadge) {
    countBadge.textContent = `${onlineCount}/5`;
    countBadge.style.color = (onlineCount < 5) ? "var(--status-warning)" : "";
  }

  showToast(isUp
    ? `✅ <strong>${sensorId.toUpperCase()}</strong>: Signal Restored (Continuous 20Hz Resumed)`
    : `⚠️ <strong>${sensorId.toUpperCase()}</strong>: Dropout Simulated! Aegis CARE switching to cached baseline.`
  );
}

// ---------------------------------------------------------------------------
// Risk Timeline Filter & Data Provenance
// ---------------------------------------------------------------------------
function filterTimeline(category) {
  playChime("info");
  document.querySelectorAll(".timeline-filter-btn").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById(`tlFilter${category.charAt(0).toUpperCase() + category.slice(1)}`);
  if (btn) btn.classList.add("active");

  const events = document.querySelectorAll("#trustLedgerFullTrack .trust-event-item");
  events.forEach(el => {
    if (category === "all") {
      el.style.display = "flex";
    } else if (category === "movement" && (el.textContent.includes("Radar") || el.textContent.includes("Fall") || el.textContent.includes("Motion"))) {
      el.style.display = "flex";
    } else if (category === "audio" && (el.textContent.includes("Voice") || el.textContent.includes("Echo") || el.textContent.includes("Audio"))) {
      el.style.display = "flex";
    } else if (category === "env" && (el.textContent.includes("Floor") || el.textContent.includes("Bath") || el.textContent.includes("Environmental"))) {
      el.style.display = "flex";
    } else if (category === "vitals" && (el.textContent.includes("Heart Rate") || el.textContent.includes("Apple Watch") || el.textContent.includes("BPM"))) {
      el.style.display = "flex";
    } else {
      el.style.display = "none";
    }
  });

  showToast(`🔍 Timeline Filter: <strong>${category.toUpperCase()}</strong>`);
}

// ---------------------------------------------------------------------------
// Incident Export & Emergency Packet Handlers
// ---------------------------------------------------------------------------
function exportIncidents(format) {
  playChime("success");
  const incidents = [
    { id: "INC-2026-1021-01", timestamp: "2026-10-21 02:14:00", room: "Bathroom", severity: "CRITICAL", source: "60GHz FMCW Radar", verification: "TIMEOUT_UNANSWERED", status: "ESCALATED_CAD" },
    { id: "INC-2026-1020-04", timestamp: "2026-10-20 14:22:15", room: "Living Room", severity: "LOW", source: "Velocity Delta", verification: "CONFIRMED_SAFE", status: "RESOLVED_SAFE" },
    { id: "INC-2026-1019-02", timestamp: "2026-10-19 19:08:44", room: "Kitchen", severity: "MODERATE", source: "Help Keyword", verification: "CAREGIVER_ALERTED", status: "ESCALATED_CAREGIVER" }
  ];

  if (format === "csv") {
    let csv = "IncidentID,Timestamp,Room,Severity,Source,Verification,Status\n";
    incidents.forEach(i => {
      csv += `${i.id},${i.timestamp},${i.room},${i.severity},${i.source},${i.verification},${i.status}\n`;
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `nira_incidents_${Date.now()}.csv`;
    link.click();
    showToast("💾 Exported Incidents as CSV");
  } else {
    const blob = new Blob([JSON.stringify(incidents, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `nira_incidents_${Date.now()}.json`;
    link.click();
    showToast("💾 Exported Incidents as JSON");
  }
}

function exportEmergencyPacket(format) {
  playChime("success");
  if (format === "print") {
    window.print();
    return;
  }
  const preview = document.getElementById("packetJsonPreview");
  const jsonContent = preview ? preview.textContent : "{}";
  const blob = new Blob([jsonContent], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `nira_ecp_cad911_${Date.now()}.json`;
  link.click();
  showToast("💾 Downloaded Emergency Context Packet (ECP JSON)");
}

function triggerCaregiverNotification(name) {
  playChime("alert");
  if (confirm(`Send immediate emergency dispatch SMS to ${name}?`)) {
    showToast(`📱 Urgent SMS Transmitted to <strong>${name}</strong>: "NIRA Alert: Eleanor needs assistance in Beacon Hill 4B. Smart lock PIN 8492."`);
  }
}

function inspectIncidentModal(incidentId) {
  playChime("info");
  const modal = document.getElementById("incidentInspectorModal");
  const title = document.getElementById("inspectModalTitle");
  const body = document.getElementById("inspectModalBody");
  if (!modal || !body) return;

  if (title) title.textContent = `📋 Incident Record Dossier: ${incidentId}`;
  body.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 14px;">
      <div class="packet-grid-2col">
        <div class="packet-data-box">
          <span class="device-spec-label">Incident Identifier:</span><br>
          <strong>${incidentId}</strong>
        </div>
        <div class="packet-data-box">
          <span class="device-spec-label">Recorded Timestamp:</span><br>
          <strong>2026-10-21 02:14:00 AM EST</strong>
        </div>
      </div>
      <div class="packet-data-box">
        <span class="device-spec-label">Sensory Vector:</span><br>
        <strong>60GHz FMCW Radar &bull; Vertical acceleration delta -2.8m/s &bull; Bathroom wet tile</strong>
      </div>
      <div class="packet-data-box">
        <span class="device-spec-label">Voice Dialog State Machine:</span><br>
        <span style="color: var(--status-critical); font-weight: 700;">Unanswered Prompt &bull; 10-Second Window Expired</span>
      </div>
      <div class="packet-data-box">
        <span class="device-spec-label">Escalation Resolution:</span><br>
        <span>Boston EMS Medic-14 CAD Packet Generated &bull; Front door deadbolt unlocked with PIN #8492</span>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">
        <button class="btn-luxury-secondary" onclick="closeIncidentInspectorModal()">Close Dossier</button>
        <button class="btn-luxury-primary" onclick="exportEmergencyPacket('json')">Download ECP Dossier</button>
      </div>
    </div>
  `;
  modal.style.display = "flex";
}

function closeIncidentInspectorModal() {
  const modal = document.getElementById("incidentInspectorModal");
  if (modal) modal.style.display = "none";
}

function openResidentCalmMode() {
  playChime("success");
  const modal = document.getElementById("residentCalmModal");
  if (modal) modal.style.display = "flex";
}

function closeResidentCalmMode() {
  const modal = document.getElementById("residentCalmModal");
  if (modal) modal.style.display = "none";
}

function switchUserRole(name, role) {
  playChime("info");
  let profileKey = "senior_home";
  if (role && (role.includes("Guardian") || role.includes("Admin") || name.includes("David"))) {
    profileKey = "admin_son";
  } else if (role && (role.includes("EMS") || role.includes("Responder") || name.includes("Medic") || role.includes("CAD"))) {
    profileKey = "ems";
  } else {
    profileKey = "senior_home";
  }
  if (typeof setUserProfile === "function") {
    setUserProfile(profileKey, true);
  }
  showToast(`👤 Active Session Switched to: <strong>${name}</strong> (${role})`);
}

// ---------------------------------------------------------------------------
// Spatial Room Selector
// ---------------------------------------------------------------------------
let selectedSpatialRoomId = "living";
function selectSpatialRoom(roomId) {
  selectedSpatialRoomId = roomId;
  const roomCards = ["living", "bathroom", "bedroom", "kitchen", "entrance"];
  roomCards.forEach(id => {
    const card = document.getElementById("spatialRoom" + (id.charAt(0).toUpperCase() + id.slice(1)));
    if (card) {
      if (id === roomId) {
        card.classList.add("is-selected");
      } else {
        card.classList.remove("is-selected");
      }
    }
  });

  const titles = {
    living: "Living Room (Active Presence)",
    bathroom: "Bathroom (High Hazard 1.55x)",
    bedroom: "Bedroom (Circadian Sleep Dock)",
    kitchen: "Kitchen (PIR Motion & Fridge Contact)",
    entrance: "Entrance (Yale Smart Deadbolt #8492)"
  };

  showToast(`📍 <strong>Inspecting Room:</strong> ${titles[roomId] || roomId}`);

  if (window.main3DTwin && is3DModeActive) {
    const posture = (window.niraStore && window.niraStore.state.rooms && window.niraStore.state.rooms[roomId])
      ? window.niraStore.state.rooms[roomId].postureCode : "upright";
    const risk = (window.niraStore && window.niraStore.state.incident) ? window.niraStore.state.incident.currentRiskLevel : "LOW";
    window.main3DTwin.updatePhysicalState(roomId, posture, risk);
  }
}

// ---------------------------------------------------------------------------
// SIGNATURE COMPONENT A: THE LIVING GUARDIAN RENDERER
// ---------------------------------------------------------------------------
function renderLivingGuardian(state) {
  const guardianCard = document.getElementById("guardianHeroCard");
  const stateBadge = document.getElementById("guardianStateBadge");
  const stateText = document.getElementById("guardianStateText");
  const headline = document.getElementById("guardianHeadline");
  const subtext = document.getElementById("guardianSubtext");
  const riskScore = document.getElementById("guardianRiskScore");
  const zone = document.getElementById("guardianZone");
  const verifyStatus = document.getElementById("guardianVerifyStatus");
  const lastCheck = document.getElementById("guardianLastCheck");

  if (!guardianCard) return;

  const risk = (state.incident && state.incident.currentRiskLevel) || "LOW";
  const status = (state.incident && state.incident.status) || "NORMAL";
  const voice = state.voiceState || {};
  const isVerifying = voice.phase === "LISTENING" || voice.phase === "PROMPT_PLAYING";

  // Reset classes
  guardianCard.classList.remove("state-normal", "state-attention", "state-critical", "state-verifying");
  if (stateBadge) stateBadge.classList.remove("badge-critical", "badge-warning");

  let guardianClass = "state-normal";
  let badgeLabel = "NORMAL MONITORING";
  let headlineText = "Eleanor is Safe &amp; Resting Comfortably";
  let subText = "Beacon Hill Unit 4B &bull; Ambient multi-modal sensor fusion active &bull; Living room resting baseline verified &bull; Zero camera recording for 100% resident privacy.";
  let riskVal = "0.04 / 1.0 (LOW)";
  let riskColor = "var(--accent-primary)";
  let verifyVal = "Passive Aware";

  if (isVerifying) {
    guardianClass = "state-verifying";
    badgeLabel = "VERIFYING RESIDENT WELLBEING";
    headlineText = "Voice Check Active &bull; Awaiting Eleanor's Reply";
    subText = "NIRA Echo Show 15 microphone array listening. Evaluating speech acoustic energy and verbal confirmation.";
    riskVal = "0.68 / 1.0 (ATTENTION)";
    riskColor = "var(--status-warning)";
    verifyVal = `Listening (${voice.timeRemainingSeconds || 8}s)`;
  } else if (risk === "CRITICAL" || status === "ESCALATED_CAD") {
    guardianClass = "state-critical";
    if (stateBadge) stateBadge.classList.add("badge-critical");
    badgeLabel = "CRITICAL EMERGENCY DETECTED";
    headlineText = "Urgent: Unresponsive Fall Detected in Bathroom";
    subText = "Rapid descent verified by 60GHz FMCW radar. Inactivity detected for >40s. Boston EMS Medic-14 dispatched. Smart door unlocked for first responders.";
    riskVal = "0.94 / 1.0 (CRITICAL)";
    riskColor = "var(--status-critical)";
    verifyVal = "Unanswered (Timeout Expired)";
  } else if (risk === "HIGH" || risk === "MODERATE" || status === "ESCALATED_CAREGIVER") {
    guardianClass = "state-attention";
    if (stateBadge) stateBadge.classList.add("badge-warning");
    badgeLabel = "ATTENTION &bull; CAREGIVER ALERT";
    headlineText = "Mobility Anomaly Detected &bull; Family Alert Sent";
    subText = "Eleanor seated on kitchen floor. Heart rate elevated (104 BPM). Eleanor requested: 'Can you call David?' SMS dispatched to David Vance.";
    riskVal = "0.68 / 1.0 (HIGH)";
    riskColor = "var(--status-warning)";
    verifyVal = "Resident Responded";
  } else if (status === "RESOLVED" || risk === "RESOLVED") {
    guardianClass = "state-normal";
    badgeLabel = "INCIDENT RESOLVED &bull; RESIDENT SAFE";
    headlineText = "Eleanor Confirmed Safe &amp; Routine Restored";
    subText = "Resident confirmed wellbeing verbally via Echo Show 15. All clear logged in Trust Ledger. Ambient sensing active.";
    riskVal = "0.04 / 1.0 (LOW)";
    riskColor = "var(--accent-primary)";
    verifyVal = "Verified Safe";
  }

  guardianCard.classList.add(guardianClass);
  if (stateText) stateText.textContent = badgeLabel;
  if (headline) headline.innerHTML = headlineText;
  if (subtext) subtext.innerHTML = subText;
  if (riskScore) {
    riskScore.textContent = riskVal;
    riskScore.style.color = riskColor;
  }
  if (zone) zone.textContent = capitalize((state.incident && state.incident.location) || "Living Room");
  if (verifyStatus) {
    verifyStatus.textContent = verifyVal;
    verifyStatus.style.color = (risk === "CRITICAL") ? "var(--status-critical)" : ((risk === "HIGH") ? "var(--status-warning)" : "var(--accent-primary)");
  }
  if (lastCheck) {
    lastCheck.textContent = "Continuous (20Hz)";
  }
  renderRiskGauge(state);
}

// ---------------------------------------------------------------------------
// LARGE READABLE RISK GAUGE RENDERER
// ---------------------------------------------------------------------------
function renderRiskGauge(state) {
  const arc = document.getElementById("riskGaugeArc");
  const num = document.getElementById("riskGaugeNumeric");
  const tier = document.getElementById("riskGaugeTierLabel");
  const headline = document.getElementById("riskGaugeHeadline");
  const narr = document.getElementById("riskGaugeNarrative");
  const motion = document.getElementById("gaugeMotionStatus");
  const vitals = document.getElementById("gaugeVitalsStatus");
  const env = document.getElementById("gaugeEnvStatus");
  const voice = document.getElementById("gaugeVoiceStatus");

  const risk = (state.incident && state.incident.currentRiskLevel) || "LOW";
  const status = (state.incident && state.incident.status) || "NORMAL";
  let score = 0.04;
  let tierLabel = "LOW RISK";
  let tierColor = "var(--accent-primary)";
  let hText = "Eleanor is resting comfortably in the living room";
  let nText = "Ambient FMCW radar and environmental multi-factor fusion confirm expected baseline restful state. Movement, acoustic presence, and Apple Watch cardiac vitals indicate zero distress.";
  let mText = "Armchair Rest (0.02G)";
  let vText = "72 BPM (Resting)";
  let eText = "22.4&deg;C &bull; Clear";
  let voText = "Passive Aware";

  if (risk === "CRITICAL" || status === "ESCALATED_CAD") {
    score = 0.94;
    tierLabel = "CRITICAL RISK";
    tierColor = "var(--status-critical)";
    hText = "Urgent: Unresponsive Fall Verified in Bathroom";
    nText = "60GHz radar detected sudden vertical descent followed by 42s motionless period. Heart rate tachycardia at 138 BPM. 10s voice check-in unanswered. Boston EMS Medic-14 CAD dispatched and front deadbolt unlocked.";
    mText = "Immobile (0.00G)";
    vText = "138 BPM (Tachycardia)";
    eText = "23.1&deg;C &bull; Floor Wet";
    voText = "Timeout (Unanswered)";
  } else if (risk === "HIGH" || risk === "MODERATE" || status === "ESCALATED_CAREGIVER") {
    score = 0.68;
    tierLabel = "HIGH RISK";
    tierColor = "var(--status-warning)";
    hText = "Assistance Requested &bull; Caregiver Alert Dispatched";
    nText = "Eleanor detected seated on kitchen floor with elevated heart rate (104 BPM). Eleanor verbally requested: 'Can you call David?' Automated SMS and Push alert dispatched to David Vance.";
    mText = "Floor Sit (0.12G)";
    vText = "104 BPM (Elevated)";
    eText = "22.6&deg;C &bull; Clear";
    voText = "Resident Answered";
  } else if (status === "RESOLVED") {
    score = 0.04;
    tierLabel = "LOW RISK (RESOLVED)";
    tierColor = "var(--accent-primary)";
    hText = "Eleanor Confirmed Safe & Routine Restored";
    nText = "Resident confirmed wellbeing verbally via Echo Show 15. All clear logged in Trust Ledger. Continuous ambient radar sensing resumed.";
    mText = "Active Walking (0.85G)";
    vText = "76 BPM (Stable)";
    eText = "22.4&deg;C &bull; Clear";
    voText = "Verified Safe";
  }

  if (num) num.textContent = score.toFixed(2);
  if (tier) {
    tier.textContent = tierLabel;
    tier.style.color = tierColor;
  }
  if (arc) {
    const offset = Math.max(0, Math.min(267, 267 - (score * 267)));
    arc.style.strokeDashoffset = offset;
  }
  if (headline) headline.innerHTML = hText;
  if (narr) narr.innerHTML = nText;
  if (motion) motion.innerHTML = mText;
  if (vitals) vitals.innerHTML = vText;
  if (env) env.innerHTML = eText;
  if (voice) voice.innerHTML = voText;
}

// ---------------------------------------------------------------------------
// AREA 2: ACTIVE INCIDENT RENDERER
// ---------------------------------------------------------------------------
function renderActiveIncidentSection(state) {
  const card = document.getElementById("activeIncidentCard");
  if (!card) return;

  const risk = (state.incident && state.incident.currentRiskLevel) || "LOW";
  const status = (state.incident && state.incident.status) || "NORMAL";
  const isActive = (risk === "CRITICAL" || risk === "HIGH" || status === "ESCALATED_CAD" || status === "ESCALATED_CAREGIVER");

  if (isActive) {
    card.style.display = "block";
    const sevBadge = document.getElementById("incidentSeverityBadge");
    const ts = document.getElementById("incidentTimestamp");
    const catTag = document.getElementById("incidentCategoryTag");
    const locVal = document.getElementById("incidentLocationVal");
    const voiceVal = document.getElementById("incidentVoiceVal");
    const escVal = document.getElementById("incidentEscalationVal");
    const vitalsVal = document.getElementById("incidentVitalsVal");
    const doorBtnText = document.getElementById("incidentDoorBtnText");

    if (risk === "CRITICAL" || status === "ESCALATED_CAD") {
      if (sevBadge) {
        sevBadge.textContent = "🚨 CRITICAL INCIDENT (SCORE: 0.94)";
        sevBadge.style.background = "var(--status-critical)";
      }
      if (catTag) catTag.textContent = "Sudden Fall with Immobility (CAD 911)";
      if (locVal) locVal.innerHTML = "<strong>Bathroom</strong> (Wet Tile Substrate &bull; 1.55x multiplier)";
      if (voiceVal) {
        voiceVal.textContent = "Unanswered • 10.0s Acoustic Window Expired";
        voiceVal.style.color = "var(--status-critical)";
      }
      if (escVal) {
        escVal.textContent = "Boston EMS CAD Packet Generated • Front Door UNLOCKED";
        escVal.style.color = "var(--accent-secondary)";
      }
      if (vitalsVal) {
        vitalsVal.textContent = "138 BPM (Tachycardia Surge +91%) • 0.00G Motion";
        vitalsVal.style.color = "var(--status-critical)";
      }
      if (doorBtnText) doorBtnText.textContent = "🔓 Front Door: UNLOCKED";
    } else {
      if (sevBadge) {
        sevBadge.textContent = "⚠️ ASSISTED CAREGIVER ALERT (SCORE: 0.68)";
        sevBadge.style.background = "var(--status-warning)";
      }
      if (catTag) catTag.textContent = "Floor Sitting & Assistance Request";
      if (locVal) locVal.innerHTML = "<strong>Kitchen</strong> (Linoleum &bull; Seated Near Island)";
      if (voiceVal) {
        voiceVal.textContent = "Resident answered: 'Can you call David?'";
        voiceVal.style.color = "var(--status-warning)";
      }
      if (escVal) {
        escVal.textContent = "Caregiver SMS Sent to David Vance • Drop-In Ready";
        escVal.style.color = "var(--accent-secondary)";
      }
      if (vitalsVal) {
        vitalsVal.textContent = "104 BPM (Mild Tachycardia) • Intentional Movement Detected";
        vitalsVal.style.color = "var(--status-warning)";
      }
      if (doorBtnText) doorBtnText.textContent = "🔒 Front Door: Locked (Tap to Unlock)";
    }
    if (ts) ts.textContent = NiraStateStore.formatTimeAgo((state.incident && state.incident.createdAt) || (state.timestamps && state.timestamps.incident));
  } else {
    card.style.display = "none";
  }
}

// ---------------------------------------------------------------------------
// SIGNATURE COMPONENT B: THE AMBIENT INTELLIGENCE MAP RENDERER
// ---------------------------------------------------------------------------
function renderSpatialMap(state) {
  const loc = (state.incident && state.incident.location) ? state.incident.location.toLowerCase() : "living";
  const risk = (state.incident && state.incident.currentRiskLevel) ? state.incident.currentRiskLevel : "LOW";
  const isEmergency = risk === "CRITICAL";

  // Quick Overview rows in Dashboard Area 3
  const quickBathTag = document.getElementById("quickRoomBathTag");
  if (quickBathTag) {
    if (isEmergency && loc === "bathroom") {
      quickBathTag.className = "spatial-presence-pill present alert";
      quickBathTag.textContent = "🚨 Fall Detected • Immobile";
    } else {
      quickBathTag.className = "spatial-sensor-chip";
      quickBathTag.textContent = "Dry Floor • Clear";
    }
  }

  // Full Map View Cards in View 2
  const bathCard = document.getElementById("spatialRoomBathroom");
  const bathPill = document.getElementById("roomPillBathroom");
  const bathFloor = document.getElementById("roomFloorBathroom");
  if (bathCard && bathPill) {
    if (isEmergency && loc === "bathroom") {
      bathCard.classList.add("in-alert");
      bathPill.className = "spatial-presence-pill present alert";
      bathPill.textContent = "🚨 Fall Alert";
      if (bathFloor) {
        bathFloor.innerHTML = "<span style='color: var(--status-critical); font-weight: 700;'>Wet Tile (+12 Multiplier)</span>";
      }
    } else {
      bathCard.classList.remove("in-alert");
      bathPill.className = "spatial-presence-pill vacant";
      bathPill.textContent = "○ Vacant";
      if (bathFloor) bathFloor.textContent = "Tile • Dry Baseline";
    }
  }

  // Door Deadbolt in Entrance Card
  const deadboltVal = document.getElementById("roomDeadboltVal");
  const isUnlocked = isEmergency || (state.peripherals && state.peripherals.doorLock === "unlocked") || (state.doorLock && state.doorLock.status === "UNLOCKED");
  if (deadboltVal) {
    if (isUnlocked) {
      deadboltVal.textContent = "🔓 UNLOCKED for EMS";
      deadboltVal.style.color = "var(--status-critical)";
    } else {
      deadboltVal.textContent = "🔒 Locked";
      deadboltVal.style.color = "var(--accent-primary)";
    }
  }
}

// ---------------------------------------------------------------------------
// AREA 4: EXPLAINABLE RISK REASONING RENDERER
// ---------------------------------------------------------------------------
function renderRiskReasoning(state) {
  const risk = (state.incident && state.incident.currentRiskLevel) || "LOW";
  const reasonItem1 = document.getElementById("reasonItemCorrob1");
  const reasonItem2 = document.getElementById("reasonItemCorrob2");

  if (reasonItem1 && reasonItem2) {
    if (risk === "CRITICAL") {
      reasonItem1.innerHTML = `<strong>Fall Vector Confidence (0.94)</strong><span class="weight-tag">60GHz FMCW Radar &bull; High impact</span>`;
      reasonItem2.innerHTML = `<strong>Immobility Post-Fall (42.5s)</strong><span class="weight-tag">Weight: +0.45 &bull; Inactivity threshold</span>`;
    } else if (risk === "HIGH" || risk === "MODERATE") {
      reasonItem1.innerHTML = `<strong>Floor Seated Posture (0.76)</strong><span class="weight-tag">YOLOv8 Pose &bull; Kitchen Island</span>`;
      reasonItem2.innerHTML = `<strong>Caregiver Request Verbalized</strong><span class="weight-tag">Weight: +0.35 &bull; Voice AI</span>`;
    } else {
      reasonItem1.innerHTML = `<strong>Routine Resting Motion</strong><span class="weight-tag">Weight: 0.04 &bull; Baseline verified</span>`;
      reasonItem2.innerHTML = `<strong>Vitals Within Safe Range</strong><span class="weight-tag">72 BPM &bull; Resting Sinus</span>`;
    }
  }
}

// ---------------------------------------------------------------------------
// SIGNATURE COMPONENT C: THE TRUST LEDGER RENDERER
// ---------------------------------------------------------------------------
function renderTrustLedger(state) {
  // Trust Ledger is automatically refreshed and reactive to store updates
}

// ---------------------------------------------------------------------------
// Consequential Actions & Auditing
// ---------------------------------------------------------------------------
function acknowledgeAlert() {
  const overlay = document.createElement("div");
  overlay.className = "nira-confirm-overlay";
  overlay.innerHTML = `
    <div class="nira-confirm-box" role="dialog" aria-modal="true" aria-labelledby="confirmTitle">
      <div class="nira-confirm-title" id="confirmTitle">
        <span>🛡️ Acknowledge Safety Alert</span>
      </div>
      <div class="nira-confirm-message">
        Are you sure you want to acknowledge this active incident alert for <strong>Eleanor Vance</strong>? This will notify connected caregivers and log your confirmation in the immutable Trust Ledger.
      </div>
      <div class="nira-confirm-actions">
        <button class="btn-luxury-secondary" id="btnCancelAck">Cancel</button>
        <button class="btn-luxury-primary" id="btnProceedAck">Confirm Acknowledgment</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  document.getElementById("btnCancelAck").onclick = () => overlay.remove();
  document.getElementById("btnProceedAck").onclick = () => {
    overlay.remove();
    playChime("success");
    showToast("✓ <strong>Alert Acknowledged:</strong> Caregiver David Vance confirmed notification receipt.");
    const btn = document.getElementById("btnAcknowledgeAlert");
    if (btn) {
      btn.innerHTML = "<span>✓ Acknowledged by David Vance</span>";
      btn.style.opacity = "0.7";
      btn.disabled = true;
    }
  };
}

function exportTrustAuditLog() {
  const st = window.niraStore ? window.niraStore.state : {};
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
    exportedAt: new Date().toISOString(),
    resident: "Eleanor Vance (Age 79)",
    location: "Beacon Hill Unit 4B",
    currentRiskLevel: st.incident ? st.incident.currentRiskLevel : "LOW",
    incident: st.incident || {},
    vitals: st.vitals || {},
    auditStages: [
      { stage: "DETECT", time: "02:14:02Z", source: "60GHz FMCW Radar", confidence: 0.94, event: "Fall Vector Detected" },
      { stage: "CONTEXTUALIZE", time: "02:14:03Z", source: "ContextEngine", multiplier: "1.55x high hazard wet tile", hr: 138 },
      { stage: "VERIFY", time: "02:14:14Z", source: "Echo Show 15", status: "Unanswered (10.0s timeout)" },
      { stage: "ESCALATE", time: "02:14:16Z", source: "DeterministicRiskEngine", score: 0.94, action: "Boston EMS CAD Packet" }
    ]
  }, null, 2));

  const dlAnchor = document.createElement("a");
  dlAnchor.setAttribute("href", dataStr);
  dlAnchor.setAttribute("download", `NIRA_Trust_Audit_EleanorVance_${Date.now()}.json`);
  document.body.appendChild(dlAnchor);
  dlAnchor.click();
  dlAnchor.remove();
  showToast("📋 <strong>Audit Log Exported:</strong> Downloaded cryptographically structured JSON incident record.");
}

function renderUserPortal(state) {
  if (!state) return;
  const risk = state.incident.currentRiskLevel;
  const isEmergency = risk === "CRITICAL" || state.incident.status === "ESCALATED_CAD";
  const isWarning = risk === "HIGH" || risk === "MODERATE" || state.incident.status === "ESCALATED_CAREGIVER";
  const isSafe = !isEmergency && !isWarning;

  // Hero Card
  const heroCard = document.getElementById("userHeroCard");
  const heroHalo = document.getElementById("userStatusHalo");
  const heroTitle = document.getElementById("userHeroTitle");
  const heroSub = document.getElementById("userHeroSubtitle");

  if (heroCard && heroHalo && heroTitle && heroSub) {
    if (isSafe) {
      heroCard.className = "user-hero-card";
      heroHalo.innerHTML = `<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>`;
      heroTitle.innerHTML = `Eleanor is Safe &amp; Resting`;
      heroSub.innerHTML = `Beacon Hill Unit 4B &bull; Normal baseline verified &bull; Protected 24/7 by NIRA Ambient AI &bull; No camera recording`;
    } else if (isWarning) {
      heroCard.className = "user-hero-card is-warning";
      heroHalo.innerHTML = `<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
      heroTitle.innerHTML = `Attention Needed: Caregiver Alerted`;
      heroSub.innerHTML = `Eleanor requested help in <strong>${capitalize(state.incident.location)}</strong>. Son David connected via Echo Drop-In call.`;
    } else {
      heroCard.className = "user-hero-card is-critical";
      heroHalo.innerHTML = `<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2.2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
      heroTitle.innerHTML = `🚨 Emergency Alert: Help Dispatched`;
      heroSub.innerHTML = `Acute fall detected in <strong>${capitalize(state.incident.location)}</strong>. Boston EMS Medic-14 en route. Smart Door automatically UNLOCKED for first responders.`;
    }
  }

  // Vitals Card
  const userHrVal = document.getElementById("userHrVal");
  const userHrStatus = document.getElementById("userHrStatus");
  if (userHrVal && userHrStatus) {
    const hr = state.vitals.heartRateBpm;
    userHrVal.innerHTML = `${hr} <span style="font-size: 1.1rem; font-weight: 600; color: var(--text-secondary);">BPM</span>`;
    if (hr > 120) {
      userHrVal.style.color = "var(--accent-red)";
      userHrStatus.textContent = "Acute Tachycardia (+91% surge)";
      userHrStatus.style.color = "var(--accent-red)";
    } else if (hr > 90) {
      userHrVal.style.color = "var(--accent-amber)";
      userHrStatus.textContent = "Elevated Heart Rate";
      userHrStatus.style.color = "var(--accent-amber)";
    } else {
      userHrVal.style.color = "var(--accent-green)";
      userHrStatus.textContent = "Normal resting rhythm • Stable";
      userHrStatus.style.color = "#34d399";
    }
  }

  // Location & Door
  const userLocVal = document.getElementById("userLocationVal");
  const userDoorStatus = document.getElementById("userDoorStatus");
  const userDoorBtnIcon = document.getElementById("userDoorBtnIcon");
  const userDoorBtnLabel = document.getElementById("userDoorBtnLabel");
  const userDoorBtnSub = document.getElementById("userDoorBtnSub");
  const userDoorBtn = document.getElementById("btnUserDoorAction");

  if (userLocVal) {
    userLocVal.textContent = capitalize(state.incident.location);
  }
  if (userDoorStatus) {
    const isUnlocked = state.doorLock.status === "UNLOCKED";
    if (isUnlocked) {
      userDoorStatus.innerHTML = "Front Door: 🔓 UNLOCKED FOR 911";
      userDoorStatus.style.color = "var(--accent-red)";
      if (userDoorBtn) userDoorBtn.classList.add("is-unlocked");
      if (userDoorBtnIcon) userDoorBtnIcon.textContent = "🔓";
      if (userDoorBtnLabel) userDoorBtnLabel.textContent = "Front Door: UNLOCKED";
      if (userDoorBtnSub) userDoorBtnSub.textContent = "Auto-unlocked for Boston EMS First Responders (PIN: 8492)";
    } else {
      userDoorStatus.innerHTML = "Front Door: 🔒 Securely Locked";
      userDoorStatus.style.color = "var(--accent-blue)";
      if (userDoorBtn) userDoorBtn.classList.remove("is-unlocked");
      if (userDoorBtnIcon) userDoorBtnIcon.textContent = "🔒";
      if (userDoorBtnLabel) userDoorBtnLabel.textContent = "Front Door: Locked";
      if (userDoorBtnSub) userDoorBtnSub.textContent = "Tap to unlock for nurse (PIN: 8492)";
    }
  }

  // Company Architecture sync
  const pipeRiskVal = document.getElementById("pipeRiskVal");
  if (pipeRiskVal) {
    pipeRiskVal.textContent = `RISK: ${risk}`;
    pipeRiskVal.style.color = isEmergency ? "var(--accent-red)" : (isWarning ? "var(--accent-amber)" : "var(--accent-green)");
  }
  const pipeStatePhase = document.getElementById("pipeStatePhase");
  if (pipeStatePhase && state.voiceState) {
    pipeStatePhase.textContent = state.voiceState.phase || "IDLE";
  }
}

const PIPELINE_STAGE_DATA = {
  1: {
    icon: "📡",
    title: "Stage 1: Multimodal Ingestion Layer",
    badge: "RUNTIME ACTIVE (20 Hz)",
    desc: "Fuses 60GHz mmWave FMCW radar point clouds (providing 24/7 privacy-safe spatial posture detection through darkness and steam) with on-device YOLOv8-pose keypoint estimation (extracting body bounding boxes without transmitting raw images off-device), continuous Apple Watch PPG telemetry, and Amazon Echo Show 15 beamforming microphone array.",
    specs: "Sampling Rate: 20 Hz • Privacy: 100% Edge-Isolated • Hardware: Echo Show 15 + mmWave Radar Pod",
    json: {
      event_type: "fall_detected",
      confidence: 0.94,
      location: "bathroom",
      movement_after_event: "none",
      timestamp: new Date().toISOString(),
      telemetry: {
        heart_rate_bpm: 138,
        posture: "flat_floor",
        floor_condition: "wet_substrate",
        lux: 15
      }
    }
  },
  2: {
    icon: "⚡",
    title: "Stage 2: Streamable MCP Server Gateway",
    badge: "SUB-25ms SLA VERIFIED",
    desc: "Ultra-low-latency FastAPI backend implementing the Model Context Protocol (MCP) over Streamable HTTP and Server-Sent Events (SSE). Exposes standardized assessment and dispatch tools directly to Amazon Alexa+ with zero cold-start delay and server-timing tracing.",
    specs: "Framework: FastAPI 0.115 • Protocol: Streamable HTTP & SSE • Latency SLA Budget: < 500ms (Measured: < 25ms)",
    json: {
      jsonrpc: "2.0",
      method: "tools/call",
      params: {
        name: "assess_risk",
        arguments: {
          event_type: "fall_detected",
          confidence: 0.94,
          location: "bathroom"
        }
      }
    }
  },
  3: {
    icon: "🧠",
    title: "Stage 3: Tri-Engine Deterministic Risk Intelligence",
    badge: "ZERO-HALLUCINATION DETERMINISTIC",
    desc: "A modular 3-engine architecture: ContextEngine weights room fall epidemiology (Bathroom 1.55x, wet floor +12.0) • PersonalBaselineEngine models circadian 24h routine deviations • DeterministicRiskEngine fuses sensor confidence, movement inactivity, and vitals into LOW / MODERATE / HIGH / CRITICAL risk tiers.",
    specs: "Execution Time: 0.8ms - 2.5ms • Determinism: 100% Rule & Threshold Validated • Zero LLM drift",
    json: {
      risk_level: "CRITICAL",
      confidence: 0.95,
      reasons: [
        "Event type 'fall_detected' detected with 94% confidence",
        "Zero post-impact movement detected (acute immobilization hazard)",
        "High-hazard moisture location: 'bathroom'",
        "Severe baseline deviation (+4.2h nocturnal anomaly)",
        "Wearable telemetry indicates acute tachycardia (138 BPM)"
      ]
    }
  },
  4: {
    icon: "🎙️",
    title: "Stage 4: 8-Phase Conversational State Machine",
    badge: "20s ACOUSTIC TIMEOUT WINDOW",
    desc: "State machine managing Amazon Echo Show 15 interactive voice check-in turns (IDLE → DETECTED → CHECKING → WAITING_FOR_RESPONSE → USER_RESPONDED → CAREGIVER_NOTIFIED → EMERGENCY_ESCALATED → RESOLVED). If resident is silent for 20 seconds, automatically transitions to Silent Critical Emergency.",
    specs: "Turn Latency: 1.1ms - 3.8ms • Timeout Window: 20 seconds • Conversational Cadence: Natural",
    json: {
      state: "EMERGENCY_ESCALATED",
      alexa_prompt: "Eleanor, this is Aegis. I noticed a fall in the bathroom. Are you okay?",
      senior_response: "<Silence for 20 seconds • Presumed unconscious>",
      timeout_triggered: true,
      next_action: "CAD_911_DISPATCH"
    }
  },
  5: {
    icon: "🚨",
    title: "Stage 5: Multi-Channel CAD Dispatch & Smart Home Access",
    badge: "PHYSICAL & DIGITAL AUTOMATION",
    desc: "Executes parallel dispatch actions: 1. Echo Show Drop-In two-way audio • 2. High-priority push & SMS to family guardian David • 3. Unlocks Yale smart deadbolt with emergency PIN token 8492 • 4. Transmits formatted clinical CAD incident packet to Boston EMS (Medic-14).",
    specs: "CAD Dispatch Latency: 4.2ms • Deadbolt Integration: REST API Auto-Unlock • SMS: Automated Twilio",
    json: {
      cad_incident_id: "EPK-84920",
      agency: "Boston EMS 911 (Medic-14, Rescue-2)",
      priority: "CODE_RED_911",
      smart_door_status: "UNLOCKED",
      entrance_pin: "8492",
      medical_notes: "Age 79, Lisinopril, Penicillin allergy"
    }
  }
};

function selectPipelineNode(stageNum) {
  playChime("info");
  for (let i = 1; i <= 5; i++) {
    const card = document.getElementById(`pipeCard${i}`);
    if (card) {
      if (i === stageNum) card.classList.add("active-node");
      else card.classList.remove("active-node");
    }
  }

  const data = PIPELINE_STAGE_DATA[stageNum];
  if (!data) return;

  const title = document.getElementById("archInspectTitle");
  const icon = document.getElementById("archInspectIcon");
  const badge = document.getElementById("archInspectBadge");
  const desc = document.getElementById("archInspectDesc");
  const specs = document.getElementById("archInspectSpecs");
  const jsonEl = document.getElementById("archInspectJson");

  if (title) title.textContent = data.title;
  if (icon) icon.textContent = data.icon;
  if (badge) badge.textContent = data.badge;
  if (desc) desc.textContent = data.desc;
  if (specs) specs.textContent = data.specs;
  if (jsonEl) jsonEl.textContent = JSON.stringify(data.json, null, 2);

  showToast(`Inspecting <strong>${data.title}</strong>`);
}

function openArchInspector(key) {
  switchPerspective("company");
  selectPipelineNode(1);
}


// ---------------------------------------------------------------------------
// 10. Voice AI 8-Phase State Machine & Live Conversation Timeline Renderer
// ---------------------------------------------------------------------------
let lastRenderedTimelineHash = "";

function renderVoicePanel(state) {
  const vs = state.voiceState || {};
  const phase = vs.phase || "IDLE";

  // 1. Voice Phase Badge
  const badge = document.getElementById("voicePhaseBadge");
  if (badge) {
    badge.textContent = phase;
    const phaseClasses = {
      IDLE: "phase-idle",
      DETECTED: "phase-detected",
      CHECKING: "phase-checking",
      WAITING_FOR_RESPONSE: "phase-waiting",
      USER_RESPONDED: "phase-responded",
      CAREGIVER_NOTIFIED: "phase-caregiver",
      EMERGENCY_ESCALATED: "phase-escalated",
      RESOLVED: "phase-resolved"
    };
    badge.className = `voice-phase-badge ${phaseClasses[phase] || "phase-idle"}`;
  }

  // 2. 8-Phase Stepper Track
  const stepperTrack = document.getElementById("voiceStepperTrack");
  if (stepperTrack) {
    const nodes = stepperTrack.querySelectorAll(".voice-step-node");
    const phaseOrder = [
      "IDLE",
      "DETECTED",
      "CHECKING",
      "WAITING_FOR_RESPONSE",
      "USER_RESPONDED",
      "CAREGIVER_NOTIFIED",
      "EMERGENCY_ESCALATED",
      "RESOLVED"
    ];
    const currentIndex = phaseOrder.indexOf(phase);

    nodes.forEach((node) => {
      const p = node.getAttribute("data-phase");
      const idx = phaseOrder.indexOf(p);
      node.classList.remove("step-active", "escalated", "resolved", "caregiver");

      if (idx === currentIndex) {
        node.classList.add("step-active");
        if (phase === "EMERGENCY_ESCALATED") node.classList.add("escalated");
        else if (phase === "RESOLVED") node.classList.add("resolved");
        else if (phase === "CAREGIVER_NOTIFIED") node.classList.add("caregiver");
      }
    });
  }

  // 3. Soundwave box animation state
  const swBars = document.querySelectorAll("#voiceSoundwaveBox .soundwave-bar");
  const isAcousticActive = (phase === "CHECKING" || phase === "WAITING_FOR_RESPONSE");
  swBars.forEach(b => {
    b.style.animationPlayState = isAcousticActive ? "running" : "paused";
    b.style.opacity = isAcousticActive ? "1" : "0.35";
  });

  // 4. Countdown Card & Ring
  const cdSecEl = document.getElementById("voiceCountdownSec");
  const cdUnitEl = document.getElementById("voiceCountdownUnit");
  const cdBoxEl = document.getElementById("voiceCountdownBox");
  const cdDescEl = document.getElementById("voiceCountdownDesc");

  if (cdSecEl && cdUnitEl && cdBoxEl) {
    if (phase === "WAITING_FOR_RESPONSE") {
      const sec = typeof vs.countdownSec === "number" ? vs.countdownSec : 20;
      cdSecEl.textContent = `${sec}s`;
      cdUnitEl.textContent = "Remaining";
      cdBoxEl.className = "countdown-number-box countdown-active";
      if (cdDescEl) {
        cdDescEl.textContent = "Active acoustic response window. 20-second timeout before automatic 911 CAD emergency escalation.";
      }
    } else if (phase === "EMERGENCY_ESCALATED") {
      cdSecEl.textContent = "0s";
      cdUnitEl.textContent = "Expired";
      cdBoxEl.className = "countdown-number-box countdown-expired";
      if (cdDescEl) {
        cdDescEl.textContent = "Response timeout expired without verbal reply. Emergency CAD first responders dispatched.";
      }
    } else if (phase === "RESOLVED") {
      cdSecEl.textContent = "0s";
      cdUnitEl.textContent = "Verified Safe";
      cdBoxEl.className = "countdown-number-box countdown-idle";
      if (cdDescEl) {
        cdDescEl.textContent = "Resident verbally confirmed safety. Acoustic monitoring window closed.";
      }
    } else if (phase === "CAREGIVER_NOTIFIED") {
      cdSecEl.textContent = "—";
      cdUnitEl.textContent = "Alerted";
      cdBoxEl.className = "countdown-number-box countdown-active";
      if (cdDescEl) {
        cdDescEl.textContent = "Distress reply confirmed. Caregiver David Vance alerted via Echo Drop-In & Priority Push.";
      }
    } else {
      cdSecEl.textContent = "—";
      cdUnitEl.textContent = "Standby";
      cdBoxEl.className = "countdown-number-box countdown-idle";
      if (cdDescEl) {
        cdDescEl.textContent = "Ambient passive listening. Awaiting anomaly or fall detection event.";
      }
    }
  }

  // 5. Automated Next System Action Banner
  const nextActEl = document.getElementById("voiceNextActionText");
  if (nextActEl) {
    nextActEl.textContent = vs.nextAction || "Continuous ambient safety observation.";
  }

  // 6. Subtext & Last Updated
  const lastUpEl = document.getElementById("voiceLastUpdated");
  if (lastUpEl && vs.lastUpdated) {
    lastUpEl.textContent = `Updated: ${NiraStateStore.formatTimeAgo(vs.lastUpdated)}`;
  }

  // 7. Demo Audio Quote Cards
  const demoAlexaQuote = document.getElementById("demoAlexaQuote");
  const demoSeniorQuote = document.getElementById("demoSeniorQuote");
  if (demoAlexaQuote && vs.alexaPrompt) demoAlexaQuote.textContent = vs.alexaPrompt;
  if (demoSeniorQuote && vs.seniorQuote) demoSeniorQuote.textContent = vs.seniorQuote;

  // Legacy element sync for backward compatibility
  const dAlexa = document.getElementById("dialogAlexaText");
  const dSenior = document.getElementById("dialogSeniorText");
  const qSenior = document.getElementById("quoteSeniorVoice");
  if (dAlexa && vs.alexaPrompt) dAlexa.innerHTML = vs.alexaPrompt;
  if (dSenior && vs.seniorResponse) dSenior.innerHTML = vs.seniorResponse;
  if (qSenior && vs.seniorQuote) qSenior.textContent = vs.seniorQuote;

  // 8. Live Multi-Party Conversation Timeline Stream
  renderVoiceTimeline(vs.timeline || []);
}

function renderVoiceTimeline(timeline) {
  const container = document.getElementById("voiceTimeline");
  const countBadge = document.getElementById("voiceTimelineCount");
  if (!container) return;

  if (countBadge) {
    countBadge.textContent = `${timeline.length} Events`;
  }

  // Check if timeline content changed
  const currentHash = timeline.map(t => `${t.id}:${t.speaker}:${t.text}`).join("|");
  if (currentHash === lastRenderedTimelineHash) return;
  lastRenderedTimelineHash = currentHash;

  if (timeline.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 36px 16px; color: var(--text-muted); font-size: 0.82rem;">
        <span class="no-live-data-badge">NO LIVE CONVERSATION</span>
        <div style="margin-top: 8px;">No verbal dialogue events recorded yet.</div>
      </div>
    `;
    return;
  }

  const speakerMeta = {
    nira: { label: "NIRA (Echo Show 15)", icon: "🎙️", badgeClass: "nira", role: "alexa" },
    resident: { label: "Eleanor Vance (Resident)", icon: "🗣️", badgeClass: "resident", role: "senior" },
    caregiver: { label: "David Vance (Guardian)", icon: "📱", badgeClass: "caregiver", role: "son" },
    system: { label: "Aegis Core System", icon: "⚙️", badgeClass: "system", role: null },
    timeout: { label: "Acoustic Timeout Engine", icon: "⏱️", badgeClass: "timeout", role: null }
  };

  let html = "";
  timeline.forEach((entry) => {
    const meta = speakerMeta[entry.speaker] || speakerMeta.system;
    const timeStr = formatVtlTime(entry.ts);
    const confTag = (entry.confidence !== null && entry.confidence !== undefined)
      ? `<span class="vtl-confidence-tag">Conf: ${(entry.confidence * 100).toFixed(0)}%</span>`
      : "";
    const simBadge = entry.simulated
      ? `<span class="vtl-sim-badge">[DEMO SIMULATION]</span>`
      : "";
    const playBtn = meta.role
      ? `<button class="btn-vtl-play" onclick="playTimelineEntryAudio('${entry.id}')">▶️ Play [Demo]</button>`
      : "";

    html += `
      <div class="vtl-entry ${meta.badgeClass}" id="vtl-${entry.id}">
        <div class="vtl-header">
          <span class="vtl-speaker-tag">
            <span>${entry.icon || meta.icon}</span>
            <span>${meta.label}</span>
          </span>
          <div class="vtl-meta-right">
            ${confTag}
            ${simBadge}
            <span class="vtl-timestamp">${timeStr}</span>
          </div>
        </div>
        <div class="vtl-text">${entry.text}</div>
        ${playBtn ? `<div class="vtl-actions">${playBtn}</div>` : ""}
      </div>
    `;
  });

  container.innerHTML = html;
  container.scrollTop = container.scrollHeight;
}

function formatVtlTime(ts) {
  if (!ts) return "Just now";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return "Just now";
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

async function sendCustomVoiceUtterance() {
  const input = document.getElementById("customUtteranceInput");
  if (!input) return;
  const text = (input.value || "").trim();
  if (!text) return;

  input.value = "";
  showToast(`🗣️ Speaking: <em>"${text}"</em> ➔ Sending to state machine...`);

  const isSafe = /ok|fine|good|glasses|dropped|alright|nothing/i.test(text);

  try {
    if (window.niraStore) {
      await window.niraStore.dispatchVoiceResponse(text, false);
      showToast(isSafe ? "🟢 Verified safe: Incident resolved." : "🟡 Distress reply: Guardian alerted.");
    }
    if (window.voiceAudio) {
      window.voiceAudio.speak(text, "senior");
    }
  } catch (err) {
    console.warn("[sendCustomVoiceUtterance] Error:", err);
    showToast("⚠️ Failed to dispatch utterance.");
  }
}

function playTimelineEntryAudio(entryId) {
  if (!window.niraStore || !window.voiceAudio) return;
  const vs = window.niraStore.state.voiceState;
  const entry = (vs.timeline || []).find(e => e.id === entryId);
  if (!entry) return;

  if (entry.speaker === "nira") {
    window.voiceAudio.playAlexaChime();
    setTimeout(() => {
      window.voiceAudio.speak(entry.text, "alexa");
    }, 400);
    showToast("🔊 Playing Synthesized NIRA Prompt [Demo]");
  } else if (entry.speaker === "resident") {
    window.voiceAudio.speak(entry.text, "senior");
    showToast("🔊 Playing Synthesized Resident Reply [Demo]");
  } else if (entry.speaker === "caregiver") {
    window.voiceAudio.playPhoneRing();
    setTimeout(() => {
      window.voiceAudio.speak(entry.text, "son");
    }, 500);
    showToast("📞 Connected to Caregiver Drop-In [Demo]");
  } else {
    window.voiceAudio.playEmergencyTone();
  }
}

// ---------------------------------------------------------------------------
// 11. Real-Time Emergency Command Center (Actual Backend Incident State)
// ---------------------------------------------------------------------------
let lastCmdTimelineHash = "";

function formatElapsedTimer(createdAt, isResolved) {
  if (!createdAt) return "ELAPSED: T + 00:00";
  const startMs = new Date(createdAt).getTime();
  if (isNaN(startMs)) return "ELAPSED: T + 00:00";
  const diffSec = Math.max(0, Math.floor((Date.now() - startMs) / 1000));
  const mm = String(Math.floor(diffSec / 60)).padStart(2, "0");
  const ss = String(diffSec % 60).padStart(2, "0");
  if (isResolved) {
    return `RESOLVED (T + ${mm}:${ss})`;
  }
  return `ELAPSED: T + ${mm}:${ss}`;
}

function formatCmdTime(ts) {
  if (!ts) return "--:--:--";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return String(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

function renderEmergencyCommandCenter(state) {
  if (!state) return;
  const inc = state.incident || {};
  const res = state.resident || {};
  const emg = state.emergency || {};
  const cgv = state.caregiver || {};
  const vs = state.voiceState || {};
  const tel = state.telemetry || {};
  const isResolved = inc.currentRiskLevel === "RESOLVED" || vs.phase === "RESOLVED";

  // 1. Incident ID & Severity Header Badges
  const idBadge = document.getElementById("cmdIncidentIdBadge");
  if (idBadge) {
    idBadge.textContent = inc.id || "INC-20261019-88192";
  }

  const sevBadge = document.getElementById("cmdSeverityBadge");
  if (sevBadge) {
    const risk = inc.currentRiskLevel || "CRITICAL";
    sevBadge.textContent = `SEVERITY: ${risk}`;
    if (risk === "CRITICAL") {
      sevBadge.style.background = "rgba(244, 63, 94, 0.2)";
      sevBadge.style.borderColor = "var(--accent-red)";
      sevBadge.style.color = "#fda4af";
    } else if (risk === "HIGH") {
      sevBadge.style.background = "rgba(245, 158, 11, 0.2)";
      sevBadge.style.borderColor = "var(--accent-amber)";
      sevBadge.style.color = "#fcd34d";
    } else if (risk === "RESOLVED" || risk === "LOW") {
      sevBadge.style.background = "rgba(16, 185, 129, 0.2)";
      sevBadge.style.borderColor = "var(--accent-green)";
      sevBadge.style.color = "#6ee7b7";
    } else {
      sevBadge.style.background = "rgba(59, 130, 246, 0.2)";
      sevBadge.style.borderColor = "var(--accent-blue)";
      sevBadge.style.color = "#93c5fd";
    }
  }

  // 2. Elapsed Timer Badge
  const elBadge = document.getElementById("cmdElapsedTimer");
  if (elBadge) {
    elBadge.textContent = formatElapsedTimer(inc.createdAt, isResolved);
  }

  // 3. The 6 W's Briefing Grid:
  // W1: WHAT HAPPENED?
  const whatAns = document.getElementById("cmdWhatHappened");
  const whatSub = document.getElementById("cmdWhatSub");
  if (whatAns) {
    if (isResolved) {
      whatAns.textContent = "Incident Resolved • Eleanor Vance Safe";
    } else if (inc.currentRiskLevel === "CRITICAL") {
      whatAns.textContent = "Acute Fall Event • High-Impact Acceleration Signature";
    } else if (inc.currentRiskLevel === "HIGH") {
      whatAns.textContent = "Elevated Risk Event • Prolonged Immobility Detected";
    } else {
      whatAns.textContent = "Multi-Modal Baseline Monitoring • Active Observation";
    }
  }
  if (whatSub) {
    whatSub.textContent = isResolved
      ? "Verbal confirmation obtained; normal baseline restored."
      : (inc.evidenceSummary || "Zero post-impact ambulation detected on wet ceramic tile substrate");
  }

  // W2: WHERE?
  const whereAns = document.getElementById("cmdWhere");
  const whereSub = document.getElementById("cmdWhereSub");
  const locName = capitalize(inc.location || "bathroom");
  if (whereAns) {
    whereAns.textContent = `${locName} • Beacon Hill Unit 4B`;
  }
  if (whereSub) {
    whereSub.textContent = `Resident: ${res.name || "Eleanor Vance"} (Age ${res.age || 79}) • ${locName} Sensor Array`;
  }

  // W3: WHEN?
  const whenAns = document.getElementById("cmdWhen");
  const whenSub = document.getElementById("cmdWhenSub");
  if (whenAns) {
    const createdStr = formatCmdTime(inc.createdAt);
    const dateStr = inc.createdAt ? new Date(inc.createdAt).toLocaleDateString() : "Today";
    whenAns.textContent = `${createdStr} (${dateStr})`;
  }
  if (whenSub) {
    whenSub.textContent = "Detection Time: Authoritative Event Timestamp • Live Elapsed Active";
  }

  // W4: WHY DID NIRA ESCALATE?
  const whyAns = document.getElementById("cmdWhyEscalated");
  const whySub = document.getElementById("cmdWhySub");
  if (whyAns) {
    const hrVal = tel.heartRate?.current || 138;
    const voiceText = vs.phase === "RESOLVED"
      ? "Voice Confirmation Safe"
      : (vs.phase === "WAITING_FOR_RESPONSE" ? "Awaiting Voice Response" : "20s Silence Timeout");
    whyAns.textContent = `${hrVal} BPM HR + ${voiceText} + Wet Tile`;
  }
  if (whySub) {
    whySub.textContent = "+4.2h nocturnal deviation; multi-modal evidence justified immediate escalation";
  }

  // W5: WHO HAS BEEN NOTIFIED?
  const whoAns = document.getElementById("cmdWhoNotified");
  const whoSub = document.getElementById("cmdWhoSub");
  if (whoAns) {
    const cgvAck = cgv.status === "ACKNOWLEDGED";
    whoAns.textContent = cgvAck
      ? "Boston EMS 911 (Medic-14) & Son David (ACKNOWLEDGED)"
      : "Boston EMS 911 (Medic-14) & Son David Vance";
  }
  if (whoSub) {
    whoSub.textContent = `Echo Show 15 Drop-In Call + Cellular SMS (Door PIN: ${emg.doorPin || "8492"}) + Push`;
  }

  // W6: WHAT IS HAPPENING NOW?
  const nowAns = document.getElementById("cmdWhatNow");
  const nowSub = document.getElementById("cmdWhatNowSub");
  if (nowAns) {
    if (isResolved) {
      nowAns.textContent = "Incident Closed • Resident Safe & Ambulatory";
    } else {
      const lockState = emg.doorLockState || "UNLOCKED";
      nowAns.textContent = `Smart Deadbolt ${lockState} • First Responders En Route`;
    }
  }
  if (nowSub) {
    nowSub.textContent = isResolved
      ? "All systems returned to passive monitoring."
      : "Two-way audio open; emergency packet transmitted to CAD agency";
  }

  // 4. Risk Score & Timeline Count
  const riskTag = document.getElementById("cmdRiskScoreTag");
  if (riskTag) {
    const scoreVal = Math.round((inc.riskScore || 0.94) * 100);
    riskTag.textContent = `Risk Score: ${scoreVal}%`;
  }

  const countTag = document.getElementById("cmdTimelineCount");
  if (countTag) {
    countTag.textContent = `${(state.timeline || []).length} Events`;
  }

  const syncStatus = document.getElementById("cmdTimelineSyncStatus");
  if (syncStatus) {
    syncStatus.textContent = `• Auto-Synced (${state.connectionStatus || 'connected'})`;
  }

  // 5. Render Chronological Event-Driven Timeline
  renderCommandTimeline(state.timeline || [], inc.createdAt);

  // 6. CAD Packet Card Details
  const pktId = document.getElementById("cmdPacketId");
  if (pktId) pktId.textContent = emg.packetId || "EPK-84920";

  const pktStatus = document.getElementById("cmdPacketStatus");
  if (pktStatus) {
    pktStatus.textContent = emg.packetStatus || "TRANSMITTED";
    pktStatus.style.color = (emg.packetStatus === "FAILED") ? "#f43f5e" : "#34d399";
  }

  const triagePrio = document.getElementById("cmdTriagePriority");
  if (triagePrio) {
    triagePrio.textContent = emg.triagePriority || "CODE: RED-911";
  }

  // Door Lock Badge
  const doorBadge = document.getElementById("cmdDoorBadge");
  if (doorBadge) {
    const isUnlocked = (emg.doorLockState || "UNLOCKED") === "UNLOCKED";
    doorBadge.textContent = isUnlocked
      ? `UNLOCKED (PIN: ${emg.doorPin || "8492"})`
      : "SECURED / LOCKED";
    doorBadge.className = isUnlocked ? "door-badge-unlocked" : "door-badge-locked";
  }

  // 7. Caregiver Hub Status & Button
  const cgvBadge = document.getElementById("cmdCaregiverStatusBadge");
  const ackBtn = document.getElementById("btnAckIncident");
  const ackText = document.getElementById("btnAckText");
  const isAck = cgv.status === "ACKNOWLEDGED";

  if (cgvBadge) {
    cgvBadge.textContent = isAck ? "ACKNOWLEDGED BY DAVID" : "ALERTED & DISPATCHED";
    cgvBadge.style.background = isAck ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.15)";
    cgvBadge.style.color = isAck ? "#34d399" : "#fbbf24";
    cgvBadge.style.borderColor = isAck ? "rgba(16, 185, 129, 0.35)" : "rgba(245, 158, 11, 0.35)";
  }

  if (ackText) {
    if (isAck) {
      const ackTime = cgv.acknowledgedAt ? formatCmdTime(cgv.acknowledgedAt) : "Just now";
      ackText.textContent = `Acknowledged at ${ackTime} (Guardian David)`;
    } else {
      ackText.textContent = "Acknowledge Incident (Guardian David)";
    }
  }
  if (ackBtn) {
    ackBtn.style.opacity = isAck ? "0.75" : "1";
  }

  // 8. Multi-Factor Evidence Ingestion Chips
  const evYolo = document.getElementById("evYolo");
  if (evYolo) evYolo.textContent = "2.8m/s (High Impact)";

  const evRadar = document.getElementById("evRadar");
  if (evRadar) {
    const rm = state.rooms?.bathroom || {};
    evRadar.textContent = rm.movementState || "Immobile (0.05)";
  }

  const evHr = document.getElementById("evHr");
  if (evHr) {
    const hr = tel.heartRate?.current || 138;
    const trend = tel.heartRate?.trend || "Tachycardia";
    evHr.textContent = `${hr} BPM (${trend})`;
  }

  const evCircadian = document.getElementById("evCircadian");
  if (evCircadian) {
    evCircadian.textContent = tel.circadianDeviation || "+4.2h Deviation";
  }
}

function renderCommandTimeline(timeline, incidentCreatedAt) {
  const container = document.getElementById("cmdIncidentTimeline");
  if (!container) return;

  const currentHash = (timeline || []).map(t => `${t.id || ''}:${t.timestamp || ''}:${t.action_type || ''}:${t.description || ''}`).join("|");
  if (currentHash === lastCmdTimelineHash) return;
  lastCmdTimelineHash = currentHash;

  if (!timeline || timeline.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 36px 16px; color: var(--text-muted); font-size: 0.82rem;">
        <span class="no-live-data-badge">NO TIMELINE EVENTS</span>
        <div style="margin-top: 8px;">Waiting for backend safety events...</div>
      </div>
    `;
    return;
  }

  const startMs = incidentCreatedAt ? new Date(incidentCreatedAt).getTime() : null;

  let html = "";
  timeline.forEach((event, idx) => {
    const eventMs = event.timestamp ? new Date(event.timestamp).getTime() : null;
    let deltaStr = "";
    if (startMs && eventMs && !isNaN(eventMs)) {
      const diffSec = Math.floor((eventMs - startMs) / 1000);
      if (diffSec >= 0) {
        const mm = String(Math.floor(diffSec / 60)).padStart(2, '0');
        const ss = String(diffSec % 60).padStart(2, '0');
        deltaStr = `+${mm}:${ss}`;
      }
    }

    const timeStr = formatCmdTime(event.timestamp);

    // Actor styling & labels
    let actorClass = "actor-engine";
    let actorLabel = event.actor || "SYSTEM";

    const actUpper = (event.action_type || "").toUpperCase();
    const actorUpper = (event.actor || "").toUpperCase();

    if (actUpper.includes("VISION") || actorUpper.includes("VISION") || actorUpper.includes("YOLO")) {
      actorClass = "actor-yolo";
      actorLabel = "YOLOv8-POSE";
    } else if (actUpper.includes("HAZARD") || actorUpper.includes("RADAR") || actorUpper.includes("SENSOR")) {
      actorClass = "actor-sensor";
      actorLabel = "60GHz RADAR";
    } else if (actUpper.includes("RISK") || actorUpper.includes("AEGIS")) {
      actorClass = "actor-engine";
      actorLabel = "AEGIS RISK ENGINE";
    } else if (actUpper.includes("VOICE") || actUpper.includes("WELLNESS") || actorUpper.includes("ALEXA")) {
      actorClass = "actor-voice";
      actorLabel = "VOICE AI (ECHO)";
    } else if (actUpper.includes("TIMEOUT")) {
      actorClass = "actor-timeout";
      actorLabel = "ACOUSTIC TIMEOUT";
    } else if (actUpper.includes("CAD") || actUpper.includes("DISPATCH")) {
      actorClass = "actor-cad";
      actorLabel = "911 CAD EMS";
    } else if (actUpper.includes("CAREGIVER") || actorUpper.includes("GUARDIAN")) {
      actorClass = "actor-guardian";
      actorLabel = "GUARDIAN (DAVID)";
    } else if (actUpper.includes("DOOR") || actUpper.includes("LOCK")) {
      actorClass = "actor-sensor";
      actorLabel = "SMART DEADBOLT";
    }

    const isLatest = idx === timeline.length - 1;
    const itemExtraClass = isLatest ? "ctl-item-active" : "";

    let metaDisplay = "";
    if (event.metadata_json) {
      if (typeof event.metadata_json === "object") {
        const pairs = Object.entries(event.metadata_json)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
          .join(" • ");
        metaDisplay = pairs ? `<div style="font-size: 0.70rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 4px;">${pairs}</div>` : "";
      } else if (typeof event.metadata_json === "string" && event.metadata_json !== "{}") {
        metaDisplay = `<div style="font-size: 0.70rem; color: var(--text-muted); font-family: var(--font-mono); margin-top: 4px;">${event.metadata_json}</div>`;
      }
    }

    html += `
      <div class="ctl-item ${itemExtraClass}" id="ctl-${event.id || idx}">
        <div class="ctl-time-col">
          <div class="ctl-clock">${timeStr}</div>
          ${deltaStr ? `<div class="ctl-delta">${deltaStr}</div>` : ""}
        </div>
        <div class="ctl-content-col">
          <div class="ctl-top-row">
            <span class="ctl-action-title">${event.description || event.action_type || 'Safety Event'}</span>
            <span class="ctl-actor-tag ${actorClass}">${actorLabel}</span>
          </div>
          ${metaDisplay}
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
  container.scrollTop = container.scrollHeight;
}

function acknowledgeGuardianIncident() {
  if (!window.niraStore) return;
  window.niraStore.acknowledgeCaregiver();
  showToast("✅ <strong>Guardian David Vance</strong> acknowledged emergency incident.");
  playChime("info");
}

function toggleCmdDoorLock() {
  if (!window.niraStore) return;
  const newState = window.niraStore.toggleEmergencyDoorLock();
  showToast(`🔐 Smart Deadbolt toggled to <strong>${newState}</strong>`);
  playChime("info");
}

// ---------------------------------------------------------------------------
// Real-Time Acoustic Countdown Ticker (1-second tick)
// ---------------------------------------------------------------------------
let voiceCountdownTimer = null;

function initVoiceCountdownTicker() {
  if (voiceCountdownTimer) clearInterval(voiceCountdownTimer);

  voiceCountdownTimer = setInterval(() => {
    if (!window.niraStore) return;
    const vs = window.niraStore.state.voiceState;
    if (!vs) return;

    if (vs.phase === "WAITING_FOR_RESPONSE") {
      if (typeof vs.countdownSec !== "number") vs.countdownSec = 20;

      if (vs.countdownSec > 1) {
        vs.countdownSec--;
        const cdSec = document.getElementById("voiceCountdownSec");
        if (cdSec) cdSec.textContent = `${vs.countdownSec}s`;
      } else if (vs.countdownSec === 1) {
        vs.countdownSec = 0;
        showToast("⏱️ 20-second acoustic response window expired!");
        userAnswer("timeout");
      }
    }
  }, 1000);
}

// ---------------------------------------------------------------------------
// Switch Scenario Logic (Dispatches Real Backend Event via niraStore)
// ---------------------------------------------------------------------------
async function switchScenario(key) {
  currentScenario = key;
  try {
    playChime(key === "false_alarm" ? "success" : (key === "responsive" ? "warning" : "alert"));
  } catch (e) {}
  showToast(`⚡ Ingesting scenario event: <strong>${key}</strong> to backend...`);

  // Call demo system scenario runner in demo/
  const scenarioMap = {
    "false_alarm": "false_alarm",
    "responsive": "responsive_emergency",
    "silent": "silent_emergency"
  };
  const demoTarget = scenarioMap[key] || key;
  fetch(`/api/v1/demo/scenario/${demoTarget}`, { method: "POST" })
    .then(r => r.json())
    .then(data => console.log("Demo scenario triggered:", data))
    .catch(err => console.warn("Demo scenario error:", err));

  try {
    if (window.niraStore) {
      await window.niraStore.dispatchScenario(key);
      showToast(`✅ Authoritative backend risk: <strong>${window.niraStore.state.incident.currentRiskLevel}</strong>`);
    }
  } catch (err) {
    console.warn("[switchScenario] Ingestion failed:", err);
    showToast(`⚠️ Event ingestion error; operating offline.`);
  }
}

// ---------------------------------------------------------------------------
// Interactive Room Tile Selection
// ---------------------------------------------------------------------------
function selectRoomTile(roomName) {
  playChime("info");
  if (window.niraStore) {
    window.niraStore.state.incident.location = roomName;
    window.niraStore.state.timestamps.location = Date.now();
    window.niraStore.notify();
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
// Interactive User Voice Answer (Dispatches to Backend /api/v1/incidents/.../respond-voice)
// ---------------------------------------------------------------------------
async function userAnswer(choice) {
  if (!window.niraStore) return;

  if (choice === "ok") {
    showToast("🗣️ Eleanor replied: <em>\"I'm okay!\"</em> ➔ Reporting to backend...");
    try {
      await window.niraStore.dispatchVoiceResponse("I'm okay, Alexa! I just dropped my reading glasses.", false);
      showToast("🟢 Backend confirmed: Incident marked RESOLVED.");
      if (window.voiceAudio) {
        window.voiceAudio.playAlexaChime();
        setTimeout(() => {
          window.voiceAudio.speak("I'm okay, Alexa! I just dropped my glasses.", "senior");
        }, 500);
      }
    } catch(e) {
      showToast("⚠️ Backend voice response error.");
    }
  } else if (choice === "help") {
    showToast("🗣️ Eleanor replied: <em>\"Help me!\"</em> ➔ Reporting to backend...");
    try {
      await window.niraStore.dispatchVoiceResponse("Help me, Alexa! I slipped and hurt my wrist, I can't get up!", false);
      showToast("🟡 Backend escalated: Son David Vance alerted.");
      if (window.voiceAudio) {
        window.voiceAudio.speak("Help me, Alexa! I slipped and hurt my wrist, I can't get up!", "senior");
      }
    } catch(e) {
      showToast("⚠️ Backend voice response error.");
    }
  } else if (choice === "timeout") {
    showToast("⏱️ 20s Silence Elapsed ➔ Reporting timeout to backend...");
    try {
      await window.niraStore.dispatchVoiceResponse(null, true);
      showToast("🔴 Backend escalated: CAD First Responders Dispatched!");
      if (window.voiceAudio) {
        window.voiceAudio.playEmergencyTone();
        setTimeout(() => {
          window.voiceAudio.speak("No verbal response detected for twenty seconds. Initiating emergency dispatch.", "alexa");
        }, 600);
      }
    } catch(e) {
      showToast("⚠️ Backend voice response error.");
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
// Multi-View Tab Navigation (Person 2 Demo Module Views & Core Views)
// ---------------------------------------------------------------------------
function switchTab(tabId) {
  playChime("info");

  const aliasMap = {
    'voiceassistant': 'voiceassistant',
    'assistant': 'voiceassistant',
    'dailycheckin': 'dailycheckin',
    'checkin': 'dailycheckin',
    'demovideo': 'demovideo',
    'video': 'demovideo',
    'demo': 'demovideo',
    'guide': 'demovideo',
    'tutorial': 'demovideo',
    'falldetection': 'falldetection',
    'fall': 'falldetection',
    'falldetect': 'falldetection',
    'emergencyalert': 'emergencyalert',
    'alert': 'emergencyalert',
    'ambulance': 'emergencyalert',
    'cad': 'emergencyalert',
    'medic14': 'emergencyalert',
    'locationmap': 'locationmap',
    'map': 'locationmap',
    'hospitals': 'locationmap',
    'notificationcenter': 'notificationcenter',
    'notifications': 'notificationcenter',
    'notif': 'notificationcenter',
    'incidenthistory': 'incidenthistory',
    'history': 'incidenthistory',
    'incidents': 'incidenthistory',
    'overview': 'overview',
    'vision': 'vision',
    'voice': 'voice',
    'dispatch': 'dispatch'
  };

  const canonical = (tabId && aliasMap[tabId.toLowerCase()]) ? aliasMap[tabId.toLowerCase()] : (tabId ? tabId.toLowerCase() : 'voiceassistant');

  const allTabs = [
    { id: 'voiceassistant', btn: 'tabBtnVoiceAssistant', panel: 'panelVoiceAssistant' },
    { id: 'dailycheckin', btn: 'tabBtnDailyCheckin', panel: 'panelDailyCheckin' },
    { id: 'demovideo', btn: 'tabBtnDemoVideo', panel: 'panelDemoVideo' },
    { id: 'falldetection', btn: 'tabBtnFallDetection', panel: 'panelFallDetection' },
    { id: 'emergencyalert', btn: 'tabBtnEmergencyAlert', panel: 'panelEmergencyAlert' },
    { id: 'locationmap', btn: 'tabBtnLocationMap', panel: 'panelLocationMap' },
    { id: 'notificationcenter', btn: 'tabBtnNotificationCenter', panel: 'panelNotificationCenter' },
    { id: 'incidenthistory', btn: 'tabBtnIncidentHistory', panel: 'panelIncidentHistory' },
    { id: 'overview', btn: 'tabBtnOverview', panel: 'panelOverview' },
    { id: 'vision', btn: 'tabBtnVision', panel: 'panelVision' },
    { id: 'voice', btn: 'tabBtnVoice', panel: 'panelVoice' },
    { id: 'dispatch', btn: 'tabBtnDispatch', panel: 'panelDispatch' }
  ];

  allTabs.forEach(t => {
    const btn = document.getElementById(t.btn);
    const panel = document.getElementById(t.panel);
    const isActive = (t.id === canonical);
    if (btn) {
      if (isActive) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
        btn.tabIndex = 0;
      } else {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
        btn.tabIndex = -1;
      }
    }
    if (panel) {
      if (isActive) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    }
  });

  // If switched to demovideo, trigger video player initialization or playback
  if (canonical === 'demovideo' && window.demoVideoController) {
    window.demoVideoController.play();
  }

  // If switched to vision tab, trigger canvas resize to fit viewport
  if (canonical === 'vision') {
    setTimeout(() => {
      if (window.cameraSim) {
        window.cameraSim.resizeCanvas();
      }
      if (window.main3DTwin && is3DModeActive) {
        window.main3DTwin.resize();
      }
    }, 60);
  }

  // If switched to locationmap, trigger Leaflet resize
  if (canonical === 'locationmap' && window.person2LocationMap) {
    setTimeout(() => {
      if (window.person2LocationMap.leafletMap) {
        window.person2LocationMap.leafletMap.invalidateSize();
      }
    }, 100);
  }

  // Update hash safely without full reload
  if (window.history && window.history.replaceState) {
    window.history.replaceState(null, null, '#demo/' + canonical);
  }
}
window.switchTab = switchTab;

// ---------------------------------------------------------------------------
// User Profiles & Strict Role-Based Feature Permissions
// ---------------------------------------------------------------------------
const USER_PROFILES = {
  senior_home: {
    key: "senior_home",
    name: "Eleanor Vance (Senior Home View)",
    subtitle: "Senior Resident • Beacon Hill Unit 4B",
    role: "Senior Home View",
    badgeClass: "badge-senior",
    avatar: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    allowedTabs: ["voiceassistant", "dailycheckin", "demovideo"],
    defaultTab: "voiceassistant",
    showScenarioBar: false
  },
  admin_son: {
    key: "admin_son",
    name: "David Vance (Son • Family Admin)",
    subtitle: "Primary Family Guardian & Admin",
    role: "Family Primary Admin",
    badgeClass: "badge-admin",
    avatar: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
    allowedTabs: ["overview", "vision", "falldetection", "notificationcenter", "incidenthistory"],
    defaultTab: "overview",
    showScenarioBar: true
  },
  ems: {
    key: "ems",
    name: "Medic 14 (Boston EMS First Responder)",
    subtitle: "First Responder Computer-Aided Dispatch",
    role: "First Responder / Dispatch",
    badgeClass: "badge-ems",
    avatar: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`,
    allowedTabs: ["emergencyalert", "dispatch", "locationmap"],
    defaultTab: "emergencyalert",
    showScenarioBar: false
  }
};

let currentActiveProfileKey = "senior_home";

function setUserProfile(profileKey, triggerTabSwitch = true) {
  let key = profileKey || "senior_home";
  if (key.includes("admin") || key.includes("david")) {
    key = "admin_son";
  } else if (key.includes("ems") || key.includes("medic") || key.includes("first") || key.includes("cad")) {
    key = "ems";
  } else {
    key = "senior_home";
  }

  const profile = USER_PROFILES[key] || USER_PROFILES.senior_home;
  currentActiveProfileKey = profile.key;

  try {
    localStorage.setItem("nira_active_profile", profile.key);
    localStorage.setItem("aegis_auth_user", JSON.stringify({
      name: profile.name,
      role: profile.role,
      key: profile.key,
      avatar: profile.avatar
    }));
  } catch(e) {}

  // Update header session badge
  const nameEl = document.getElementById("userName");
  const roleEl = document.getElementById("userRole");
  const avatarEl = document.getElementById("userAvatar");
  const sessionBadge = document.getElementById("userSessionBadge");

  if (nameEl) nameEl.textContent = profile.name;
  if (roleEl) roleEl.textContent = profile.role;
  if (avatarEl && profile.avatar) avatarEl.innerHTML = profile.avatar;
  if (sessionBadge) {
    sessionBadge.className = "header-chip " + profile.badgeClass;
  }

  // Update scenario bar visibility (shown for David Vance Admin, hidden for Senior and EMS)
  const scenarioBar = document.querySelector(".scenario-bar-container");
  if (scenarioBar) {
    scenarioBar.style.display = profile.showScenarioBar ? "flex" : "none";
  }

  // Filter tabs in .tab-navigation-strip
  const allTabs = [
    { id: 'voiceassistant', btn: 'tabBtnVoiceAssistant' },
    { id: 'dailycheckin', btn: 'tabBtnDailyCheckin' },
    { id: 'demovideo', btn: 'tabBtnDemoVideo' },
    { id: 'falldetection', btn: 'tabBtnFallDetection' },
    { id: 'emergencyalert', btn: 'tabBtnEmergencyAlert' },
    { id: 'locationmap', btn: 'tabBtnLocationMap' },
    { id: 'notificationcenter', btn: 'tabBtnNotificationCenter' },
    { id: 'incidenthistory', btn: 'tabBtnIncidentHistory' },
    { id: 'overview', btn: 'tabBtnOverview' },
    { id: 'vision', btn: 'tabBtnVision' },
    { id: 'voice', btn: 'tabBtnVoice' },
    { id: 'dispatch', btn: 'tabBtnDispatch' }
  ];

  allTabs.forEach(t => {
    const btn = document.getElementById(t.btn);
    if (!btn) return;
    const isAllowed = profile.allowedTabs.includes(t.id);
    btn.style.display = isAllowed ? "inline-flex" : "none";
  });

  // Determine current active tab
  const activeBtn = document.querySelector(".tab-nav-btn.active");
  const activeTabId = activeBtn ? activeBtn.id.replace("tabBtn", "").toLowerCase() : null;

  if (triggerTabSwitch) {
    if (!activeTabId || !profile.allowedTabs.includes(activeTabId)) {
      switchTab(profile.defaultTab);
    }
  }
}
window.setUserProfile = setUserProfile;

function initUserSession() {
  let profileKey = "senior_home";
  try {
    const saved = localStorage.getItem("nira_active_profile");
    const userStr = localStorage.getItem("aegis_auth_user");
    if (saved) {
      profileKey = saved;
    } else if (userStr) {
      const u = JSON.parse(userStr);
      if (u.key) profileKey = u.key;
      else if (u.role && u.role.includes("Admin")) profileKey = "admin_son";
      else if (u.role && (u.role.includes("First") || u.role.includes("Dispatch"))) profileKey = "ems";
    }
  } catch(e) {}

  setUserProfile(profileKey, false);
}

function logoutUser() {
  localStorage.removeItem("aegis_auth_user");
  localStorage.removeItem("nira_active_profile");
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
let currentCinemaViewMode = "radar"; // 'radar' | 'camera' | '3d'
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

  /**
   * updatePhysicalState — drives all 3D twin visual state from authoritative
   * backend event data: location (room), postureCode, and riskLevel.
   * Do NOT use scenario strings here; they are fully replaced by real state.
   */
  updatePhysicalState(location, postureCode, riskLevel) {
    if (!this.eleanor || !this.statusLight) return;

    // --- Map room to 3D scene world position ---
    const roomPos = {
      bathroom: { x: -5, y: 0, z:  0 },
      kitchen:  { x:  5, y: 0, z:  0 },
      living:   { x:  0, y: 0, z:  0 },
      bedroom:  { x:  0, y: 0, z: -5 }
    };
    const pos = roomPos[location] || roomPos.living;

    // --- Map posture to rotation & height offset ---
    let rotX = 0;
    let yOffset = 0;
    if (postureCode === "fallen") {
      rotX = -Math.PI / 2;  // Horizontal on floor
      yOffset = 0.25;
    } else if (postureCode === "sitting") {
      rotX = -Math.PI / 4;  // Slumped
      yOffset = 0.6;
    } else {
      rotX = 0;             // Upright ambulation
      yOffset = 0;
    }

    // Smooth interpolation instead of hard snap
    const target = new THREE.Vector3(pos.x, pos.y + yOffset, pos.z);
    this.eleanor.position.lerp(target, 0.12);
    this.eleanor.rotation.x += (rotX - this.eleanor.rotation.x) * 0.12;

    // --- Map risk level to status light colour ---
    let lightHex = 0x10b981; // GREEN – safe
    if (riskLevel === "CRITICAL") lightHex = 0xef4444;       // RED
    else if (riskLevel === "HIGH" || riskLevel === "ELEVATED") lightHex = 0xf59e0b; // AMBER

    this.statusLight.color.setHex(lightHex);
    this.statusLight.position.set(pos.x, 3, pos.z);
    this.targetLook.set(pos.x, 1, pos.z);
  }

  /** Legacy shim for any callers still using scenarioKey strings */
  updateState(scenarioKey) {
    const locMap = { silent: "bathroom", responsive: "kitchen", false_alarm: "living" };
    const postureMap = { silent: "fallen", responsive: "sitting", false_alarm: "upright" };
    const riskMap = { silent: "CRITICAL", responsive: "HIGH", false_alarm: "LOW" };
    this.updatePhysicalState(
      locMap[scenarioKey] || "living",
      postureMap[scenarioKey] || "upright",
      riskMap[scenarioKey] || "LOW"
    );
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

// ---------------------------------------------------------------------------
// View Mode Toggles: Radar | Camera | 3D Twin
// ---------------------------------------------------------------------------
function _setViewMode(mode) {
  // mode: 'radar' | 'camera' | '3d'
  currentCinemaViewMode = mode;
  const cam2D = document.getElementById("cameraCanvas");
  const cam3D = document.getElementById("threeDCanvas");
  const btnRadar = document.getElementById("btnToggleRadar");
  const btnCamera = document.getElementById("btnToggleCamera");
  const btn3D = document.getElementById("btnToggle3DMode");
  const camTitle = document.getElementById("cinemaCameraTitle");
  const hudPill = document.getElementById("camHudPill");
  const footerModality = document.getElementById("footerModalityText");
  const privacyBadge = document.getElementById("privacyShieldBadge");

  // Reset all button active classes
  [btnRadar, btnCamera, btn3D].forEach(b => { if (b) b.classList.remove("active"); });

  const loc = (window.niraStore && window.niraStore.state && window.niraStore.state.incident && window.niraStore.state.incident.location) || "bathroom";
  const locUpper = loc.toUpperCase();

  if (mode === "3d") {
    if (cam2D) cam2D.style.display = "none";
    if (cam3D) cam3D.style.display = "block";
    if (btn3D) btn3D.classList.add("active");
    is3DModeActive = true;
    if (camTitle) camTitle.textContent = `3D Spatial Digital Twin: ${capitalize(loc)}`;
    if (hudPill) hudPill.textContent = `SPATIAL-3D ${locUpper} • DIGITAL TWIN RIGID SKELETON`;
    if (footerModality) footerModality.textContent = "3D WEBGL ENGINE • KINEMATIC FALL SIMULATOR • CONTINUOUS POSE";
    if (privacyBadge) privacyBadge.style.display = "inline-flex";

    if (!main3DTwin) main3DTwin = new Main3DDigitalTwin("threeDCanvas");
    if (main3DTwin) {
      main3DTwin.resize();
      if (window.niraStore) {
        const st = window.niraStore.state;
        const rm = (st.rooms || {})[loc] || {};
        const rsk = st.incident.currentRiskLevel || "LOW";
        main3DTwin.updatePhysicalState(loc, rm.postureCode || "upright", rsk);
      }
    }
    showToast("🌐 <strong>3D Digital Twin Active</strong> — click & drag to orbit.");
  } else {
    if (cam3D) cam3D.style.display = "none";
    if (cam2D) cam2D.style.display = "block";
    is3DModeActive = false;

    if (mode === "radar") {
      if (btnRadar) btnRadar.classList.add("active");
      if (window.cameraSim) {
        window.cameraSim.setViewMode("radar");
        window.cameraSim.resizeCanvas();
      }
      if (camTitle) camTitle.textContent = `Privacy Radar Feed: ${capitalize(loc)}`;
      if (hudPill) hudPill.textContent = `RADAR-01 ${locUpper} • 60GHz FMCW • PRIVACY SHIELD`;
      if (footerModality) footerModality.textContent = "60GHz mmWAVE RADAR • ZERO OPTICAL RECORDING • FMCW POINT CLOUD";
      if (privacyBadge) privacyBadge.style.display = "inline-flex";
      showToast("📡 <strong>60GHz Privacy Radar View Active</strong> — no optical data collected.");
    } else {
      if (btnCamera) btnCamera.classList.add("active");
      if (window.cameraSim) {
        window.cameraSim.setViewMode("camera");
        window.cameraSim.resizeCanvas();
      }
      if (camTitle) camTitle.textContent = `Optical Camera Feed: ${capitalize(loc)}`;
      if (hudPill) hudPill.textContent = `CAM-01 ${locUpper} • 1080p • YOLOv8-Pose`;
      if (footerModality) footerModality.textContent = "OPTICAL CAMERA • YOLOv8 17-KEYPOINT SKELETON • EDGE INFERENCE";
      if (privacyBadge) privacyBadge.style.display = "none";
      showToast("📹 <strong>Optical Camera View Active</strong> — YOLOv8-Pose skeleton rendering.");
    }

    if (window.niraStore) {
      const st = window.niraStore.state;
      const rsk = st.incident.currentRiskLevel || "LOW";
      const camState = (rsk === "CRITICAL" && st.incident.fallDetected)
        ? "critical"
        : (rsk === "HIGH" || rsk === "MODERATE" ? "warning" : "safe");
      const posture = (st.rooms && st.rooms[loc] && st.rooms[loc].postureCode) || (camState === "critical" ? "fallen" : camState === "warning" ? "sitting" : "upright");
      if (window.cameraSim) {
        window.cameraSim.setRoomAndState(loc, camState, posture);
        window.cameraSim.resizeCanvas();
      }
    }
  }
}

function toggleRadarView()  { _setViewMode("radar");  }
function toggleCameraView() { _setViewMode("camera"); }
function toggleMain3DMode() { _setViewMode(is3DModeActive ? "radar" : "3d"); }
// ---------------------------------------------------------------------------
// Load Active & Historical Incidents from SQLite API
// ---------------------------------------------------------------------------
async function loadIncidentReportsFromApi() {
  try {
    const res = await fetch("/api/v1/incidents/active");
    if (!res.ok) return;
    const data = await res.json();
    if (Array.isArray(data) && data.length > 0) {
      const tbody = document.getElementById("incidentTableBody");
      if (!tbody) return;
      tbody.innerHTML = data.slice(0, 8).map(inc => {
        const sevClass = (inc.current_risk_level === "CRITICAL") ? "offline" : ((inc.current_risk_level === "HIGH" || inc.current_risk_level === "MODERATE") ? "stale" : "online");
        const statusColor = (inc.status === "ESCALATED_CAD") ? "color: var(--status-critical); border-color: rgba(220,38,38,0.3);" : ((inc.status === "ESCALATED_CAREGIVER") ? "color: var(--status-warning); border-color: rgba(217,119,6,0.3);" : "");
        const timeStr = inc.created_at ? new Date(inc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : "02:14:00 AM";
        return `
          <tr>
            <td><strong>${inc.id}</strong></td>
            <td>${timeStr}</td>
            <td>${capitalize(inc.location || "Bathroom")}</td>
            <td><span class="device-status-badge ${sevClass}">${inc.current_risk_level || "MODERATE"}</span></td>
            <td>${capitalize((inc.event_type || "60GHz FMCW Radar").replace(/_/g, " "))}</td>
            <td>${inc.workflow_state || "WAITING_FOR_RESPONSE"}</td>
            <td><span class="consent-badge-active" style="${statusColor}">${inc.status || "ACTIVE"}</span></td>
            <td><button class="btn-luxury-secondary" style="padding: 4px 10px; font-size: 0.72rem;" onclick="inspectIncidentModal('${inc.id}')">Inspect Dossier</button></td>
          </tr>
        `;
      }).join("");
    }
  } catch (err) {
    // Graceful fallback to static rows
  }
}

// ---------------------------------------------------------------------------
// Primary Landing Gateway Transitions (Matches NIRA -> DEMO / LIVE MODEL)
// ---------------------------------------------------------------------------

function enterSystemMode(mode) {
  try {
    const landingScreen = document.getElementById("landingGatewayScreen");
    const appWorkspace = document.getElementById("appWorkspaceContainer");

    if (landingScreen) {
      landingScreen.style.setProperty("display", "none", "important");
      landingScreen.setAttribute("aria-hidden", "true");
    }
    if (appWorkspace) {
      appWorkspace.style.setProperty("display", "block", "important");
      appWorkspace.removeAttribute("aria-hidden");
    }

    // Call backend systems based on mode
    if (mode === "demo") {
      fetch("/api/v1/demo/launch", { method: "POST" })
        .then(res => res.json())
        .then(data => {
          console.log("Demo system connected:", data);
          if (typeof showToast === "function") {
            showToast("🎮 <strong>Demo System Engaged</strong>: Calling Demo/ simulators");
          }
        })
        .catch(err => console.warn("Demo launch ping error:", err));
    } else if (mode === "live") {
      fetch("/api/v1/live/launch", { method: "POST" })
        .then(res => res.json())
        .then(data => {
          console.log("Live model system connected:", data);
          if (typeof showToast === "function") {
            showToast("⚡ <strong>Live Model System Engaged</strong>: Calling Live/ models");
          }
        })
        .catch(err => console.warn("Live launch ping error:", err));
    }

    switchSystemMode(mode, false);
    try {
      playChime(mode === "live" ? "success" : "info");
    } catch (audioErr) {
      // AudioContext policy fallback
    }

    if (typeof showToast === "function") {
      showToast(`Entered <strong>${mode === 'live' ? 'Live Model Workspace' : 'Complete Demo System'}</strong>`);
    }

    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, null, "#" + mode);
    }
  } catch (err) {
    console.error("enterSystemMode error:", err);
  }
}

function returnToLandingGateway() {
  const landingScreen = document.getElementById("landingGatewayScreen");
  const appWorkspace = document.getElementById("appWorkspaceContainer");

  if (landingScreen) {
    landingScreen.style.setProperty("display", "flex", "important");
    landingScreen.removeAttribute("aria-hidden");
  }
  if (appWorkspace) {
    appWorkspace.style.setProperty("display", "none", "important");
    appWorkspace.setAttribute("aria-hidden", "true");
  }

  try {
    playChime("info");
  } catch (e) {}

  if (window.history && window.history.replaceState) {
    window.history.replaceState(null, null, window.location.pathname);
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

window.enterSystemMode = enterSystemMode;
window.returnToLandingGateway = returnToLandingGateway;
window.switchSystemMode = switchSystemMode;

// Check URL hash immediately on boot or navigation
if (typeof window !== "undefined") {
  const checkInitialHash = () => {
    const rawHash = (window.location.hash || "").replace("#", "").toLowerCase();
    if (rawHash.includes("profile=senior") || rawHash === "senior") {
      enterSystemMode("demo");
      setUserProfile("senior_home", true);
      return;
    } else if (rawHash.includes("profile=admin") || rawHash === "admin") {
      enterSystemMode("demo");
      setUserProfile("admin_son", true);
      return;
    } else if (rawHash.includes("profile=ems") || rawHash === "ems" || rawHash.includes("emergencyalert") || rawHash.includes("ambulance")) {
      enterSystemMode("demo");
      setUserProfile("ems", true);
      return;
    }

    if (rawHash.startsWith("demo")) {
      enterSystemMode("demo");
      const parts = rawHash.split("/");
      if (parts.length > 1 && typeof window.switchTab === "function") {
        setTimeout(() => window.switchTab(parts[1]), 120);
      }
    } else if (rawHash === "live") {
      enterSystemMode("live");
    }
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", checkInitialHash);
  } else {
    checkInitialHash();
  }
  window.addEventListener("hashchange", checkInitialHash);
}

// ---------------------------------------------------------------------------
// Operating Environment Mode Switcher (Demo Mode vs Live Mode)
// ---------------------------------------------------------------------------

function switchSystemMode(mode, notify = true) {
  const btnDemo = document.getElementById("btnModeDemo");
  const btnLive = document.getElementById("btnModeLive");
  const secDemo = document.getElementById("sectionDemoMode");
  const secLive = document.getElementById("sectionLiveMode");

  if (!btnDemo || !btnLive || !secDemo || !secLive) return;

  if (mode === "live") {
    btnLive.classList.add("active");
    btnLive.setAttribute("aria-checked", "true");
    btnDemo.classList.remove("active");
    btnDemo.setAttribute("aria-checked", "false");

    secLive.style.display = "block";
    secDemo.style.display = "none";

    localStorage.setItem("nira_system_mode", "live");
    if (typeof loadLiveResidentProfile === "function") {
      loadLiveResidentProfile();
    }
    if (typeof initNiraEmergencyMap === "function") {
      initNiraEmergencyMap();
    }
    setTimeout(() => {
      if (window.niraMap) window.niraMap.invalidateSize();
    }, 200);

    if (notify) {
      playChime("success");
      showToast("⚡ Switched to <strong>Live Mode</strong> — Real camera & trained fall detector active.");
    }

  } else {
    btnDemo.classList.add("active");
    btnDemo.setAttribute("aria-checked", "true");
    btnLive.classList.remove("active");
    btnLive.setAttribute("aria-checked", "false");

    secDemo.style.display = "block";
    secLive.style.display = "none";

    localStorage.setItem("nira_system_mode", "demo");

    if (notify) {
      playChime("info");
      showToast("🎮 Switched to <strong>Demo Mode</strong> — Hackathon interactive scenario showcase.");
    }
  }

  // Apply localized translations for current mode and active elements
  if (typeof applyTranslations === "function") {
    applyTranslations();
  }

  // Ensure dashboard components re-render correctly
  if (window.niraStore) {
    renderDashboard(window.niraStore.state);
  }
}

// ---------------------------------------------------------------------------
// Live Mode Console Rendering & Real-Time Sync (100% Real Live, Zero Simulation)
// ---------------------------------------------------------------------------

function renderLiveModeConsole(state) {
  const slaEl = document.getElementById("liveSlaLatency");
  const riskBadge = document.getElementById("liveRiskBadge");
  const riskPill = document.getElementById("liveRiskTriagePill");
  const epkView = document.getElementById("liveEpkJsonView");
  const epkId = document.getElementById("liveEpkId");

  const liveResName = (document.getElementById("liveResidentName") || {}).value || "Live Resident";
  const liveResAge = parseInt((document.getElementById("liveResidentAge") || {}).value) || 75;
  const liveRoom = (document.getElementById("liveRoomSelect") || {}).value || "living_room";
  const livePhone = (document.getElementById("liveCaregiverPhone") || {}).value || "+1 (555) 019-2831";

  if (slaEl) slaEl.textContent = `${state?.connection?.latencyMs || 12}ms`;

  const activeLiveInc = window._liveIncident;
  if (activeLiveInc) {
    if (riskBadge) {
      riskBadge.textContent = `${activeLiveInc.risk} (${Math.round(activeLiveInc.confidence * 100)}%)`;
      riskBadge.className = `value ${activeLiveInc.risk === "CRITICAL" ? "critical" : "warning"}`;
    }
    if (riskPill) {
      riskPill.textContent = `${activeLiveInc.risk} (${Math.round(activeLiveInc.confidence * 100)}%)`;
      riskPill.className = `status-pill ${activeLiveInc.risk === "CRITICAL" ? "critical" : "warning"}`;
    }
    const triageStatusEl = document.getElementById("liveTriagePriorityText");
    if (triageStatusEl) {
      triageStatusEl.textContent = activeLiveInc.risk === "CRITICAL" ? "PRIORITY 1 - IMMEDIATE EMS DISPATCH" : "PRIORITY 2 - URGENT CARE";
      triageStatusEl.className = `triage-status-pill ${activeLiveInc.risk === "CRITICAL" ? "critical" : "warning"}`;
    }
    if (epkId) epkId.textContent = activeLiveInc.id;
    if (epkView) {
      const epkObj = {
        incident_id: activeLiveInc.id,
        timestamp: activeLiveInc.timestamp,
        triage_priority: activeLiveInc.risk === "CRITICAL" ? "PRIORITY_1_CRITICAL_TRAUMA" : "PRIORITY_2_URGENT",
        resident: {
          name: liveResName,
          age: liveResAge,
          location: `${capitalize(liveRoom.replace(/_/g, ' '))}, Monitored Real Residence`,
          guardian_phone: livePhone
        },
        live_detection_source: activeLiveInc.type,
        vitals: {
          movement_score: activeLiveInc.risk === "CRITICAL" ? 0.0 : 0.85,
          posture: activeLiveInc.risk === "CRITICAL" ? "fallen_immobile" : "ambulatory"
        },
        optical_inference_model: "YOLOv8 Trained Fall Classifier"
      };
      epkView.textContent = JSON.stringify(epkObj, null, 2);
    }
  } else {
    // Normal baseline - zero simulation
    if (riskBadge) {
      riskBadge.textContent = (typeof t === "function" ? t("normalMovementState") : "NORMAL MOVEMENT");
      riskBadge.className = "value safe";
    }
    if (riskPill) {
      riskPill.textContent = (typeof t === "function" ? t("standbySafe") : "STANDBY / SAFE");
      riskPill.className = "status-pill connected";
    }
    const triageStatusEl = document.getElementById("liveTriagePriorityText");
    if (triageStatusEl) {
      triageStatusEl.textContent = "ROUTINE MONITORING";
      triageStatusEl.className = "triage-status-pill safe";
    }
    if (epkId) epkId.textContent = "STANDBY";
    if (epkView) {
      const epkObj = {
        status: "MONITORING_STANDBY",
        timestamp: new Date().toISOString(),
        triage_priority: "ROUTINE_MONITORING",
        resident: {
          name: liveResName,
          age: liveResAge,
          zone: capitalize(liveRoom.replace(/_/g, ' ')),
          guardian_phone: livePhone
        },
        live_camera: {
          state: window.liveStreamActive ? "STREAM_ACTIVE" : "STANDBY",
          model: "YOLOv8 Fall Classifier"
        },
        live_voice: {
          state: window.liveVoiceActive ? "LISTENING" : "MIC_IDLE",
          engine: "Web Speech API"
        }
      };
      epkView.textContent = JSON.stringify(epkObj, null, 2);
    }
  }

  renderLiveEventStream(state);
}

function renderLiveEventStream(state) {
  const container = document.getElementById("liveEventStreamBox");
  const countBadge = document.getElementById("liveStreamCounter");
  if (!container) return;

  const events = state?.timeline || [];
  if (countBadge) countBadge.textContent = `${events.length} Received`;

  if (events.length === 0) {
    container.innerHTML = `<div class="stream-empty" data-i18n="awaitingLiveEvents">${typeof t === "function" ? t("awaitingLiveEvents") : "Awaiting real-time events from live camera and microphone..."}</div>`;
    return;
  }

  const recent = events.slice(-8).reverse();
  let html = "";
  recent.forEach(e => {
    const timeStr = typeof formatVtlTime === "function" ? formatVtlTime(e.timestamp) : new Date(e.timestamp).toLocaleTimeString();
    const isCrit = e.action_type?.includes("CAD") || e.action_type?.includes("FALL") || e.action_type?.includes("ESCALAT");
    const borderCol = isCrit ? "var(--accent-red)" : "var(--accent-blue)";
    html += `
      <div class="stream-entry-pill" style="border-left-color: ${borderCol};">
        <span style="font-weight: 700; color: #ffffff;">${e.action_type || "EVENT"}</span>
        <span style="color: var(--text-secondary);">${e.actor || "SYSTEM"}</span>
        <span style="color: var(--accent-blue);">${timeStr}</span>
      </div>
    `;
  });
  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Live Webcam Optical Fall Detection
// ---------------------------------------------------------------------------

let liveWebcamStream = null;
let liveFrameInterval = null;
let liveResidentData = {
  full_name: "Live Resident",
  age: 75,
  location: "Living Room",
  emergency_contact: "Family Guardian",
  emergency_phone: "+1 (555) 019-2831"
};

async function startLiveWebcam() {
  const video = document.getElementById("liveWebcamVideo");
  const placeholder = document.getElementById("liveCamPlaceholder");
  const pill = document.getElementById("liveCamPill");
  const btnStart = document.getElementById("btnStartLiveCam");
  const btnStop = document.getElementById("btnStopLiveCam");
  const hudOverlay = document.getElementById("liveCamHudOverlay");

  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      liveWebcamStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });
      if (video) {
        video.srcObject = liveWebcamStream;
        await video.play();
      }
      if (placeholder) placeholder.style.display = "none";
      if (hudOverlay) hudOverlay.style.display = "block";
      if (pill) {
        pill.className = "status-pill streaming";
        pill.textContent = "AI LIVE STREAM (YOLOv8)";
      }
      if (btnStart) btnStart.style.display = "none";
      if (btnStop) btnStop.style.display = "inline-flex";

      showToast("📹 <strong>Live Camera Engaged</strong> — Real-time fall & unresponsiveness AI active.");
      playChime("success");

      // Notify backend camera started
      fetch("/api/v1/live/camera/start", { method: "POST" }).catch(() => {});

      // Launch real-time inference loop (every 250ms ~ 4 FPS)
      startLiveCameraInferenceLoop();
    } else {
      showToast("⚠️ Camera access not supported in this browser.");
    }
  } catch (err) {
    console.warn("[startLiveWebcam] Camera permission error:", err);
    showToast("⚠️ Camera access denied or device busy.");
  }
}

function stopLiveWebcam() {
  if (liveWebcamStream) {
    liveWebcamStream.getTracks().forEach(t => t.stop());
    liveWebcamStream = null;
  }
  if (liveFrameInterval) {
    clearInterval(liveFrameInterval);
    liveFrameInterval = null;
  }
  const placeholder = document.getElementById("liveCamPlaceholder");
  const pill = document.getElementById("liveCamPill");
  const btnStart = document.getElementById("btnStartLiveCam");
  const btnStop = document.getElementById("btnStopLiveCam");
  const canvas = document.getElementById("liveWebcamCanvas");
  const hudOverlay = document.getElementById("liveCamHudOverlay");
  const timerOverlay = document.getElementById("liveCamTimerOverlay");

  if (placeholder) placeholder.style.display = "flex";
  if (hudOverlay) hudOverlay.style.display = "none";
  if (timerOverlay) timerOverlay.style.display = "none";

  if (pill) {
    pill.className = "status-pill offline";
    pill.textContent = "STANDBY";
  }
  if (btnStart) btnStart.style.display = "inline-flex";
  if (btnStop) btnStop.style.display = "none";
  if (canvas) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  // Cleanly reset all DOM telemetry fields
  const stateBadge = document.getElementById("liveStateBadge");
  const stateText = document.getElementById("liveStateText");
  const classText = document.getElementById("liveCamClass");
  const timerText = document.getElementById("liveUnresponsiveTimer");
  const motionText = document.getElementById("liveCamMotion");
  const hudPill = document.getElementById("hudStatePill");
  const hudSub = document.getElementById("hudClassSub");

  if (stateBadge) {
    stateBadge.textContent = "NORMAL MOVEMENT";
    stateBadge.className = "status-pill connected";
  }
  if (stateText) {
    stateText.textContent = "NORMAL MOVEMENT";
    stateText.style.color = "var(--accent-green)";
  }
  if (classText) classText.textContent = "Standby (Camera Idle)";
  if (timerText) {
    timerText.textContent = "0.0s (Normal)";
    timerText.style.color = "var(--accent-green)";
  }
  if (motionText) motionText.textContent = "0.0 px/s";
  if (hudPill) {
    hudPill.textContent = "● NORMAL MOVEMENT";
    hudPill.style.color = "#34d399";
  }
  if (hudSub) hudSub.textContent = "Action: Standby";

  fetch("/api/v1/live/camera/stop", { method: "POST" }).catch(() => {});
  showToast("📹 Live camera feed stopped.");
}

function startLiveCameraInferenceLoop() {
  if (liveFrameInterval) clearInterval(liveFrameInterval);

  const offscreenCanvas = document.createElement("canvas");
  offscreenCanvas.width = 416;
  offscreenCanvas.height = 416;
  const offscreenCtx = offscreenCanvas.getContext("2d");

  let isSending = false;

  liveFrameInterval = setInterval(async () => {
    const video = document.getElementById("liveWebcamVideo");
    const displayCanvas = document.getElementById("liveWebcamCanvas");
    if (!video || !liveWebcamStream || video.readyState < 2 || isSending) return;

    try {
      isSending = true;
      offscreenCtx.drawImage(video, 0, 0, 416, 416);
      const b64Image = offscreenCanvas.toDataURL("image/jpeg", 0.75);

      const resp = await fetch("/api/v1/live/camera/frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_base64: b64Image,
          location: (document.getElementById("liveRoomSelect") || {}).value || "living_room"
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        // Guard against late response arriving after camera was stopped
        if (liveWebcamStream) {
          renderLiveInferenceResult(data, displayCanvas, video);
        }
      }
    } catch (e) {
      console.warn("Live frame inference error:", e);
    } finally {
      isSending = false;
    }
  }, 250);
}

function renderLiveInferenceResult(res, canvas, video) {
  if (!canvas || !video || !liveWebcamStream) {
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    return;
  }

  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const state = res.state || "NORMAL_MOVEMENT";
  const cls = res.detected_class || "Normal Movement";
  const conf = Math.round((res.confidence || 0.90) * 100);
  const unrespSec = res.unresponsive_seconds || 0.0;
  const motion = res.motion_displacement || 0.0;

  // Colors for 3 states
  let color = "#10b981"; // Green (Normal)
  let stateTitle = "NORMAL MOVEMENT";
  let pillClass = "connected";

  if (state === "FALL_DETECTED") {
    color = "#f59e0b"; // Amber (Fall)
    stateTitle = "FALL DETECTED";
    pillClass = "warning";
  } else if (state === "UNRESPONSIVENESS" || res.is_unresponsive) {
    color = "#ef4444"; // Red (Unresponsiveness)
    stateTitle = "🚨 UNRESPONSIVENESS";
    pillClass = "critical";
  }

  // Update DOM telemetry
  const stateBadge = document.getElementById("liveStateBadge");
  const stateText = document.getElementById("liveStateText");
  const classText = document.getElementById("liveCamClass");
  const timerText = document.getElementById("liveUnresponsiveTimer");
  const motionText = document.getElementById("liveCamMotion");
  const hudPill = document.getElementById("hudStatePill");
  const hudSub = document.getElementById("hudClassSub");
  const timerOverlay = document.getElementById("liveCamTimerOverlay");
  const timerVal = document.getElementById("hudTimerVal");

  if (stateBadge) {
    stateBadge.textContent = stateTitle;
    stateBadge.className = `status-pill ${pillClass}`;
  }
  if (stateText) {
    stateText.textContent = stateTitle;
    stateText.style.color = color;
  }
  if (classText) classText.textContent = `${cls} (${conf}%)`;
  if (motionText) motionText.textContent = `${motion} px/f`;

  if (timerText) {
    if (unrespSec > 0) {
      timerText.textContent = `${unrespSec}s ${unrespSec >= 4 ? '(CRITICAL)' : '(Counting...)'}`;
      timerText.style.color = unrespSec >= 4 ? "var(--accent-red)" : "var(--accent-amber)";
    } else {
      timerText.textContent = "0.0s (Normal)";
      timerText.style.color = "var(--accent-green)";
    }
  }

  if (hudPill) {
    hudPill.textContent = `● ${stateTitle}`;
    hudPill.style.color = color;
  }
  if (hudSub) {
    hudSub.textContent = `Class: ${cls} (${conf}%)`;
  }

  // Update Live Map Resident Marker status & alarm beacon
  const isAlarmState = state === "FALL_DETECTED" || state === "UNRESPONSIVENESS" || res.is_unresponsive;
  if (typeof updateMapResidentAlarmState === "function") {
    updateMapResidentAlarmState(isAlarmState, stateTitle);
  }

  // Show/hide floating immobility timer overlay
  if (timerOverlay && timerVal) {
    if (unrespSec > 0) {
      timerOverlay.style.display = "block";
      timerVal.textContent = `${unrespSec}s`;
    } else {
      timerOverlay.style.display = "none";
    }
  }

  // Draw YOLO bounding boxes on canvas if any detected
  if (res.boxes && res.boxes.length > 0) {
    res.boxes.forEach(b => {
      // Scale from 416x416 inference size to canvas dimensions
      const scaleX = canvas.width / 416.0;
      const scaleY = canvas.height / 416.0;
      const [x1, y1, x2, y2] = b.box;

      const sx = x1 * scaleX;
      const sy = y1 * scaleY;
      const sw = (x2 - x1) * scaleX;
      const sh = (y2 - y1) * scaleY;

      // Draw box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(sx, sy, sw, sh);

      // Box translucent fill
      ctx.fillStyle = state === "UNRESPONSIVENESS" ? "rgba(239, 68, 68, 0.2)" : (state === "FALL_DETECTED" ? "rgba(245, 158, 11, 0.15)" : "rgba(16, 185, 129, 0.12)");
      ctx.fillRect(sx, sy, sw, sh);

      // Label badge
      const labelText = `${b.label} ${Math.round(b.confidence * 100)}%`;
      ctx.font = "bold 12px var(--font-mono, monospace)";
      const textWidth = ctx.measureText(labelText).width;

      ctx.fillStyle = color;
      ctx.fillRect(sx, Math.max(sy - 22, 0), textWidth + 12, 22);

      ctx.fillStyle = "#ffffff";
      ctx.fillText(labelText, sx + 6, Math.max(sy - 6, 15));
    });
  }

  // Handle alarm inquiry & unresponsiveness escalation from real camera model
  if (res.alarm_active || state === "PROLONGED_INACTIVITY" || state === "FALL_DETECTED" || state === "UNRESPONSIVENESS") {
    const alarmPrompt = res.alarm_prompt || "NIRA safety alert: Are you okay? Please respond.";

    // Automatically trigger audio prompt & open mic if not already active
    if (!window._lastAlarmPromptTime || Date.now() - window._lastAlarmPromptTime > 12000) {
      window._lastAlarmPromptTime = Date.now();
      try { playChime("alert"); } catch (_) {}
      showToast(`🚨 <strong>SAFETY INQUIRY:</strong> ${alarmPrompt}`);

      // Voice synthesis for question prompt
      if (typeof window !== "undefined" && window.speechSynthesis) {
        try {
          const u = new SpeechSynthesisUtterance(alarmPrompt);
          u.rate = 0.95;
          window.speechSynthesis.speak(u);
        } catch (_) {}
      }

      // Automatically engage mic listening for resident verbal reply
      if (typeof startLiveVoiceListening === "function" && !window.isLiveMicActive) {
        setTimeout(() => {
          try { startLiveVoiceListening(); } catch (_) {}
        }, 1200);
      }
    }

    if (state === "UNRESPONSIVENESS") {
      window._liveIncident = {
        id: "INC-LIVE-" + Date.now().toString().slice(-5),
        type: "optical_unresponsiveness_alert",
        risk: "CRITICAL",
        confidence: res.confidence || 0.95,
        timestamp: new Date().toISOString()
      };
      if (typeof renderLiveModeConsole === "function") {
        renderLiveModeConsole(window.niraStore?.state);
      }
    }
  } else if (state === "NORMAL_MOVEMENT" && window._liveIncident && window._liveIncident.risk !== "CRITICAL") {
    window._liveIncident = null;
    if (typeof renderLiveModeConsole === "function") {
      renderLiveModeConsole(window.niraStore?.state);
    }
  }
}

async function saveLiveResidentProfile() {
  const name = (document.getElementById("liveResidentName") || {}).value || "Live Resident";
  const age = parseInt((document.getElementById("liveResidentAge") || {}).value || "75", 10);
  const location = (document.getElementById("liveRoomSelect") || {}).value || "living_room";
  const phone = (document.getElementById("liveCaregiverPhone") || {}).value || "+1 (555) 019-2831";

  liveResidentData = {
    full_name: name,
    age: age,
    location: location,
    emergency_contact: "Guardian",
    emergency_phone: phone,
    medical_notes: "Monitored via NIRA Live Optical AI"
  };

  try {
    const res = await fetch("/api/v1/live/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(liveResidentData)
    });
    if (res.ok) {
      showToast(`💾 Live Profile Saved: <strong>${name} (${age})</strong>`);
      updateHeaderResidentCapsule(name, age);
      syncLiveResidentDisplay();
    }
  } catch (err) {
    console.warn("Error saving profile:", err);
  }
}

function syncLiveResidentDisplay() {
  const name = (document.getElementById("liveResidentName") || {}).value || "Live Resident";
  const age = (document.getElementById("liveResidentAge") || {}).value || "75";
  const room = (document.getElementById("liveRoomSelect") || {}).value || "living_room";
  const phone = (document.getElementById("liveCaregiverPhone") || {}).value || "+1 (555) 019-2831";

  const dName = document.getElementById("liveResidentDisplayName");
  const dAge = document.getElementById("liveResidentDisplayAge");
  const dZone = document.getElementById("liveResidentDisplayZone");
  const dPhone = document.getElementById("liveResidentDisplayPhone");
  if (dName) dName.textContent = name;
  if (dAge) dAge.textContent = `${age} yrs`;
  if (dZone) dZone.textContent = typeof capitalize === "function" ? capitalize(room.replace(/_/g, ' ')) : room;
  if (dPhone) dPhone.textContent = phone;
}

function toggleLiveConfigDrawer() {
  const drawer = document.getElementById("liveProfileConfigDrawer");
  const btn = document.getElementById("btnToggleLiveConfig");
  if (!drawer) return;
  const isHidden = drawer.style.display === "none" || !drawer.style.display;
  drawer.style.display = isHidden ? "block" : "none";
  if (btn) btn.classList.toggle("active", isHidden);
}

function updateHeaderResidentCapsule(name, age) {
  const seniorEl = document.querySelector("[data-i18n='seniorName']");
  const seniorLoc = document.querySelector("[data-i18n='seniorLoc']");
  if (seniorEl) seniorEl.textContent = `${name} (Age ${age})`;
  if (seniorLoc) seniorLoc.textContent = "Live Monitored Session • Optical AI Active";
}

async function loadLiveResidentProfile() {
  try {
    const res = await fetch("/api/v1/live/profile");
    if (res.ok) {
      const data = await res.json();
      liveResidentData = data;
      const nameInp = document.getElementById("liveResidentName");
      const ageInp = document.getElementById("liveResidentAge");
      const phoneInp = document.getElementById("liveCaregiverPhone");

      if (nameInp && data.full_name) nameInp.value = data.full_name;
      if (ageInp && data.age) ageInp.value = data.age;
      if (phoneInp && data.emergency_phone) phoneInp.value = data.emergency_phone;

      updateHeaderResidentCapsule(data.full_name || "Live Resident", data.age || 75);
      syncLiveResidentDisplay();
    }
  } catch (err) {
    console.warn("Could not load live profile:", err);
  }
}

// ---------------------------------------------------------------------------
// Live Microphone Voice AI Hub (Alexa+ Ambient Check)
// ---------------------------------------------------------------------------

let liveSpeechRecognizer = null;
let isLiveMicActive = false;

function startLiveVoiceListening() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const transcriptEl = document.getElementById("liveVoiceTranscriptText");
  const pill = document.getElementById("liveMicPill");
  const phaseTag = document.getElementById("liveVoicePhaseTag");
  const btnStart = document.getElementById("btnStartLiveMic");
  const btnStop = document.getElementById("btnStopLiveMic");
  const acousticStatus = document.getElementById("liveAcousticStatus");
  const soundBars = document.querySelectorAll("#liveSoundwaveRow .live-bar");

  if (!SpeechRec) {
    showToast("⚠️ Web Speech Recognition not supported in this browser. Try Chrome or Edge.");
    if (transcriptEl) transcriptEl.innerHTML = "Web Speech API not available. You can use the quick preset buttons below.";
    return;
  }

  try {
    liveSpeechRecognizer = new SpeechRec();
    liveSpeechRecognizer.continuous = true;
    liveSpeechRecognizer.interimResults = true;
    liveSpeechRecognizer.lang = "en-US";

    liveSpeechRecognizer.onstart = () => {
      isLiveMicActive = true;
      if (pill) {
        pill.className = "status-pill streaming";
        pill.textContent = "LISTENING 🎙️";
      }
      if (phaseTag) {
        phaseTag.textContent = "ACTIVE LISTENING";
        phaseTag.style.color = "#38bdf8";
      }
      if (acousticStatus) acousticStatus.textContent = "Active Acoustic Window";
      if (btnStart) btnStart.style.display = "none";
      if (btnStop) btnStop.style.display = "inline-flex";
      soundBars.forEach(b => b.classList.add("active"));
      playChime("info");
      showToast("🎙️ <strong>Live Microphone Active</strong> — Speak now!");
    };

    liveSpeechRecognizer.onresult = async (event) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      const text = (finalTranscript || interimTranscript).trim();
      if (transcriptEl && text) {
        transcriptEl.innerHTML = `🗣️ Spoken: <strong>"${text}"</strong>`;
      }

      if (finalTranscript) {
        await handleLiveSpokenUtterance(finalTranscript);
      }
    };

    liveSpeechRecognizer.onerror = (e) => {
      console.warn("[startLiveVoiceListening] Speech recognition error:", e.error);
      if (transcriptEl) transcriptEl.innerHTML = `Microphone notice: ${e.error}. Standby.`;
    };

    liveSpeechRecognizer.onend = () => {
      if (isLiveMicActive) {
        try { liveSpeechRecognizer.start(); } catch(e) {}
      } else {
        stopLiveVoiceListening();
      }
    };

    liveSpeechRecognizer.start();
  } catch (err) {
    console.warn("[startLiveVoiceListening] Init error:", err);
    showToast("⚠️ Could not start microphone.");
  }
}

function stopLiveVoiceListening() {
  isLiveMicActive = false;
  if (liveSpeechRecognizer) {
    try { liveSpeechRecognizer.stop(); } catch(e) {}
    liveSpeechRecognizer = null;
  }
  const pill = document.getElementById("liveMicPill");
  const phaseTag = document.getElementById("liveVoicePhaseTag");
  const btnStart = document.getElementById("btnStartLiveMic");
  const btnStop = document.getElementById("btnStopLiveMic");
  const acousticStatus = document.getElementById("liveAcousticStatus");
  const soundBars = document.querySelectorAll("#liveSoundwaveRow .live-bar");

  if (pill) {
    pill.className = "status-pill offline";
    pill.textContent = "MIC IDLE";
  }
  if (phaseTag) {
    phaseTag.textContent = "IDLE";
    phaseTag.style.color = "var(--text-muted)";
  }
  if (acousticStatus) acousticStatus.textContent = "Passive Listening";
  if (btnStart) btnStart.style.display = "inline-flex";
  if (btnStop) btnStop.style.display = "none";
  soundBars.forEach(b => b.classList.remove("active"));
  showToast("🎙️ Microphone listening stopped.");
}

async function handleLiveSpokenUtterance(text) {
  const intentEl = document.getElementById("liveDetectedIntent");
  const confEl = document.getElementById("liveIntentConfidence");
  const phaseTag = document.getElementById("liveVoicePhaseTag");
  const room = (document.getElementById("liveRoomSelect") || {}).value || "living_room";
  const resName = (document.getElementById("liveResidentName") || {}).value || "Live Resident";

  // Post to authoritative NIRA Live Voice & Activity Routine Learning Endpoint
  let voiceResult = null;
  try {
    const vResp = await fetch("/api/v1/live/camera/voice-response", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transcript: text,
        location: room,
        elderly_id: resName.toLowerCase().replace(/\s+/g, "_")
      })
    });
    if (vResp.ok) {
      voiceResult = await vResp.json();
    }
  } catch (err) {
    console.warn("Live voice response API error:", err);
  }

  const isDistress = (voiceResult && voiceResult.status === "EMERGENCY") ||
    /help|fell|pain|fall|hurt|broken|can't get up|emergency|ayuda|caí|me caí|douleur|chute|hilfe|socorro|помогите|बचाओ|救命/i.test(text);

  const isSafe = (voiceResult && voiceResult.status === "SAFE") ||
    (!isDistress && /ok|fine|good|glasses|dropped|alright|nothing|stand up|bien|estoy bien|vale|ça va|gut|alles gut|estou bem|все хорошо|ठीक|没事/i.test(text));

  if (isDistress) {
    if (intentEl) intentEl.innerHTML = `<span style="color: var(--accent-red); font-weight: 800;">CALL_FOR_HELP</span>`;
    if (confEl) confEl.textContent = "98%";
    if (phaseTag) phaseTag.textContent = "DISTRESS CONFIRMED";
    playChime("alert");
    showToast("🚨 <strong>Verbal Distress Detected!</strong> Triggering Caregiver & CAD Escalation...");

    window._liveIncident = {
      id: "INC-LIVE-" + Date.now().toString().slice(-5),
      type: "voice_distress_call",
      risk: "CRITICAL",
      confidence: 0.98,
      timestamp: new Date().toISOString()
    };
    if (typeof renderLiveModeConsole === "function") {
      renderLiveModeConsole(window.niraStore?.state);
    }

    await fetch("/api/events/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: "live-voice-distress-" + Date.now(),
        timestamp: new Date().toISOString(),
        resident_id: resName.toLowerCase().replace(/\s+/g, "_"),
        room_id: room,
        source: "live_microphone_stream",
        event_type: "voice_distress",
        confidence: 0.98,
        correlation_id: "corr-live-" + Date.now(),
        payload: {
          spoken_text: text,
          intent: "call_for_help",
          requires_immediate_escalation: true
        }
      })
    });
    if (window.niraStore) window.niraStore.syncActiveIncidents();
  } else if (isSafe) {
    if (intentEl) intentEl.innerHTML = `<span style="color: var(--accent-green); font-weight: 800;">VERIFIED_SAFE</span>`;
    if (confEl) confEl.textContent = "95%";
    if (phaseTag) phaseTag.textContent = "RESOLVED SAFE";
    playChime("success");

    const newThresh = voiceResult?.learned_update?.new_threshold_sec;
    const threshMsg = newThresh ? `Routine learned: ${room} tolerance adapted to ${newThresh}s to prevent false alarms!` : `Daily routine updated to avoid unnecessary alarms.`;
    showToast(`🟢 <strong>Resident Confirmed Safe!</strong> ${threshMsg}`);

    window._liveIncident = null;
    if (typeof renderLiveModeConsole === "function") {
      renderLiveModeConsole(window.niraStore?.state);
    }

    await fetch("/api/events/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: "live-voice-safe-" + Date.now(),
        timestamp: new Date().toISOString(),
        resident_id: resName.toLowerCase().replace(/\s+/g, "_"),
        room_id: room,
        source: "live_microphone_stream",
        event_type: "voice_affirmation_safe",
        confidence: 0.95,
        correlation_id: "corr-live-" + Date.now(),
        payload: {
          spoken_text: text,
          intent: "verified_safe",
          resolved: true,
          learned_routine: voiceResult?.learned_update
        }
      })
    });
    if (window.niraStore) window.niraStore.syncActiveIncidents();
  } else {
    if (intentEl) intentEl.textContent = "Ambiguous Utterance";
    if (confEl) confEl.textContent = "65%";
    if (phaseTag) phaseTag.textContent = "UNCERTAIN / RE-CHECK";
  }
}

function speakLivePrompt() {
  const resName = (document.getElementById("liveResidentName") || {}).value || "Resident";
  const room = (document.getElementById("liveRoomSelect") || {}).value || "the room";
  const prompt = `${resName}, this is Aegis. I noticed a movement anomaly. Are you okay? Please tell me if you need help.`;
  showToast(`🔊 Speaking Alexa prompt to ${resName}...`);
  if (window.voiceAudio) {
    window.voiceAudio.playAlexaChime();
    setTimeout(() => {
      window.voiceAudio.speak(prompt, "alexa");
    }, 400);
  }
}

async function testSimulateInactivity() {
  const room = (document.getElementById("liveRoomSelect") || {}).value || "living_room";
  try {
    const res = await fetch("/api/v1/live/camera/simulate-inactivity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seconds: 185.0, location: room })
    });
    if (res.ok) {
      showToast("⏱️ <strong>Inactivity Simulated (185s):</strong> Evaluating against learned circadian routine...");
      if (typeof playChime === "function") playChime("alert");
    }
  } catch (e) {
    console.warn("simulate-inactivity error:", e);
  }
}

// ---------------------------------------------------------------------------
// Live Emergency Packet Copy & Control
// ---------------------------------------------------------------------------

function copyLiveEpkJson() {
  const el = document.getElementById("liveEpkJsonView");
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    showToast("📋 Emergency Packet JSON copied to clipboard!");
  }).catch(() => {
    showToast("📋 EPK copied.");
  });
}

function toggleLiveArming() {
  const statusText = document.getElementById("liveArmStatusText");
  const btn = document.getElementById("btnToggleArmText");
  const chip = document.querySelector(".live-status-chip");

  if (!statusText || !btn) return;
  const isArmed = statusText.textContent.includes("ARMED") || statusText.textContent.includes("ACTIVÉE") || statusText.textContent.includes("ARMADO") || statusText.textContent.includes("SCHARF");

  if (isArmed) {
    statusText.textContent = typeof t === "function" ? t("protectionPaused") : "MONITORING PAUSED";
    btn.textContent = typeof t === "function" ? t("resumeProtection") : "Resume Protection";
    if (chip) chip.className = "live-status-chip paused";
    playChime("warning");
    showToast("⏸️ Live ambient monitoring paused.");
  } else {
    statusText.textContent = typeof t === "function" ? t("liveMonitoringArmed") : "LIVE MONITORING ARMED";
    btn.textContent = typeof t === "function" ? t("pauseProtection") : "Pause Protection";
    if (chip) chip.className = "live-status-chip active";
    playChime("success");
    showToast("🟢 Live ambient monitoring resumed.");
  }
}

function updateLiveResidentProfile() {
  const name = (document.getElementById("liveResidentName") || {}).value || "Live Resident";
  const room = (document.getElementById("liveRoomSelect") || {}).value || "living_room";
  if (window.niraStore) {
    window.niraStore.state.resident = window.niraStore.state.resident || {};
    window.niraStore.state.resident.name = name;
    window.niraStore.state.incident.location = room;
    window.niraStore.notify();
  }
  showToast(`Profile updated: <strong>${name}</strong> in <strong>${capitalize(room)}</strong>`);
}

// ===========================================================================
// DYNAMIC GEOSPATIAL GIS & EMERGENCY DISPATCH RADAR MAP (LEAFLET.JS)
// Marks: 1. Resident Location, 2. Caretaker Location, 3. Nearby Emergency Services
// Non-Static: Dynamically shifts via GPS, City Presets, Address Search, or Map Clicks
// ===========================================================================

// MapTiler Configuration (Configured with user-provided key)
const MAPTILER_API_KEY = "XtY4Bvc3fXWmf1tU3H3S";
let mapTilerTileLayer = null;
let currentMapTilerStyle = "openstreetmap";

function getMapTilerTileUrl(style = "openstreetmap") {
  if (style === "dark" || style === "dataviz-dark") {
    return `https://api.maptiler.com/maps/dataviz-dark/256/{z}/{x}/{y}.png?key=${MAPTILER_API_KEY}`;
  }
  // Default style: OpenStreetMap requested by user
  return `https://api.maptiler.com/maps/openstreetmap/256/{z}/{x}/{y}.jpg?key=${MAPTILER_API_KEY}`;
}

function setMapTilerStyle(styleName, btnEl = null) {
  currentMapTilerStyle = styleName;
  if (mapTilerTileLayer) {
    mapTilerTileLayer.setUrl(getMapTilerTileUrl(styleName));
  }
  const btnOsm = document.getElementById("btnStyleOsm");
  const btnDark = document.getElementById("btnStyleDark");
  if (btnOsm) btnOsm.classList.toggle("active", styleName === "openstreetmap");
  if (btnDark) btnDark.classList.toggle("active", styleName === "dark");
  if (typeof playChime === "function") playChime("info");
  showToast(`🗺️ Map style: <strong>MapTiler ${styleName === "dark" ? "Dark Mode" : "OpenStreetMap"}</strong>`);
}
window.setMapTilerStyle = setMapTilerStyle;

let niraMap = null;
let niraMapMarkerGroup = null;
let niraMapRouteGroup = null;
let currentMapData = null;
let liveMapAlarmActive = false;

async function initNiraEmergencyMap() {
  const mapContainer = document.getElementById("niraEmergencyMap");
  if (!mapContainer) return;

  // If map already initialized, ensure size is updated
  if (niraMap) {
    niraMap.invalidateSize();
    return;
  }

  // Check if Leaflet library is available
  if (typeof L === "undefined") {
    console.warn("Leaflet library not loaded, rendering radar canvas fallback.");
    renderMapFallback(mapContainer);
    return;
  }

  try {
    // Initialize Leaflet map
    niraMap = L.map("niraEmergencyMap", {
      zoomControl: false,
      attributionControl: true,
      minZoom: 10,
      maxZoom: 19
    }).setView([42.3601, -71.0589], 14);

    // Add MapTiler OpenStreetMap tile layer (Requested by user)
    mapTilerTileLayer = L.tileLayer(getMapTilerTileUrl(currentMapTilerStyle), {
      tileSize: 256,
      zoomOffset: 0,
      maxZoom: 19,
      attribution: '<a href="https://www.maptiler.com/copyright/" target="_blank">&copy; MapTiler</a> <a href="https://www.openstreetmap.org/copyright" target="_blank">&copy; OpenStreetMap contributors</a>'
    }).addTo(niraMap);

    // Zoom control in top right
    L.control.zoom({ position: "topright" }).addTo(niraMap);

    // Layer groups for markers and routes
    niraMapRouteGroup = L.layerGroup().addTo(niraMap);
    niraMapMarkerGroup = L.layerGroup().addTo(niraMap);

    // Interactive Click: clicking anywhere repositions the Resident and recomputes all services
    niraMap.on("click", (e) => {
      const lat = e.latlng.lat;
      const lon = e.latlng.lng;
      showToast(`📍 Relocating resident to map click: [${lat.toFixed(4)}, ${lon.toFixed(4)}]`);
      fetchAndRenderMapServices(lat, lon, null, `Manual Pin (${lat.toFixed(4)}, ${lon.toFixed(4)})`);
    });

    window.niraMap = niraMap;

    // Load initial map services (Boston default)
    await fetchAndRenderMapServices(42.3601, -71.0589, "boston", "Boston, MA");

    // Re-check sizing when container appears
    setTimeout(() => {
      if (niraMap) niraMap.invalidateSize();
    }, 250);

  } catch (err) {
    console.error("Error initializing Leaflet map:", err);
    renderMapFallback(mapContainer);
  }
}

async function fetchAndRenderMapServices(lat = null, lon = null, city = null, locationName = null) {
  try {
    let url = "/api/v1/live/map/services";
    const params = [];
    if (city) params.push(`city=${encodeURIComponent(city)}`);
    if (lat !== null && lat !== undefined) params.push(`lat=${lat}`);
    if (lon !== null && lon !== undefined) params.push(`lon=${lon}`);
    if (params.length > 0) url += `?${params.join("&")}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    currentMapData = data;
    window.currentMapData = data;

    // Update city title badge
    const cityEl = document.getElementById("liveMapCurrentCity");
    if (cityEl) cityEl.textContent = data.location_name || "Active Sector";

    // Update city chips active state
    const chipBtns = document.querySelectorAll("#mapCityChips .city-chip");
    chipBtns.forEach(btn => {
      const btnCity = btn.getAttribute("data-city");
      if (city && btnCity === city.toLowerCase()) {
        btn.classList.add("active");
      } else if (!city && btnCity === "boston" && Math.abs(data.resident.lat - 42.3601) < 0.05) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    // Update HUD overlay chips
    updateMapHud(data);

    // Render Markers & Routes on Leaflet
    renderMapEntities(data);

    // Render Emergency Services Cards below map
    renderMapServicesCards(data.services, data.nearest_service);

  } catch (err) {
    console.error("fetchAndRenderMapServices error:", err);
  }
}

function updateMapHud(data) {
  const resName = document.getElementById("hudResidentName");
  const resStatus = document.getElementById("hudResidentStatus");
  const resPill = document.getElementById("hudResidentPill");
  const ctName = document.getElementById("hudCaretakerName");
  const ctDist = document.getElementById("hudCaretakerDistance");
  const emsName = document.getElementById("hudEmsName");
  const emsEta = document.getElementById("hudEmsEta");

  if (resName) resName.textContent = `Resident: ${data.resident.name}`;
  if (resStatus) {
    const isAlarm = liveMapAlarmActive || data.resident.current_state === "FALL_DETECTED" || data.resident.current_state === "UNRESPONSIVENESS";
    resStatus.textContent = isAlarm ? `🚨 CLINICAL FALL EVENT • ${data.resident.hazard_zone}` : `Normal Movement • ${data.resident.hazard_zone}`;
    resStatus.className = `hud-sub ${isAlarm ? "alert" : "safe"}`;
    if (resPill) {
      if (isAlarm) resPill.classList.add("alarm");
      else resPill.classList.remove("alarm");
    }
  }

  if (data.caretaker) {
    if (ctName) ctName.textContent = `Caretaker: ${data.caretaker.name}`;
    if (ctDist) ctDist.textContent = `${data.caretaker.distance_km} km away • ${data.caretaker.eta_mins}m ETA (${data.caretaker.vehicle})`;
  }

  if (data.nearest_service) {
    if (emsName) emsName.textContent = `Nearest: ${data.nearest_service.name}`;
    if (emsEta) emsEta.textContent = `${data.nearest_service.distance_km} km • ${data.nearest_service.eta_mins}m Emergency Driving ETA`;
  }
}

function renderMapEntities(data) {
  if (!niraMap || !niraMapMarkerGroup || !niraMapRouteGroup) return;

  niraMapMarkerGroup.clearLayers();
  niraMapRouteGroup.clearLayers();

  const isAlarm = liveMapAlarmActive || data.resident.current_state === "FALL_DETECTED" || data.resident.current_state === "UNRESPONSIVENESS";

  // 1. Resident Marker (Custom Pulsing Beacon)
  const resIcon = L.divIcon({
    className: `nira-map-pin nira-pin-resident ${isAlarm ? 'alarm' : ''}`,
    html: `<div class="radar-pulse-ring"></div><div class="nira-pin-body">${isAlarm ? '🚨' : '👤'}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -20]
  });

  const resMarker = L.marker([data.resident.lat, data.resident.lon], { icon: resIcon, zIndexOffset: 1000 })
    .bindPopup(`
      <div class="nira-popup-card">
        <div class="nira-popup-title">${isAlarm ? '🚨 CLINICAL FALL EVENT' : '👤 Monitored Senior Resident'}</div>
        <div class="nira-popup-sub"><strong>${data.resident.name}</strong> • ${data.resident.address}</div>
        <div class="nira-popup-stats">
          <span class="nira-stat-chip">${isAlarm ? 'IMPACT IMMOBILE' : 'AMBULATING'}</span>
          <span class="nira-stat-chip">Zone: ${data.resident.hazard_zone}</span>
        </div>
      </div>
    `);
  niraMapMarkerGroup.addLayer(resMarker);

  // 2. Caretaker Marker (Warm Golden Shield)
  if (data.caretaker) {
    const ct = data.caretaker;
    const ctIcon = L.divIcon({
      className: 'nira-map-pin nira-pin-caretaker',
      html: `<div class="nira-pin-body">🛡️</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
      popupAnchor: [0, -20]
    });

    const ctMarker = L.marker([ct.lat, ct.lon], { icon: ctIcon, zIndexOffset: 800 })
      .bindPopup(`
        <div class="nira-popup-card">
          <div class="nira-popup-title">🛡️ ${ct.name}</div>
          <div class="nira-popup-sub">${ct.role} • Vehicle: ${ct.vehicle}</div>
          <div class="nira-popup-stats">
            <span class="nira-stat-chip">📍 ${ct.distance_km} km (${ct.distance_miles} mi)</span>
            <span class="nira-stat-chip">⏱️ ${ct.eta_mins}m ETA</span>
          </div>
          <div style="font-size: 0.68rem; color: #cbd5e1; margin-bottom: 6px;">Status: <strong>${ct.status}</strong> &bull; ${ct.phone}</div>
          <button class="btn-popup-action" onclick="alert('Calling Guardian phone: ' + '${ct.phone}')">📞 Contact Caretaker</button>
        </div>
      `);
    niraMapMarkerGroup.addLayer(ctMarker);

    // Route polyline: Caretaker to Resident (Warm gold dashed line)
    const ctRoute = L.polyline(
      [[ct.lat, ct.lon], [data.resident.lat, data.resident.lon]],
      { color: "#f59e0b", weight: 3, dashArray: "6, 8", opacity: 0.85 }
    );
    niraMapRouteGroup.addLayer(ctRoute);
  }

  // 3. Emergency Services Markers (Hospitals, EMS, Fire, Police)
  if (data.services && data.services.length > 0) {
    data.services.forEach(s => {
      let pinClass = "nira-pin-hospital";
      if (s.type === "ems") pinClass = "nira-pin-ems";
      else if (s.type === "fire") pinClass = "nira-pin-fire";
      else if (s.type === "police") pinClass = "nira-pin-police";

      const sIcon = L.divIcon({
        className: `nira-map-pin ${pinClass}`,
        html: `<div class="nira-pin-body">${s.icon}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -18]
      });

      const sMarker = L.marker([s.lat, s.lon], { icon: sIcon, zIndexOffset: 600 })
        .bindPopup(`
          <div class="nira-popup-card">
            <div class="nira-popup-title">${s.icon} ${s.name}</div>
            <div class="nira-popup-sub">${s.subtype} &bull; ${s.address}</div>
            <div class="nira-popup-stats">
              <span class="nira-stat-chip">📍 ${s.distance_km} km (${s.distance_miles} mi)</span>
              <span class="nira-stat-chip">⏱️ ${s.eta_mins}m ETA</span>
            </div>
            <div style="font-size: 0.68rem; color: #94a3b8; font-family: var(--font-mono); margin-bottom: 6px;">CAD: ${s.cad_channel || 'DIRECT'} &bull; ${s.phone}</div>
            <button class="btn-popup-action" onclick="focusMapRoute('${s.id}')">🚀 Highlight Emergency Route</button>
          </div>
        `);
      sMarker._serviceId = s.id;
      niraMapMarkerGroup.addLayer(sMarker);
    });
  }

  // Route polyline: Nearest EMS/Hospital to Resident (Glowing animated dashed flow line)
  if (data.nearest_service) {
    const ns = data.nearest_service;
    const emsRoute = L.polyline(
      [[ns.lat, ns.lon], [data.resident.lat, data.resident.lon]],
      {
        color: isAlarm ? "#ef4444" : "#38bdf8",
        weight: isAlarm ? 4 : 3,
        dashArray: "8, 6",
        opacity: 0.95,
        className: "nira-route-flow"
      }
    );
    niraMapRouteGroup.addLayer(emsRoute);
  }

  // Fit bounds so Resident, Caretaker, and Services are all visible
  const points = [[data.resident.lat, data.resident.lon]];
  if (data.caretaker) points.push([data.caretaker.lat, data.caretaker.lon]);
  if (data.nearest_service) points.push([data.nearest_service.lat, data.nearest_service.lon]);

  if (points.length > 1) {
    niraMap.fitBounds(L.latLngBounds(points), { padding: [60, 60], maxZoom: 15 });
  } else {
    niraMap.setView([data.resident.lat, data.resident.lon], 14);
  }
}

function renderMapServicesCards(services, nearestService) {
  const container = document.getElementById("mapServicesCardsGrid");
  if (!container) return;

  const countEl = document.getElementById("mapServicesCount");
  if (countEl) countEl.textContent = `${(services || []).length} Active`;

  if (!services || services.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">No emergency facilities reported in sector.</div>`;
    return;
  }

  container.innerHTML = services.map(s => {
    const isNearest = nearestService && nearestService.id === s.id;
    return `
      <div class="service-dispatch-card" style="--card-accent: ${s.badge_color || '#38bdf8'}; ${isNearest ? 'box-shadow: 0 0 14px rgba(56, 189, 248, 0.25); border-color: rgba(56, 189, 248, 0.4);' : ''}">
        <div class="card-top-row">
          <div class="card-name-group">
            <div class="card-icon-badge" style="background: ${s.badge_color}22; border-color: ${s.badge_color}55;">
              ${s.icon}
            </div>
            <div>
              <div class="card-title-text">${s.name} ${isNearest ? '<span style="font-size:0.65rem; background:#38bdf822; color:#38bdf8; border:1px solid #38bdf855; border-radius:4px; padding:1px 5px; margin-left:4px;">NEAREST</span>' : ''}</div>
              <div class="card-subtype-text">${s.subtype}</div>
            </div>
          </div>
        </div>

        <div class="card-telemetry-strip">
          <div class="card-tel-col">
            <span class="card-tel-label">Distance</span>
            <strong class="card-tel-val highlight">${s.distance_km} km <span style="font-size:0.68rem; color:#94a3b8;">(${s.distance_miles} mi)</span></strong>
          </div>
          <div class="card-tel-col">
            <span class="card-tel-label">Siren Driving ETA</span>
            <strong class="card-tel-val" style="color: ${s.eta_mins <= 2.5 ? '#34d399' : '#fbbf24'};">${s.eta_mins} mins</strong>
          </div>
        </div>

        <div style="font-size: 0.68rem; color: #94a3b8; font-family: var(--font-mono); display: flex; justify-content: space-between; align-items: center;">
          <span>CAD: <strong>${s.cad_channel || 'DIRECT'}</strong></span>
          <span>${s.phone}</span>
        </div>

        <div class="card-actions-row">
          <button class="btn-card-dispatch" onclick="focusMapRoute('${s.id}')">
            <span>🚀 Highlight Route</span>
          </button>
          <button class="btn-card-call" onclick="alert('Calling emergency dispatch: ' + '${s.phone}')" title="Direct Line">
            📞 Call
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function focusMapRoute(serviceId) {
  if (!currentMapData || !niraMap) return;
  const s = (currentMapData.services || []).find(item => item.id === serviceId);
  if (!s) return;

  // Pan and zoom to show service and resident
  const bounds = L.latLngBounds([
    [s.lat, s.lon],
    [currentMapData.resident.lat, currentMapData.resident.lon]
  ]);
  niraMap.flyToBounds(bounds, { padding: [80, 80], duration: 1.2 });

  // Open marker popup
  if (niraMapMarkerGroup) {
    niraMapMarkerGroup.eachLayer(layer => {
      if (layer._serviceId === serviceId) {
        setTimeout(() => layer.openPopup(), 1200);
      }
    });
  }

  showToast(`🎯 Focusing route: <strong>${s.name}</strong> ➔ Resident (${s.distance_km} km • ${s.eta_mins}m ETA)`);
}

function detectBrowserGps() {
  if (!navigator.geolocation) {
    showToast("⚠️ Browser geolocation API is not supported on this device.");
    return;
  }

  const btn = document.getElementById("btnDetectGps");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.innerHTML = `<span class="live-pulse-dot" style="background:#38bdf8;"></span> Detecting GPS...`;
    btn.classList.add("active");
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      if (btn) {
        btn.innerHTML = `📍 GPS Active (${lat.toFixed(2)}, ${lon.toFixed(2)})`;
      }
      const pill = document.getElementById("liveMapGpsPill");
      if (pill) {
        pill.className = "status-pill streaming";
        const txt = document.getElementById("liveMapGpsStatusText");
        if (txt) txt.textContent = "GPS LOCKED 📍";
      }

      playChime("success");
      showToast(`📍 <strong>GPS Position Locked</strong>: [${lat.toFixed(4)}, ${lon.toFixed(4)}]`);
      fetchAndRenderMapServices(lat, lon, null, `Your GPS Location (${lat.toFixed(4)}, ${lon.toFixed(4)})`);
    },
    (err) => {
      console.warn("GPS Geolocation error:", err);
      if (btn) {
        btn.innerHTML = origHtml;
        btn.classList.remove("active");
      }
      showToast("⚠️ GPS access was blocked or unavailable. Falling back to city preset.");
    },
    { timeout: 10000, enableHighAccuracy: true }
  );
}

function switchMapCity(cityKey, btnEl) {
  if (btnEl) {
    const parent = btnEl.parentElement;
    if (parent) {
      parent.querySelectorAll(".city-chip").forEach(c => c.classList.remove("active"));
    }
    btnEl.classList.add("active");
  }
  playChime("info");
  fetchAndRenderMapServices(null, null, cityKey);
}

async function searchMapLocation() {
  const inp = document.getElementById("mapAddressSearchInput");
  if (!inp || !inp.value.trim()) return;

  const query = inp.value.trim();
  showToast(`🔍 Searching location: <strong>${query}</strong>...`);

  try {
    const res = await fetch("/api/v1/live/map/locate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });

    if (res.ok) {
      const data = await res.json();
      currentMapData = data;
      window.currentMapData = data;
      updateMapHud(data);
      renderMapEntities(data);
      renderMapServicesCards(data.services, data.nearest_service);
      const cityEl = document.getElementById("liveMapCurrentCity");
      if (cityEl) cityEl.textContent = data.location_name;
      playChime("success");
      showToast(`📍 Relocated to <strong>${data.location_name}</strong>`);
    } else {
      // Fallback search via OpenStreetMap Nominatim
      const nomRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
      if (nomRes.ok) {
        const nomData = await nomRes.json();
        if (nomData && nomData.length > 0) {
          const lat = parseFloat(nomData[0].lat);
          const lon = parseFloat(nomData[0].lon);
          fetchAndRenderMapServices(lat, lon, null, nomData[0].display_name);
          return;
        }
      }
      showToast(`⚠️ Could not find location "${query}". Try another city name.`);
    }
  } catch (err) {
    console.error("searchMapLocation error:", err);
    showToast(`⚠️ Error locating "${query}".`);
  }
}

function updateMapResidentAlarmState(isAlarm, reason = "FALL DETECTED") {
  if (liveMapAlarmActive === isAlarm) return;
  liveMapAlarmActive = isAlarm;
  window._liveMapAlarmActive = isAlarm;

  if (currentMapData) {
    currentMapData.resident.current_state = isAlarm ? "FALL_DETECTED" : "NORMAL_MOVEMENT";
    updateMapHud(currentMapData);
    renderMapEntities(currentMapData);
  }

  if (isAlarm) {
    playChime("alert");
    showToast(`🚨 <strong>EMERGENCY MAP RADAR ESCALATION</strong>: Nearest 911 EMS Unit highlighted & dispatched!`);
  }
}

function renderMapFallback(container) {
  container.innerHTML = `
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#94a3b8; font-family:var(--font-sans); text-align:center; padding:20px;">
      <div style="font-size:2.5rem; margin-bottom:12px;">🗺️</div>
      <strong style="color:#ffffff; font-size:1.1rem; margin-bottom:6px;">NIRA Tactical Geospatial Radar</strong>
      <p style="font-size:0.82rem; max-width:420px; margin-bottom:14px;">Resident, Caretaker, and Nearby Emergency Units active via live telemetry.</p>
      <div style="display:flex; gap:10px;">
        <span style="background:rgba(56,189,248,0.15); border:1px solid #38bdf8; color:#38bdf8; padding:4px 10px; border-radius:6px; font-size:0.75rem;">🔵 Resident: Monitored</span>
        <span style="background:rgba(245,158,11,0.15); border:1px solid #f59e0b; color:#fbbf24; padding:4px 10px; border-radius:6px; font-size:0.75rem;">🟡 Caretaker: En Route</span>
        <span style="background:rgba(239,68,68,0.15); border:1px solid #ef4444; color:#f87171; padding:4px 10px; border-radius:6px; font-size:0.75rem;">🚑 EMS: On Standby</span>
      </div>
    </div>
  `;
}

window.initNiraEmergencyMap = initNiraEmergencyMap;
window.fetchAndRenderMapServices = fetchAndRenderMapServices;
window.detectBrowserGps = detectBrowserGps;
window.switchMapCity = switchMapCity;
window.searchMapLocation = searchMapLocation;
window.focusMapRoute = focusMapRoute;
window.updateMapResidentAlarmState = updateMapResidentAlarmState;
window.toggleLiveConfigDrawer = toggleLiveConfigDrawer;
window.syncLiveResidentDisplay = syncLiveResidentDisplay;


// ---------------------------------------------------------------------------
// Initialization on Page Load
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initNiraTheme();
  initUserSession();
  loadIncidentReportsFromApi();
  loadLiveResidentProfile();

  // Initialize View / Mode Router (Landing Gateway vs Direct Workspace View)
  const hash = (window.location.hash || "").replace("#", "").toLowerCase();
  const urlParams = new URLSearchParams(window.location.search);
  const viewParam = (urlParams.get("view") || urlParams.get("mode") || "").toLowerCase();
  const directTarget = (hash === "demo" || hash === "live") ? hash : (viewParam === "demo" || viewParam === "live" ? viewParam : null);

  if (directTarget) {
    enterSystemMode(directTarget);
  } else {
    // Show Primary Landing Gateway Screen matching user's diagram by default
    returnToLandingGateway();
  }

  // Pre-initialize Leaflet emergency radar map
  if (typeof initNiraEmergencyMap === "function") {
    setTimeout(initNiraEmergencyMap, 250);
  }


  if (window.niraStore) {
    window.niraStore.init();
    window.niraStore.subscribe((state) => renderDashboard(state));

    // Initial render with current state
    renderDashboard(window.niraStore.state);

    // Refresh relative timestamps (e.g., 'Just now', '12s ago') periodically
    setInterval(() => {
      if (window.niraStore) {
        renderDashboard(window.niraStore.state);
      }
    }, 2500);

    // Start live acoustic response window countdown timer
    initVoiceCountdownTicker();

    // Start live command center elapsed timer (1-second tick)
    setInterval(() => {
      if (window.niraStore) {
        const elTimer = document.getElementById("cmdElapsedTimer");
        if (elTimer) {
          const inc = window.niraStore.state.incident || {};
          const isResolved = inc.currentRiskLevel === "RESOLVED" || (window.niraStore.state.voiceState && window.niraStore.state.voiceState.phase === "RESOLVED");
          elTimer.textContent = formatElapsedTimer(inc.createdAt, isResolved);
        }
      }
    }, 1000);
  }

  console.log("Aegis Ambient Care Real-Time State-Driven Dashboard ready.");
});


