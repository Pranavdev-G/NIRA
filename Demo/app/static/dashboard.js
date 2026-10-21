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

  // Auto-select radar when in privacy-protected rooms (bathroom/bedroom)
  if (window.cameraSim && !is3DModeActive) {
    if (isRadarRoom) {
      window.cameraSim.setManualRadar(false); // auto-radar based on room
    }
    const camState = (risk === "CRITICAL" && state.incident.fallDetected)
      ? "critical"
      : (risk === "HIGH" || risk === "MODERATE" ? "warning" : "safe");
    const postureCodeFromRoom = currentRoom.postureCode || (camState === "critical" ? "fallen" : camState === "warning" ? "sitting" : "upright");
    window.cameraSim.setRoomAndState(location, camState, postureCodeFromRoom);
  }

  if (camTitle) {
    const modeName = isRadarRoom ? "Privacy Radar" : "Optical Camera";
    camTitle.textContent = `${modeName} Feed: ${capitalize(location)}`;
  }

  if (hudPill) {
    hudPill.textContent = isRadarRoom
      ? `RADAR-01 ${location.toUpperCase()} • 60GHz FMCW • PRIVACY SHIELD`
      : `CAM-01 ${location.toUpperCase()} • 1080p • YOLOv8-Pose`;
  }

  if (privacyBadge) {
    privacyBadge.style.display = isRadarRoom ? "inline-flex" : "none";
  }

  if (footerModality) {
    footerModality.textContent = isRadarRoom
      ? "60GHz mmWAVE RADAR • ZERO OPTICAL RECORDING • FMCW POINT CLOUD"
      : "YOLOv8-POSE • 17 KEYPOINTS • 30 FPS OPTICAL INFERENCE [SIMULATED]";
  }

  if (hudTag) {
    if (state.incident.fallDetected) {
      hudTag.style.display = "block";
      hudTag.textContent = isRadarRoom
        ? `⚠ FALL DETECTED (RADAR) • CONF: ${(state.incident.confidence * 100).toFixed(0)}%`
        : `FALL DETECTED • CONF: ${(state.incident.confidence * 100).toFixed(0)}% [SIMULATED]`;
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

  // 12. Live Mode Operations Console Synchronization
  renderLiveModeConsole(state);
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
// Multi-View Tab Navigation (Overview, Vision & Floorplan, Voice AI, Dispatch)
// ---------------------------------------------------------------------------
// Multi-View Tab Navigation (Overview, Vision, Voice AI, Dispatch & Person 2 Demo Module Views)
// ---------------------------------------------------------------------------
function switchTab(tabId) {
  playChime("info");
  
  // Tab ID canonical mapping & aliases
  const aliasMap = {
    'voiceassistant': 'voiceassistant',
    'assistant': 'voiceassistant',
    'dailycheckin': 'dailycheckin',
    'checkin': 'dailycheckin',
    'falldetection': 'falldetection',
    'fall': 'falldetection',
    'falldetect': 'falldetection',
    'emergencyalert': 'emergencyalert',
    'alert': 'emergencyalert',
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

  // If switched to vision tab, trigger camera canvas resize to fit viewport
  if (canonical === 'vision' && window.cameraSim) {
    setTimeout(() => {
      window.cameraSim.resizeCanvas();
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
  const cam2D = document.getElementById("cameraCanvas");
  const cam3D = document.getElementById("threeDCanvas");
  const btnRadar = document.getElementById("btnToggleRadar");
  const btnCamera = document.getElementById("btnToggleCamera");
  const btn3D = document.getElementById("btnToggle3DMode");

  // Reset all button active classes
  [btnRadar, btnCamera, btn3D].forEach(b => { if (b) b.classList.remove("active"); });

  if (mode === "3d") {
    if (cam2D) cam2D.style.display = "none";
    if (cam3D) cam3D.style.display = "block";
    if (btn3D) btn3D.classList.add("active");
    is3DModeActive = true;
    if (!main3DTwin) main3DTwin = new Main3DDigitalTwin("threeDCanvas");
    if (main3DTwin) {
      main3DTwin.resize();
      // Drive from current authoritative state
      if (window.niraStore) {
        const st = window.niraStore.state;
        const loc = st.incident.location || "bathroom";
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
      if (window.cameraSim) window.cameraSim.setManualRadar(true);
      if (btnRadar) btnRadar.classList.add("active");
      showToast("📡 <strong>60GHz Privacy Radar View Active</strong> — no optical data collected.");
    } else {
      if (window.cameraSim) window.cameraSim.setManualRadar(false);
      if (btnCamera) btnCamera.classList.add("active");
      showToast("📹 <strong>Optical Camera View Active</strong> — YOLOv8-Pose skeleton rendering.");
    }
    // Re-sync camera simulator from latest store state
    if (window.niraStore) renderDashboard(window.niraStore.state);
  }
}

function toggleRadarView()  { _setViewMode("radar");  }
function toggleCameraView() { _setViewMode("camera"); }
function toggleMain3DMode() { _setViewMode(is3DModeActive ? "radar" : "3d"); }

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
    const raw = (window.location.hash || "").replace("#", "").toLowerCase();
    const parts = raw.split('/');
    const mode = parts[0];
    const subTab = parts[1];
    if (mode === "demo" || mode === "live") {
      enterSystemMode(mode);
      if (mode === "demo" && subTab) {
        setTimeout(() => switchTab(subTab), 120);
      }
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
    if (notify) {
      playChime("success");
      showToast("⚡ Switched to <strong>Live Mode</strong> — Real-time sensor pipeline & device pairing.");
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

  // Ensure dashboard components re-render correctly
  if (window.niraStore) {
    renderDashboard(window.niraStore.state);
  }
}

// ---------------------------------------------------------------------------
// Live Mode Console Rendering & Real-Time Sync
// ---------------------------------------------------------------------------

function renderLiveModeConsole(state) {
  if (!state) return;

  const slaEl = document.getElementById("liveSlaLatency");
  const countEl = document.getElementById("liveEventCountDisplay");
  const riskBadge = document.getElementById("liveRiskBadge");
  const riskPill = document.getElementById("liveRiskTriagePill");
  const fleetHr = document.getElementById("liveFleetHr");
  const fleetBattery = document.getElementById("liveFleetBattery");
  const fleetLock = document.getElementById("liveFleetLockState");
  const fleetEnv = document.getElementById("liveFleetEnv");
  const epkView = document.getElementById("liveEpkJsonView");
  const epkId = document.getElementById("liveEpkId");

  const inc = state.incident || {};
  const risk = inc.currentRiskLevel || "LOW";
  const hrVal = state.vitals ? state.vitals.heartRateBpm : 138;
  const isUnlocked = (state.emergency && state.emergency.doorLockState || "UNLOCKED") === "UNLOCKED";

  if (slaEl) slaEl.textContent = `${state.connection ? state.connection.latencyMs || 18 : 18}ms`;
  if (countEl) countEl.textContent = `${state.timeline ? state.timeline.length : 7}`;

  if (riskBadge) {
    riskBadge.textContent = `${risk} (${Math.round((inc.confidence || 0.94) * 100)}%)`;
    riskBadge.className = `value ${risk === "CRITICAL" ? "critical" : (risk === "HIGH" ? "warning" : "safe")}`;
  }

  if (riskPill) {
    riskPill.textContent = `${risk} (${Math.round((inc.confidence || 0.94) * 100)}%)`;
    riskPill.className = `status-pill ${risk === "CRITICAL" ? "critical" : (risk === "HIGH" ? "warning" : "connected")}`;
  }

  if (fleetHr) {
    fleetHr.textContent = `${hrVal} BPM`;
    fleetHr.style.color = hrVal > 120 ? "var(--accent-red)" : (hrVal > 90 ? "var(--accent-amber)" : "var(--accent-green)");
  }

  if (fleetBattery) fleetBattery.textContent = `${state.telemetry?.device?.batteryPercent || 84}% 🔋`;

  if (fleetLock) {
    fleetLock.textContent = isUnlocked ? "UNLOCKED FOR 911" : "SECURED (LOCKED)";
    fleetLock.style.color = isUnlocked ? "var(--accent-red)" : "var(--accent-green)";
  }

  if (fleetEnv) {
    const temp = state.telemetry?.environment?.temperatureC || 22.4;
    const lux = state.telemetry?.environment?.lightLux || 15;
    fleetEnv.textContent = `${temp}°C • ${lux} Lux`;
  }

  if (epkId) epkId.textContent = inc.id || "INC-LIVE-88192";

  if (epkView) {
    const epkObj = {
      incident_id: inc.id || "INC-LIVE-88192",
      timestamp: inc.createdAt || new Date().toISOString(),
      triage_priority: risk === "CRITICAL" ? "PRIORITY_1_CRITICAL_TRAUMA" : (risk === "HIGH" ? "PRIORITY_2_URGENT" : "ROUTINE_MONITORING"),
      resident: {
        name: (document.getElementById("liveResidentName") || {}).value || "Eleanor Vance",
        age: 79,
        location: `${capitalize(inc.location || "bathroom")}, Beacon Hill Unit 4B`
      },
      vitals: {
        heart_rate_bpm: hrVal,
        movement_score: state.vitals ? state.vitals.movementScore : 0.05,
        posture: inc.fallDetected ? "fallen_immobile" : "ambulatory"
      },
      first_responder_access: {
        smart_lock_status: isUnlocked ? "UNLOCKED" : "LOCKED",
        door_pin: "8492",
        pathway_lights: "100%_ACTIVE"
      },
      voice_status: state.voiceState ? state.voiceState.phase : "EMERGENCY_ESCALATED"
    };
    epkView.textContent = JSON.stringify(epkObj, null, 2);
  }

  renderLiveEventStream(state);
}

function renderLiveEventStream(state) {
  const container = document.getElementById("liveEventStreamBox");
  const countBadge = document.getElementById("liveStreamCounter");
  if (!container) return;

  const events = state.timeline || [];
  if (countBadge) countBadge.textContent = `${events.length} Received`;

  if (events.length === 0) {
    container.innerHTML = `<div class="stream-empty">Awaiting live events from IoT devices and simulators...</div>`;
    return;
  }

  const recent = events.slice(-8).reverse();
  let html = "";
  recent.forEach(e => {
    const timeStr = formatVtlTime(e.timestamp);
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
let liveWebcamAnimId = null;

async function startLiveWebcam() {
  const video = document.getElementById("liveWebcamVideo");
  const placeholder = document.getElementById("liveCamPlaceholder");
  const pill = document.getElementById("liveCamPill");
  const btnStart = document.getElementById("btnStartLiveCam");
  const btnStop = document.getElementById("btnStopLiveCam");

  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      liveWebcamStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false
      });
      if (video) {
        video.srcObject = liveWebcamStream;
        video.play();
      }
      if (placeholder) placeholder.style.display = "none";
      if (pill) {
        pill.className = "status-pill streaming";
        pill.textContent = "LIVE STREAM (30 FPS)";
      }
      if (btnStart) btnStart.style.display = "none";
      if (btnStop) btnStop.style.display = "inline-flex";
      showToast("📹 <strong>Live Webcam Stream Active</strong> — Edge optical motion tracking engaged.");
      playChime("success");

      animateLiveWebcamCanvas();
    } else {
      showToast("⚠️ Camera access not supported in this browser.");
    }
  } catch (err) {
    console.warn("[startLiveWebcam] Camera permission error:", err);
    showToast("⚠️ Camera access denied or unavailable.");
  }
}

function stopLiveWebcam() {
  if (liveWebcamStream) {
    liveWebcamStream.getTracks().forEach(t => t.stop());
    liveWebcamStream = null;
  }
  if (liveWebcamAnimId) {
    cancelAnimationFrame(liveWebcamAnimId);
    liveWebcamAnimId = null;
  }
  const placeholder = document.getElementById("liveCamPlaceholder");
  const pill = document.getElementById("liveCamPill");
  const btnStart = document.getElementById("btnStartLiveCam");
  const btnStop = document.getElementById("btnStopLiveCam");
  const canvas = document.getElementById("liveWebcamCanvas");

  if (placeholder) placeholder.style.display = "flex";
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
  showToast("📹 Live camera feed stopped.");
}

function animateLiveWebcamCanvas() {
  const canvas = document.getElementById("liveWebcamCanvas");
  const video = document.getElementById("liveWebcamVideo");
  if (!canvas || !video || !liveWebcamStream) return;

  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = canvas.parentElement.clientHeight;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const cx = canvas.width / 2;
  const cy = canvas.height * 0.45;

  ctx.strokeStyle = "rgba(56, 189, 248, 0.85)";
  ctx.lineWidth = 2;
  ctx.strokeRect(cx - 70, cy - 60, 140, 160);
  ctx.fillStyle = "rgba(56, 189, 248, 0.15)";
  ctx.fillRect(cx - 70, cy - 60, 140, 160);

  ctx.font = "bold 11px monospace";
  ctx.fillStyle = "#38bdf8";
  ctx.fillText("RESIDENT (97% CONF)", cx - 65, cy - 68);

  const kps = [
    [cx, cy - 40], [cx - 20, cy - 10], [cx + 20, cy - 10],
    [cx - 40, cy + 30], [cx + 40, cy + 30],
    [cx - 25, cy + 85], [cx + 25, cy + 85]
  ];
  kps.forEach(([kx, ky]) => {
    ctx.beginPath();
    ctx.arc(kx, ky, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#34d399";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();
  });

  liveWebcamAnimId = requestAnimationFrame(animateLiveWebcamCanvas);
}

async function triggerOpticalFallDetection() {
  playChime("alert");
  const postureEl = document.getElementById("liveCamPosture");
  const velEl = document.getElementById("liveCamVelocity");
  const probEl = document.getElementById("liveCamFallProb");

  if (postureEl) postureEl.innerHTML = `<span style="color: var(--accent-red);">Horizontal (Fall Impact)</span>`;
  if (velEl) velEl.innerHTML = `<span style="color: var(--accent-red);">2.9 m/s (High Impact)</span>`;
  if (probEl) {
    probEl.className = "tel-val danger";
    probEl.textContent = "96% (CRITICAL)";
  }

  showToast("🚨 <strong>Acute Fall Detected on Camera!</strong> Dispatching event to NIRA backend...");

  const resName = (document.getElementById("liveResidentName") || {}).value || "Eleanor Vance";
  const room = (document.getElementById("liveRoomSelect") || {}).value || "bathroom";

  try {
    const payload = {
      event_id: "evt-opt-fall-" + Date.now(),
      timestamp: new Date().toISOString(),
      resident_id: resName.toLowerCase().replace(/\s+/g, "_"),
      room_id: room,
      source: "live_edge_camera_01",
      event_type: "possible_fall",
      confidence: 0.96,
      correlation_id: "corr-live-" + Date.now(),
      payload: {
        impact_velocity_mps: 2.9,
        posture_after_event: "fallen",
        movement_after_event: "none",
        optical_yolo_confidence: 0.96
      }
    };

    const resp = await fetch("/api/events/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (resp.ok) {
      const data = await resp.json();
      showToast(`✅ Ingested Fall Event (ID: ${data.event_id}). Risk: <strong>${data.risk?.risk_level || 'CRITICAL'}</strong>`);
      if (window.niraStore) window.niraStore.syncActiveIncidents();
    }
  } catch (err) {
    console.warn("[triggerOpticalFallDetection] Ingestion error:", err);
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
  const room = (document.getElementById("liveRoomSelect") || {}).value || "bathroom";
  const resName = (document.getElementById("liveResidentName") || {}).value || "Eleanor Vance";

  const isDistress = /help|fell|pain|fall|hurt|broken|can't get up|emergency/i.test(text);
  const isSafe = /ok|fine|good|glasses|dropped|alright|nothing|stand up/i.test(text);

  if (isDistress) {
    if (intentEl) intentEl.innerHTML = `<span style="color: var(--accent-red); font-weight: 800;">CALL_FOR_HELP</span>`;
    if (confEl) confEl.textContent = "98%";
    if (phaseTag) phaseTag.textContent = "DISTRESS CONFIRMED";
    playChime("alert");
    showToast("🚨 <strong>Verbal Distress Detected!</strong> Triggering Caregiver & CAD Escalation...");

    await fetch("/api/events/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: "live-voice-distress-" + Date.now(),
        timestamp: new Date().toISOString(),
        resident_id: resName.toLowerCase().replace(/\s+/g, "_"),
        room_id: room,
        source: "alexa_echo_show_15",
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
    showToast("🟢 <strong>Resident Confirmed Safe!</strong> Incident resolved.");

    await fetch("/api/events/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: "live-voice-safe-" + Date.now(),
        timestamp: new Date().toISOString(),
        resident_id: resName.toLowerCase().replace(/\s+/g, "_"),
        room_id: room,
        source: "alexa_echo_show_15",
        event_type: "voice_affirmation_safe",
        confidence: 0.95,
        correlation_id: "corr-live-" + Date.now(),
        payload: {
          spoken_text: text,
          intent: "verified_safe",
          resolved: true
        }
      })
    });
    if (window.niraStore) window.niraStore.syncActiveIncidents();
  } else {
    if (intentEl) intentEl.textContent = "Ambiguous Utterance";
    if (confEl) confEl.textContent = "65%";
  }
}

function speakLivePrompt() {
  const resName = (document.getElementById("liveResidentName") || {}).value || "Eleanor";
  const room = (document.getElementById("liveRoomSelect") || {}).value || "the room";
  const prompt = `${resName}, this is Aegis. I noticed a movement anomaly in the ${room}. Are you okay? Please tell me if you need help.`;
  showToast(`🔊 Speaking Alexa prompt to ${resName}...`);
  if (window.voiceAudio) {
    window.voiceAudio.playAlexaChime();
    setTimeout(() => {
      window.voiceAudio.speak(prompt, "alexa");
    }, 400);
  }
}

// ---------------------------------------------------------------------------
// Live Hardware REST Event Presets & Ingestion
// ---------------------------------------------------------------------------

async function sendLiveHardwarePreset(presetKey) {
  const resName = (document.getElementById("liveResidentName") || {}).value || "Eleanor Vance";
  const room = (document.getElementById("liveRoomSelect") || {}).value || "bathroom";
  const residentId = resName.toLowerCase().replace(/\s+/g, "_");
  const corrId = "corr-live-" + Date.now();

  let eventPayload = null;
  let chimeType = "info";

  if (presetKey === "fall") {
    chimeType = "alert";
    eventPayload = {
      event_id: "live-fall-" + Date.now(),
      timestamp: new Date().toISOString(),
      resident_id: residentId,
      room_id: room,
      source: "wearable_imu_radar",
      event_type: "possible_fall",
      confidence: 0.95,
      correlation_id: corrId,
      payload: {
        impact_acceleration_g: 3.2,
        posture_after_event: "fallen",
        movement_after_event: "none",
        vital_bpm: 138
      }
    };
  } else if (presetKey === "wet_floor") {
    chimeType = "warning";
    eventPayload = {
      event_id: "live-wet-" + Date.now(),
      timestamp: new Date().toISOString(),
      resident_id: residentId,
      room_id: room,
      source: "environment_sensor_pod",
      event_type: "environmental_hazard",
      confidence: 0.92,
      correlation_id: corrId,
      payload: {
        hazard_type: "wet_floor",
        floor_condition: "wet",
        light_lux: 15,
        temperature_c: 22.1
      }
    };
  } else if (presetKey === "heart_rate_surge") {
    chimeType = "warning";
    eventPayload = {
      event_id: "live-hr-" + Date.now(),
      timestamp: new Date().toISOString(),
      resident_id: residentId,
      room_id: room,
      source: "apple_watch_series_10",
      event_type: "wearable_telemetry",
      confidence: 0.98,
      correlation_id: corrId,
      payload: {
        heart_rate_bpm: 145,
        baseline_deviation: 73,
        vital_trend: "rising",
        device_status: "connected"
      }
    };
  } else if (presetKey === "timeout") {
    chimeType = "alert";
    eventPayload = {
      event_id: "live-timeout-" + Date.now(),
      timestamp: new Date().toISOString(),
      resident_id: residentId,
      room_id: room,
      source: "acoustic_timeout_engine",
      event_type: "wellness_timeout",
      confidence: 0.99,
      correlation_id: corrId,
      payload: {
        timeout_seconds: 20,
        unresponsive: true,
        recommended_action: "IMMEDIATE_CAD_EMERGENCY_DISPATCH"
      }
    };
  } else if (presetKey === "textbee_sms") {
    chimeType = "info";
    const phone = (document.getElementById("liveCaregiverPhone") || {}).value || "+15550192834";
    showToast(`📱 Dispatching live <strong>TextBee SMS</strong> alert to ${phone}...`);
    eventPayload = {
      event_id: "live-sms-req-" + Date.now(),
      timestamp: new Date().toISOString(),
      resident_id: residentId,
      room_id: room,
      source: "guardian_sms_gateway",
      event_type: "caregiver_notification",
      confidence: 1.0,
      correlation_id: corrId,
      payload: {
        recipient_phone: phone,
        channel: "textbee_sms",
        message: `NIRA EMERGENCY ALERT: Urgent assistance needed for ${resName} in ${room}. Smart door lock UNLOCKED (PIN: 8492).`
      }
    };
  } else if (presetKey === "resolve") {
    chimeType = "success";
    eventPayload = {
      event_id: "live-resolve-" + Date.now(),
      timestamp: new Date().toISOString(),
      resident_id: residentId,
      room_id: room,
      source: "manual_terminal_override",
      event_type: "incident_resolved",
      confidence: 1.0,
      correlation_id: corrId,
      payload: {
        resolution_reason: "Elder confirmed safe, normal movement restored.",
        actor: "FAMILY_GUARDIAN"
      }
    };
  }

  playChime(chimeType);
  if (!eventPayload) return;

  try {
    showToast(`⚡ Ingesting live event: <strong>${eventPayload.event_type}</strong>...`);
    const resp = await fetch("/api/events/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(eventPayload)
    });

    if (resp.ok) {
      const data = await resp.json();
      showToast(`✅ Event Ingested! ID: ${data.event_id} &bull; Status: ${data.status}`);
      if (window.niraStore) window.niraStore.syncActiveIncidents();
    } else {
      showToast(`⚠️ Ingestion returned HTTP ${resp.status}`);
    }
  } catch (err) {
    console.warn("[sendLiveHardwarePreset] Ingestion error:", err);
    showToast("⚠️ Failed to ingest event.");
  }
}

async function dispatchCustomLiveJson() {
  const area = document.getElementById("liveCustomJsonInput");
  const feedback = document.getElementById("liveJsonFeedback");
  if (!area) return;

  try {
    const parsed = JSON.parse(area.value);
    parsed.event_id = parsed.event_id || ("live-custom-" + Date.now());
    parsed.timestamp = new Date().toISOString();

    if (feedback) feedback.innerHTML = `<span style="color: #38bdf8;">Transmitting to /api/events/ingest...</span>`;

    const resp = await fetch("/api/events/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed)
    });

    if (resp.ok) {
      const data = await resp.json();
      if (feedback) feedback.innerHTML = `<span style="color: #34d399;">✓ Ingested Event ID: ${data.event_id}</span>`;
      playChime("success");
      showToast(`✅ Custom event ingested! Risk Level: <strong>${data.risk?.risk_level || 'ASSESSED'}</strong>`);
      if (window.niraStore) window.niraStore.syncActiveIncidents();
    } else {
      if (feedback) feedback.innerHTML = `<span style="color: #f43f5e;">HTTP ${resp.status}: Failed</span>`;
    }
  } catch (err) {
    if (feedback) feedback.innerHTML = `<span style="color: #f43f5e;">Invalid JSON format. Check syntax.</span>`;
  }
}

function copyLiveEpkJson() {
  const el = document.getElementById("liveEpkJsonView");
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    showToast("📋 Emergency Packet JSON copied to clipboard!");
  }).catch(() => {
    showToast("📋 EPK copied.");
  });
}

function toggleLiveDoorLock() {
  if (window.niraStore) {
    const cur = window.niraStore.state.emergency.doorLockState || "UNLOCKED";
    const next = cur === "UNLOCKED" ? "LOCKED" : "UNLOCKED";
    window.niraStore.state.emergency.doorLockState = next;
    window.niraStore.state.timestamps.doorLock = Date.now();
    window.niraStore.notify();
    playChime(next === "UNLOCKED" ? "alert" : "success");
    showToast(`🚪 Smart Entrance Deadbolt is now <strong>${next}</strong> (PIN: 8492)`);
  }
}

function toggleLiveArming() {
  const statusText = document.getElementById("liveArmStatusText");
  const btn = document.getElementById("btnToggleArmText");
  const chip = document.querySelector(".live-status-chip");

  if (!statusText || !btn) return;
  const isArmed = statusText.textContent.includes("ARMED");

  if (isArmed) {
    statusText.textContent = "MONITORING PAUSED";
    btn.textContent = "Resume Protection";
    if (chip) chip.className = "live-status-chip paused";
    playChime("warning");
    showToast("⏸️ Live ambient monitoring paused.");
  } else {
    statusText.textContent = "LIVE MONITORING ARMED";
    btn.textContent = "Pause Protection";
    if (chip) chip.className = "live-status-chip active";
    playChime("success");
    showToast("🟢 Live ambient monitoring resumed.");
  }
}

function updateLiveResidentProfile() {
  const name = (document.getElementById("liveResidentName") || {}).value || "Eleanor Vance";
  const room = (document.getElementById("liveRoomSelect") || {}).value || "bathroom";
  if (window.niraStore) {
    window.niraStore.state.resident = window.niraStore.state.resident || {};
    window.niraStore.state.resident.name = name;
    window.niraStore.state.incident.location = room;
    window.niraStore.notify();
  }
  showToast(`Profile updated: <strong>${name}</strong> in <strong>${capitalize(room)}</strong>`);
}

// ---------------------------------------------------------------------------
// Initialization on Page Load
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initUserSession();

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


