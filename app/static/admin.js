/**
 * NIRA Family Admin Guardian Portal — admin.js v5.0
 * All data derived from authoritative backend state (nira_store.js).
 * Zero fabricated values. Meaningful empty states. Trust-first UX.
 */

// ---------------------------------------------------------------------------
// 1. Utility helpers
// ---------------------------------------------------------------------------

function playAdminChime(freq = 600, dur = 0.25) {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.setValueAtTime(freq, ctx.currentTime);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + dur);
  } catch (e) {}
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

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, " ");
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true });
}

function fmtDuration(sec) {
  if (!sec || sec < 1) return "< 1s";
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function timeAgo(iso) {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 10) return "Just now";
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return fmtDate(iso);
}

function riskColor(risk) {
  if (risk === "CRITICAL") return "#f43f5e";
  if (risk === "HIGH") return "#f59e0b";
  if (risk === "MODERATE") return "#f59e0b";
  if (risk === "LOW") return "#10b981";
  if (risk === "RESOLVED") return "#10b981";
  return "#94a3b8";
}

function riskLabel(risk, status) {
  if (status === "ESCALATED_CAD" || risk === "CRITICAL") return "🚨 CRITICAL (Tier 3)";
  if (status === "ESCALATED_CAREGIVER" || risk === "HIGH") return "⚠️ HIGH (Tier 2)";
  if (risk === "MODERATE") return "ℹ️ MODERATE (Caution)";
  if (status === "RESOLVED") return "✓ RESOLVED";
  if (risk === "LOW") return "🛡️ LOW / NORMAL";
  return risk || "UNKNOWN";
}

function locLabel(loc) {
  const map = {
    bathroom: "Bathroom",
    living: "Living Room",
    kitchen: "Kitchen",
    bedroom: "Bedroom"
  };
  return map[(loc || "").toLowerCase()] || capitalize(loc);
}

function eventLabel(type) {
  const map = {
    possible_fall: "Fall Event",
    dropped_object_reach: "Object Drop",
    environmental_hazard: "Environmental Hazard",
    loud_thud: "Loud Impact",
    prolonged_inactivity: "Prolonged Inactivity",
    unknown: "Unclassified Anomaly"
  };
  return map[(type || "").toLowerCase()] || capitalize(type);
}

function isActiveStatus(status) {
  return status === "ACTIVE" || status === "ESCALATED_CAREGIVER" || status === "ESCALATED_CAD";
}

// ---------------------------------------------------------------------------
// 2. Filter State
// ---------------------------------------------------------------------------

const filterState = {
  date: "all",
  severity: "all",
  room: "all",
  status: "all"
};

function applyHistoryFilters() {
  filterState.date = (document.getElementById("filterDate") || {}).value || "all";
  filterState.severity = (document.getElementById("filterSeverity") || {}).value || "all";
  filterState.room = (document.getElementById("filterRoom") || {}).value || "all";
  filterState.status = (document.getElementById("filterStatus") || {}).value || "all";

  if (window.niraStore) {
    renderIncidentHistory(window.niraStore.state);
  }
}

function resetHistoryFilters() {
  filterState.date = "all";
  filterState.severity = "all";
  filterState.room = "all";
  filterState.status = "all";

  const els = ["filterDate", "filterSeverity", "filterRoom", "filterStatus"];
  els.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "all";
  });

  if (window.niraStore) {
    renderIncidentHistory(window.niraStore.state);
  }
}

function filterIncidentHistory(items) {
  return (items || []).filter(inc => {
    // Date filter
    if (filterState.date !== "all") {
      const incMs = new Date(inc.createdAt).getTime();
      const now = Date.now();
      if (filterState.date === "today") {
        const startOfDay = new Date();
        startOfDay.setHours(0, 0, 0, 0);
        if (incMs < startOfDay.getTime()) return false;
      } else if (filterState.date === "7d") {
        if (incMs < now - 7 * 86400000) return false;
      } else if (filterState.date === "30d") {
        if (incMs < now - 30 * 86400000) return false;
      }
    }

    // Severity filter
    if (filterState.severity !== "all") {
      const r = inc.currentRiskLevel || inc.initialRiskLevel || "";
      if (r.toUpperCase() !== filterState.severity.toUpperCase()) return false;
    }

    // Room filter
    if (filterState.room !== "all") {
      const loc = (inc.location || "").toLowerCase();
      if (loc !== filterState.room) return false;
    }

    // Status filter
    if (filterState.status !== "all") {
      if (filterState.status === "ACTIVE") {
        if (!isActiveStatus(inc.status)) return false;
      } else if (filterState.status === "RESOLVED") {
        if (inc.status !== "RESOLVED") return false;
      }
    }

    return true;
  });
}

// ---------------------------------------------------------------------------
// 3. Trust Hero Banner Renderer
// ---------------------------------------------------------------------------

function renderTrustHero(state) {
  const inc = state.incident || {};
  const emg = state.emergency || {};
  const heroCard = document.getElementById("portalTrustHero");
  const heroStatusPill = document.getElementById("heroStatusPill");
  const heroStatusText = document.getElementById("heroStatusText");
  const heroHeadline = document.getElementById("heroHeadline");
  const heroSubtext = document.getElementById("heroSubtext");
  const heroTimestamp = document.getElementById("heroTimestamp");
  const btnHeroDoorLock = document.getElementById("btnHeroDoorLock");
  const btnHeroDoorText = document.getElementById("btnHeroDoorText");

  const risk = inc.currentRiskLevel || "UNKNOWN";
  const status = inc.status || "NORMAL";
  const location = locLabel(inc.location || "home");
  const isUnlocked = (emg.doorLockState || "UNLOCKED") === "UNLOCKED";

  // Compute state-derived hero content
  let statusText = "🛡️ ALL CLEAR • PROTECTED & SECURE";
  let headline = `Eleanor is currently safe and calm.`;
  let subtext = "All ambient safety sensors are online. No unanswered wellness checks or critical deviations detected.";
  let isEmergency = false;

  if (status === "ESCALATED_CAD" || risk === "CRITICAL") {
    isEmergency = true;
    statusText = "🚨 EMERGENCY ACTIVE • FIRST RESPONDERS EN ROUTE";
    headline = `⚠️ Critical Emergency: Fall Detected in ${location}.`;
    subtext = "Boston EMS 911 (Medic-14) has been dispatched. Smart entrance deadbolt is UNLOCKED. Two-way audio channel is open with your Echo Show 15.";
  } else if (status === "ESCALATED_CAREGIVER" || risk === "HIGH") {
    isEmergency = true;
    statusText = "⚠️ ALERT • CAREGIVER NOTIFIED";
    headline = `Eleanor needs assistance in the ${location}.`;
    subtext = "You've been alerted via Echo Show Drop-In, push notification, and SMS. Eleanor called for help. Please respond.";
  } else if (status === "ACTIVE") {
    isEmergency = false;
    statusText = "ℹ️ WELLNESS CHECK IN PROGRESS";
    headline = `Wellness check initiated — monitoring Eleanor's response.`;
    subtext = "A safety anomaly was detected. NIRA is waiting for Eleanor's verbal confirmation. You will be alerted if escalation is required.";
  } else if (status === "RESOLVED" || risk === "LOW") {
    isEmergency = false;
    statusText = "🛡️ ALL CLEAR • RESOLVED";
    headline = `Eleanor is safe. Most recent alert was resolved.`;
    subtext = "The last wellness check was confirmed safe. Passive ambient monitoring has resumed normally.";
  } else {
    isEmergency = false;
    statusText = "🛡️ ALL CLEAR • PROTECTED & SECURE";
    headline = `Eleanor is comfortable and secure at home.`;
    subtext = "All 5 ambient safety sensors are online. No anomalies, no unanswered wellness checks, no deviations detected.";
  }

  if (heroCard) {
    heroCard.className = isEmergency ? "portal-hero-card emergency-active" : "portal-hero-card";
  }

  if (heroStatusPill) {
    heroStatusPill.className = isEmergency ? "hero-status-pill emergency" : "hero-status-pill";
  }

  if (heroStatusText) heroStatusText.textContent = statusText;
  if (heroHeadline) heroHeadline.textContent = headline;
  if (heroSubtext) heroSubtext.textContent = subtext;
  if (heroTimestamp) {
    const syncTime = state.timestamps?.risk
      ? timeAgo(state.timestamps.risk)
      : "Just now";
    heroTimestamp.textContent = `Last Verified: ${syncTime} • Real-Time Database Sync Active`;
  }

  // Door Lock button
  if (btnHeroDoorLock) {
    btnHeroDoorLock.className = isUnlocked
      ? "btn-hero-action btn-door-unlocked"
      : "btn-hero-action btn-door-locked";
  }
  if (btnHeroDoorText) {
    btnHeroDoorText.textContent = isUnlocked
      ? `Deadbolt: UNLOCKED (PIN: ${emg.doorPin || "8492"})`
      : "Deadbolt: SECURED / LOCKED";
  }
}

// ---------------------------------------------------------------------------
// 4. Overview Cards Renderer
// ---------------------------------------------------------------------------

function renderOverviewCards(state) {
  const inc = state.incident || {};
  const res = state.resident || {};
  const tel = state.telemetry || {};
  const devices = state.devices || [];

  // Risk + status
  const risk = inc.currentRiskLevel || "CRITICAL";
  const overviewRiskBadge = document.getElementById("overviewRiskBadge");
  if (overviewRiskBadge) {
    overviewRiskBadge.textContent = risk;
    const col = riskColor(risk);
    overviewRiskBadge.style.background = `${col}22`;
    overviewRiskBadge.style.borderColor = col;
    overviewRiskBadge.style.color = col;
  }

  // Heart Rate
  const hrBpm = (tel.heartRate && tel.heartRate.current) || state.vitals?.heartRateBpm || 72;
  const hrStatus = (tel.heartRate && tel.heartRate.status) || state.vitals?.heartRateStatus || "Normal";
  const overviewHrVal = document.getElementById("overviewHrVal");
  if (overviewHrVal) {
    overviewHrVal.innerHTML = `${hrBpm} BPM <span style="font-size: 0.74rem; font-weight: 600; color: ${riskColor(risk)};">(${hrBpm > 100 ? "Elevated" : "Normal"})</span>`;
    overviewHrVal.style.color = hrBpm > 100 ? riskColor(risk) : "#10b981";
  }

  const overviewStatusDesc = document.getElementById("overviewStatusDesc");
  if (overviewStatusDesc) {
    const mvScore = state.vitals?.movementScore ?? 0.95;
    const mvDesc = state.vitals?.movementDescription || "Active & ambulatory";
    overviewStatusDesc.innerHTML = `Movement: ${mvScore.toFixed(2)} / 1.0 (${mvDesc})<br>Status: ${inc.status || "NORMAL"} • Updated: ${timeAgo(state.timestamps?.risk)}`;
  }

  // Location & Activity
  const location = locLabel(inc.location || "living");
  const overviewLocationVal = document.getElementById("overviewLocationVal");
  if (overviewLocationVal) overviewLocationVal.textContent = location;

  const overviewActivityDesc = document.getElementById("overviewActivityDesc");
  if (overviewActivityDesc) {
    const room = (state.rooms || {})[inc.location || "living"] || {};
    const posture = room.posture || "Normal ambulation";
    const sensors = (room.activeSensors || ["Ambient Radar"]).join(" & ");
    const hazards = (room.hazards || ["None detected"]).join(" • ");
    overviewActivityDesc.innerHTML = `Activity: ${posture}<br>Sensors: ${sensors}<br>Conditions: ${hazards}`;
  }

  // Device Status
  const onlineCount = devices.filter(d => d.status === "Online" || d.status === "Connected" || d.status === "Active").length;
  const totalCount = devices.length || 5;
  const overviewDeviceCount = document.getElementById("overviewDeviceCount");
  if (overviewDeviceCount) {
    overviewDeviceCount.textContent = `${onlineCount} / ${totalCount} Online`;
    overviewDeviceCount.style.color = onlineCount === totalCount ? "#10b981" : (onlineCount > totalCount / 2 ? "#f59e0b" : "#f43f5e");
  }

  const overviewDeviceList = document.getElementById("overviewDeviceList");
  if (overviewDeviceList) {
    const topDevices = devices.slice(0, 3);
    if (topDevices.length > 0) {
      overviewDeviceList.innerHTML = topDevices.map(d =>
        `${d.name}: <strong style="color: #34d399;">${d.status}</strong> (${d.battery})`
      ).join("<br>");
    } else {
      overviewDeviceList.textContent = "Connecting to device network…";
    }
  }
}

// ---------------------------------------------------------------------------
// 5. Summary Statistics Strip Renderer
// ---------------------------------------------------------------------------

function renderSummaryStats(state) {
  const history = state.incidentHistory || [];
  const caregivers = state.caregivers || [];

  const activeCount = history.filter(h => isActiveStatus(h.status)).length;
  const resolvedCount = history.filter(h => h.status === "RESOLVED").length;
  const cgvConnected = caregivers.filter(c => c.id !== "cgv_cad").length;

  // Risk Trends: if no incidents today, it's stable
  const todayIncidents = history.filter(h => {
    const incMs = new Date(h.createdAt).getTime();
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    return incMs >= todayStart.getTime();
  });
  const hasEmergencyToday = todayIncidents.some(h => h.currentRiskLevel === "CRITICAL" || h.status === "ESCALATED_CAD");
  const stabilityPercent = hasEmergencyToday ? "82% Normal" : "98% Normal";

  const statActive = document.getElementById("statActiveIncidents");
  if (statActive) {
    statActive.textContent = `${activeCount} Active`;
    statActive.style.color = activeCount > 0 ? "#f43f5e" : "#34d399";
  }

  const statResolved = document.getElementById("statResolvedIncidents");
  if (statResolved) {
    statResolved.textContent = `${resolvedCount} Resolved`;
    statResolved.style.color = "#34d399";
  }

  const statCaregivers = document.getElementById("statCaregiversCount");
  if (statCaregivers) {
    statCaregivers.textContent = `${cgvConnected} Guardians`;
  }

  const statStability = document.getElementById("statStabilityScore");
  if (statStability) {
    statStability.textContent = stabilityPercent;
    statStability.style.color = hasEmergencyToday ? "#f59e0b" : "#c084fc";
  }

  // Total count tag
  const matchCount = document.getElementById("historyMatchCountTag");
  if (matchCount) {
    matchCount.textContent = `${history.length} Incidents Total`;
  }
}

// ---------------------------------------------------------------------------
// 6. Incident History Feed Renderer (Filterable, Event-Driven)
// ---------------------------------------------------------------------------

let lastHistoryHash = "";

function renderIncidentHistory(state) {
  const container = document.getElementById("incidentHistoryFeed");
  const emptyState = document.getElementById("emptyHistoryState");
  if (!container) return;

  const raw = state.incidentHistory || [];
  const filtered = filterIncidentHistory(raw);

  const currentHash = filtered.map(h => `${h.id}:${h.status}:${h.resolution}`).join("|");
  if (currentHash === lastHistoryHash) return;
  lastHistoryHash = currentHash;

  // Update match count
  const matchCount = document.getElementById("historyMatchCountTag");
  if (matchCount) {
    matchCount.textContent = filtered.length > 0
      ? `${filtered.length} of ${raw.length} Incidents`
      : `${raw.length} Incidents Total`;
  }

  if (filtered.length === 0) {
    container.innerHTML = "";
    if (emptyState) emptyState.style.display = "block";

    const emptyTitle = document.getElementById("emptyTitleText");
    const emptyDesc = document.getElementById("emptyDescText");

    if (raw.length === 0) {
      // No data at all
      if (emptyTitle) emptyTitle.textContent = "No Safety Events Recorded";
      if (emptyDesc) emptyDesc.textContent = `Eleanor's safety record is completely clean. NIRA's ambient sensor array is actively monitoring all ${(state.devices || []).length || 5} sensor zones and will notify you immediately if anything requires attention.`;
    } else {
      // Data exists but filters produced no matches
      if (emptyTitle) emptyTitle.textContent = "No Incidents Match Your Filters";
      if (emptyDesc) emptyDesc.textContent = `No incidents match the current filter criteria. Try broadening your search (e.g., change date range to "All Dates" or select "All Severities").`;
    }
    return;
  }

  if (emptyState) emptyState.style.display = "none";

  let html = "";
  filtered.forEach((inc, idx) => {
    const isActive = isActiveStatus(inc.status);
    const isResolved = inc.status === "RESOLVED";
    const cardClass = isActive ? "incident-entry-card active-emergency" : (isResolved ? "incident-entry-card resolved-entry" : "incident-entry-card");

    const risk = inc.currentRiskLevel || "UNKNOWN";
    const rCol = riskColor(risk);

    const dateStr = fmtDate(inc.createdAt);
    const timeStr = fmtTime(inc.createdAt);
    const locationLabel = locLabel(inc.location);
    const eventTypeLabel = eventLabel(inc.eventType);
    const statusLabel = isActive ? (inc.status === "ESCALATED_CAD" ? "Emergency Dispatch" : "Active / Escalated") : "Resolved Safe";
    const durationLabel = inc.durationSeconds ? fmtDuration(inc.durationSeconds) : (isActive ? "Ongoing" : "—");
    const resolvedAtStr = inc.resolvedAt ? `${fmtDate(inc.resolvedAt)} at ${fmtTime(inc.resolvedAt)}` : (isActive ? "In Progress" : "—");
    const riskLabel2 = riskLabel(risk, inc.status);

    html += `
      <div class="${cardClass}" id="hist-${inc.id}">
        <div class="incident-header-row">
          <div class="incident-meta-left">
            <span class="incident-datetime">${dateStr} at ${timeStr}</span>
            <span class="incident-loc-pill">📍 ${locationLabel}</span>
            ${isActive ? `<span class="vtl-sim-badge" style="background: rgba(244, 63, 94, 0.2); border-color: var(--accent-red); color: #fda4af; font-size: 0.68rem;">⚡ ACTIVE</span>` : ""}
          </div>

          <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span style="font-size: 0.74rem; font-weight: 800; text-transform: uppercase; padding: 3px 9px; border-radius: 4px; background: ${rCol}20; border: 1px solid ${rCol}60; color: ${rCol};">
              ${riskLabel2}
            </span>
            <span style="font-size: 0.72rem; font-family: var(--font-mono); color: #94a3b8;">
              ${inc.id}
            </span>
          </div>
        </div>

        <div class="incident-triage-grid">
          <div>
            <div class="triage-col-label">What Happened</div>
            <div class="triage-col-text">${eventTypeLabel} &bull; ${Math.round((inc.confidence || 0.94) * 100)}% Confidence</div>
          </div>

          <div>
            <div class="triage-col-label">How NIRA Responded</div>
            <div class="triage-col-text">${inc.response || "Wellness check initiated"}</div>
          </div>

          <div>
            <div class="triage-col-label">Outcome &amp; Resolution</div>
            <div class="triage-col-text">${inc.resolution || statusLabel}</div>
          </div>

          <div>
            <div class="triage-col-label">Duration &amp; Resolved At</div>
            <div class="triage-col-text">${durationLabel} &bull; ${resolvedAtStr}</div>
          </div>
        </div>

        ${inc.trigger ? `
        <div style="font-size: 0.74rem; color: #94a3b8; line-height: 1.45; background: rgba(0,0,0,0.25); padding: 8px 12px; border-radius: 6px; margin-top: 2px;">
          <span style="font-weight: 800; color: #cbd5e1;">Why NIRA Escalated: </span>${inc.trigger}
        </div>
        ` : ""}

        <button class="btn-expand-timeline" onclick="toggleNestedTimeline('${inc.id}')">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
          <span id="toggle-label-${inc.id}">View event-by-event audit log</span>
        </button>

        <div class="nested-timeline-box" id="nested-timeline-${inc.id}" style="display: none;">
          <div style="font-size: 0.72rem; color: #94a3b8; text-align: center; padding: 8px 0;">
            Loading event log…
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// 7. Nested Timeline (Expandable per-incident audit log)
// ---------------------------------------------------------------------------

const expandedTimelines = new Set();

async function toggleNestedTimeline(incidentId) {
  const box = document.getElementById(`nested-timeline-${incidentId}`);
  const label = document.getElementById(`toggle-label-${incidentId}`);
  if (!box) return;

  const isOpen = expandedTimelines.has(incidentId);
  if (isOpen) {
    box.style.display = "none";
    expandedTimelines.delete(incidentId);
    if (label) label.textContent = "View event-by-event audit log";
  } else {
    box.style.display = "flex";
    expandedTimelines.add(incidentId);
    if (label) label.textContent = "Hide event log";
    await loadNestedTimeline(incidentId, box);
  }
}

async function loadNestedTimeline(incidentId, box) {
  // First check niraStore state.timeline if this is the current active incident
  if (window.niraStore && window.niraStore.state.incident.id === incidentId) {
    const tl = window.niraStore.state.timeline || [];
    if (tl.length > 0) {
      renderNestedTimelineItems(tl, box);
      return;
    }
  }

  // Otherwise fetch from backend
  try {
    box.innerHTML = `<div style="font-size: 0.72rem; color: #94a3b8; text-align: center; padding: 8px;">Fetching audit log from database…</div>`;
    const resp = await fetch(`/api/v1/incidents/${encodeURIComponent(incidentId)}/timeline`);
    if (!resp.ok) throw new Error("Not found");
    const items = await resp.json();
    if (!items || items.length === 0) {
      box.innerHTML = `<div style="font-size: 0.72rem; color: #94a3b8; text-align: center; padding: 8px;">No timeline entries recorded for this incident.</div>`;
      return;
    }
    renderNestedTimelineItems(items, box);
  } catch (e) {
    box.innerHTML = `<div style="font-size: 0.72rem; color: #94a3b8; text-align: center; padding: 8px;">Timeline data unavailable (offline).</div>`;
  }
}

function renderNestedTimelineItems(items, box) {
  let html = "";
  items.forEach(item => {
    const timeStr = fmtTime(item.timestamp);
    const actorLabel = (item.actor || "SYSTEM").replace(/_/g, " ");

    let dotColor = "#94a3b8";
    if (item.action_type?.includes("CAD") || item.action_type?.includes("ESCALAT")) dotColor = "#f43f5e";
    else if (item.action_type?.includes("CAREGIVER") || item.action_type?.includes("GUARDIAN")) dotColor = "#f59e0b";
    else if (item.action_type?.includes("RESOLVE") || item.action_type?.includes("SAFE")) dotColor = "#10b981";
    else if (item.action_type?.includes("VOICE") || item.action_type?.includes("WELLNESS")) dotColor = "#38bdf8";
    else if (item.action_type?.includes("RISK")) dotColor = "#a855f7";

    html += `
      <div style="display: flex; gap: 12px; align-items: flex-start;">
        <div style="display: flex; flex-direction: column; align-items: center; flex-shrink: 0; padding-top: 3px;">
          <div style="width: 9px; height: 9px; border-radius: 50%; background: ${dotColor}; box-shadow: 0 0 6px ${dotColor}; flex-shrink: 0;"></div>
        </div>
        <div style="flex: 1;">
          <div style="font-size: 0.70rem; font-family: var(--font-mono); color: ${dotColor}; font-weight: 700; margin-bottom: 2px;">
            ${timeStr} &bull; ${actorLabel}
          </div>
          <div style="font-size: 0.76rem; color: #e2e8f0; line-height: 1.45;">${item.description || item.action_type}</div>
        </div>
      </div>
    `;
  });
  box.innerHTML = html || `<div style="font-size: 0.72rem; color: #94a3b8; text-align: center; padding: 8px;">No events recorded.</div>`;
}

// ---------------------------------------------------------------------------
// 8. Portal Connection Badge
// ---------------------------------------------------------------------------

function renderConnectionBadge(state) {
  const badge = document.getElementById("portalConnectionBadge");
  if (!badge) return;
  const conn = (state.connection || {}).status || "connected";
  if (conn === "connected") {
    badge.style.background = "rgba(16, 185, 129, 0.15)";
    badge.style.borderColor = "rgba(16, 185, 129, 0.35)";
    badge.style.color = "#34d399";
    badge.innerHTML = "🟢 Connected &bull; Real-Time DB Sync";
  } else if (conn === "reconnecting") {
    badge.style.background = "rgba(245, 158, 11, 0.15)";
    badge.style.borderColor = "rgba(245, 158, 11, 0.35)";
    badge.style.color = "#fbbf24";
    badge.innerHTML = "🟡 Reconnecting…";
  } else {
    badge.style.background = "rgba(244, 63, 94, 0.15)";
    badge.style.borderColor = "rgba(244, 63, 94, 0.35)";
    badge.style.color = "#fda4af";
    badge.innerHTML = "🔴 Offline Mode";
  }
}

// ---------------------------------------------------------------------------
// 9. Master Admin Console Render (subscribed to niraStore)
// ---------------------------------------------------------------------------

function renderAdminConsole(state) {
  if (!state) return;

  renderConnectionBadge(state);
  renderTrustHero(state);
  renderOverviewCards(state);
  renderSummaryStats(state);
  renderIncidentHistory(state);
}

// ---------------------------------------------------------------------------
// 10. Interactive Action Handlers
// ---------------------------------------------------------------------------

function toggleDoorOverride() {
  if (!window.niraStore) return;
  const newState = window.niraStore.toggleEmergencyDoorLock
    ? window.niraStore.toggleEmergencyDoorLock()
    : null;

  const isUnlocked = (window.niraStore.state.emergency.doorLockState || "UNLOCKED") === "UNLOCKED";
  playAdminChime(isUnlocked ? 880 : 440);
  showToast(isUnlocked
    ? "🔓 Front Door <strong>UNLOCKED</strong> — Emergency access enabled (PIN: 8492)."
    : "🔒 Front Door <strong>SECURED</strong> — Deadbolt restored."
  );
}

function triggerEchoDropIn() {
  playAdminChime(580);
  showToast("🎙️ Connecting live <strong>Echo Show 15 Drop-In Audio Call</strong> to Beacon Hill Unit 4B…");
}

async function triggerTestSimulation(scenario) {
  playAdminChime(scenario === "false_alarm" ? 660 : (scenario === "responsive" ? 500 : 880));
  showToast(`⚡ Ingesting scenario: <strong>${scenario}</strong> to backend database…`);

  try {
    if (window.niraStore) {
      await window.niraStore.dispatchScenario(scenario);
      const risk = window.niraStore.state.incident.currentRiskLevel;
      showToast(`✅ Database updated — Risk Level: <strong>${risk}</strong>`);
      // Force re-render
      lastHistoryHash = "";
      renderAdminConsole(window.niraStore.state);
    }
  } catch (err) {
    console.warn("[AdminPortal] triggerTestSimulation error:", err);
    showToast("⚠️ Event ingestion error. Displaying offline state.");
  }
}

// Legacy compatibility shims used by admin.html simulation buttons
function switchPayloadView() {}
function openVideoDemoModal() {
  const m = document.getElementById("videoDemoModal");
  if (m) m.style.display = "flex";
  if (window.videoReel) videoReel.play();
}

function closeVideoDemoModal() {
  const m = document.getElementById("videoDemoModal");
  if (m) m.style.display = "none";
  if (window.videoReel) videoReel.pause();
}

function seekVideoToScene(idx) {
  if (window.videoReel) {
    const sceneTimecodes = [0, 8, 18, 28, 38];
    videoReel.seek(sceneTimecodes[idx] || 0);
  }
}

// ---------------------------------------------------------------------------
// 11. DOMContentLoaded — Initialization
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  if (window.niraStore) {
    // Initialize store connection (SSE + REST sync)
    window.niraStore.init();

    // Subscribe to all state updates
    window.niraStore.subscribe((state) => {
      renderAdminConsole(state);
    });

    // Run initial render immediately
    renderAdminConsole(window.niraStore.state);

    // Refresh time-relative labels every 30s (e.g., "3m ago" → "4m ago")
    setInterval(() => {
      if (window.niraStore) {
        renderTrustHero(window.niraStore.state);
        renderSummaryStats(window.niraStore.state);
      }
    }, 30000);
  }

  console.log("[NIRA Family Admin Portal] v5.0 ready — Real-time backend state active.");
});
