/**
 * NIRA — Person 1 Complete Demo Module
 * Core Dashboard, Elderly Profile, Caregiver Dashboard, and Medication Reminders
 * Amazon Developer Hackathon 2026
 */

(function() {
  'use strict';

  function getStore() {
    return window.person2DemoStore || window.person1Store;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatTimeAgo(isoDate) {
    if (!isoDate) return '--';
    const diff = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000);
    if (diff < 5) return 'Just now';
    if (diff < 60) return diff + 's ago';
    const m = Math.floor(diff / 60);
    if (m < 60) return m + 'm ago';
    const h = Math.floor(m / 60);
    if (h < 24) return h + 'h ago';
    const d = Math.floor(h / 24);
    return d + 'd ago';
  }

  // ===========================================================================
  // 1. HOME DASHBOARD CONTROLLER
  // ===========================================================================
  const HomeDashboardController = {
    init() {
      const store = getStore();
      if (!store) return;
      store.subscribe(state => this.render(state));
      this.bindEvents();
    },

    bindEvents() {
      const quickBtns = [
        { id: 'dashBtnCheckin', tab: 'dailycheckin' },
        { id: 'dashBtnProfile', tab: 'elderlyprofile' },
        { id: 'dashBtnMeds', tab: 'medicationreminders' },
        { id: 'dashBtnVoice', tab: 'voiceassistant' },
        { id: 'dashBtnFall', tab: 'falldetection' },
        { id: 'dashBtnHospitals', tab: 'locationmap' }
      ];
      quickBtns.forEach(b => {
        const el = document.getElementById(b.id);
        if (el) {
          el.addEventListener('click', () => {
            if (typeof window.switchTab === 'function') window.switchTab(b.tab);
          });
        }
      });
    },

    render(state) {
      if (!state) {
        const store = getStore();
        if (!store) return;
        state = store.state;
      }
      if (!state) return;

      const resident = state.resident || { name: 'Eleanor Vance', age: 79, room: 'Living Room', address: 'Unit 4B - Beacon Hill' };
      const checkins = state.checkins || [];
      const medications = state.medications || [];
      const incidents = state.incidents || [];
      const activeInc = state.activeIncidentId ? incidents.find(i => i.id === state.activeIncidentId) : null;

      const welcomeName = document.getElementById('dashWelcomeName');
      if (welcomeName) welcomeName.textContent = resident.name || 'Eleanor Vance';

      const resAge = document.getElementById('dashResidentAge');
      if (resAge) resAge.textContent = resident.age + ' years old';

      const resRoom = document.getElementById('dashResidentRoom');
      if (resRoom) resRoom.textContent = resident.room || (state.sensors && state.sensors.room) || 'Living Room';

      const resAddress = document.getElementById('dashResidentAddress');
      if (resAddress) resAddress.textContent = resident.address || 'Beacon Hill, Boston';

      const latestCheckin = checkins[0];
      const checkinBadge = document.getElementById('dashCheckinStatusBadge');
      const checkinDesc = document.getElementById('dashCheckinDesc');
      const checkinTime = document.getElementById('dashCheckinTime');

      if (latestCheckin) {
        if (checkinBadge) {
          if (latestCheckin.statusType === 'fine') {
            checkinBadge.className = 'pill-badge pill-green';
            checkinBadge.innerHTML = '● Checked In — Feeling Fine';
          } else if (latestCheckin.statusType === 'unwell') {
            checkinBadge.className = 'pill-badge pill-amber';
            checkinBadge.innerHTML = '▲ Logged: Feeling Unwell';
          } else {
            checkinBadge.className = 'pill-badge pill-red';
            checkinBadge.innerHTML = '🚨 Requested Assistance';
          }
        }
        if (checkinDesc) {
          checkinDesc.textContent = 'Mood: ' + (latestCheckin.mood || 'Calm') + ' • Sleep: ' + (latestCheckin.sleepQuality || 'Good') + ' • ' + (latestCheckin.notes || 'Routine verified.');
        }
        if (checkinTime) {
          checkinTime.textContent = 'Logged ' + formatTimeAgo(latestCheckin.timestamp);
        }
      } else {
        if (checkinBadge) {
          checkinBadge.className = 'pill-badge pill-amber';
          checkinBadge.innerHTML = '▲ Check-in Pending Today';
        }
        if (checkinDesc) checkinDesc.textContent = 'Morning wellness check has not been submitted yet.';
        if (checkinTime) checkinTime.textContent = 'Due: 08:30 AM';
      }

      const totalMeds = medications.length;
      const takenMeds = medications.filter(m => m.status === 'taken').length;
      const nextMed = medications.find(m => m.status === 'upcoming');

      const medCountEl = document.getElementById('dashMedCount');
      if (medCountEl) medCountEl.textContent = takenMeds + ' of ' + totalMeds + ' taken today';

      const medNextEl = document.getElementById('dashMedNext');
      if (medNextEl) {
        if (nextMed) {
          medNextEl.textContent = 'Next: ' + nextMed.name + ' (' + nextMed.dosage + ') at ' + (nextMed.schedule || nextMed.time || 'Upcoming');
        } else if (totalMeds > 0 && takenMeds === totalMeds) {
          medNextEl.textContent = 'All scheduled medications completed for today!';
        } else {
          medNextEl.textContent = 'No upcoming doses pending.';
        }
      }

      const medProgressBar = document.getElementById('dashMedProgressBar');
      if (medProgressBar) {
        const pct = totalMeds > 0 ? Math.round((takenMeds / totalMeds) * 100) : 0;
        medProgressBar.style.width = pct + '%';
      }

      const incStatusBadge = document.getElementById('dashIncStatusBadge');
      const incDetails = document.getElementById('dashIncDetails');
      const incActionBtn = document.getElementById('dashIncActionBtn');
      const incCardWrap = document.getElementById('dashIncCardWrap');

      if (activeInc) {
        if (incCardWrap) incCardWrap.classList.add('emergency-pulse-border');
        if (incStatusBadge) {
          incStatusBadge.className = 'pill-badge pill-red';
          incStatusBadge.innerHTML = '🚨 ACTIVE EMERGENCY: ' + escapeHtml(activeInc.eventLabel || 'Fall Detected');
        }
        if (incDetails) {
          incDetails.innerHTML = '<strong>Location:</strong> ' + escapeHtml(activeInc.location) + '<br>' +
            '<strong>Risk Score:</strong> ' + activeInc.riskScore + '/100 • <strong>Velocity:</strong> ' + (activeInc.sensorReadings ? activeInc.sensorReadings.impactVelocity : 'High') + '<br>' +
            '<em>' + escapeHtml(activeInc.caregiverStatus) + '</em>';
        }
        if (incActionBtn) {
          incActionBtn.textContent = '⚠️ Open CAD Emergency Alert';
          incActionBtn.className = 'btn-demo-primary emergency-btn';
          incActionBtn.onclick = () => { if (typeof window.switchTab === 'function') window.switchTab('emergencyalert'); };
        }
      } else {
        if (incCardWrap) incCardWrap.classList.remove('emergency-pulse-border');
        if (incStatusBadge) {
          incStatusBadge.className = 'pill-badge pill-green';
          incStatusBadge.innerHTML = '🛡️ All Clear • 0 Active Emergencies';
        }
        const lastInc = incidents[0];
        if (incDetails) {
          if (lastInc) {
            incDetails.textContent = 'Last Event: ' + lastInc.eventLabel + ' (' + formatTimeAgo(lastInc.timestamp) + ') — Status: ' + lastInc.status + '.';
          } else {
            incDetails.textContent = 'No critical safety anomalies recorded. Ambient radar & vision sensors nominal.';
          }
        }
        if (incActionBtn) {
          incActionBtn.textContent = 'Simulate Safety Event';
          incActionBtn.className = 'btn-demo-secondary';
          incActionBtn.onclick = () => { if (typeof window.switchTab === 'function') window.switchTab('falldetection'); };
        }
      }

      const caregiverName = document.getElementById('dashCaregiverName');
      if (caregiverName) caregiverName.textContent = resident.guardian || 'David Vance (Son)';

      const caregiverPhone = document.getElementById('dashCaregiverPhone');
      if (caregiverPhone) caregiverPhone.textContent = resident.guardianPhone || '+1-555-019-2834';

      const activityFeed = document.getElementById('dashRecentActivityList');
      if (activityFeed) {
        const events = [];
        if (activeInc) events.push({ text: 'Emergency Fall Detected in ' + activeInc.location, time: formatTimeAgo(activeInc.timestamp), type: 'critical' });
        if (latestCheckin) events.push({ text: 'Daily Check-in recorded: \"' + latestCheckin.statusText + '\"', time: formatTimeAgo(latestCheckin.timestamp), type: 'checkin' });
        const takenList = medications.filter(m => m.status === 'taken');
        if (takenList.length > 0) events.push({ text: 'Medication taken: ' + takenList[0].name + ' ' + takenList[0].dosage, time: takenList[0].takenAt || 'Today', type: 'med' });
        if (incidents.length > 0 && incidents[0] !== activeInc) events.push({ text: 'Incident ' + incidents[0].id + ': ' + incidents[0].eventLabel + ' (' + incidents[0].status + ')', time: formatTimeAgo(incidents[0].timestamp), type: 'info' });

        if (events.length === 0) {
          activityFeed.innerHTML = '<div class="demo-empty-state">No recent activity recorded today. System baseline steady.</div>';
        } else {
          activityFeed.innerHTML = events.map(ev => 
            '<div class="dash-activity-item">' +
              '<span class="dash-activity-dot dot-' + ev.type + '"></span>' +
              '<div class="dash-activity-content">' +
                '<div class="dash-activity-text">' + escapeHtml(ev.text) + '</div>' +
                '<div class="dash-activity-time">' + escapeHtml(ev.time) + '</div>' +
              '</div>' +
            '</div>'
          ).join('');
        }
      }
    }
  };
  // ===========================================================================
  // 2. CAREGIVER DASHBOARD CONTROLLER
  // ===========================================================================
  const CaregiverDashboardController = {
    init() {
      const store = getStore();
      if (!store) return;
      store.subscribe(state => this.render(state));
    },

    render(state) {
      if (!state) {
        const store = getStore();
        if (!store) return;
        state = store.state;
      }
      if (!state) return;

      const resident = state.resident || { name: 'Eleanor Vance', age: 79, address: 'Unit 4B - Beacon Hill', guardian: 'David Vance' };
      const incidents = state.incidents || [];
      const checkins = state.checkins || [];
      const medications = state.medications || [];
      const sensors = state.sensors || {};
      const activeInc = state.activeIncidentId ? incidents.find(i => i.id === state.activeIncidentId) : null;
      const latestCheckin = checkins[0];

      const statusBadge = document.getElementById('caregiverResidentStatusBadge');
      if (statusBadge) {
        if (activeInc) {
          statusBadge.className = 'caregiver-status-badge badge-emergency';
          statusBadge.innerHTML = '🚨 EMERGENCY — ACTION REQUIRED';
        } else if (latestCheckin && (latestCheckin.statusType === 'unwell' || latestCheckin.statusType === 'assistance')) {
          statusBadge.className = 'caregiver-status-badge badge-attention';
          statusBadge.innerHTML = '▲ NEEDS ATTENTION';
        } else {
          statusBadge.className = 'caregiver-status-badge badge-normal';
          statusBadge.innerHTML = '🛡️ NORMAL — RESIDENT SAFE';
        }
      }

      const emergencyCallout = document.getElementById('caregiverEmergencyAlertCallout');
      if (emergencyCallout) {
        if (activeInc) {
          emergencyCallout.style.display = 'block';
          emergencyCallout.innerHTML = 
            '<div class="caregiver-emergency-card">' +
              '<div class="caregiver-emergency-header">' +
                '<div style="display: flex; align-items: center; gap: 10px;">' +
                  '<span style="font-size: 1.5rem;">🚨</span>' +
                  '<div>' +
                    '<h4 style="color: var(--accent-red); margin: 0; font-size: 1.05rem;">HIGH-IMPACT EMERGENCY ALERT</h4>' +
                    '<div style="font-size: 0.8rem; color: var(--text-secondary);">Incident ID: ' + escapeHtml(activeInc.id) + ' &bull; ' + formatTimeAgo(activeInc.timestamp) + '</div>' +
                  '</div>' +
                '</div>' +
                '<span class="pill-badge pill-red">CONFIDENCE: ' + activeInc.riskScore + '%</span>' +
              '</div>' +
              '<div style="margin: 12px 0; font-size: 0.88rem; line-height: 1.5; color: #fff;">' +
                '<strong>Event:</strong> ' + escapeHtml(activeInc.eventLabel) + '<br>' +
                '<strong>Location:</strong> ' + escapeHtml(activeInc.location) + '<br>' +
                '<strong>Sensor Telemetry:</strong> Posture: ' + escapeHtml(activeInc.sensorReadings ? activeInc.sensorReadings.posture : 'Immobile') + ' &bull; Heart Rate: ' + escapeHtml(activeInc.sensorReadings ? activeInc.sensorReadings.heartRate : '--') + '<br>' +
                '<strong>Status:</strong> ' + escapeHtml(activeInc.caregiverStatus) +
              '</div>' +
              '<div style="display: flex; gap: 10px; flex-wrap: wrap;">' +
                '<button class="btn-demo-primary" id="caregiverBtnAckAlert" onclick="window.person1CaregiverDashboard.acknowledgeCurrentAlert(\'' + activeInc.id + '\')">' +
                  '✓ Acknowledge Alert (Primary Guardian)' +
                '</button>' +
                '<button class="btn-demo-secondary" onclick="if(window.switchTab) window.switchTab(\'emergencyalert\')">' +
                  'Open CAD Emergency Command Center &rarr;' +
                '</button>' +
              '</div>' +
            '</div>';
        } else {
          emergencyCallout.style.display = 'none';
          emergencyCallout.innerHTML = '';
        }
      }

      const resName = document.getElementById('cgResidentName');
      if (resName) resName.textContent = resident.name || 'Eleanor Vance';

      const resAge = document.getElementById('cgResidentAge');
      if (resAge) resAge.textContent = resident.age + ' years old • Female';

      const resAddress = document.getElementById('cgResidentAddress');
      if (resAddress) resAddress.textContent = resident.address || 'Unit 4B - Beacon Hill, Boston';

      const resRoom = document.getElementById('cgResidentRoom');
      if (resRoom) resRoom.textContent = sensors.room || resident.room || 'Bathroom';

      const cgHeartRate = document.getElementById('cgSensorHeartRate');
      if (cgHeartRate) cgHeartRate.textContent = (sensors.heartRateBpm || resident.restingHeartRate || 74) + ' BPM';

      const cgPosture = document.getElementById('cgSensorPosture');
      if (cgPosture) cgPosture.textContent = sensors.posture || 'Standing / Ambulatory';

      const cgMotion = document.getElementById('cgSensorMotion');
      if (cgMotion) cgMotion.textContent = (sensors.radarMicromotion !== undefined ? sensors.radarMicromotion : '0.35') + ' m/s (Nominal)';

      const cgCheckinStatus = document.getElementById('cgCheckinStatus');
      const cgCheckinNotes = document.getElementById('cgCheckinNotes');
      if (latestCheckin) {
        if (cgCheckinStatus) {
          cgCheckinStatus.textContent = latestCheckin.statusText + ' (' + formatTimeAgo(latestCheckin.timestamp) + ')';
          cgCheckinStatus.style.color = latestCheckin.statusType === 'fine' ? 'var(--accent-green-text)' : 'var(--accent-amber-text)';
        }
        if (cgCheckinNotes) {
          cgCheckinNotes.textContent = 'Mood: ' + (latestCheckin.mood || 'Calm') + ' • Notes: ' + (latestCheckin.notes || 'Normal morning tea routine.');
        }
      } else {
        if (cgCheckinStatus) {
          cgCheckinStatus.textContent = 'Check-in Pending';
          cgCheckinStatus.style.color = 'var(--accent-amber-text)';
        }
        if (cgCheckinNotes) cgCheckinNotes.textContent = 'No morning verification logged yet today.';
      }

      const totalMeds = medications.length;
      const takenCount = medications.filter(m => m.status === 'taken').length;

      const cgMedSummary = document.getElementById('cgMedAdherenceSummary');
      if (cgMedSummary) {
        cgMedSummary.textContent = takenCount + ' of ' + totalMeds + ' Doses Taken (' + (totalMeds > 0 ? Math.round((takenCount/totalMeds)*100) : 0) + '%)';
      }

      const cgMedDoseList = document.getElementById('cgMedDoseList');
      if (cgMedDoseList) {
        cgMedDoseList.innerHTML = medications.map(m => 
          '<div class="cg-med-row">' +
            '<div><strong>' + escapeHtml(m.name) + '</strong> (' + escapeHtml(m.dosage) + ') &bull; <span style="font-size: 0.78rem; color: var(--text-secondary);">' + escapeHtml(m.schedule || m.time) + '</span></div>' +
            '<div>' + (m.status === 'taken' 
              ? '<span class="pill-badge pill-green">Taken ' + escapeHtml(m.takenAt || '') + '</span>'
              : (m.status === 'missed' 
                ? '<span class="pill-badge pill-red">Missed</span>' 
                : '<span class="pill-badge pill-blue">Pending</span>')) + '</div>' +
          '</div>'
        ).join('');
      }
    },

    acknowledgeCurrentAlert(incidentId) {
      const store = getStore();
      if (!store) return;
      store.acknowledgeIncident(incidentId);
      this.render();
    }
  };
  // ===========================================================================
  // 3. ELDERLY PERSON'S PROFILE CONTROLLER
  // ===========================================================================
  const ElderlyProfileController = {
    init() {
      const store = getStore();
      if (!store) return;
      store.subscribe(state => this.render(state));
      this.bindEvents();
    },

    bindEvents() {
      const btnEdit = document.getElementById('btnEditProfile');
      if (btnEdit) btnEdit.addEventListener('click', () => this.toggleEditMode(true));

      const btnCancel = document.getElementById('btnCancelProfileEdit');
      if (btnCancel) btnCancel.addEventListener('click', () => this.toggleEditMode(false));

      const btnSave = document.getElementById('btnSaveProfile');
      if (btnSave) btnSave.addEventListener('click', () => this.saveProfile());
    },

    toggleEditMode(isEditing) {
      const viewContainer = document.getElementById('profileViewContainer');
      const editContainer = document.getElementById('profileEditContainer');
      const btnEdit = document.getElementById('btnEditProfile');

      if (viewContainer) viewContainer.style.display = isEditing ? 'none' : 'block';
      if (editContainer) editContainer.style.display = isEditing ? 'block' : 'none';
      if (btnEdit) btnEdit.style.display = isEditing ? 'none' : 'inline-flex';

      if (isEditing) {
        this.populateEditForm();
      }
    },

    populateEditForm() {
      const store = getStore();
      if (!store || !store.state) return;
      const res = store.state.resident || {};

      const nameInput = document.getElementById('editProfileName');
      if (nameInput) nameInput.value = res.name || 'Eleanor Vance';

      const ageInput = document.getElementById('editProfileAge');
      if (ageInput) ageInput.value = res.age || 79;

      const addressInput = document.getElementById('editProfileAddress');
      if (addressInput) addressInput.value = res.address || 'Unit 4B - Beacon Hill, Boston, MA 02108';

      const guardianInput = document.getElementById('editProfileGuardian');
      if (guardianInput) guardianInput.value = res.guardian || 'David Vance (Son)';

      const phoneInput = document.getElementById('editProfileGuardianPhone');
      if (phoneInput) phoneInput.value = res.guardianPhone || '+1-555-019-2834';

      const pinInput = document.getElementById('editProfileDoorPin');
      if (pinInput) pinInput.value = res.doorPin || '8492';
    },

    saveProfile() {
      const name = (document.getElementById('editProfileName')?.value || '').trim();
      const age = parseInt(document.getElementById('editProfileAge')?.value, 10);
      const address = (document.getElementById('editProfileAddress')?.value || '').trim();
      const guardian = (document.getElementById('editProfileGuardian')?.value || '').trim();
      const guardianPhone = (document.getElementById('editProfileGuardianPhone')?.value || '').trim();
      const doorPin = (document.getElementById('editProfileDoorPin')?.value || '').trim();

      const errorEl = document.getElementById('profileFormError');
      if (!name) {
        if (errorEl) { errorEl.textContent = 'Resident full name cannot be blank.'; errorEl.style.display = 'block'; }
        return;
      }
      if (isNaN(age) || age < 50 || age > 120) {
        if (errorEl) { errorEl.textContent = 'Please enter a valid age between 50 and 120.'; errorEl.style.display = 'block'; }
        return;
      }
      if (!guardianPhone) {
        if (errorEl) { errorEl.textContent = 'Emergency guardian phone number is required.'; errorEl.style.display = 'block'; }
        return;
      }
      if (errorEl) errorEl.style.display = 'none';

      const store = getStore();
      if (store) {
        store.updateResidentProfile({
          name,
          age,
          address,
          guardian,
          guardianPhone,
          doorPin: doorPin || '8492'
        });
      }

      this.toggleEditMode(false);
      this.render();
    },

    render(state) {
      if (!state) {
        const store = getStore();
        if (!store) return;
        state = store.state;
      }
      if (!state) return;

      const res = state.resident || {};

      const nameEl = document.getElementById('profileResidentName');
      if (nameEl) nameEl.textContent = res.name || 'Eleanor Vance';

      const ageEl = document.getElementById('profileResidentAge');
      if (ageEl) ageEl.textContent = (res.age || 79) + ' Years Old • Female • DOB: June 14, 1947';

      const addrEl = document.getElementById('profileResidentAddress');
      if (addrEl) addrEl.textContent = res.address || 'Unit 4B - Beacon Hill, Boston, MA 02108';

      const pinEl = document.getElementById('profileDoorPinDisplay');
      if (pinEl) pinEl.textContent = res.doorPin || '8492';

      const guardianEl = document.getElementById('profileGuardianDisplay');
      if (guardianEl) guardianEl.textContent = res.guardian || 'David Vance (Son)';

      const phoneEl = document.getElementById('profileGuardianPhoneDisplay');
      if (phoneEl) phoneEl.textContent = res.guardianPhone || '+1-555-019-2834';

      const condList = document.getElementById('profileConditionsList');
      if (condList) {
        const conditions = res.medicalConditions || [
          "Mild Cognitive Impairment (Early Stage)",
          "Hypertension (Managed with Lisinopril 10mg)",
          "Documented bathroom slip & fall history (Jan 2026)",
          "Penicillin Allergy (High Risk)"
        ];
        condList.innerHTML = conditions.map(c => 
          '<li class="profile-condition-item">' +
            '<span class="condition-dot"></span>' +
            '<span>' + escapeHtml(c) + '</span>' +
          '</li>'
        ).join('');
      }
    }
  };
  // ===========================================================================
  // 4. MEDICATION REMINDERS CONTROLLER
  // ===========================================================================
  const MedicationRemindersController = {
    init() {
      const store = getStore();
      if (!store) return;
      store.subscribe(state => this.render(state));
      this.bindEvents();
    },

    bindEvents() {
      const btnOpenAdd = document.getElementById('btnAddMedicationModalBtn');
      if (btnOpenAdd) btnOpenAdd.addEventListener('click', () => this.openAddModal());

      const btnCloseAdd = document.getElementById('btnCancelNewMedication');
      if (btnCloseAdd) btnCloseAdd.addEventListener('click', () => this.closeAddModal());

      const btnSaveNew = document.getElementById('btnSaveNewMedication');
      if (btnSaveNew) btnSaveNew.addEventListener('click', () => this.saveNewMedication());
    },

    openAddModal() {
      const modal = document.getElementById('addMedicationModal');
      if (modal) {
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
      }
    },

    closeAddModal() {
      const modal = document.getElementById('addMedicationModal');
      if (modal) {
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
      }
      const err = document.getElementById('addMedErrorMsg');
      if (err) err.style.display = 'none';
    },

    saveNewMedication() {
      const name = (document.getElementById('inputMedName')?.value || '').trim();
      const dosage = (document.getElementById('inputMedDosage')?.value || '').trim();
      const time = (document.getElementById('inputMedTime')?.value || '').trim();
      const purpose = (document.getElementById('inputMedPurpose')?.value || '').trim();
      const prescriber = (document.getElementById('inputMedPrescriber')?.value || '').trim();

      const err = document.getElementById('addMedErrorMsg');
      if (!name) {
        if (err) { err.textContent = 'Medication name is required.'; err.style.display = 'block'; }
        return;
      }
      if (!dosage) {
        if (err) { err.textContent = 'Dosage instructions are required (e.g. 10mg tablet).'; err.style.display = 'block'; }
        return;
      }

      const store = getStore();
      if (store) {
        store.addMedication({
          name,
          dosage,
          time: time || '08:00 AM',
          schedule: time ? time + ' (Daily)' : 'Daily Scheduled',
          purpose: purpose || 'Clinical Maintenance',
          prescriber: prescriber || 'Dr. Marcus Chen, MD'
        });
      }

      this.closeAddModal();
      this.render();
    },

    markTaken(medId) {
      const store = getStore();
      if (!store) return;
      store.markMedicationTaken(medId);
      this.render();
    },

    markMissed(medId) {
      const store = getStore();
      if (!store) return;
      store.markMedicationMissed(medId);
      this.render();
    },

    render(state) {
      if (!state) {
        const store = getStore();
        if (!store) return;
        state = store.state;
      }
      if (!state) return;

      const medications = state.medications || [];
      const history = state.medicationHistory || [];

      const totalCount = medications.length;
      const takenCount = medications.filter(m => m.status === 'taken').length;
      const nextMed = medications.find(m => m.status === 'upcoming');

      const adherenceHeader = document.getElementById('medAdherenceSummary');
      if (adherenceHeader) adherenceHeader.textContent = takenCount + ' / ' + totalCount + ' Doses Taken';

      const nextDoseHeader = document.getElementById('medNextDoseSummary');
      if (nextDoseHeader) {
        nextDoseHeader.textContent = nextMed ? nextMed.name + ' (' + nextMed.dosage + ') at ' + (nextMed.schedule || nextMed.time) : 'All doses completed';
      }

      const scoreHeader = document.getElementById('medAdherenceScore');
      if (scoreHeader) {
        const rate = totalCount > 0 ? Math.round((takenCount / totalCount) * 100) : 100;
        scoreHeader.textContent = rate + '% Today';
      }

      const grid = document.getElementById('demoMedicationsGrid');
      if (grid) {
        if (medications.length === 0) {
          grid.innerHTML = '<div class="demo-empty-state">No scheduled medication reminders configured.</div>';
        } else {
          grid.innerHTML = medications.map(med => {
            const isTaken = med.status === 'taken';
            const isMissed = med.status === 'missed';
            return '<div class="medication-card ' + (isTaken ? 'card-taken' : (isMissed ? 'card-missed' : 'card-upcoming')) + '" id="medCard-' + med.id + '">' +
                '<div class="med-card-top">' +
                  '<div class="med-icon-box">💊</div>' +
                  '<div class="med-header-text">' +
                    '<div class="med-name">' + escapeHtml(med.name) + '</div>' +
                    '<div class="med-dosage">' + escapeHtml(med.dosage) + ' &bull; ' + escapeHtml(med.purpose || 'Therapy') + '</div>' +
                  '</div>' +
                  '<div>' +
                    (isTaken ? '<span class="pill-badge pill-green" id="medStatusPill-' + med.id + '">TAKEN</span>' :
                      (isMissed ? '<span class="pill-badge pill-red" id="medStatusPill-' + med.id + '">MISSED</span>' :
                      '<span class="pill-badge pill-blue" id="medStatusPill-' + med.id + '">UPCOMING</span>')) +
                  '</div>' +
                '</div>' +

                '<div class="med-details-body">' +
                  '<div class="med-detail-item">' +
                    '<span class="med-detail-label">SCHEDULED TIME:</span>' +
                    '<span class="med-detail-val">' + escapeHtml(med.schedule || med.time || 'Daily') + '</span>' +
                  '</div>' +
                  '<div class="med-detail-item">' +
                    '<span class="med-detail-label">INSTRUCTIONS:</span>' +
                    '<span class="med-detail-val">' + escapeHtml(med.instruction || 'Take with water') + '</span>' +
                  '</div>' +
                  '<div class="med-detail-item">' +
                    '<span class="med-detail-label">PRESCRIBER:</span>' +
                    '<span class="med-detail-val">' + escapeHtml(med.prescriber || 'Dr. Marcus Chen') + '</span>' +
                  '</div>' +
                  (isTaken && med.takenAt ? 
                    '<div class="med-detail-item med-timestamp-record">' +
                      '<span class="med-detail-label">RECORDED AT:</span>' +
                      '<span class="med-detail-val" style="color: var(--accent-green-text); font-weight: 700;">✓ Completed at ' + escapeHtml(med.takenAt) + '</span>' +
                    '</div>' : '') +
                '</div>' +

                '<div class="med-actions-footer">' +
                  '<button class="btn-demo-primary btn-sm" id="btnMarkTaken-' + med.id + '" data-med-action="taken" onclick="window.person1MedicationReminders.markTaken(\'' + med.id + '\')" ' + (isTaken ? 'disabled style="opacity: 0.6;"' : '') + '>' +
                    (isTaken ? '✓ Taken' : 'Mark as Taken') +
                  '</button>' +
                  '<button class="btn-demo-secondary btn-sm" id="btnMarkMissed-' + med.id + '" data-med-action="missed" onclick="window.person1MedicationReminders.markMissed(\'' + med.id + '\')" ' + (isMissed ? 'disabled style="opacity: 0.6;"' : '') + '>' +
                    (isMissed ? '✕ Missed' : 'Mark as Missed') +
                  '</button>' +
                '</div>' +
              '</div>';
          }).join('');
        }
      }

      const histTable = document.getElementById('demoMedicationHistoryTableBody');
      if (histTable) {
        if (history.length === 0) {
          histTable.innerHTML = '<tr><td colspan="5" class="demo-empty-table">No medication intake records logged yet.</td></tr>';
        } else {
          histTable.innerHTML = history.slice(0, 15).map(h => 
            '<tr>' +
              '<td><strong>' + escapeHtml(h.medName || h.medId) + '</strong></td>' +
              '<td>' + escapeHtml(h.scheduledTime || '--') + '</td>' +
              '<td>' + (h.status === 'taken' 
                ? '<span class="pill-badge pill-green">✓ Taken</span>' 
                : '<span class="pill-badge pill-red">✕ Missed</span>') + '</td>' +
              '<td>' + escapeHtml(h.timestamp || '--') + '</td>' +
              '<td><span style="font-size: 0.78rem; color: var(--text-secondary);">' + escapeHtml(h.recordedBy || 'System') + '</span></td>' +
            '</tr>'
          ).join('');
        }
      }
    }
  };

  // ===========================================================================
  // 5. DEMO AUTH & PERSONA SWITCHER CONTROLLER
  // ===========================================================================
  const DemoAuthController = {
    init() {
      this.updateHeaderAuthDisplay();
      this.bindEvents();
    },

    bindEvents() {
      const btnLogout = document.getElementById('btnLogout');
      if (btnLogout) {
        btnLogout.addEventListener('click', () => this.logout());
      }
    },

    getCurrentUser() {
      try {
        const raw = localStorage.getItem('aegis_auth_user');
        if (raw) return JSON.parse(raw);
      } catch (e) {}
      return {
        name: 'Eleanor Vance (Resident)',
        role: 'Senior / Family View',
        roleKey: 'senior_home',
        avatar: '👵'
      };
    },

    loginAsResident() {
      const user = {
        name: 'Eleanor Vance (Resident)',
        role: 'Senior / Family View',
        roleKey: 'senior_home',
        avatar: '👵',
        email: 'family@beaconhill.care'
      };
      localStorage.setItem('aegis_auth_user', JSON.stringify(user));
      this.updateHeaderAuthDisplay();
      if (typeof window.switchTab === 'function') window.switchTab('homedashboard');
      const store = getStore();
      if (store) store.showToast('Logged in as Eleanor Vance (Resident Home View)', 'success');
    },

    loginAsCaregiver() {
      const user = {
        name: 'David Vance (Son • Primary Caregiver)',
        role: 'Family Primary Admin',
        roleKey: 'admin_son',
        avatar: '👨‍💼',
        email: 'david.vance@example.com'
      };
      localStorage.setItem('aegis_auth_user', JSON.stringify(user));
      this.updateHeaderAuthDisplay();
      if (typeof window.switchTab === 'function') window.switchTab('caregiverdashboard');
      const store = getStore();
      if (store) store.showToast('Logged in as David Vance (Caregiver View)', 'success');
    },

    logout() {
      localStorage.removeItem('aegis_auth_user');
      const store = getStore();
      if (store) store.showToast('Logged out of session.', 'info');
      setTimeout(() => {
        window.location.href = '/login';
      }, 300);
    },

    updateHeaderAuthDisplay() {
      const user = this.getCurrentUser();
      const badge = document.getElementById('headerActiveUserBadge');
      if (badge) {
        badge.innerHTML = 
          '<span style="font-size: 1rem;">' + (user.avatar || '👤') + '</span>' +
          '<span style="font-weight: 700; color: #fff;">' + escapeHtml(user.name) + '</span>';
      }
    }
  };

  window.person1HomeDashboard = HomeDashboardController;
  window.person1CaregiverDashboard = CaregiverDashboardController;
  window.person1ElderlyProfile = ElderlyProfileController;
  window.person1MedicationReminders = MedicationRemindersController;
  window.person1Auth = DemoAuthController;

  function initAllPerson1() {
    HomeDashboardController.init();
    CaregiverDashboardController.init();
    ElderlyProfileController.init();
    MedicationRemindersController.init();
    DemoAuthController.init();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllPerson1);
  } else {
    initAllPerson1();
  }

})();