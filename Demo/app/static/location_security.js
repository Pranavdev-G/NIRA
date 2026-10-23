/**
 * NIRA - Location & Residence Security Integration
 * Live GPS tracking, EMS arrival verification, and automated smart-lock security.
 */

(function () {
  'use strict';

  // State cache
  let secState = null;
  let secMap = null;
  let residentMarker = null;
  let responderMarker = null;
  let geofenceCircle = null;
  let routePolyline = null;
  let syncTimer = null;

  // Icons for Leaflet
  function createCustomIcon(htmlContent, className, iconSize) {
    if (typeof L === 'undefined' || !L.divIcon) return null;
    return L.divIcon({
      html: htmlContent,
      className: className || 'custom-map-icon',
      iconSize: iconSize || [32, 32],
      iconAnchor: [iconSize ? iconSize[0] / 2 : 16, iconSize ? iconSize[1] / 2 : 16]
    });
  }

  // Initialize interactive Leaflet map or high-contrast vector fallback
  function initSecurityMap() {
    const mapEl = document.getElementById('securityLiveMap');
    if (!mapEl) return;

    if (typeof L === 'undefined') {
      renderVectorSecurityMap(mapEl);
      return;
    }

    try {
      const defaultCenter = [42.3588, -71.0638];
      secMap = L.map('securityLiveMap', {
        center: defaultCenter,
        zoom: 16,
        zoomControl: false,
        attributionControl: false
      });

      // Dark style tile layer from CartoDB Dark Matter
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd'
      }).addTo(secMap);

      // 35m residence geofence perimeter
      geofenceCircle = L.circle(defaultCenter, {
        color: '#14b8a6',
        fillColor: '#14b8a6',
        fillOpacity: 0.15,
        weight: 2,
        dashArray: '4, 4',
        radius: 35
      }).addTo(secMap);

      // Resident pin (Teal pulse)
      const residentIconHtml = `
        <div style="position:relative; width:28px; height:28px; display:flex; align-items:center; justify-content:center;">
          <div style="position:absolute; width:100%; height:100%; background:rgba(20, 184, 166, 0.4); border-radius:50%; animation:pulseTeal 1.8s infinite;"></div>
          <div style="position:relative; width:14px; height:14px; background:#14b8a6; border:2px solid #ffffff; border-radius:50%; box-shadow:0 0 10px #14b8a6;"></div>
        </div>`;
      const residentIcon = createCustomIcon(residentIconHtml, 'sec-resident-icon', [28, 28]);
      residentMarker = L.marker(defaultCenter, { icon: residentIcon }).addTo(secMap);
      residentMarker.bindPopup('<strong>Eleanor Vance (Resident)</strong><br>48 Beacon St, Apt 4B • Within 35m Geofence<br><span style="color:#14b8a6;font-size:0.75rem;">GPS Signal: High Confidence (Simulation)</span>');

      // Responder pin (Ambulance / Emergency vehicle)
      const responderIconHtml = `
        <div style="position:relative; width:34px; height:34px; display:flex; align-items:center; justify-content:center;">
          <div style="position:absolute; width:100%; height:100%; background:rgba(244, 63, 94, 0.35); border-radius:50%; animation:pulseRed 1.2s infinite;"></div>
          <div style="background:#e11d48; color:#fff; border:2px solid #fff; border-radius:8px; padding:3px 6px; font-size:11px; font-weight:800; font-family:sans-serif; box-shadow:0 2px 8px rgba(0,0,0,0.6); display:flex; align-items:center; gap:3px;">
            <span>🚑</span><span>42</span>
          </div>
        </div>`;
      const responderIcon = createCustomIcon(responderIconHtml, 'sec-responder-icon', [34, 34]);
      responderMarker = L.marker([42.3631, -71.0682], { icon: responderIcon }).addTo(secMap);
      responderMarker.bindPopup('<strong>EMS Medic-42</strong><br>Boston EMS First Responders<br><span style="color:#38bdf8;font-size:0.75rem;">Status: Dispatched</span>');

      // Polyline route
      routePolyline = L.polyline([[42.3631, -71.0682], defaultCenter], {
        color: '#38bdf8',
        weight: 3,
        opacity: 0.7,
        dashArray: '6, 6'
      }).addTo(secMap);

      // Fit bounds nicely
      secMap.fitBounds([
        [42.3631, -71.0682],
        defaultCenter
      ], { padding: [35, 35] });

    } catch (err) {
      console.warn('[SecurityMap] Leaflet init fallback to vector SVG:', err);
      renderVectorSecurityMap(mapEl);
    }
  }

  // High-fidelity animated vector SVG fallback map
  function renderVectorSecurityMap(mapEl) {
    mapEl.innerHTML = `
      <div style="position:relative; width:100%; height:100%; background:#020617; overflow:hidden;">
        <svg viewBox="0 0 500 220" style="width:100%; height:100%; display:block;">
          <defs>
            <radialGradient id="secBeaconGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#14b8a6" stop-opacity="0.35"/>
              <stop offset="100%" stop-color="#14b8a6" stop-opacity="0"/>
            </radialGradient>
            <radialGradient id="secEmsGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.4"/>
              <stop offset="100%" stop-color="#f43f5e" stop-opacity="0"/>
            </radialGradient>
          </defs>
          <line x1="0" y1="110" x2="500" y2="110" stroke="rgba(255,255,255,0.04)" stroke-dasharray="4 4"/>
          <line x1="250" y1="0" x2="250" y2="220" stroke="rgba(255,255,255,0.04)" stroke-dasharray="4 4"/>
          <!-- Street corridors -->
          <path d="M 30 170 Q 200 130 470 70" stroke="rgba(56, 189, 248, 0.15)" stroke-width="14" fill="none" stroke-linecap="round"/>
          <path d="M 30 170 Q 200 130 470 70" stroke="#1e293b" stroke-width="4" fill="none"/>
          <path d="M 320 20 L 375 200" stroke="#1e293b" stroke-width="3" fill="none"/>
          <text x="60" y="188" fill="#475569" font-size="8.5" font-family="monospace">Cambridge St Corridor</text>
          <text x="360" y="195" fill="#475569" font-size="8.5" font-family="monospace">Beacon Hill Sector</text>

          <!-- 35m residence geofence perimeter around Eleanor Vance (cx=360, cy=130) -->
          <circle cx="360" cy="130" r="44" fill="rgba(20, 184, 166, 0.12)" stroke="#14b8a6" stroke-width="1.8" stroke-dasharray="4 3"/>
          <circle cx="360" cy="130" r="62" fill="url(#secBeaconGlow)"/>

          <!-- Dynamic Route Line -->
          <line id="secSvgRouteLine" x1="80" y1="50" x2="360" y2="130" stroke="#38bdf8" stroke-width="2.5" stroke-dasharray="6 4" opacity="0.8"/>

          <!-- Resident Marker -->
          <g transform="translate(360, 130)">
            <circle cx="0" cy="0" r="8" fill="#14b8a6" stroke="#ffffff" stroke-width="2"/>
            <circle cx="0" cy="0" r="15" fill="none" stroke="#14b8a6" stroke-width="1.5" opacity="0.8">
              <animate attributeName="r" values="8;20" dur="2s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.8;0" dur="2s" repeatCount="indefinite"/>
            </circle>
            <text x="0" y="-14" fill="#5eead4" font-size="9.5" font-weight="700" text-anchor="middle" font-family="sans-serif">Eleanor Vance (Apt 4B)</text>
            <text x="0" y="24" fill="#94a3b8" font-size="8" text-anchor="middle" font-family="monospace">35m Geofence Perimeter</text>
          </g>

          <!-- Responder Marker (Medic-42) -->
          <g id="secSvgEmsMarker" transform="translate(80, 50)" style="transition: transform 0.6s ease-in-out;">
            <circle cx="0" cy="0" r="18" fill="url(#secEmsGlow)"/>
            <rect x="-15" y="-11" width="30" height="22" rx="5" fill="#e11d48" stroke="#ffffff" stroke-width="1.5"/>
            <text x="0" y="4" fill="#ffffff" font-size="9" font-weight="900" text-anchor="middle" font-family="sans-serif">🚑 42</text>
            <text id="secSvgEmsStatus" x="0" y="-15" fill="#fca5a5" font-size="8.5" font-weight="700" text-anchor="middle" font-family="sans-serif">Medic-42 (DISPATCHED)</text>
          </g>
        </svg>
      </div>`;
  }

  // Fetch security state from backend
  async function fetchSecurityStatus() {
    try {
      const res = await fetch('/api/v1/security/status', {
        headers: { 'Cache-Control': 'no-cache' }
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      secState = data;
      renderSecurityUI(data);
    } catch (err) {
      console.warn('[Security] Status fetch failed:', err);
    }
  }

  // Update UI components with state
  function renderSecurityUI(data) {
    if (!data) return;

    // 1. Resident telemetry strip
    const residentCoordsEl = document.getElementById('secResidentCoords');
    const residentStatusEl = document.getElementById('secResidentStatus');
    const lastUpdatedEl = document.getElementById('secLastUpdated');
    if (residentCoordsEl && data.resident) {
      residentCoordsEl.textContent = `${data.resident.latitude.toFixed(4)}° N, ${Math.abs(data.resident.longitude).toFixed(4)}° W`;
    }
    if (residentStatusEl && data.resident) {
      residentStatusEl.textContent = data.resident.status;
      residentStatusEl.style.color = data.resident.is_in_residence ? 'var(--accent-teal)' : 'var(--accent-amber)';
    }
    if (lastUpdatedEl && data.resident) {
      lastUpdatedEl.textContent = data.resident.last_updated_time || 'Just now';
    }

    // 2. HUD values
    const hudDist = document.getElementById('hudEmsDistance');
    const hudEta = document.getElementById('hudEmsEta');
    const hudGeofence = document.getElementById('hudGeofenceStatus');
    if (hudDist) {
      hudDist.textContent = data.distance_meters > 0 ? `${Math.round(data.distance_meters)} m` : '0 m (On Scene)';
    }
    if (hudEta) {
      hudEta.textContent = data.eta_seconds > 0 ? formatEta(data.eta_seconds) : 'ARRIVED';
    }
    if (hudGeofence) {
      if (data.is_within_geofence) {
        hudGeofence.textContent = 'INSIDE (35m)';
        hudGeofence.style.color = 'var(--accent-green)';
      } else {
        hudGeofence.textContent = 'OUTSIDE (35m)';
        hudGeofence.style.color = '#f59e0b';
      }
    }

    // 3. Response stage & stepper
    const currentStage = (data.responder && data.responder.status) || 'DISPATCHED';
    const stageBadge = document.getElementById('secStageBadge');
    if (stageBadge) {
      stageBadge.textContent = currentStage;
      if (currentStage === 'ARRIVED') {
        stageBadge.style.background = 'rgba(20, 184, 166, 0.2)';
        stageBadge.style.color = '#2dd4bf';
      } else if (currentStage === 'ARRIVING') {
        stageBadge.style.background = 'rgba(245, 158, 11, 0.2)';
        stageBadge.style.color = '#fbbf24';
      } else {
        stageBadge.style.background = 'rgba(56, 189, 248, 0.2)';
        stageBadge.style.color = '#38bdf8';
      }
    }
    updateStepper(currentStage);

    // 4. Verification Checklist
    const chkIdentity = document.getElementById('chkIdentity');
    const valIdentity = document.getElementById('valIdentity');
    const chkGeofence = document.getElementById('chkGeofence');
    const valGeofence = document.getElementById('valGeofence');
    const chkAuth = document.getElementById('chkAuth');
    const valAuth = document.getElementById('valAuth');

    if (chkIdentity && valIdentity && data.responder) {
      const isAuth = !!data.responder.is_authorized;
      valIdentity.textContent = `${data.responder.unit_name} (${data.responder.authorized_badge_id}) • ${isAuth ? 'Verified Official' : 'UNAUTHORIZED'}`;
      chkIdentity.className = 'verify-item ' + (isAuth ? 'verified' : 'failed');
      chkIdentity.querySelector('.verify-icon').innerHTML = isAuth ? '&#10004;' : '&#10006;';
    }

    if (chkGeofence && valGeofence) {
      const inside = !!data.is_within_geofence;
      valGeofence.textContent = inside
        ? `Verified within 35m (${Math.round(data.distance_meters)}m from door)`
        : `Outside perimeter (${Math.round(data.distance_meters)}m away)`;
      chkGeofence.className = 'verify-item ' + (inside ? 'verified' : (currentStage === 'ARRIVED' ? 'failed' : ''));
      chkGeofence.querySelector('.verify-icon').innerHTML = inside ? '&#10004;' : (currentStage === 'ARRIVED' ? '&#10006;' : '&#9675;');
    }

    if (chkAuth && valAuth && data.smart_lock) {
      const lockOnline = data.smart_lock.is_online;
      valAuth.textContent = `${data.smart_lock.provider_name} • ${lockOnline ? 'Encrypted Stream Online' : 'OFFLINE / NO COMMS'}`;
      chkAuth.className = 'verify-item ' + (lockOnline ? 'verified' : 'failed');
      chkAuth.querySelector('.verify-icon').innerHTML = lockOnline ? '&#10004;' : '&#10006;';
    }

    // 5. Smart Lock Card & Buttons
    const doorBar = document.getElementById('doorLockBar');
    const doorTitle = document.getElementById('doorTitle');
    const doorSub = document.getElementById('doorSub');
    const btnUnlock = document.getElementById('btnExecuteUnlock');

    const lockState = (data.smart_lock && data.smart_lock.state) || 'LOCKED';
    if (doorBar && doorTitle && doorSub) {
      // Remove previous status classes
      doorBar.classList.remove('lock-state-locked', 'lock-state-unlocking', 'lock-state-unlocked', 'lock-state-error');

      if (lockState === 'UNLOCKED') {
        doorBar.classList.add('lock-state-unlocked');
        doorBar.style.background = 'rgba(20, 184, 166, 0.15)';
        doorBar.style.borderColor = 'rgba(20, 184, 166, 0.4)';
        doorTitle.textContent = 'Front Door Smart Lock: UNLOCKED';
        doorTitle.style.color = '#2dd4bf';
        doorSub.textContent = data.smart_lock.message || 'Door unlocked for authorized responders';
        if (btnUnlock) {
          btnUnlock.disabled = true;
          btnUnlock.textContent = 'Unlocked';
          btnUnlock.style.opacity = '0.6';
        }
      } else if (lockState === 'UNLOCKING') {
        doorBar.classList.add('lock-state-unlocking');
        doorBar.style.background = 'rgba(245, 158, 11, 0.15)';
        doorBar.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        doorTitle.textContent = 'Front Door Smart Lock: UNLOCKING...';
        doorTitle.style.color = '#fbbf24';
        doorSub.textContent = 'Verifying cryptographic credentials and dispatching pulse...';
        if (btnUnlock) {
          btnUnlock.disabled = true;
          btnUnlock.textContent = 'Authenticating...';
        }
      } else if (lockState === 'ERROR') {
        doorBar.classList.add('lock-state-error');
        doorBar.style.background = 'rgba(244, 63, 94, 0.15)';
        doorBar.style.borderColor = 'rgba(244, 63, 94, 0.4)';
        doorTitle.textContent = 'Front Door Smart Lock: ERROR';
        doorTitle.style.color = '#fb7185';
        doorSub.textContent = data.smart_lock.message || 'Automatic unlock unavailable — manual access required';
        if (btnUnlock) {
          btnUnlock.disabled = false;
          btnUnlock.textContent = 'Retry Unlock';
          btnUnlock.style.opacity = '1';
        }
      } else {
        // LOCKED
        doorBar.classList.add('lock-state-locked');
        doorBar.style.background = 'rgba(15, 23, 42, 0.6)';
        doorBar.style.borderColor = 'var(--border-subtle)';
        doorTitle.textContent = 'Front Door Smart Lock: LOCKED';
        doorTitle.style.color = '#f1f5f9';
        doorSub.textContent = data.smart_lock.message || 'Waiting for authorized response team';
        if (btnUnlock) {
          // Enable if arrived or ready to unlock
          const canUnlock = data.is_within_geofence && data.responder && data.responder.is_authorized;
          btnUnlock.disabled = !canUnlock;
          btnUnlock.textContent = 'Unlock Door';
          btnUnlock.style.opacity = canUnlock ? '1' : '0.5';
        }
      }
    }

    // 6. Map positions
    updateMapPositions(data);

    // 7. Activity Log
    renderActivityLog(data.audit_log || []);
  }

  function updateStepper(stage) {
    const stages = ['DISPATCHED', 'EN_ROUTE', 'ARRIVING', 'ARRIVED'];
    const activeIdx = stages.indexOf(stage);

    stages.forEach((st, idx) => {
      const stepEl = document.getElementById(`step-${st}`);
      if (!stepEl) return;
      stepEl.classList.remove('active', 'completed');
      if (idx < activeIdx) {
        stepEl.classList.add('completed');
      } else if (idx === activeIdx) {
        stepEl.classList.add('active');
      }
    });

    for (let c = 1; c <= 3; c++) {
      const conn = document.getElementById(`conn-${c}`);
      if (conn) {
        if (activeIdx >= c) {
          conn.classList.add('completed');
        } else {
          conn.classList.remove('completed');
        }
      }
    }
  }

  function updateMapPositions(data) {
    if (!data.resident || !data.responder) return;

    if (secMap) {
      try {
        const residentLatLng = [data.resident.latitude, data.resident.longitude];
        const responderLatLng = [data.responder.latitude, data.responder.longitude];

        if (residentMarker) {
          residentMarker.setLatLng(residentLatLng);
        }
        if (geofenceCircle) {
          geofenceCircle.setLatLng(residentLatLng);
        }
        if (responderMarker) {
          responderMarker.setLatLng(responderLatLng);
          responderMarker.setPopupContent(`
            <strong>${data.responder.unit_name}</strong><br>
            Status: <b>${data.responder.status}</b><br>
            Distance: ${Math.round(data.distance_meters)}m<br>
            <span style="color:${data.responder.is_authorized ? '#14b8a6' : '#e11d48'};font-size:0.75rem;">
              ${data.responder.is_authorized ? '✓ Authorized Responder' : '⚠ Unauthorized'}
            </span>
          `);
        }
        if (routePolyline) {
          routePolyline.setLatLngs([responderLatLng, residentLatLng]);
        }
      } catch (e) {
        console.error('[SecurityMap] Error updating map coords:', e);
      }
    }

    updateVectorMapCoords(data);
  }

  function updateVectorMapCoords(data) {
    const emsMarker = document.getElementById('secSvgEmsMarker');
    const routeLine = document.getElementById('secSvgRouteLine');
    const emsStatus = document.getElementById('secSvgEmsStatus');
    if (!emsMarker) return;

    const stage = (data.responder && data.responder.status) || 'DISPATCHED';
    let targetX = 80;
    let targetY = 50;

    if (stage === 'EN_ROUTE') {
      targetX = 180;
      targetY = 80;
    } else if (stage === 'ARRIVING') {
      targetX = 275;
      targetY = 110;
    } else if (stage === 'ARRIVED') {
      targetX = 352;
      targetY = 126;
    }

    emsMarker.setAttribute('transform', `translate(${targetX}, ${targetY})`);

    if (routeLine) {
      routeLine.setAttribute('x1', targetX);
      routeLine.setAttribute('y1', targetY);
      if (stage === 'ARRIVED') {
        routeLine.setAttribute('stroke', '#14b8a6');
        routeLine.setAttribute('opacity', '0.4');
      } else {
        routeLine.setAttribute('stroke', '#38bdf8');
        routeLine.setAttribute('opacity', '0.8');
      }
    }

    if (emsStatus) {
      emsStatus.textContent = `${data.responder.unit_id} (${stage}) • ${Math.round(data.distance_meters)}m`;
    }
  }

  function renderActivityLog(logs) {
    const logBox = document.getElementById('secActivityLog');
    if (!logBox) return;

    if (!logs || logs.length === 0) {
      logBox.innerHTML = '<div style="color:#64748b;font-size:0.7rem;padding:4px;">No security actions recorded yet.</div>';
      return;
    }

    logBox.innerHTML = logs.map(entry => {
      let badgeClass = 'badge-info';
      if (entry.badge === 'SUCCESS') badgeClass = 'badge-success';
      else if (entry.badge === 'WARN') badgeClass = 'badge-warning';
      else if (entry.badge === 'ERROR') badgeClass = 'badge-error';
      else if (entry.badge === 'AUTH') badgeClass = 'badge-success';

      return `
        <div class="sec-log-row">
          <span class="log-time">${escapeHtml(entry.time)}</span>
          <span class="log-badge ${badgeClass}">${escapeHtml(entry.badge)}</span>
          <span class="log-msg">${escapeHtml(entry.message)}</span>
        </div>`;
    }).join('');
  }

  function formatEta(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins === 0) return `${secs} sec`;
    return `${mins}m ${secs}s`;
  }

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // --- ACTIONS EXPOSED GLOBALLY ---

  // Complete end-to-end demo flow sequence
  window.runCompleteVerifiedFlow = async function () {
    if (window.showToast) {
      window.showToast('🚨 Step 1/5: Emergency Alert triggered. Boston EMS Medic-42 dispatched...', 'info');
    }
    try {
      // Step 1: Emergency Trigger
      const resEmg = await fetch('/api/v1/security/emergency/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resident_id: 'user_eleanor_vance',
          room: 'bathroom',
          severity: 'HIGH',
          reason: 'Bathroom fall detected on wet tile with tachycardia'
        })
      });
      secState = await resEmg.json();
      renderSecurityUI(secState);
      await new Promise(r => setTimeout(r, 1300));

      // Step 2: En Route
      if (window.showToast) {
        window.showToast('🚑 Step 2/5: Medic-42 En Route (Cambridge St Corridor, 620m away)...', 'info');
      }
      const resEnRoute = await fetch('/api/v1/security/responder/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_status: 'EN_ROUTE' })
      });
      secState = await resEnRoute.json();
      renderSecurityUI(secState);
      await new Promise(r => setTimeout(r, 1300));

      // Step 3: Arriving (< 150m)
      if (window.showToast) {
        window.showToast('📍 Step 3/5: Medic-42 Arriving (<150m perimeter approach)...', 'info');
      }
      const resArr = await fetch('/api/v1/security/responder/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_status: 'ARRIVING' })
      });
      secState = await resArr.json();
      renderSecurityUI(secState);
      await new Promise(r => setTimeout(r, 1300));

      // Step 4: Arrival Verified Check-In (< 35m residence perimeter)
      if (window.showToast) {
        window.showToast('🛡️ Step 4/5: Verified Arrival Check-In (8m away, Badge BEMS-8821 verified)...', 'info');
      }
      const resChk = await fetch('/api/v1/security/responder/checkin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          badge_id: 'BEMS-8821',
          badge_number: 'BEMS-8821',
          auth_token: 'AUTH-TOKEN-BEMS-8821-EXP2026',
          latitude: 42.358810,
          longitude: -71.063810,
          override_stage: 'ARRIVED'
        })
      });
      secState = await resChk.json();
      renderSecurityUI(secState);
      await new Promise(r => setTimeout(r, 1000));

      // Step 5: Authenticated Smart Door Unlock
      if (window.showToast) {
        window.showToast('🔑 Step 5/5: Transmitting authenticated unlock token to Yale/Matter smart lock...', 'info');
      }
      await window.executeVerifiedUnlock();

    } catch (err) {
      console.error('[Security] Failed running complete flow:', err);
    }
  };

  // Advance responder along their route
  window.advanceResponderStage = async function () {
    try {
      const res = await fetch('/api/v1/security/responder/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      secState = data;
      renderSecurityUI(data);

      if (window.showToast) {
        window.showToast(`EMS Status: ${data.responder.status} (${Math.round(data.distance_meters)}m away)`, 'info');
      }
    } catch (err) {
      console.error('[Security] Failed to advance step:', err);
    }
  };

  // Jump to specific stage
  window.jumpToStage = async function (stage) {
    try {
      const res = await fetch('/api/v1/security/responder/checkin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          badge_id: 'BEMS-8821',
          override_stage: stage
        })
      });
      const data = await res.json();
      secState = data;
      renderSecurityUI(data);
    } catch (err) {
      console.error('[Security] Failed to jump stage:', err);
    }
  };

  // Simulate verified arrival at the residence
  window.simulateVerifiedArrival = async function () {
    try {
      if (window.showToast) {
        window.showToast('Simulating verified EMS arrival at 48 Beacon St perimeter...', 'info');
      }

      const res = await fetch('/api/v1/security/responder/checkin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          badge_id: 'BEMS-8821',
          badge_number: 'BEMS-8821',
          auth_token: 'AUTH-TOKEN-BEMS-8821-EXP2026',
          latitude: 42.358810,
          longitude: -71.063810,
          override_stage: 'ARRIVED'
        })
      });
      const data = await res.json();
      secState = data;
      renderSecurityUI(data);

      if (window.showToast) {
        window.showToast('EMS Arrival Verified! Proximity check passed (8m).', 'success');
      }

      // Auto-trigger verified unlock demonstration after 600ms
      setTimeout(() => {
        window.executeVerifiedUnlock();
      }, 700);

    } catch (err) {
      console.error('[Security] Failed arrival simulation:', err);
    }
  };

  // Execute authenticated smart door unlock
  window.executeVerifiedUnlock = async function () {
    const btnUnlock = document.getElementById('btnExecuteUnlock');
    if (btnUnlock) {
      btnUnlock.disabled = true;
      btnUnlock.textContent = 'Verifying...';
    }

    // Set UI to UNLOCKING state immediately
    const doorBar = document.getElementById('doorLockBar');
    const doorTitle = document.getElementById('doorTitle');
    const doorSub = document.getElementById('doorSub');
    if (doorBar && doorTitle && doorSub) {
      doorBar.style.background = 'rgba(245, 158, 11, 0.15)';
      doorBar.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      doorTitle.textContent = 'Front Door Smart Lock: UNLOCKING...';
      doorTitle.style.color = '#fbbf24';
      doorSub.textContent = 'Verifying cryptographic credentials and dispatching pulse...';
    }

    try {
      const res = await fetch('/api/v1/security/lock/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          badge_id: 'BEMS-8821',
          responder_badge: 'BEMS-8821',
          responder_name: 'Capt. Marcus Chen (Medic-42)',
          security_token: 'AUTH-TOKEN-BEMS-8821-EXP2026',
          auth_token: 'AUTH-TOKEN-BEMS-8821-EXP2026'
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Unlock failed');
      }

      secState = data;
      renderSecurityUI(data);

      if (window.showToast) {
        window.showToast('Smart Lock Unlocked! First responders granted entry.', 'success');
      }

      if (window.niraStore && typeof window.niraStore.playChime === 'function') {
        window.niraStore.playChime();
      }

    } catch (err) {
      console.error('[Security] Unlock command rejected:', err);
      await fetchSecurityStatus();
      if (window.showToast) {
        window.showToast(`Unlock failed: ${err.message}`, 'error');
      }
    }
  };

  // Toggle manual key override
  window.toggleManualLock = async function () {
    try {
      const isCurrentlyLocked = !secState || !secState.smart_lock || secState.smart_lock.state !== 'UNLOCKED';
      const targetAction = isCurrentlyLocked ? 'UNLOCK' : 'LOCK';

      const res = await fetch('/api/v1/security/lock/manual-override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: targetAction,
          reason: 'Authorized Operator Manual Override'
        })
      });
      const data = await res.json();
      secState = data;
      renderSecurityUI(data);

      if (window.showToast) {
        window.showToast(`Manual Override: Lock set to ${targetAction}ED`, 'warning');
      }
    } catch (err) {
      console.error('[Security] Manual override failed:', err);
    }
  };

  // Failure simulation trigger
  window.triggerSimFailure = async function (type) {
    const dd = document.getElementById('failureDropdown');
    if (dd) dd.style.display = 'none';

    if (type === 'unauthorized') {
      if (window.showToast) window.showToast('Simulating unauthorized responder badge (BOGUS-999)...', 'warning');
      try {
        const res = await fetch('/api/v1/security/lock/unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            badge_id: 'BOGUS-999',
            responder_badge: 'BOGUS-999',
            responder_name: 'Unknown Imposter',
            security_token: 'invalid_token',
            auth_token: 'INVALID-TOKEN'
          })
        });
        const data = await res.json();
        await fetchSecurityStatus();
        if (window.showToast) window.showToast(`Security Alert: ${data.detail || 'Unauthorized responder rejected.'}`, 'error');
      } catch (e) {
        console.error(e);
      }
    } else if (type === 'wrong_location') {
      if (window.showToast) window.showToast('Simulating unlock outside geofence perimeter (450m away)...', 'warning');
      try {
        await fetch('/api/v1/security/responder/step', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_status: 'EN_ROUTE',
            simulate_wrong_location: true
          })
        });
        const res = await fetch('/api/v1/security/lock/unlock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            badge_id: 'BEMS-8821',
            responder_badge: 'BEMS-8821',
            responder_name: 'Capt. Marcus Chen (Medic-42)',
            security_token: 'AUTH-TOKEN-BEMS-8821-EXP2026',
            auth_token: 'AUTH-TOKEN-BEMS-8821-EXP2026'
          })
        });
        const data = await res.json();
        await fetchSecurityStatus();
        if (window.showToast) window.showToast(`Geofence Alert: ${data.detail || 'Responder has not arrived.'}`, 'error');
      } catch (e) {
        console.error(e);
      }
    } else if (type === 'offline_lock') {
      if (window.showToast) window.showToast('Simulating smart lock provider outage / IoT mesh timeout...', 'error');
      try {
        const res = await fetch('/api/v1/security/lock/manual-override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'OFFLINE_FAIL',
            reason: 'Smart lock IoT gateway timeout'
          })
        });
        const data = await res.json();
        secState = data;
        renderSecurityUI(data);
        if (window.showToast) window.showToast('Automatic unlock unavailable — manual access required.', 'error');
      } catch (e) {
        console.error(e);
      }
    } else if (type === 'hardware_failure') {
      if (window.showToast) window.showToast('Simulating smart lock deadbolt motor jam / retraction failure...', 'error');
      try {
        const res = await fetch('/api/v1/security/lock/manual-override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'SIMULATE_LOCK_FAILURE',
            reason: 'Hardware motor failed to retract latch'
          })
        });
        const data = await res.json();
        secState = data;
        renderSecurityUI(data);
        if (window.showToast) window.showToast('Motor retraction jam: Automatic unlock unavailable — manual access required.', 'error');
      } catch (e) {
        console.error(e);
      }
    } else if (type === 'restore_online') {
      if (window.showToast) window.showToast('Restoring smart lock online & locked...', 'info');
      try {
        const res = await fetch('/api/v1/security/lock/manual-override', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action: 'RESTORE_ONLINE',
            reason: 'Restoring smart lock device online'
          })
        });
        const data = await res.json();
        secState = data;
        renderSecurityUI(data);
        if (window.showToast) window.showToast('Smart lock device online and reconnected.', 'success');
      } catch (e) {
        console.error(e);
      }
    }
  };

  // Toggle failure menu dropdown
  window.toggleFailureDropdown = function (event) {
    if (event) event.stopPropagation();
    const dd = document.getElementById('failureDropdown');
    if (!dd) return;
    dd.style.display = dd.style.display === 'block' ? 'none' : 'block';
  };

  // Close dropdown on outside click
  document.addEventListener('click', () => {
    const dd = document.getElementById('failureDropdown');
    if (dd && dd.style.display === 'block') {
      dd.style.display = 'none';
    }
  });

  // Reset simulation state
  window.resetSecuritySimulation = async function () {
    try {
      const res = await fetch('/api/v1/security/reset', { method: 'POST' });
      const data = await res.json();
      secState = data;
      renderSecurityUI(data);

      if (window.showToast) {
        window.showToast('Location & Residence Security simulation reset.', 'info');
      }
    } catch (err) {
      console.error('[Security] Failed to reset simulation:', err);
    }
  };

  // Document ready initialization
  function init() {
    initSecurityMap();
    fetchSecurityStatus();

    // Periodic light status sync every 5 seconds
    if (syncTimer) clearInterval(syncTimer);
    syncTimer = setInterval(fetchSecurityStatus, 5000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
