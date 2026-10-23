/**
 * NIRA — Person 2 Complete Demo Module
 * Centralized Interactive Monitoring & Emergency Workflow System
 * 
 * Includes:
 * 1. Shared Demo-State & Data Layer (LocalStorage Persisted)
 * 2. Voice Assistant (Mic interaction, speech recognition + synthesis, predefined responses, text fallback)
 * 3. Daily Check-in (Wellness questions, options, attention alerts, timestamped history)
 * 4. Fall Detection Simulation (Sensors HUD, Simulate Fall, debouncing, duplicate prevention)
 * 5. Emergency Alert Screen (Incident ID, type, location, caregiver status, acknowledge, cancel)
 * 6. Location Map & Nearby Hospitals (Leaflet OpenStreetMap + vector fallback, hospital cards, legend)
 * 7. Notification Center (Emergency, check-in, reminder categories, unread badges, mark-read, links)
 * 8. Incident History (Filterable audit logs, incident details modal, duplicate prevention)
 */

(function() {
  'use strict';

  const STORAGE_KEY = 'nira_person2_demo_state_v2';

  // ---------------------------------------------------------------------------
  // Default Initial State
  // ---------------------------------------------------------------------------
  function getDefaultDemoState() {
    return {
      resident: {
        id: "user_eleanor_vance",
        name: "Eleanor Vance",
        age: 79,
        address: "Unit 4B - Beacon Hill, Boston, MA 02108",
        lat: 42.3588,
        lng: -71.0638,
        room: "Bathroom",
        guardian: "David Vance (Son)",
        guardianPhone: "+1-555-019-2834",
        medicalConditions: [
          "Mild Cognitive Impairment (Early Stage)",
          "Hypertension (Managed with Lisinopril 10mg)",
          "Documented bathroom slip & fall history (Jan 2026)",
          "Penicillin Allergy (High Risk)"
        ],
        doorPin: "8492",
        restingHeartRate: 72
      },
      activeIncidentId: null,
      incidents: [
        {
          id: "INC-20261021-94821",
          eventType: "rapid_posture_change",
          eventLabel: "Rapid Posture Change (Bedside)",
          timestamp: new Date(Date.now() - 3600000 * 6).toISOString(),
          severity: "MODERATE",
          status: "RESOLVED",
          location: "Bedroom, Unit 4B - Beacon Hill",
          riskScore: 68,
          details: "Dropped reading glasses followed by sudden floor reach. Resident verbally verified 'I am fine' on Alexa Echo Show.",
          sensorReadings: {
            impactVelocity: "1.4 m/s",
            heartRate: "82 BPM",
            posture: "Sitting (Recovered)",
            substrate: "Oak hardwood (Dry)",
            lux: 75
          },
          caregiverStatus: "Standby (Auto-Resolved)",
          timeline: [
            { time: "18:20:00", action: "Rapid drop velocity (1.4 m/s) detected by Optical Sensor" },
            { time: "18:20:04", action: "Echo Show 15 prompt: 'Eleanor, are you okay?'" },
            { time: "18:20:11", action: "Eleanor replied: 'I just dropped my glasses, I am fine.'" },
            { time: "18:20:15", action: "Incident auto-resolved as False Alarm" }
          ]
        }
      ],
      checkins: [
        {
          id: "CHK-20261021-0830",
          timestamp: new Date(Date.now() - 3600000 * 14).toISOString(),
          statusText: "I'm fine",
          statusType: "fine", // 'fine' | 'unwell' | 'assistance'
          mood: "Energetic & Calm",
          sleepQuality: "Slept well (7.5 hrs uninterrupted)",
          medicationsTaken: true,
          mobilityConcern: "None",
          notes: "Prepared morning tea, completed living room stretch routine.",
          requiresAttention: false,
          elderlyName: "Eleanor Vance"
        },
        {
          id: "CHK-20261020-0845",
          timestamp: new Date(Date.now() - 3600000 * 38).toISOString(),
          statusText: "I'm fine",
          statusType: "fine",
          mood: "Good",
          sleepQuality: "Slept 8 hrs",
          medicationsTaken: true,
          mobilityConcern: "None",
          notes: "Enjoyed morning walk down hallway.",
          requiresAttention: false,
          elderlyName: "Eleanor Vance"
        }
      ],
      notifications: [
        {
          id: "NOTIF-20261021-001",
          timestamp: new Date(Date.now() - 3600000 * 6).toISOString(),
          category: "check_in",
          severity: "info",
          title: "Wellness Verification Recorded",
          description: "Eleanor Vance verified 'I am fine' after minor bedside movement.",
          read: true,
          incidentId: "INC-20261021-94821",
          simulated: true,
          acknowledged: true
        },
        {
          id: "NOTIF-20261021-002",
          timestamp: new Date(Date.now() - 3600000 * 10).toISOString(),
          category: "reminder",
          severity: "info",
          title: "Hydration & Vital Check",
          description: "Routine midday vitals logged: 74 BPM, baseline temperature 98.4°F.",
          read: true,
          incidentId: null,
          simulated: true,
          acknowledged: false
        }
      ],
      voiceHistory: [
        {
          id: "vh-1",
          speaker: "assistant",
          text: "Hello Eleanor! This is your NIRA Ambient Safety Assistant. How are you feeling right now?",
          timestamp: new Date(Date.now() - 300000).toISOString()
        }
      ],
      sensors: {
        accelerometer: { x: 0.08, y: -0.02, z: 0.98, magnitudeG: 0.99 },
        impactVelocity: 0.2, // m/s
        posture: "Standing / Ambulatory",
        torsoAngleDeg: 12,
        radarMicromotion: 0.35, // m/s
        heartRateBpm: 74,
        room: "Living Room",
        substrateCondition: "Dry",
        ambientLux: 140,
        isFallDetected: false,
        lastUpdated: new Date().toISOString()
      },
      hospitals: [
        {
          id: "mgh",
          name: "Massachusetts General Hospital (MGH)",
          address: "55 Fruit St, Boston, MA 02114",
          distance: "0.4 miles",
          eta: "3 mins (EMS)",
          traumaLevel: "Level 1 Adult & Pediatric Trauma Center",
          phone: "(617) 726-2000",
          lat: 42.3631,
          lng: -71.0686,
          erStatus: "Accepting Acute Trauma",
          waitMinutes: 12,
          sampleDisclaimer: "Sample Data for Demo"
        },
        {
          id: "tufts",
          name: "Tufts Medical Center",
          address: "800 Washington St, Boston, MA 02111",
          distance: "1.1 miles",
          eta: "6 mins (EMS)",
          traumaLevel: "Level 1 Trauma Center",
          phone: "(617) 636-5000",
          lat: 42.3496,
          lng: -71.0634,
          erStatus: "Accepting Critical Dispatch",
          waitMinutes: 18,
          sampleDisclaimer: "Sample Data for Demo"
        },
        {
          id: "bmc",
          name: "Boston Medical Center (BMC)",
          address: "1 Boston Medical Center Pl, Boston, MA 02118",
          distance: "1.8 miles",
          eta: "9 mins (EMS)",
          traumaLevel: "Level 1 Trauma Center (New England Regional)",
          phone: "(617) 638-8000",
          lat: 42.3361,
          lng: -71.0725,
          erStatus: "Open 24/7",
          waitMinutes: 25,
          sampleDisclaimer: "Sample Data for Demo"
        },
        {
          id: "bwh",
          name: "Brigham and Women's Hospital",
          address: "75 Francis St, Boston, MA 02115",
          distance: "2.4 miles",
          eta: "12 mins (EMS)",
          traumaLevel: "Level 1 Trauma Center",
          phone: "(617) 732-5500",
          lat: 42.3365,
          lng: -71.1070,
          erStatus: "Open 24/7",
          waitMinutes: 20,
          sampleDisclaimer: "Sample Data for Demo"
        }
      ]
 ,
      medications: [
        {
          id: "med-lisinopril",
          name: "Lisinopril",
          dosage: "10mg tablet",
          schedule: "08:00 AM (Morning)",
          time: "08:00 AM",
          instruction: "Take 1 tablet daily with a full glass of water for blood pressure",
          purpose: "Hypertension / Blood Pressure Management",
          prescriber: "Dr. Marcus Chen, MD",
          status: "taken",
          takenAt: "08:15 AM",
          remainingDoses: 26
        },
        {
          id: "med-vitamind",
          name: "Vitamin D3",
          dosage: "2000 IU softgel",
          schedule: "12:30 PM (Midday)",
          time: "12:30 PM",
          instruction: "Take 1 softgel daily with lunch for bone density & calcium absorption",
          purpose: "Bone Density & Fracture Prevention",
          prescriber: "Dr. Marcus Chen, MD",
          status: "taken",
          takenAt: "12:45 PM",
          remainingDoses: 42
        },
        {
          id: "med-metformin",
          name: "Metformin",
          dosage: "500mg tablet",
          schedule: "06:00 PM (Evening)",
          time: "06:00 PM",
          instruction: "Take 1 tablet with dinner to maintain glycemic control",
          purpose: "Glucose Regulation / Metabolic Health",
          prescriber: "Dr. Marcus Chen, MD",
          status: "upcoming",
          takenAt: null,
          remainingDoses: 18
        },
        {
          id: "med-donepezil",
          name: "Donepezil",
          dosage: "5mg tablet",
          schedule: "09:00 PM (Bedtime)",
          time: "09:00 PM",
          instruction: "Take 1 tablet immediately before bed for memory & cognitive function",
          purpose: "Cognitive Support / Mild Cognitive Impairment",
          prescriber: "Dr. Marcus Chen, MD",
          status: "upcoming",
          takenAt: null,
          remainingDoses: 30
        }
      ],
      medicationHistory: [
        {
          id: "med-log-1",
          medId: "med-lisinopril",
          medName: "Lisinopril (10mg tablet)",
          scheduledTime: "08:00 AM",
          status: "taken",
          timestamp: "08:15 AM",
          recordedBy: "Eleanor Vance (Confirmed via Voice Check-in)"
        },
        {
          id: "med-log-2",
          medId: "med-vitamind",
          medName: "Vitamin D3 (2000 IU softgel)",
          scheduledTime: "12:30 PM",
          status: "taken",
          timestamp: "12:45 PM",
          recordedBy: "Eleanor Vance (Confirmed via Dashboard)"
        }
      ]
    };
  }

  // ---------------------------------------------------------------------------
  // Central State Store
  // ---------------------------------------------------------------------------
  class Person2DemoStore {
    constructor() {
      this.listeners = [];
      this.isSimulatingFall = false;
      this.loadState();
    }

    loadState() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          this.state = JSON.parse(raw);
          // Safety defaults check
          if (!Array.isArray(this.state.incidents)) this.state.incidents = [];
          if (!Array.isArray(this.state.checkins)) this.state.checkins = [];
          if (!Array.isArray(this.state.notifications)) this.state.notifications = [];
          if (!Array.isArray(this.state.voiceHistory)) this.state.voiceHistory = [];
          if (!this.state.sensors) this.state.sensors = getDefaultDemoState().sensors;
          if (!this.state.hospitals) this.state.hospitals = getDefaultDemoState().hospitals;
          if (!Array.isArray(this.state.medications)) this.state.medications = getDefaultDemoState().medications;
          if (!Array.isArray(this.state.medicationHistory)) this.state.medicationHistory = getDefaultDemoState().medicationHistory;
          return;
        }
      } catch (err) {
        console.warn("Error loading stored demo state:", err);
      }
      this.state = getDefaultDemoState();
      this.saveState();
    }

    saveState() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
      } catch (err) {
        console.warn("Error saving demo state to localStorage:", err);
      }
      this.notify();
    }

    resetDemoData() {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch (e) {}
      this.state = getDefaultDemoState();
      this.saveState();
      this.showToast("Demo data reset to clean initial state.", "info");
    }

    subscribe(fn) {
      if (typeof fn === 'function') {
        this.listeners.push(fn);
        fn(this.state);
      }
      return () => {
        this.listeners = this.listeners.filter(l => l !== fn);
      };
    }

    notify() {
      this.listeners.forEach(fn => {
        try { fn(this.state); } catch (e) { console.error("Listener error:", e); }
      });
      // Synchronize unread badge in header
      this.updateHeaderBadges();
    }

    updateHeaderBadges() {
      const unreadCount = this.getUnreadNotificationCount();
      const badges = document.querySelectorAll('.demo-unread-badge-counter');
      badges.forEach(b => {
        if (unreadCount > 0) {
          b.textContent = unreadCount > 99 ? '99+' : unreadCount;
          b.style.display = 'inline-flex';
        } else {
          b.style.display = 'none';
        }
      });
    }

    getUnreadNotificationCount() {
      return (this.state.notifications || []).filter(n => !n.read).length;
    }

    getActiveIncident() {
      if (!this.state.activeIncidentId) return null;
      return this.state.incidents.find(i => i.id === this.state.activeIncidentId) || null;
    }

    // --- Daily Check-in Action ---
    submitDailyCheckin({ statusType, mood, sleepQuality, medicationsTaken, mobilityConcern, notes }) {
      const id = "CHK-" + new Date().toISOString().slice(0, 10).replace(/-/g, '') + "-" + Math.floor(1000 + Math.random() * 9000);
      const isUrgent = (statusType === 'unwell' || statusType === 'assistance');

      let statusText = "I'm fine";
      if (statusType === 'unwell') statusText = "Feeling unwell";
      if (statusType === 'assistance') statusText = "Need assistance";

      const newCheckin = {
        id,
        timestamp: new Date().toISOString(),
        statusText,
        statusType,
        mood: mood || "Calm",
        sleepQuality: sleepQuality || "Normal",
        medicationsTaken: Boolean(medicationsTaken),
        mobilityConcern: mobilityConcern || "None",
        notes: notes ? notes.trim() : "",
        requiresAttention: isUrgent,
        elderlyName: this.state.resident.name
      };

      this.state.checkins.unshift(newCheckin);

      // Create notification
      const notifSeverity = statusType === 'assistance' ? 'critical' : (statusType === 'unwell' ? 'warning' : 'info');
      const notifTitle = isUrgent 
        ? `Daily Check-in Alert: Eleanor Reported '${statusText}'`
        : `Daily Check-in Completed: Eleanor Reported '${statusText}'`;
      const notifDesc = isUrgent
        ? `Eleanor reported: "${notes || statusText}". Attention required. Primary guardian notified.`
        : `Eleanor confirmed wellness. Sleep: ${sleepQuality || 'Good'}, Meds: ${medicationsTaken ? 'Taken' : 'Pending'}.`;

      const notif = {
        id: "NOTIF-" + Date.now(),
        timestamp: new Date().toISOString(),
        category: "check_in",
        severity: notifSeverity,
        title: notifTitle,
        description: notifDesc,
        read: false,
        incidentId: null,
        simulated: true,
        acknowledged: false
      };
      this.state.notifications.unshift(notif);

      this.saveState();
      return newCheckin;
    }

    // --- Fall Simulation Action (Guarded against duplicate calls) ---
    simulateFall() {
      if (this.isSimulatingFall) {
        console.warn("Fall simulation already in progress. Ignoring duplicate trigger.");
        return null;
      }

      this.isSimulatingFall = true;

      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const uniqueSuffix = Math.floor(10000 + Math.random() * 90000);
      const incidentId = `INC-${dateStr}-${uniqueSuffix}`;

      // Update simulated sensor readings to high-impact fall signature
      this.state.sensors = {
        accelerometer: { x: 0.85, y: -1.24, z: 2.98, magnitudeG: 3.42 },
        impactVelocity: 2.85, // m/s
        posture: "Lying Prone on Floor (Motionless)",
        torsoAngleDeg: 84,
        radarMicromotion: 0.04, // m/s motionless
        heartRateBpm: 138, // tachycardia surge
        room: "Bathroom",
        substrateCondition: "Wet Ceramic Tile",
        ambientLux: 15,
        isFallDetected: true,
        lastUpdated: new Date().toISOString()
      };

      const newIncident = {
        id: incidentId,
        eventType: "possible_fall",
        eventLabel: "High-Impact Fall Detected",
        timestamp: new Date().toISOString(),
        severity: "CRITICAL",
        status: "ACTIVE", // ACTIVE | ACKNOWLEDGED | CANCELLED_FALSE_ALARM | RESOLVED
        location: "Bathroom, Unit 4B - Beacon Hill",
        riskScore: 94,
        details: "Rapid acceleration spike (3.42g) followed by impact with ceramic tile substrate. Post-impact stillness detected by 60GHz mmWave radar. Acute tachycardia (138 BPM).",
        sensorReadings: {
          impactVelocity: "2.85 m/s",
          heartRate: "138 BPM (Tachycardia)",
          posture: "Lying Prone (Horizontal 84°)",
          substrate: "Wet Ceramic Tile",
          lux: 15,
          radarMotion: "0.04 m/s (Immobile)"
        },
        caregiverStatus: "Simulated Alert Sent (Echo Show Drop-In, SMS, Push Notification) — Awaiting Acknowledgment",
        timeline: [
          { time: new Date().toLocaleTimeString(), action: "Tri-axial accelerometer registered 3.42g impact velocity in Bathroom" },
          { time: new Date().toLocaleTimeString(), action: "60GHz mmWave radar classified posture: Lying Prone (Immobile)" },
          { time: new Date().toLocaleTimeString(), action: "Aegis Multimodal Risk Engine evaluated: CRITICAL (94% confidence)" },
          { time: new Date().toLocaleTimeString(), action: "Simulated emergency alert dispatched to Guardian David Vance" }
        ]
      };

      this.state.incidents.unshift(newIncident);
      this.state.activeIncidentId = incidentId;

      // Create corresponding emergency notification
      const emergencyNotif = {
        id: "NOTIF-" + Date.now(),
        timestamp: new Date().toISOString(),
        category: "emergency",
        severity: "critical",
        title: "🚨 CRITICAL: High-Impact Fall Detected in Bathroom",
        description: `Incident ${incidentId}: Eleanor Vance detected motionless on wet bathroom tile. Pulse: 138 BPM. Simulated dispatch alerted David Vance.`,
        read: false,
        incidentId: incidentId,
        simulated: true,
        acknowledged: false
      };
      this.state.notifications.unshift(emergencyNotif);

      // Add voice assistant dialogue entry
      this.state.voiceHistory.unshift({
        id: "vh-" + Date.now(),
        speaker: "system",
        text: `EMERGENCY ALERT: High-impact fall detected in Bathroom. Eleanor, this is NIRA. Are you alright? Please speak if you can hear me.`,
        timestamp: new Date().toISOString()
      });

      this.saveState();

      // Cooldown timer to prevent accidental double-clicks
      setTimeout(() => {
        this.isSimulatingFall = false;
      }, 1200);

      // Mirror into NiraStateStore if globally present
      if (window.niraStore && typeof window.niraStore.updateIncidentFromBackend === 'function') {
        try {
          window.niraStore.updateIncidentFromBackend({
            id: incidentId,
            event_type: "possible_fall",
            confidence: 0.94,
            location: "bathroom",
            movement_after_event: "none",
            initial_risk_level: "CRITICAL",
            current_risk_level: "CRITICAL",
            status: "ACTIVE",
            workflow_state: "DETECTED",
            risk_reasons: [
              "High-impact acceleration signature (3.42g)",
              "Prolonged post-impact inactivity detected on wet tile",
              "Acute heart-rate surge (+91% above baseline)"
            ],
            recommended_action: "IMMEDIATE_CAD_EMERGENCY_DISPATCH",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          });
        } catch (err) {
          console.warn("Could not mirror into NiraStateStore:", err);
        }
      }

      return newIncident;
    }

    // --- Acknowledge Incident Action ---
    acknowledgeIncident(incidentId) {
      const inc = this.state.incidents.find(i => i.id === incidentId);
      if (!inc) return false;

      inc.status = "ACKNOWLEDGED";
      inc.caregiverStatus = "Acknowledged by David Vance (Primary Guardian)";
      inc.timeline.unshift({
        time: new Date().toLocaleTimeString(),
        action: "Caregiver David Vance acknowledged emergency notification via Guardian App"
      });

      // Update related notification
      this.state.notifications.forEach(n => {
        if (n.incidentId === incidentId) {
          n.acknowledged = true;
          n.read = true;
          n.description += ` [Acknowledged by Caregiver at ${new Date().toLocaleTimeString()}]`;
        }
      });

      this.saveState();
      this.showToast(`Incident ${incidentId} successfully acknowledged.`, "success");
      return true;
    }

    // --- Cancel Incident (False Alarm) Action ---
    cancelIncident(incidentId, reason = "Caregiver confirmed false alarm") {
      const inc = this.state.incidents.find(i => i.id === incidentId);
      if (!inc) return false;

      inc.status = "CANCELLED_FALSE_ALARM";
      inc.caregiverStatus = "Alert Cancelled — False Alarm Confirmed";
      inc.timeline.unshift({
        time: new Date().toLocaleTimeString(),
        action: `Alert cancelled: ${reason}. Incident preserved in audit history.`
      });

      if (this.state.activeIncidentId === incidentId) {
        this.state.activeIncidentId = null;
      }

      // Reset sensors to normal
      this.state.sensors.isFallDetected = false;
      this.state.sensors.posture = "Sitting / Recovered";
      this.state.sensors.heartRateBpm = 76;
      this.state.sensors.impactVelocity = 0.1;

      // Update related notifications
      this.state.notifications.forEach(n => {
        if (n.incidentId === incidentId) {
          n.acknowledged = true;
          n.read = true;
          n.description += ` [Cancelled: False Alarm confirmed at ${new Date().toLocaleTimeString()}]`;
        }
      });

      this.saveState();
      this.showToast(`Incident ${incidentId} cancelled as false alarm and archived.`, "info");
      return true;
    }

    // --- Notification Actions ---
    markNotificationRead(notificationId) {
      const notif = this.state.notifications.find(n => n.id === notificationId);
      if (notif) {
        notif.read = true;
        this.saveState();
      }
    }

    markAllNotificationsRead() {
      this.state.notifications.forEach(n => { n.read = true; });
      this.saveState();
      this.showToast("All notifications marked as read.", "info");
    }

    clearNotifications() {
      this.state.notifications = [];
      this.saveState();
      this.showToast("Notification center cleared.", "info");
    }

    // --- Voice Assistant Message ---
    addVoiceMessage(speaker, text) {
      const msg = {
        id: "vh-" + Date.now(),
        speaker, // 'user' | 'assistant' | 'system'
        text,
        timestamp: new Date().toISOString()
      };
      this.state.voiceHistory.push(msg);
      this.saveState();
      return msg;
    }

    
    // -------------------------------------------------------------------------
    // Person 1 Integration Methods (Medication & Resident Profile)
    // -------------------------------------------------------------------------
    markMedicationTaken(medId) {
      if (!Array.isArray(this.state.medications)) return false;
      const med = this.state.medications.find(m => m.id === medId);
      if (!med) return false;
      med.status = 'taken';
      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      med.takenAt = timeStr;

      if (!Array.isArray(this.state.medicationHistory)) this.state.medicationHistory = [];
      this.state.medicationHistory.unshift({
        id: "med-log-" + Date.now(),
        medId: med.id,
        medName: `${med.name} (${med.dosage})`,
        scheduledTime: med.schedule || med.time || "Scheduled",
        status: "taken",
        timestamp: timeStr,
        recordedBy: "Eleanor Vance (Confirmed via Demo Dashboard)"
      });

      this.state.notifications.unshift({
        id: "NOTIF-MED-" + Date.now(),
        timestamp: new Date().toISOString(),
        category: "reminder",
        severity: "info",
        title: `Medication Taken: ${med.name}`,
        description: `Eleanor Vance recorded scheduled dose of ${med.name} (${med.dosage}) at ${timeStr}.`,
        read: false,
        incidentId: null,
        simulated: true,
        acknowledged: true
      });

      this.saveState();
      this.showToast(`Dose recorded: ${med.name} marked as taken.`, "success");
      return true;
    }

    markMedicationMissed(medId) {
      if (!Array.isArray(this.state.medications)) return false;
      const med = this.state.medications.find(m => m.id === medId);
      if (!med) return false;
      med.status = 'missed';
      const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      if (!Array.isArray(this.state.medicationHistory)) this.state.medicationHistory = [];
      this.state.medicationHistory.unshift({
        id: "med-log-" + Date.now(),
        medId: med.id,
        medName: `${med.name} (${med.dosage})`,
        scheduledTime: med.schedule || med.time || "Scheduled",
        status: "missed",
        timestamp: timeStr,
        recordedBy: "Caregiver Alert: Missed Dose"
      });

      this.state.notifications.unshift({
        id: "NOTIF-MED-" + Date.now(),
        timestamp: new Date().toISOString(),
        category: "reminder",
        severity: "warning",
        title: `⚠️ Medication Missed: ${med.name}`,
        description: `Scheduled dose of ${med.name} (${med.dosage}) was marked as missed. Caregiver alert triggered.`,
        read: false,
        incidentId: null,
        simulated: true,
        acknowledged: false
      });

      this.saveState();
      this.showToast(`Medication ${med.name} marked as missed. Caregiver notified.`, "warning");
      return true;
    }

    addMedication(medData) {
      if (!Array.isArray(this.state.medications)) this.state.medications = [];
      const newMed = {
        id: "med-" + Date.now(),
        name: medData.name || "Unnamed Medication",
        dosage: medData.dosage || "Standard Dose",
        schedule: medData.schedule || (medData.time ? `${medData.time} (Daily)` : "Daily"),
        time: medData.time || "08:00 AM",
        instruction: medData.instruction || "Take as directed with water",
        purpose: medData.purpose || "Prescribed Regimen",
        prescriber: medData.prescriber || "Dr. Marcus Chen, MD",
        status: "upcoming",
        takenAt: null,
        remainingDoses: parseInt(medData.remainingDoses) || 30
      };
      this.state.medications.push(newMed);
      this.saveState();
      this.showToast(`Added reminder for ${newMed.name} (${newMed.dosage}).`, "success");
      return newMed;
    }

    updateResidentProfile(profileData) {
      if (!this.state.resident) this.state.resident = getDefaultDemoState().resident;
      this.state.resident = {
        ...this.state.resident,
        ...profileData
      };
      this.saveState();
      this.showToast("Resident profile successfully updated and saved.", "success");
      return this.state.resident;
    }

    showToast(message, type = "info") {
      if (typeof window.showToastNotification === 'function') {
        window.showToastNotification(message, type);
        return;
      }
      console.log(`[TOAST - ${type.toUpperCase()}]: ${message}`);
    }
  }

  // Instantiate global singleton
  const demoStore = new Person2DemoStore();
  window.person2DemoStore = demoStore;
  window.person1Store = demoStore;

  // ---------------------------------------------------------------------------
  // View Controllers & Renderers
  // ---------------------------------------------------------------------------

  // --- 1. VOICE ASSISTANT CONTROLLER ---
  const VoiceAssistantController = {
    isListening: false,
    recognition: null,

    init() {
      this.initSpeechRecognition();
      this.render();
      demoStore.subscribe(() => this.renderHistory());
    },

    initSpeechRecognition() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          this.recognition = new SpeechRecognition();
          this.recognition.continuous = false;
          this.recognition.interimResults = true;
          this.recognition.lang = 'en-US';

          this.recognition.onstart = () => {
            this.isListening = true;
            this.updateListeningUI(true);
          };

          this.recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
              transcript += event.results[i][0].transcript;
            }
            const input = document.getElementById('demoVoiceInput');
            if (input) input.value = transcript;
            const liveTrans = document.getElementById('demoLiveTranscriptionText');
            if (liveTrans) liveTrans.textContent = transcript || 'Listening...';
          };

          this.recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            this.isListening = false;
            this.updateListeningUI(false);
          };

          this.recognition.onend = () => {
            this.isListening = false;
            this.updateListeningUI(false);
            const input = document.getElementById('demoVoiceInput');
            if (input && input.value.trim()) {
              this.handleUserInput(input.value.trim());
              input.value = '';
            }
          };
        } catch (e) {
          console.warn("SpeechRecognition init error:", e);
        }
      }
    },

    toggleListening() {
      if (!this.recognition) {
        // Fallback: simulated speech input
        this.simulateVoiceListening();
        return;
      }

      if (this.isListening) {
        try { this.recognition.stop(); } catch (e) {}
        this.isListening = false;
        this.updateListeningUI(false);
      } else {
        try {
          this.recognition.start();
        } catch (e) {
          console.warn("SpeechRecognition start error:", e);
          this.simulateVoiceListening();
        }
      }
    },

    simulateVoiceListening() {
      this.isListening = true;
      this.updateListeningUI(true);
      const liveTrans = document.getElementById('demoLiveTranscriptionText');
      if (liveTrans) liveTrans.textContent = "Listening to ambient speech...";

      setTimeout(() => {
        const samplePhrases = [
          "I am feeling okay today.",
          "I need some assistance getting to the bathroom.",
          "What is my scheduled medication for today?",
          "I'm fine, that loud noise was just dropped books."
        ];
        const chosen = samplePhrases[Math.floor(Math.random() * samplePhrases.length)];
        if (liveTrans) liveTrans.textContent = `"${chosen}"`;
        
        setTimeout(() => {
          this.isListening = false;
          this.updateListeningUI(false);
          this.handleUserInput(chosen);
        }, 1000);
      }, 1600);
    },

    updateListeningUI(listening) {
      const micBtn = document.getElementById('demoMicToggleBtn');
      const micStatus = document.getElementById('demoMicStatusText');
      const visualizer = document.getElementById('demoAudioVisualizer');
      const liveBox = document.getElementById('demoLiveTranscriptionBox');

      if (micBtn) {
        if (listening) {
          micBtn.classList.add('is-listening');
          micBtn.setAttribute('aria-pressed', 'true');
        } else {
          micBtn.classList.remove('is-listening');
          micBtn.setAttribute('aria-pressed', 'false');
        }
      }

      if (micStatus) {
        micStatus.textContent = listening ? "Listening... (Speak now)" : "Microphone Ready • Click to speak";
      }

      if (visualizer) {
        visualizer.style.display = listening ? "flex" : "none";
      }

      if (liveBox) {
        liveBox.style.display = listening ? "block" : "none";
      }
    },

    handleUserInput(text) {
      if (!text || !text.trim()) return;
      const clean = text.trim();
      demoStore.addVoiceMessage('user', clean);

      // Generate context-aware assistant response
      let reply = "I understand Eleanor. I'm keeping an eye on your safety.";
      const lower = clean.toLowerCase();

      if (lower.includes("help") || lower.includes("fell") || lower.includes("fall") || lower.includes("assistance")) {
        reply = "I've noted that you need assistance. Your son David has been notified via Echo Show Drop-In and SMS.";
        // Dispatch checkin notification
        demoStore.submitDailyCheckin({
          statusType: "assistance",
          mood: "Distressed",
          sleepQuality: "Interrupted",
          medicationsTaken: false,
          mobilityConcern: "Needs Help",
          notes: `Voice request: "${clean}"`
        });
      } else if (lower.includes("fine") || lower.includes("okay") || lower.includes("ok")) {
        reply = "Glad to hear that, Eleanor! I've updated your daily record. Keep staying hydrated.";
        demoStore.submitDailyCheckin({
          statusType: "fine",
          mood: "Good",
          sleepQuality: "Normal",
          medicationsTaken: true,
          mobilityConcern: "None",
          notes: `Voice check-in: "${clean}"`
        });
      } else if (lower.includes("medication") || lower.includes("pill") || lower.includes("medicine")) {
        reply = "Your Lisinopril 10mg is scheduled with dinner at 7:00 PM. A reminder will sound on this Echo Show.";
      } else if (lower.includes("heart") || lower.includes("pulse") || lower.includes("vitals")) {
        const hr = demoStore.state.sensors.heartRateBpm;
        reply = `Your current heart rate is ${hr} BPM from your Apple Watch, with normal resting rhythm.`;
      }

      setTimeout(() => {
        demoStore.addVoiceMessage('assistant', reply);
        this.speakText(reply);
      }, 450);
    },

    speakText(text) {
      if ('speechSynthesis' in window) {
        try {
          window.speechSynthesis.cancel();
          const utter = new SpeechSynthesisUtterance(text);
          utter.rate = 1.0;
          utter.pitch = 1.0;
          window.speechSynthesis.speak(utter);
        } catch (e) {
          console.warn("speechSynthesis error:", e);
        }
      }
    },

    render() {
      this.renderHistory();
    },

    renderHistory() {
      const container = document.getElementById('demoVoiceHistoryList');
      if (!container) return;

      const history = demoStore.state.voiceHistory || [];
      if (history.length === 0) {
        container.innerHTML = `<div class="demo-empty-state">No conversation history yet. Tap the microphone or click a prompt below to begin.</div>`;
        return;
      }

      container.innerHTML = history.map(item => {
        const isUser = item.speaker === 'user';
        const isSystem = item.speaker === 'system';
        const avatar = isUser ? '👵' : (isSystem ? '⚠️' : '🛡️');
        const speakerName = isUser ? 'Eleanor Vance' : (isSystem ? 'NIRA Safety Guard' : 'NIRA Ambient Voice');
        const roleClass = isUser ? 'user-bubble' : (isSystem ? 'system-bubble' : 'assistant-bubble');
        const timeStr = new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        return `
          <div class="demo-voice-message ${roleClass}">
            <div class="demo-msg-avatar" aria-hidden="true">${avatar}</div>
            <div class="demo-msg-body">
              <div class="demo-msg-header">
                <strong>${speakerName}</strong>
                <span class="demo-msg-time">${timeStr}</span>
              </div>
              <div class="demo-msg-text">${escapeHtml(item.text)}</div>
            </div>
          </div>
        `;
      }).join('');

      container.scrollTop = container.scrollHeight;
    }
  };

  // --- 2. DAILY CHECK-IN CONTROLLER ---
  const DailyCheckinController = {
    selectedStatus: 'fine',

    init() {
      this.renderHistory();
      demoStore.subscribe(() => {
        this.renderHistory();
        this.renderLatestBadge();
      });
    },

    selectStatus(statusType) {
      this.selectedStatus = statusType;
      const options = document.querySelectorAll('.demo-checkin-option-card');
      options.forEach(opt => {
        if (opt.dataset.status === statusType) {
          opt.classList.add('selected');
          opt.setAttribute('aria-checked', 'true');
        } else {
          opt.classList.remove('selected');
          opt.setAttribute('aria-checked', 'false');
        }
      });
    },

    submitCheckin() {
      const notesEl = document.getElementById('demoCheckinNotes');
      const sleepEl = document.querySelector('input[name="demoSleep"]:checked');
      const medsEl = document.getElementById('demoCheckinMeds');
      const mobilityEl = document.querySelector('input[name="demoMobility"]:checked');

      const notes = notesEl ? notesEl.value : '';
      const sleepQuality = sleepEl ? sleepEl.value : 'Good';
      const medicationsTaken = medsEl ? medsEl.checked : true;
      const mobilityConcern = mobilityEl ? mobilityEl.value : 'None';

      const checkin = demoStore.submitDailyCheckin({
        statusType: this.selectedStatus,
        mood: this.selectedStatus === 'fine' ? 'Good' : (this.selectedStatus === 'unwell' ? 'Fatigued' : 'Distressed'),
        sleepQuality,
        medicationsTaken,
        mobilityConcern,
        notes
      });

      // Clear input
      if (notesEl) notesEl.value = '';

      // Show confirmation box
      const confirmBox = document.getElementById('demoCheckinConfirmation');
      if (confirmBox) {
        const isUrgent = checkin.requiresAttention;
        confirmBox.className = `demo-confirmation-card ${isUrgent ? 'requires-attention' : 'success'}`;
        confirmBox.style.display = 'block';
        confirmBox.innerHTML = `
          <div class="confirm-icon">${isUrgent ? '⚠️' : '✅'}</div>
          <div class="confirm-details">
            <h4>Check-in Recorded — ${checkin.statusText}</h4>
            <p>${isUrgent ? 'Guardian David Vance notified. Clinical staff on standby.' : 'All vitals and responses within Eleanor\'s normal baseline.'}</p>
            <div class="confirm-meta">Recorded: ${new Date(checkin.timestamp).toLocaleTimeString()} • ID: ${checkin.id}</div>
          </div>
        `;
        confirmBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      demoStore.showToast(`Daily check-in submitted: "${checkin.statusText}"`, checkin.requiresAttention ? "warning" : "success");
    },

    renderLatestBadge() {
      const badge = document.getElementById('demoLatestCheckinStatus');
      if (!badge) return;
      const latest = demoStore.state.checkins[0];
      if (!latest) {
        badge.innerHTML = `<span class="pill-badge pill-neutral">No Check-ins Today</span>`;
        return;
      }
      const timeAgo = formatTimeAgo(latest.timestamp);
      if (latest.statusType === 'fine') {
        badge.innerHTML = `<span class="pill-badge pill-green">🟢 Checked in Fine (${timeAgo})</span>`;
      } else if (latest.statusType === 'unwell') {
        badge.innerHTML = `<span class="pill-badge pill-amber">🟡 Unwell Reported (${timeAgo})</span>`;
      } else {
        badge.innerHTML = `<span class="pill-badge pill-red">🔴 Assistance Requested (${timeAgo})</span>`;
      }
    },

    renderHistory() {
      const container = document.getElementById('demoCheckinHistoryTableBody');
      if (!container) return;

      const list = demoStore.state.checkins || [];
      if (list.length === 0) {
        container.innerHTML = `<tr><td colspan="5" class="demo-empty-cell">No previous check-in records found.</td></tr>`;
        return;
      }

      container.innerHTML = list.map(item => {
        const timeStr = new Date(item.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
        let badgeClass = 'pill-green';
        let badgeIcon = '🟢';
        if (item.statusType === 'unwell') {
          badgeClass = 'pill-amber';
          badgeIcon = '🟡';
        } else if (item.statusType === 'assistance') {
          badgeClass = 'pill-red';
          badgeIcon = '🔴';
        }

        return `
          <tr>
            <td><strong>${timeStr}</strong></td>
            <td><span class="pill-badge ${badgeClass}">${badgeIcon} ${escapeHtml(item.statusText)}</span></td>
            <td>${escapeHtml(item.sleepQuality || 'Normal')}</td>
            <td>${item.medicationsTaken ? '<span style="color: var(--accent-green);">✓ Taken</span>' : '<span style="color: var(--accent-amber);">Pending</span>'}</td>
            <td><em>${escapeHtml(item.notes || 'No custom notes')}</em></td>
          </tr>
        `;
      }).join('');
    }
  };

  // --- 3. FALL DETECTION SIMULATION CONTROLLER ---
  const FallSimulationController = {
    init() {
      this.renderSensors();
      demoStore.subscribe(() => this.renderSensors());
    },

    simulateFallAction() {
      const btn = document.getElementById('btnTriggerFallSimulation');
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="demo-spinner"></span> Simulating Fall Impact...`;
      }

      const incident = demoStore.simulateFall();

      setTimeout(() => {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `🚨 Simulate Fall`;
        }
        if (incident) {
          demoStore.showToast(`Simulated fall triggered! Incident ${incident.id} created.`, "warning");
          // Offer quick transition or open emergency alert
          const banner = document.getElementById('demoFallIncidentResultBanner');
          if (banner) {
            banner.style.display = 'block';
            banner.innerHTML = `
              <div class="banner-top">
                <strong>🚨 INCIDENT GENERATED: ${incident.id}</strong>
                <span class="pill-badge pill-red">SEVERITY: ${incident.severity}</span>
              </div>
              <p>Bathroom impact registered (3.42g). Eleanor motionless. Simulated caregiver alert dispatched.</p>
              <div class="banner-actions">
                <button class="btn-demo-primary" onclick="window.switchTab('alert')">View Emergency Alert Screen &rarr;</button>
                <button class="btn-demo-secondary" onclick="window.switchTab('map')">View Location & Hospitals &rarr;</button>
                <button class="btn-demo-secondary" onclick="window.person2DemoStore.acknowledgeIncident('${incident.id}')">Acknowledge Alert</button>
              </div>
            `;
          }
        }
      }, 600);
    },

    resetSensors() {
      demoStore.state.sensors = getDefaultDemoState().sensors;
      demoStore.saveState();
      const banner = document.getElementById('demoFallIncidentResultBanner');
      if (banner) banner.style.display = 'none';
      demoStore.showToast("Simulated sensors reset to normal baseline.", "info");
    },

    renderSensors() {
      const s = demoStore.state.sensors;
      if (!s) return;

      const accEl = document.getElementById('demoSensorAccel');
      const velEl = document.getElementById('demoSensorVelocity');
      const postEl = document.getElementById('demoSensorPosture');
      const hrEl = document.getElementById('demoSensorHeartRate');
      const subEl = document.getElementById('demoSensorSubstrate');
      const radarEl = document.getElementById('demoSensorRadar');

      if (accEl) accEl.textContent = `${s.accelerometer.magnitudeG.toFixed(2)} g (${s.accelerometer.x}, ${s.accelerometer.y}, ${s.accelerometer.z})`;
      if (velEl) velEl.textContent = `${s.impactVelocity.toFixed(2)} m/s`;
      if (postEl) {
        postEl.textContent = s.posture;
        postEl.style.color = s.isFallDetected ? 'var(--accent-red)' : 'var(--accent-green-text)';
      }
      if (hrEl) {
        hrEl.textContent = `${s.heartRateBpm} BPM`;
        hrEl.style.color = s.heartRateBpm > 110 ? 'var(--accent-red)' : 'var(--accent-green-text)';
      }
      if (subEl) subEl.textContent = s.substrateCondition;
      if (radarEl) radarEl.textContent = `${s.radarMicromotion} m/s (${s.room})`;
    }
  };

  // --- 4. EMERGENCY ALERT SCREEN CONTROLLER ---
  const EmergencyAlertController = {
    init() {
      this.render();
      demoStore.subscribe(() => this.render());
    },

    acknowledgeActiveIncident() {
      const inc = demoStore.getActiveIncident();
      if (!inc) {
        demoStore.showToast("No active incident to acknowledge.", "info");
        return;
      }
      demoStore.acknowledgeIncident(inc.id);
    },

    cancelActiveIncident() {
      const inc = demoStore.getActiveIncident();
      if (!inc) {
        demoStore.showToast("No active incident to cancel.", "info");
        return;
      }
      if (confirm(`Confirm cancellation of Incident ${inc.id}? This will record a false alarm resolution in the audit log.`)) {
        demoStore.cancelIncident(inc.id, "Caregiver clicked Cancel False Alarm");
      }
    },

    render() {
      const card = document.getElementById('demoEmergencyAlertContent');
      if (!card) return;

      const inc = demoStore.getActiveIncident();
      if (!inc) {
        card.innerHTML = `
          <!-- Ambulance CAD Dispatch Mode Banner -->
          <div class="ambulance-cad-hud" style="background: linear-gradient(135deg, rgba(225, 29, 72, 0.22) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1.5px solid rgba(244, 63, 94, 0.55); border-radius: 16px; padding: 18px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; box-shadow: 0 10px 30px rgba(244, 63, 94, 0.25);">
            <div style="display: flex; align-items: center; gap: 14px;">
              <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(244, 63, 94, 0.25); border: 1.5px solid rgba(244, 63, 94, 0.6); display: flex; align-items: center; justify-content: center; font-size: 1.6rem;">🚑</div>
              <div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                  <span style="font-size: 1.05rem; font-weight: 800; color: #ffffff; letter-spacing: -0.01em;">Boston EMS Medic 14 &bull; Ambulance CAD Driver Portal</span>
                  <span class="pill-badge pill-green">CAD LINK ONLINE &bull; READY</span>
                </div>
                <div style="font-size: 0.82rem; color: #cbd5e1; margin-top: 4px;">
                  MDT Terminal ID: <strong>CAD-BOS-02108</strong> &bull; Sector: <strong>Beacon Hill District</strong> &bull; Primary Trauma Center: <strong>Mass General Hospital</strong>
                </div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px; background: rgba(0, 0, 0, 0.45); padding: 10px 18px; border-radius: 12px; border: 1.5px dashed rgba(244, 63, 94, 0.55);">
              <div>
                <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #fda4af; font-weight: 800;">Smart Door Token</div>
                <div style="font-size: 1.45rem; font-weight: 900; color: #34d399; font-family: monospace; letter-spacing: 0.16em;">8492</div>
              </div>
              <span class="pill-badge pill-green" style="font-size: 0.68rem;">FIRST RESPONDER OVERRIDE</span>
            </div>
          </div>

          <!-- Standby CAD Patrol Monitor Card -->
          <div class="demo-standby-card" style="border: 1px solid rgba(244, 63, 94, 0.3); background: rgba(15, 23, 42, 0.85); border-radius: 16px; padding: 28px 24px; text-align: center;">
            <div class="standby-icon" style="background: rgba(244, 63, 94, 0.15); border: 1.5px solid rgba(244, 63, 94, 0.4); width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2rem; margin: 0 auto;">🚑</div>
            <h3 style="color: #fff; margin-top: 14px; font-size: 1.25rem;">Ambulance CAD Dispatcher Active</h3>
            <p style="color: #94a3b8; max-width: 580px; margin: 8px auto 18px; font-size: 0.88rem;">Boston EMS Medic 14 is linked to Eleanor Vance's Beacon Hill Unit 4B ambient sensor array. All telemetry is streaming in real time.</p>
            
            <div style="background: rgba(0, 0, 0, 0.35); border-radius: 12px; padding: 16px 22px; max-width: 560px; margin: 0 auto 22px; text-align: left; font-size: 0.84rem; color: #cbd5e1; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; border: 1px solid rgba(255, 255, 255, 0.08);">
              <div>👤 <strong>Patient:</strong> Eleanor Vance (Age 79)</div>
              <div>📍 <strong>Address:</strong> Unit 4B - Beacon Hill</div>
              <div>🔑 <strong>Door Deadbolt:</strong> PIN 8492 Armed</div>
              <div>🏥 <strong>Hospital:</strong> Mass General ER (1.2 mi)</div>
            </div>

            <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
              <button class="btn-demo-primary" onclick="window.person2DemoStore.simulateFall()" style="background: linear-gradient(135deg, #e11d48, #be123c); border-color: #f43f5e; box-shadow: 0 4px 16px rgba(244,63,94,0.4); padding: 10px 20px; font-size: 0.88rem;">
                🚨 Simulate Live CAD Fall Dispatch &rarr;
              </button>
              <button class="btn-demo-secondary" onclick="window.switchTab('map')" style="padding: 10px 18px; font-size: 0.88rem;">
                🗺️ Open GPS CAD Route Map &rarr;
              </button>
              <button class="btn-demo-secondary" onclick="window.switchTab('history')" style="padding: 10px 18px; font-size: 0.88rem;">
                📜 CAD Incident History &rarr;
              </button>
            </div>
          </div>
        `;
        return;
      }

      const isAcknowledged = inc.status === "ACKNOWLEDGED";
      const isCritical = inc.severity === "CRITICAL";

      card.innerHTML = `
        <!-- Ambulance CAD Dispatch Mode Banner -->
        <div class="ambulance-cad-hud" style="background: linear-gradient(135deg, rgba(225, 29, 72, 0.22) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1.5px solid rgba(244, 63, 94, 0.55); border-radius: 16px; padding: 18px 20px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; box-shadow: 0 10px 30px rgba(244, 63, 94, 0.25);">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(244, 63, 94, 0.25); border: 1.5px solid rgba(244, 63, 94, 0.6); display: flex; align-items: center; justify-content: center; font-size: 1.6rem; animation: pulse 1.5s infinite;">🚑</div>
            <div>
              <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span style="font-size: 1.05rem; font-weight: 800; color: #ffffff; letter-spacing: -0.01em;">Ambulance CAD Dispatch &bull; Boston EMS Medic 14</span>
                <span class="pill-badge pill-red">EN ROUTE (ETA 4 MIN)</span>
              </div>
              <div style="font-size: 0.82rem; color: #cbd5e1; margin-top: 4px;">
                CAD Unit: <strong>Medic-14</strong> &bull; Priority 1 Traumatic Fall &bull; Destination: <strong>Mass General Hospital Level 1 Trauma Center</strong>
              </div>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 12px; background: rgba(0, 0, 0, 0.45); padding: 10px 18px; border-radius: 12px; border: 1.5px dashed rgba(244, 63, 94, 0.55);">
            <div>
              <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #fda4af; font-weight: 800;">Smart Door Token</div>
              <div style="font-size: 1.45rem; font-weight: 900; color: #34d399; font-family: monospace; letter-spacing: 0.16em;">8492</div>
            </div>
            <span class="pill-badge pill-green" style="font-size: 0.68rem;">UNLOCKED FOR FIRST RESPONDERS</span>
          </div>
        </div>

        <div class="demo-emergency-banner ${isCritical ? 'critical-pulse' : 'warning-pulse'}">
          <div class="banner-header-row">
            <div class="em-title-wrap">
              <span class="em-pulsing-dot"></span>
              <h2>${isCritical ? 'CRITICAL SAFETY INCIDENT' : 'SAFETY ANOMALY DETECTED'}</h2>
            </div>
            <span class="pill-badge pill-red">${inc.status}</span>
          </div>

          <div class="em-grid">
            <div class="em-cell">
              <label>Incident ID:</label>
              <strong>${inc.id}</strong>
            </div>
            <div class="em-cell">
              <label>Event Type:</label>
              <strong>${inc.eventLabel || inc.eventType}</strong>
            </div>
            <div class="em-cell">
              <label>Timestamp:</label>
              <strong>${new Date(inc.timestamp).toLocaleString()} (${formatTimeAgo(inc.timestamp)})</strong>
            </div>
            <div class="em-cell">
              <label>Severity / Risk Score:</label>
              <strong style="color: var(--accent-red);">${inc.severity} (${inc.riskScore}%)</strong>
            </div>
          </div>

          <div class="em-resident-section">
            <h4>Resident &amp; Incident Location</h4>
            <div class="resident-info-bar">
              <div><strong>Eleanor Vance</strong> (Age 79)</div>
              <div>${inc.location}</div>
              <div>Smart Lock Deadbolt: <span class="pill-badge pill-green">UNLOCKED (PIN: 8492)</span></div>
            </div>
          </div>

          <div class="em-caregiver-section">
            <h4>Guardian Dispatch Status (Simulated)</h4>
            <div class="caregiver-status-box">
              <div class="cg-icon">📱</div>
              <div class="cg-text">
                <strong>David Vance (Son &bull; Primary Guardian)</strong>
                <p>${escapeHtml(inc.caregiverStatus)}</p>
                <div class="cg-channels">
                  <span class="pill-badge pill-blue">Echo Show 15 Drop-In: Active</span>
                  <span class="pill-badge pill-blue">SMS Alert: Delivered</span>
                  <span class="pill-badge pill-blue">Mobile Push: Sent</span>
                </div>
              </div>
            </div>
          </div>

          <div class="em-controls-row">
            ${!isAcknowledged ? `
              <button class="btn-demo-primary" id="btnAckEmergency" onclick="window.person2DemoStore.acknowledgeIncident('${inc.id}')">
                ✅ Acknowledge Incident (Medic 14)
              </button>
            ` : `
              <button class="btn-demo-primary" disabled style="opacity: 0.7;">
                ✓ Acknowledged by First Responder
              </button>
            `}
            <button class="btn-demo-primary" onclick="window.EmergencyAlertController.markOnScene()" style="background: linear-gradient(135deg, #10b981, #059669); border-color: #10b981;">
              🚑 Mark On-Scene (Arrived)
            </button>
            <button class="btn-demo-secondary" id="btnCancelEmergency" onclick="window.person2DemoStore.cancelIncident('${inc.id}', 'First Responder cancelled false alarm')">
              ✖ Cancel Incident (False Alarm)
            </button>
            <button class="btn-demo-secondary" onclick="window.switchTab('map')">
              🗺️ Open CAD GPS Map
            </button>
            <button class="btn-demo-secondary" onclick="window.switchTab('history')">
              📜 View CAD History
            </button>
          </div>
        </div>
      `;
    },

    markOnScene() {
      demoStore.showToast("🚑 Boston EMS Medic 14 marked ON-SCENE at Beacon Hill Unit 4B. Smart Lock PIN 8492 verified.", "success");
    }
  };

  // --- 5. LOCATION MAP & HOSPITALS CONTROLLER ---
  const LocationMapController = {
    leafletMap: null,
    incidentMarker: null,
    hospitalMarkers: [],

    init() {
      this.renderHospitalCards();
      // Render Leaflet or SVG fallback
      setTimeout(() => this.initMap(), 150);
      demoStore.subscribe(() => {
        this.updateMapMarker();
        this.renderHospitalCards();
      });
    },

    initMap() {
      const container = document.getElementById('demoMapContainer');
      if (!container) return;

      const resident = demoStore.state.resident;
      const centerLat = resident.lat || 42.3588;
      const centerLng = resident.lng || -71.0638;

      if (typeof window.L !== 'undefined') {
        try {
          if (!this.leafletMap) {
            this.leafletMap = window.L.map('demoMapContainer', {
              zoomControl: true,
              scrollWheelZoom: false
            }).setView([centerLat, centerLng], 14);

            window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
              attribution: '&copy; OpenStreetMap contributors | NIRA Demo Data',
              maxZoom: 18
            }).addTo(this.leafletMap);
          }

          this.updateMapMarker();
          return;
        } catch (e) {
          console.warn("Leaflet initialization failed, switching to vector SVG fallback:", e);
        }
      }

      // Fallback: High-fidelity interactive vector SVG map
      this.renderVectorSvgMap(container);
    },

    updateMapMarker() {
      if (!this.leafletMap || typeof window.L === 'undefined') return;

      const resident = demoStore.state.resident;
      const activeInc = demoStore.getActiveIncident();
      const hasActiveIncident = Boolean(activeInc && activeInc.status === "ACTIVE");

      if (this.incidentMarker) {
        this.leafletMap.removeLayer(this.incidentMarker);
      }

      this.hospitalMarkers.forEach(m => this.leafletMap.removeLayer(m));
      this.hospitalMarkers = [];

      // Add resident marker
      const markerColor = hasActiveIncident ? "#f43f5e" : "#10b981";
      const iconHtml = `
        <div style="
          width: 32px; height: 32px; border-radius: 50%;
          background: ${markerColor}; border: 3px solid #ffffff;
          box-shadow: 0 0 15px ${markerColor}; display: flex; align-items: center; justify-content: center;
          color: #fff; font-size: 16px; font-weight: bold;
        ">
          ${hasActiveIncident ? '🚨' : '🏠'}
        </div>
      `;

      const customIcon = window.L.divIcon({
        className: 'demo-map-custom-marker',
        html: iconHtml,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      });

      this.incidentMarker = window.L.marker([resident.lat, resident.lng], { icon: customIcon }).addTo(this.leafletMap);
      this.incidentMarker.bindPopup(`
        <div style="font-family: sans-serif; color: #1e293b;">
          <strong>${resident.name} (${resident.address})</strong><br>
          ${hasActiveIncident ? `<span style="color: #e11d48; font-weight: bold;">🚨 ACTIVE EMERGENCY: ${activeInc.id}</span>` : '🟢 Status: Safe Baseline'}
        </div>
      `);

      if (hasActiveIncident) {
        this.incidentMarker.openPopup();
      }

      // Add nearby hospital markers
      const hospitals = demoStore.state.hospitals || [];
      hospitals.forEach(h => {
        const hospIcon = window.L.divIcon({
          className: 'demo-hosp-marker',
          html: `<div style="background: #38bdf8; width: 26px; height: 26px; border-radius: 6px; border: 2px solid #ffffff; display: flex; align-items: center; justify-content: center; color: #040812; font-size: 14px; font-weight: 800;">🏥</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13]
        });
        const m = window.L.marker([h.lat, h.lng], { icon: hospIcon }).addTo(this.leafletMap);
        m.bindPopup(`
          <div style="font-family: sans-serif; color: #1e293b;">
            <strong>${escapeHtml(h.name)}</strong><br>
            <span>${escapeHtml(h.traumaLevel)}</span><br>
            <span>Distance: ${h.distance} &bull; ETA: ${h.eta}</span><br>
            <span>Phone: ${h.phone}</span>
          </div>
        `);
        this.hospitalMarkers.push(m);
      });
    },

    renderVectorSvgMap(container) {
      const activeInc = demoStore.getActiveIncident();
      const isEmergency = Boolean(activeInc && activeInc.status === "ACTIVE");

      container.innerHTML = `
        <div class="demo-vector-map-wrap">
          <svg viewBox="0 0 800 480" class="demo-vector-svg">
            <!-- Background / City Base -->
            <rect width="800" height="480" fill="#0b111e"/>
            <!-- Charles River curve -->
            <path d="M 0,260 Q 220,180 420,290 T 800,210 L 800,480 L 0,480 Z" fill="#0d233a" opacity="0.75"/>
            <!-- Major Arteries / Bridges -->
            <line x1="260" y1="0" x2="260" y2="480" stroke="#1e293b" stroke-width="6"/>
            <line x1="0" y1="210" x2="800" y2="210" stroke="#1e293b" stroke-width="6"/>
            <line x1="120" y1="420" x2="680" y2="80" stroke="#334155" stroke-width="4" stroke-dasharray="8 4"/>

            <!-- Boston Common / Public Garden green zone -->
            <rect x="360" y="270" width="130" height="110" rx="14" fill="#064e3b" opacity="0.45"/>
            <text x="425" y="330" fill="#34d399" font-size="12" font-weight="bold" text-anchor="middle">Boston Common</text>

            <!-- Beacon Hill Resident Location Pin -->
            <g transform="translate(380, 220)" style="cursor: pointer;">
              <circle cx="0" cy="0" r="${isEmergency ? '28' : '18'}" fill="${isEmergency ? 'rgba(244,63,94,0.3)' : 'rgba(16,185,129,0.25)'}" ${isEmergency ? 'class="pulse-ring"' : ''}/>
              <circle cx="0" cy="0" r="14" fill="${isEmergency ? '#f43f5e' : '#10b981'}" stroke="#ffffff" stroke-width="2.5"/>
              <text x="0" y="4" font-size="11" text-anchor="middle" fill="#fff">${isEmergency ? '🚨' : '🏠'}</text>
              <text x="0" y="-22" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">Eleanor Vance (Unit 4B)</text>
              ${isEmergency ? `<text x="0" y="32" font-size="11" font-weight="bold" fill="#f43f5e" text-anchor="middle">FALL INCIDENT ACTIVE</text>` : ''}
            </g>

            <!-- Hospital 1: MGH -->
            <g transform="translate(310, 150)" style="cursor: pointer;">
              <circle cx="0" cy="0" r="13" fill="#38bdf8" stroke="#ffffff" stroke-width="2"/>
              <text x="0" y="4" font-size="10" text-anchor="middle" fill="#040812">🏥</text>
              <text x="0" y="-18" font-size="11" font-weight="600" fill="#38bdf8" text-anchor="middle">MGH (0.4 mi &bull; 3m ETA)</text>
            </g>

            <!-- Hospital 2: Tufts -->
            <g transform="translate(450, 360)" style="cursor: pointer;">
              <circle cx="0" cy="0" r="13" fill="#38bdf8" stroke="#ffffff" stroke-width="2"/>
              <text x="0" y="4" font-size="10" text-anchor="middle" fill="#040812">🏥</text>
              <text x="0" y="24" font-size="11" font-weight="600" fill="#38bdf8" text-anchor="middle">Tufts Medical (1.1 mi)</text>
            </g>

            <!-- Hospital 3: BMC -->
            <g transform="translate(560, 420)" style="cursor: pointer;">
              <circle cx="0" cy="0" r="13" fill="#38bdf8" stroke="#ffffff" stroke-width="2"/>
              <text x="0" y="4" font-size="10" text-anchor="middle" fill="#040812">🏥</text>
              <text x="0" y="24" font-size="11" font-weight="600" fill="#38bdf8" text-anchor="middle">Boston Medical (1.8 mi)</text>
            </g>
          </svg>
          <div class="demo-vector-map-overlay">
            <span class="pill-badge pill-neutral">Vector Fallback Map • Beacon Hill, Boston</span>
            <small style="color: var(--text-secondary);">Interactive simulated coordinate overlay</small>
          </div>
        </div>
      `;
    },

    renderHospitalCards() {
      const container = document.getElementById('demoHospitalCardsGrid');
      if (!container) return;

      const hospitals = demoStore.state.hospitals || [];
      container.innerHTML = hospitals.map(h => {
        return `
          <div class="demo-hospital-card">
            <div class="hosp-card-header">
              <div class="hosp-icon">🏥</div>
              <div class="hosp-title-group">
                <h5>${escapeHtml(h.name)}</h5>
                <span class="pill-badge pill-blue">${escapeHtml(h.traumaLevel)}</span>
              </div>
            </div>
            <div class="hosp-meta-grid">
              <div><small>Distance:</small> <strong>${h.distance}</strong></div>
              <div><small>EMS Transit:</small> <strong>${h.eta}</strong></div>
              <div><small>ER Status:</small> <strong style="color: var(--accent-green);">${h.erStatus}</strong></div>
              <div><small>Phone:</small> <strong>${h.phone}</strong></div>
            </div>
            <div class="hosp-card-footer">
              <span class="hosp-sample-tag">${h.sampleDisclaimer}</span>
              <button class="btn-demo-secondary" onclick="window.person2DemoStore.showToast('Dispatch route queued to ${escapeHtml(h.name)}.', 'info')">
                Dispatch Route
              </button>
            </div>
          </div>
        `;
      }).join('');
    }
  };

  // --- 6. NOTIFICATION CENTER CONTROLLER ---
  const NotificationCenterController = {
    activeCategory: 'all',

    init() {
      this.render();
      demoStore.subscribe(() => this.render());
    },

    setFilter(cat) {
      this.activeCategory = cat;
      const pills = document.querySelectorAll('.demo-notif-filter-pill');
      pills.forEach(p => {
        if (p.dataset.category === cat) {
          p.classList.add('active');
        } else {
          p.classList.remove('active');
        }
      });
      this.render();
    },

    render() {
      const listContainer = document.getElementById('demoNotificationList');
      const unreadCountEl = document.getElementById('demoNotifUnreadCount');
      if (!listContainer) return;

      const all = demoStore.state.notifications || [];
      const unreadCount = demoStore.getUnreadNotificationCount();
      if (unreadCountEl) {
        unreadCountEl.textContent = `${unreadCount} unread`;
      }

      const filtered = all.filter(item => {
        if (this.activeCategory === 'all') return true;
        return item.category === this.activeCategory;
      });

      if (filtered.length === 0) {
        listContainer.innerHTML = `<div class="demo-empty-state">No notifications in this category.</div>`;
        return;
      }

      listContainer.innerHTML = filtered.map(item => {
        const timeAgo = formatTimeAgo(item.timestamp);
        let categoryIcon = '🔔';
        if (item.category === 'emergency') categoryIcon = '🚨';
        else if (item.category === 'check_in') categoryIcon = '📋';
        else if (item.category === 'reminder') categoryIcon = '⏰';

        let severityBadge = 'pill-blue';
        if (item.severity === 'critical') severityBadge = 'pill-red';
        else if (item.severity === 'warning') severityBadge = 'pill-amber';

        return `
          <div class="demo-notif-item ${item.read ? 'is-read' : 'is-unread'} ${item.severity === 'critical' ? 'critical-glow' : ''}">
            <div class="notif-icon-col" aria-hidden="true">${categoryIcon}</div>
            <div class="notif-content-col">
              <div class="notif-header-line">
                <span class="pill-badge ${severityBadge}">${item.severity.toUpperCase()}</span>
                <span class="notif-title">${escapeHtml(item.title)}</span>
                <span class="notif-time" title="${item.timestamp}">${timeAgo}</span>
              </div>
              <p class="notif-desc">${escapeHtml(item.description)}</p>
              <div class="notif-actions-line">
                <span class="notif-sim-badge">Simulated Delivery &bull; Demo Mode</span>
                <div class="notif-btn-group">
                  ${item.incidentId ? `
                    <button class="btn-demo-link" onclick="window.switchTab('alert')">View Emergency Alert &rarr;</button>
                  ` : ''}
                  ${!item.read ? `
                    <button class="btn-demo-link" onclick="window.person2DemoStore.markNotificationRead('${item.id}')">Mark as Read</button>
                  ` : ''}
                </div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }
  };

  // --- 7. INCIDENT HISTORY CONTROLLER ---
  const IncidentHistoryController = {
    filterType: 'all',
    filterStatus: 'all',

    init() {
      this.render();
      demoStore.subscribe(() => this.render());
    },

    setFilters(type, status) {
      if (type !== undefined) this.filterType = type;
      if (status !== undefined) this.filterStatus = status;
      this.render();
    },

    openIncidentDetails(incidentId) {
      const inc = demoStore.state.incidents.find(i => i.id === incidentId);
      if (!inc) return;

      const modal = document.getElementById('demoIncidentDetailModal');
      const body = document.getElementById('demoIncidentDetailModalBody');
      if (!modal || !body) return;

      body.innerHTML = `
        <div class="modal-incident-header">
          <h3>Incident Details: ${inc.id}</h3>
          <span class="pill-badge ${inc.severity === 'CRITICAL' ? 'pill-red' : 'pill-amber'}">${inc.severity}</span>
          <span class="pill-badge pill-neutral">${inc.status}</span>
        </div>
        <div class="modal-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 16px 0;">
          <div><small>Location:</small><br><strong>${escapeHtml(inc.location)}</strong></div>
          <div><small>Timestamp:</small><br><strong>${new Date(inc.timestamp).toLocaleString()}</strong></div>
          <div><small>Event Type:</small><br><strong>${escapeHtml(inc.eventLabel || inc.eventType)}</strong></div>
          <div><small>Caregiver Status:</small><br><strong>${escapeHtml(inc.caregiverStatus)}</strong></div>
        </div>
        <p><strong>Description:</strong> ${escapeHtml(inc.details || 'No additional narrative logged.')}</p>

        <h4 style="margin-top: 18px; margin-bottom: 8px;">Audit Trail Timeline:</h4>
        <div class="modal-timeline-strip">
          ${(inc.timeline || []).map(t => `
            <div class="tl-item">
              <span class="tl-time">${t.time}</span>
              <span class="tl-action">${escapeHtml(t.action)}</span>
            </div>
          `).join('')}
        </div>

        <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end;">
          ${inc.status === 'ACTIVE' ? `
            <button class="btn-demo-primary" onclick="window.person2DemoStore.acknowledgeIncident('${inc.id}'); window.closeIncidentModal();">Acknowledge</button>
            <button class="btn-demo-secondary" onclick="window.person2DemoStore.cancelIncident('${inc.id}'); window.closeIncidentModal();">Cancel (False Alarm)</button>
          ` : ''}
          <button class="btn-demo-secondary" onclick="window.closeIncidentModal()">Close</button>
        </div>
      `;

      modal.style.display = 'flex';
      modal.setAttribute('aria-hidden', 'false');
    },

    render() {
      const tbody = document.getElementById('demoIncidentHistoryTableBody');
      if (!tbody) return;

      const list = demoStore.state.incidents || [];
      const filtered = list.filter(item => {
        if (this.filterType !== 'all' && item.eventType !== this.filterType) return false;
        if (this.filterStatus !== 'all' && item.status !== this.filterStatus) return false;
        return true;
      });

      if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="demo-empty-cell">No incidents match the active filters.</td></tr>`;
        return;
      }

      tbody.innerHTML = filtered.map(item => {
        const timeStr = new Date(item.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
        let statusBadge = 'pill-green';
        if (item.status === 'ACTIVE') statusBadge = 'pill-red';
        else if (item.status === 'ACKNOWLEDGED') statusBadge = 'pill-blue';
        else if (item.status === 'CANCELLED_FALSE_ALARM') statusBadge = 'pill-neutral';

        let sevBadge = 'pill-red';
        if (item.severity === 'MODERATE') sevBadge = 'pill-amber';
        else if (item.severity === 'LOW') sevBadge = 'pill-green';

        return `
          <tr>
            <td><strong>${item.id}</strong></td>
            <td>${escapeHtml(item.eventLabel || item.eventType)}</td>
            <td>${timeStr}</td>
            <td>${escapeHtml(item.location)}</td>
            <td><span class="pill-badge ${sevBadge}">${item.severity}</span></td>
            <td><span class="pill-badge ${statusBadge}">${item.status}</span></td>
            <td>
              <button class="btn-demo-link" onclick="window.person2IncidentHistory.openIncidentDetails('${item.id}')">
                Inspect Details &rarr;
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }
  };

  // Expose controllers to window
  window.person2VoiceAssistant = VoiceAssistantController;
  window.person2DailyCheckin = DailyCheckinController;
  window.person2FallSimulation = FallSimulationController;
  window.person2EmergencyAlert = EmergencyAlertController;
  window.person2LocationMap = LocationMapController;
  window.person2NotificationCenter = NotificationCenterController;
  window.person2IncidentHistory = IncidentHistoryController;

  window.closeIncidentModal = function() {
    const modal = document.getElementById('demoIncidentDetailModal');
    if (modal) {
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
    }
  };

  window.openResidentProfileModal = function() {
    const modal = document.getElementById('residentProfileModal');
    if (modal) {
      modal.style.display = 'flex';
      modal.setAttribute('aria-hidden', 'false');
    }
  };

  window.closeResidentProfileModal = function() {
    const modal = document.getElementById('residentProfileModal');
    if (modal) {
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
    }
  };

  window.toggleMedicationDose = function(medId) {
    const badge = document.getElementById('medStatus_' + medId);
    const btn = document.getElementById('btnMedAction_' + medId);
    const overviewBadge = document.getElementById('overviewCoq10Badge');

    const isTaken = badge ? badge.getAttribute('data-taken') === 'true' : false;

    if (!isTaken) {
      if (badge) {
        badge.setAttribute('data-taken', 'true');
        badge.className = 'pill-badge pill-green';
        badge.innerHTML = '✓ Taken Just Now';
      }
      if (btn) {
        btn.className = 'btn-demo-secondary';
        btn.innerHTML = 'Undo / Mark Pending';
      }
      if (overviewBadge) {
        overviewBadge.className = 'pill-badge pill-green';
        overviewBadge.innerHTML = '✓ Taken';
      }
      if (window.person2DemoStore) {
        window.person2DemoStore.showToast("💊 CoQ10 100mg recorded as taken. Caregiver portal synced.", "success");
      }
    } else {
      if (badge) {
        badge.setAttribute('data-taken', 'false');
        badge.className = 'pill-badge pill-amber';
        badge.innerHTML = '⏳ Pending (Due 7:00 PM)';
      }
      if (btn) {
        btn.className = 'btn-demo-primary';
        btn.innerHTML = 'Take Dose Now &rarr;';
      }
      if (overviewBadge) {
        overviewBadge.className = 'pill-badge pill-amber';
        overviewBadge.innerHTML = 'Pending';
      }
      if (window.person2DemoStore) {
        window.person2DemoStore.showToast("Medication status reset to Pending.", "info");
      }
    }
  };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function formatTimeAgo(isoDate) {
    if (!isoDate) return '--';
    const diff = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000);
    if (diff < 5) return 'Just now';
    if (diff < 60) return `${diff}s ago`;
    const m = Math.floor(diff / 60);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const d = Math.floor(h / 24);
    return `${d}d ago`;
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

  // --- 8. EXPLAINABLE AI DEMO VIDEO & SYSTEM WALKTHROUGH CONTROLLER ---
  const DemoVideoController = {
    currentScene: 0,
    isPlaying: false,
    timer: null,
    progressInterval: null,
    playbackSpeed: 1,
    voiceNarrationEnabled: false,
    currentTime: 0,
    captionsVisible: true,
    viewMode: 'video', // Default to official Gemini-generated video
    reelInstance: null,

    scenes: [
      {
        id: "voice",
        title: "Ambient Non-Invasive Protection & Alexa+ Integration",
        sub: "Ceiling mmWave Radar • 0 Cameras (100% Privacy) • Sub-500ms Voice Verification",
        duration: 10,
        tabTarget: "voiceassistant",
        tag: "1. AMBIENT PROTECTION",
        roomTitle: "🌐 3D DIGITAL TWIN • UNIT 4B LIVING ROOM",
        roomTelemetry: "3D Articulated Eleanor Walking • 60GHz Ceiling Micro-Radar Active • 0 Cameras (100% Privacy)",
        statusPill: "🟢 3D ANIMATION LIVE",
        timeOffset: 0.0,
        caption: "Eleanor Vance, age 79, lives independently in Beacon Hill Unit 4B. The apartment is continuously protected by ceiling micro-radar and ambient sensors, preserving total privacy without cameras.",
        explanation: {
          confidence: "99.4%",
          aiRationale: "Continuous mmWave radar Doppler frequency evaluation confirms steady ambulatory gait (0.92 m/s) with zero spatial obstruction.",
          sensorFusion: "Echo Show 15 beamforming microphone + Ceiling mmWave radar array + Apple Watch resting heart rate (74 BPM).",
          safetyOutput: "All baseline telemetry optimal. 0 privacy violations, continuous non-invasive protection."
        }
      },
      {
        id: "checkin",
        title: "Daily Morning Wellness Check-In & Motion Sync",
        sub: "1-Tap Safety Verification • Hallway Radar Confirmation • Family Sync",
        duration: 10,
        tabTarget: "dailycheckin",
        tag: "2. DAILY VERIFICATION",
        roomTitle: "🌐 3D DIGITAL TWIN • UNIT 4B HALLWAY & LIVING ROOM",
        roomTelemetry: "Verified Ambulatory Gait 0.92 m/s • Morning Check-In Completed • Son David Synced",
        statusPill: "✅ MORNING VERIFIED",
        timeOffset: 5.0,
        caption: "Every morning at 09:30 AM, Eleanor selects her wellness status ('I'm fine', 'Feeling unwell', 'Need assistance'). Confirmation is instantly logged and synced to David's Family Admin console.",
        explanation: {
          confidence: "100.0%",
          aiRationale: "Verified positive morning compliance response. Automatically clears 10:00 AM unresponsiveness escalation countdown timer.",
          sensorFusion: "Screen touch verification event + Hallway motion passive radar confirmation.",
          safetyOutput: "Updated resident wellness index to 'Optimal', synced timestamped check-in record to David Vance Family Admin portal."
        }
      },
      {
        id: "falldetect",
        title: "Sudden Fall Detected & Biometric Telemetry Surge",
        sub: "Bathroom Wet Tile Impact • >2.2 m/s Descent • Acute Tachycardia 138 BPM",
        duration: 10,
        tabTarget: "falldetection",
        tag: "3. SUDDEN FALL KINEMATICS",
        roomTitle: "🚨 3D KINEMATICS • BATHROOM WET TILE FALL",
        roomTelemetry: "Sudden Downward Drop (2.84 m/s) • Horizontal Posture (78°) • Red Shockwave Ring",
        statusPill: "🚨 FALL DETECTED (98.7%)",
        timeOffset: 10.5,
        caption: "At 2:14 AM, the ceiling radar detects a sudden downward drop in the bathroom. The multimodal AI confirms a 94 percent probability of a fall, while Apple Watch telemetry captures acute tachycardia surging to 138 BPM.",
        explanation: {
          confidence: "98.7%",
          aiRationale: "Dual-sensor fusion triggered: rapid descent velocity >2.2 m/s matched with 78° horizontal posture angle and abrupt zero-mobility.",
          sensorFusion: "60GHz mmWave Radar doppler shift (2.84 m/s impact) + Optical YOLOv8-pose skeleton + Apple Watch PPG tachycardia surge (138 BPM).",
          safetyOutput: "Triggered Level-3 Emergency State; initiated 30-second Alexa verbal inquiry countdown before auto-escalation."
        }
      },
      {
        id: "escalation",
        title: "Son David Vance Alerted & 2-Way Echo Drop-In",
        sub: "Multi-Channel Push & SMS • Live Guardian Audio • Smart Deadbolt PIN: 8492",
        duration: 10,
        tabTarget: "emergencyalert",
        tag: "4. FAMILY GUARDIAN",
        roomTitle: "📱 GUARDIAN ESCALATION • SON DAVID VANCE",
        roomTelemetry: "Live 2-Way Drop-In Connected • Mobile Priority Push • Deadbolt Token 8492 Generated",
        statusPill: "📲 GUARDIAN ALERTED",
        timeOffset: 30.5,
        caption: "Aegis immediately connects her primary guardian and son, David Vance. His phone receives an instant priority notification and opens a live Echo Drop-In audio stream, allowing David to speak directly to his mother.",
        explanation: {
          confidence: "99.8%",
          aiRationale: "Zero resident response detected after 30s verbal verification timeout. Escalated incident to Tier-1 Family Guardian emergency protocol.",
          sensorFusion: "Living Room acoustic silence verification + Biometric tachycardia alert (94 BPM pulse on floor).",
          safetyOutput: "Dispatched high-priority push & SMS alerts to Son David Vance; activated Smart Lock Deadbolt with emergency token PIN 8492."
        }
      },
      {
        id: "ambulance",
        title: "Boston EMS Medic 14 CAD Dispatch & Smart Door Unlocked",
        sub: "Autonomous CAD Packet • Deadbolt PIN 8492 Auto-Unlocked • MGH Trauma 1",
        duration: 10,
        tabTarget: "emergencyalert",
        tag: "5. 911 EMS CAD DISPATCH",
        roomTitle: "🚑 FIRST RESPONDER • BOSTON EMS MEDIC 14",
        roomTelemetry: "Smart Door LED Green (Unlocked) • Ambulance Drives In • Dual Flashing Strobes",
        statusPill: "🚑 AMBULANCE ARRIVED",
        timeOffset: 40.5,
        caption: "Simultaneously, Aegis dispatches Boston EMS Medic 14 with Eleanor's clinical vitals and floor status. The front door smart lock is automatically unlocked with emergency PIN 8492, allowing paramedics to enter instantly without delay.",
        explanation: {
          confidence: "100.0%",
          aiRationale: "Autonomous Computer-Aided Dispatch (CAD) packet generated with clinical vitals summary, floorplan GPS coordinates, and hospital pre-alert.",
          sensorFusion: "Telemetry packet (Fall severity, pulse, address Beacon Hill Unit 4B) + Mass General Trauma 1 route telemetry.",
          safetyOutput: "Boston EMS Medic 14 ambulance dispatched under Code 3; Smart Door Token 8492 issued for direct zero-delay paramedic entry."
        }
      }
    ],

    init() {
      this.render();
      setTimeout(() => {
        this.init3DReel();
      }, 50);
    },

    init3DReel() {
      if (typeof THREE === "undefined" || typeof OperationalVideoReel === "undefined") {
        return;
      }
      const canvas = document.getElementById("geminiSplit3dCanvas");
      if (!canvas) return;

      try {
        if (!this.reelInstance || this.reelInstance.canvas !== canvas) {
          this.reelInstance = new OperationalVideoReel("geminiSplit3dCanvas");
          this.reelInstance.isAudioMuted = true;
        }
        this.sync3DReel();
      } catch (err) {
        console.warn("3D Reel Init:", err);
      }
    },

    sync3DReel() {
      if (!this.reelInstance) {
        this.init3DReel();
        if (!this.reelInstance) return;
      }
      const sc = this.scenes[this.currentScene];
      if (!sc) return;

      const baseTime = sc.timeOffset || 0;
      const targetTime = baseTime + (this.currentTime || 0);
      try {
        this.reelInstance.seek(targetTime);
        this.reelInstance.resize();
        if (this.isPlaying) {
          this.reelInstance.play();
        } else {
          this.reelInstance.pause();
        }
      } catch (e) {
        console.warn("3D Reel Sync:", e);
      }
    },

    setViewMode(mode) {
      this.viewMode = mode;
      const stage = document.getElementById("geminiStageContainer");
      const videoPane = document.getElementById("geminiVideoFilePane");
      const realVid = document.getElementById("geminiRealVideoPlayer");

      if (mode === "video") {
        if (stage) stage.style.display = "none";
        if (videoPane) videoPane.style.display = "flex";
        if (realVid && this.isPlaying) {
          realVid.play().catch(() => {});
        }
      } else {
        if (videoPane) {
          videoPane.style.display = "none";
          if (realVid) realVid.pause();
        }
        if (stage) {
          stage.style.display = "grid";
          stage.className = "gemini-stage-container" + 
            (mode === "human" ? " view-human-only" : (mode === "3d" ? " view-3d-only" : ""));
        }
      }

      const btns = document.querySelectorAll(".gemini-view-toggles .view-mode-btn");
      btns.forEach(b => {
        const isTarget = b.getAttribute("data-mode") === mode;
        b.classList.toggle("active-view-mode", isTarget);
      });
      if (this.reelInstance && mode !== "video") {
        setTimeout(() => {
          this.reelInstance.resize();
        }, 60);
      }
    },

    play() {
      if (this.isPlaying) return;
      this.isPlaying = true;
      this.updateControlsUI();
      const realVid = document.getElementById("geminiRealVideoPlayer");
      if (this.viewMode === "video" && realVid) {
        realVid.play().catch(() => {});
      } else {
        this.speakNarration(this.scenes[this.currentScene].caption);
        this.startTimer();
        if (this.reelInstance) {
          this.reelInstance.play();
        } else {
          this.init3DReel();
          if (this.reelInstance) this.reelInstance.play();
        }
      }
    },

    pause() {
      this.isPlaying = false;
      this.clearTimer();
      this.stopNarration();
      this.updateControlsUI();
      const realVid = document.getElementById("geminiRealVideoPlayer");
      if (realVid) realVid.pause();
      if (this.reelInstance) {
        this.reelInstance.pause();
      }
    },

    togglePlay() {
      if (this.isPlaying) {
        this.pause();
      } else {
        this.play();
      }
    },

    toggleVoiceover() {
      this.voiceNarrationEnabled = !this.voiceNarrationEnabled;
      const ttsBtn = document.getElementById('demoVideoTtsBtn');
      const sideBtn = document.getElementById('demoVideoVoiceSideBtn');
      const text = this.voiceNarrationEnabled ? '🔊 Voice: ON' : '🔇 Voice: OFF';
      const fullText = this.voiceNarrationEnabled ? '🔊 Voiceover: ON' : '🔇 Voiceover: OFF';

      if (ttsBtn) {
        ttsBtn.textContent = fullText;
        ttsBtn.style.background = this.voiceNarrationEnabled ? 'rgba(16, 185, 129, 0.2)' : '';
        ttsBtn.style.borderColor = this.voiceNarrationEnabled ? '#10b981' : '';
        ttsBtn.style.color = this.voiceNarrationEnabled ? '#34d399' : '';
      }
      if (sideBtn) {
        sideBtn.textContent = text;
        sideBtn.style.background = this.voiceNarrationEnabled ? 'rgba(16, 185, 129, 0.2)' : '';
        sideBtn.style.borderColor = this.voiceNarrationEnabled ? '#10b981' : '';
        sideBtn.style.color = this.voiceNarrationEnabled ? '#34d399' : '';
      }

      if (this.voiceNarrationEnabled) {
        this.speakNarration(this.scenes[this.currentScene].caption);
      } else {
        this.stopNarration();
      }
    },

    speakNarration(text) {
      if (!this.voiceNarrationEnabled || !('speechSynthesis' in window)) return;
      try {
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(text);
        utt.rate = this.playbackSpeed || 1.0;
        utt.pitch = 1.0;
        const voices = window.speechSynthesis.getVoices();
        const enVoice = voices.find(v => v.lang && v.lang.startsWith('en'));
        if (enVoice) utt.voice = enVoice;
        window.speechSynthesis.speak(utt);
      } catch (e) {
        console.warn("Speech narration:", e);
      }
    },

    stopNarration() {
      if ('speechSynthesis' in window) {
        try { window.speechSynthesis.cancel(); } catch (e) {}
      }
    },

    next() {
      this.clearTimer();
      this.stopNarration();
      this.currentTime = 0;
      this.currentScene = (this.currentScene + 1) % this.scenes.length;
      this.render();
      if (this.isPlaying) {
        this.speakNarration(this.scenes[this.currentScene].caption);
        this.startTimer();
      }
    },

    prev() {
      this.clearTimer();
      this.stopNarration();
      this.currentTime = 0;
      this.currentScene = (this.currentScene - 1 + this.scenes.length) % this.scenes.length;
      this.render();
      if (this.isPlaying) {
        this.speakNarration(this.scenes[this.currentScene].caption);
        this.startTimer();
      }
    },

    goToScene(index) {
      this.clearTimer();
      this.stopNarration();
      this.currentTime = 0;
      this.currentScene = Math.max(0, Math.min(index, this.scenes.length - 1));
      this.render();

      const realVid = document.getElementById("geminiRealVideoPlayer");
      if (this.viewMode === "video" && realVid) {
        const offsets = [0, 2.0, 4.0, 6.0, 8.0];
        realVid.currentTime = offsets[this.currentScene] || 0;
        if (this.isPlaying) realVid.play().catch(() => {});
      }

      if (this.isPlaying || this.voiceNarrationEnabled) {
        this.speakNarration(this.scenes[this.currentScene].caption);
      }
      if (this.isPlaying && this.viewMode !== "video") this.startTimer();
    },

    setSpeed(speed) {
      this.playbackSpeed = speed;
      this.clearTimer();
      const realVid = document.getElementById("geminiRealVideoPlayer");
      if (realVid) realVid.playbackRate = speed;

      if (this.isPlaying && this.viewMode !== "video") {
        this.speakNarration(this.scenes[this.currentScene].caption);
        this.startTimer();
      }
      this.updateControlsUI();
      const speedPill = document.getElementById("videoSpeedDisplay");
      if (speedPill) speedPill.textContent = speed + "x";
    },

    seek(e) {
      const container = document.getElementById('videoProgressContainer');
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const ratio = Math.max(0, Math.min(1, clickX / rect.width));

      const realVid = document.getElementById("geminiRealVideoPlayer");
      if (this.viewMode === "video" && realVid && realVid.duration) {
        realVid.currentTime = ratio * realVid.duration;
      } else {
        const current = this.scenes[this.currentScene];
        this.currentTime = ratio * current.duration;
        this.updateTimelineUI();
        this.sync3DReel();
      }
    },

    toggleCaptions() {
      this.captionsVisible = !this.captionsVisible;
      const ccEl = document.getElementById('videoCaptionsOverlay');
      if (ccEl) {
        ccEl.style.display = this.captionsVisible ? 'block' : 'none';
      }
      const ccBtn = document.getElementById('btnToggleCC');
      if (ccBtn) {
        ccBtn.classList.toggle('active-view-mode', this.captionsVisible);
      }
    },

    toggleFullscreen() {
      const card = document.getElementById('demoVideoPlayerCard');
      if (!card) return;
      if (!document.fullscreenElement) {
        if (card.requestFullscreen) card.requestFullscreen();
        else if (card.webkitRequestFullscreen) card.webkitRequestFullscreen();
      } else {
        if (document.exitFullscreen) document.exitFullscreen();
      }
    },

    startTimer() {
      this.clearTimer();
      const tickMs = 100;
      this.progressInterval = setInterval(() => {
        const current = this.scenes[this.currentScene];
        this.currentTime += (tickMs / 1000) * this.playbackSpeed;
        this.updateTimelineUI();

        if (this.currentTime >= current.duration) {
          this.currentTime = 0;
          this.next();
        }
      }, tickMs);
    },

    clearTimer() {
      if (this.progressInterval) {
        clearInterval(this.progressInterval);
        this.progressInterval = null;
      }
      if (this.timer) {
        clearTimeout(this.timer);
        this.timer = null;
      }
    },

    updateTimelineUI() {
      const fill = document.getElementById('videoProgressFill');
      const timecode = document.getElementById('videoTimecodeText');
      const current = this.scenes[this.currentScene];
      if (!current) return;

      const pct = Math.min(100, (this.currentTime / current.duration) * 100);
      if (fill) fill.style.width = pct.toFixed(1) + '%';

      if (timecode) {
        const curSec = Math.floor(this.currentTime);
        const durSec = Math.floor(current.duration);
        const curFmt = (curSec < 10 ? '0' : '') + curSec;
        const durFmt = (durSec < 10 ? '0' : '') + durSec;
        timecode.innerHTML = `<strong>00:${curFmt}</strong> / 00:${durFmt}`;
      }
    },

    updateControlsUI() {
      const playBtn = document.getElementById('demoVideoPlayBtn');
      if (playBtn) {
        playBtn.innerHTML = this.isPlaying ? '⏸ Pause' : '▶ Play';
        playBtn.setAttribute('aria-label', this.isPlaying ? 'Pause Animated Video' : 'Play Animated Video');
      }
      const centerPlay = document.getElementById('videoCenterPlayOverlay');
      if (centerPlay) {
        centerPlay.style.display = this.isPlaying ? 'none' : 'flex';
      }
      const soundbars = document.getElementById('geminiSoundbars');
      if (soundbars) {
        soundbars.style.opacity = this.isPlaying ? '1' : '0.4';
      }
    },

    render() {
      const container = document.getElementById('demoVideoPlayerContainer');
      if (!container) return;

      const sc = this.scenes[this.currentScene];
      const total = this.scenes.length;
      const xai = sc.explanation || {
        confidence: "99.0%",
        aiRationale: "Real-time edge sensor processing.",
        sensorFusion: "Multimodal edge ingestion.",
        safetyOutput: "Automated verified action."
      };

      const existingCard = document.getElementById('demoVideoPlayerCard');
      if (existingCard) {
        // Fast in-place DOM update so 3D WebGL Canvas never loses context or reloads!
        const phasePill = document.getElementById('videoPhasePill');
        if (phasePill) phasePill.textContent = sc.tag;

        const phaseCounter = document.getElementById('videoPhaseCounter');
        if (phaseCounter) phaseCounter.textContent = `Phase ${this.currentScene + 1} of ${total}`;

        const roomTitle = document.getElementById('gemini3dRoomTitle');
        if (roomTitle) roomTitle.textContent = sc.roomTitle;

        const telemetrySub = document.getElementById('gemini3dTelemetrySub');
        if (telemetrySub) telemetrySub.textContent = sc.roomTelemetry;

        const statusPill = document.getElementById('gemini3dStatusPill');
        if (statusPill) statusPill.textContent = sc.statusPill;

        const speechText = document.getElementById('geminiSpeechText');
        if (speechText) speechText.textContent = sc.caption;

        const lowerTopic = document.getElementById('tvLowerTopic');
        if (lowerTopic) lowerTopic.textContent = `Phase 0${this.currentScene + 1}: ${sc.title}`;

        const captionsOverlay = document.getElementById('videoCaptionsOverlay');
        if (captionsOverlay) captionsOverlay.textContent = sc.caption;

        const sceneTitle = document.getElementById('videoSceneTitle');
        if (sceneTitle) sceneTitle.textContent = sc.title;

        const sceneSub = document.getElementById('videoSceneSub');
        if (sceneSub) sceneSub.textContent = sc.sub;

        const xaiConf = document.getElementById('xaiConfidence');
        if (xaiConf) xaiConf.innerHTML = `Confidence Score: <strong>${escapeHtml(xai.confidence)}</strong>`;

        const xaiRat = document.getElementById('xaiAiRationale');
        if (xaiRat) xaiRat.textContent = xai.aiRationale;

        const xaiSens = document.getElementById('xaiSensorFusion');
        if (xaiSens) xaiSens.textContent = xai.sensorFusion;

        const xaiSafe = document.getElementById('xaiSafetyOutput');
        if (xaiSafe) xaiSafe.textContent = xai.safetyOutput;

        const tryBtn = document.getElementById('btnTryFeatureLive');
        if (tryBtn) tryBtn.setAttribute('onclick', `window.switchTab('${sc.tabTarget}')`);

        // Update chapter dots
        const chapterBtns = document.querySelectorAll('.chapter-dot-btn');
        chapterBtns.forEach((btn, idx) => {
          btn.classList.toggle('active-chapter', idx === this.currentScene);
        });

        this.updateControlsUI();
        this.updateTimelineUI();
        this.sync3DReel();
        return;
      }

      // Initial Mount: Render Full Video Stage HTML including Three.js Canvas
      container.innerHTML = `
        <div class="video-player-card" id="demoVideoPlayerCard">
          <!-- Top Stream Status Bar with Gemini Branding & View Toggles -->
          <div class="video-top-bar" style="flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <span class="gemini-brand-pill">✨ Powered by Gemini Multimodal AI</span>
              <span class="pill-badge pill-blue" id="videoPhasePill">${escapeHtml(sc.tag)}</span>
            </div>

            <!-- 3D / Human Presenter & Video View Switcher -->
            <div class="gemini-view-toggles" role="group" aria-label="Explainer Presentation Mode">
              <button class="view-mode-btn ${this.viewMode === 'video' ? 'active-view-mode' : ''}" data-mode="video" onclick="window.demoVideoController.setViewMode('video')" title="Play Official Gemini AI Generated Video">
                🎬 Official Video
              </button>
              <button class="view-mode-btn ${this.viewMode === 'split' ? 'active-view-mode' : ''}" data-mode="split" onclick="window.demoVideoController.setViewMode('split')" title="Side-by-side 3D Simulation and Human AI Presenter">
                ✨ Split Studio
              </button>
              <button class="view-mode-btn ${this.viewMode === 'human' ? 'active-view-mode' : ''}" data-mode="human" onclick="window.demoVideoController.setViewMode('human')" title="Focused Human AI Presenter View">
                👤 Presenter
              </button>
              <button class="view-mode-btn ${this.viewMode === '3d' ? 'active-view-mode' : ''}" data-mode="3d" onclick="window.demoVideoController.setViewMode('3d')" title="Focused 3D Digital Twin View">
                🌐 3D Twin
              </button>
            </div>              </button>
            </div>

            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-weight: 700; color: #e2e8f0; font-size: 0.78rem;" id="videoPhaseCounter">Phase ${this.currentScene + 1} of ${total}</span>
              <div class="video-speed-pill">
                <span>Speed: <strong id="videoSpeedDisplay">${this.playbackSpeed}x</strong></span>
              </div>
            </div>
          </div>

          <!-- Gemini 3D & Human Explainer Main Video Viewport -->
          <div class="gemini-video-viewport-wrapper">
            
            <div class="gemini-video-screen" id="geminiVideoScreen" onclick="if(event.target.closest('.view-mode-btn, button, input')) return; window.demoVideoController.togglePlay();" title="Click to Play / Pause Video">
              
              <!-- Subtle CRT/Film Scanlines Layer -->
              <div class="video-cinematic-scanlines" aria-hidden="true"></div>

              <!-- Top Left Watermark Badge -->
              <div class="video-broadcast-watermark">
                <span class="rec-pulse-dot"></span>
                <span>🔴 LIVE GEMINI AI EXPLAINER &bull; HD REEL</span>
              </div>

              <!-- Center Big Play Button Overlay (visible when paused) -->
              <div class="video-center-play-overlay" id="videoCenterPlayOverlay" style="display: ${this.isPlaying ? 'none' : 'flex'};">
                <div class="video-center-play-btn" aria-label="Play Video">▶</div>
              </div>

              <!-- Real Gemini-Generated Video Reel Pane -->
              <div class="gemini-video-file-pane" id="geminiVideoFilePane" style="display: ${this.viewMode === 'video' ? 'flex' : 'none'}; width: 100%; min-height: 420px; background: radial-gradient(circle at center, #0f172a 0%, #020617 100%); align-items: center; justify-content: center; position: relative; border-radius: 8px; overflow: hidden;">
                <video id="geminiRealVideoPlayer" src="/static/gemini_generated_video.mp4" playsinline preload="auto" poster="/static/gemini_video_poster.jpg" style="max-width: 100%; max-height: 460px; width: 100%; object-fit: contain; display: block; border-radius: 8px; box-shadow: 0 12px 36px rgba(0,0,0,0.7);"></video>
                <div style="position: absolute; bottom: 12px; left: 16px; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(8px); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 9999px; padding: 4px 12px; display: flex; align-items: center; gap: 8px; font-size: 0.72rem; color: #e2e8f0; pointer-events: none;">
                  <span style="width: 8px; height: 8px; border-radius: 50%; background: #38bdf8; box-shadow: 0 0 8px #38bdf8;"></span>
                  <span>Official Gemini AI Generated Demo Video &bull; 720p HD</span>
                </div>
              </div>

              <!-- The Split Stage: 3D Simulation & Human Presenter -->
              <div class="gemini-stage-container ${this.viewMode === 'human' ? 'view-human-only' : (this.viewMode === '3d' ? 'view-3d-only' : '')}" id="geminiStageContainer" style="display: ${this.viewMode === 'video' ? 'none' : 'grid'}; margin: 0; border: none; min-height: 420px; border-radius: 0;">
                
                <!-- Left Pane: True 3D Three.js Animated WebGL Operational Canvas -->
                <div class="gemini-simulation-pane">
                  <div class="gemini-3d-canvas-wrap" id="gemini3dCanvasWrap">
                    <canvas id="geminiSplit3dCanvas" class="gemini-split-3d-canvas"></canvas>
                    
                    <div class="gemini-3d-hud-overlay" id="gemini3dHudOverlay">
                      <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="rec-pulse-dot" style="background: #38bdf8; box-shadow: 0 0 8px #38bdf8;"></span>
                        <div>
                          <strong style="color: #38bdf8;" id="gemini3dRoomTitle">${escapeHtml(sc.roomTitle)}</strong>
                          <div style="font-size: 0.7rem; color: #94a3b8;" id="gemini3dTelemetrySub">
                            ${escapeHtml(sc.roomTelemetry)}
                          </div>
                        </div>
                      </div>
                      <span class="pill-badge pill-green" id="gemini3dStatusPill" style="font-size: 0.65rem;">${escapeHtml(sc.statusPill)}</span>
                    </div>
                  </div>
                </div>

                <!-- Right Pane: Dr. Maya (Gemini Healthcare AI Presenter) -->
                <div class="gemini-presenter-pane">
                  <div>
                    <div class="gemini-presenter-header">
                      <div class="gemini-avatar-frame">
                        <img src="/static/gemini_presenter.jpg" alt="Dr. Maya - Gemini Healthcare AI Doctor / Presenter" loading="eager" />
                        <span class="gemini-live-pulse-dot" title="Gemini Multimodal Presenter Online"></span>
                      </div>
                      <div class="gemini-presenter-identity">
                        <h4>
                          <span>Dr. Maya Thorne</span>
                          <span style="font-size: 0.7rem; color: #38bdf8; font-weight: 700;">MD</span>
                        </h4>
                        <div class="presenter-title">Gemini Healthcare AI Explainer</div>
                        <div style="font-size: 0.68rem; color: #6ee7b7; font-weight: 700; margin-top: 3px;">
                          ● Clinical Presenter &bull; Active
                        </div>
                      </div>
                    </div>

                    <!-- Speech Narration Bubble -->
                    <div class="gemini-speech-bubble">
                      <div class="gemini-speech-meta">
                        <span>✨ GEMINI CLINICAL EXPLANATION</span>
                        <div class="gemini-soundbars" id="geminiSoundbars" aria-hidden="true" style="opacity: ${this.isPlaying ? '1' : '0.4'};">
                          <div class="gemini-bar"></div>
                          <div class="gemini-bar"></div>
                          <div class="gemini-bar"></div>
                          <div class="gemini-bar"></div>
                        </div>
                      </div>
                      <div id="geminiSpeechText">${escapeHtml(sc.caption)}</div>
                    </div>
                  </div>

                  <!-- Action Bar in Presenter Card -->
                  <div style="margin-top: 14px; display: flex; gap: 8px; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                    <button class="btn-demo-primary" id="btnTryFeatureLive" onclick="window.switchTab('${sc.tabTarget}')" style="white-space: nowrap; font-size: 0.76rem; padding: 6px 12px;">
                      🚀 Try Feature Live &rarr;
                    </button>
                    <button class="btn-demo-secondary" id="demoVideoVoiceSideBtn" onclick="window.demoVideoController.toggleVoiceover()" style="white-space: nowrap; font-size: 0.76rem; padding: 6px 12px; ${this.voiceNarrationEnabled ? 'background: rgba(16, 185, 129, 0.2); border-color: #10b981; color: #34d399;' : ''}">
                      ${this.voiceNarrationEnabled ? '🔊 Voice: ON' : '🔇 Voice: OFF'}
                    </button>
                  </div>
                </div>

              </div>

              <!-- TV Style Lower Third Banner -->
              <div class="video-tv-lower-third">
                <div class="tv-lower-name">
                  <span>DR. MAYA THORNE, MD</span>
                  <span style="color: #94a3b8; font-size: 0.68rem;">&bull; GEMINI CLINICAL AI</span>
                </div>
                <div class="tv-lower-topic" id="tvLowerTopic">Phase 0${this.currentScene + 1}: ${escapeHtml(sc.title)}</div>
              </div>

              <!-- Floating Subtitles / Closed Captions (CC) Overlay -->
              <div class="video-captions-overlay" id="videoCaptionsOverlay" style="display: ${this.captionsVisible ? 'block' : 'none'};">
                ${escapeHtml(sc.caption)}
              </div>

              <!-- Video Scrubber Bar & Controls Overlay -->
              <div class="video-scrubber-track-bar">
                <div class="video-progress-container" id="videoProgressContainer" onclick="window.demoVideoController.seek(event)" title="Click to seek">
                  <div class="video-progress-fill" id="videoProgressFill" style="width: 0%;">
                    <div class="video-progress-thumb"></div>
                  </div>
                </div>

                <div class="video-bar-bottom-row">
                  <div style="display: flex; align-items: center; gap: 12px;">
                    <span class="video-timecode" id="videoTimecodeText"><strong>00:00</strong> / 00:0${sc.duration}</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <button class="view-mode-btn ${this.captionsVisible ? 'active-view-mode' : ''}" id="btnToggleCC" onclick="window.demoVideoController.toggleCaptions()" title="Toggle Closed Captions (CC)">
                      CC
                    </button>
                    <button class="view-mode-btn" onclick="window.demoVideoController.toggleFullscreen()" title="Fullscreen Video Mode">
                      ⛶ Fullscreen
                    </button>
                  </div>
                </div>
              </div>

            </div>

          </div>

          <!-- Video Title & XAI Breakdown -->
          <div class="video-meta-section">
            <div class="video-title-row">
              <div>
                <h3 class="video-scene-title" id="videoSceneTitle">${escapeHtml(sc.title)}</h3>
                <div class="video-scene-sub" id="videoSceneSub">${escapeHtml(sc.sub)}</div>
              </div>
            </div>

            <!-- Explainable AI Decision Breakdown Panel -->
            <div class="video-xai-panel">
              <div class="video-xai-header">
                <span class="xai-chip">🧠 EXPLAINABLE AI (XAI) DECISION BREAKDOWN &bull; GEMINI 1.5 PRO REASONING</span>
                <span class="xai-confidence" id="xaiConfidence">Confidence Score: <strong>${escapeHtml(xai.confidence)}</strong></span>
              </div>
              <div class="video-xai-grid">
                <div class="xai-col">
                  <small>🔍 AI Decision Rationale</small>
                  <div id="xaiAiRationale">${escapeHtml(xai.aiRationale)}</div>
                </div>
                <div class="xai-col">
                  <small>📡 Sensor Fusion Inputs</small>
                  <div id="xaiSensorFusion">${escapeHtml(xai.sensorFusion)}</div>
                </div>
                <div class="xai-col">
                  <small>⚡ Actuation &amp; Safety Output</small>
                  <div id="xaiSafetyOutput">${escapeHtml(xai.safetyOutput)}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Player Controls Bar -->
          <div class="video-controls-bar">
            <!-- Scrubber Track & Chapter Dots -->
            <div class="video-chapters-track">
              ${this.scenes.map((s, idx) => `
                <button class="chapter-dot-btn ${idx === this.currentScene ? 'active-chapter' : ''}" onclick="window.demoVideoController.goToScene(${idx})" title="Go to ${escapeHtml(s.title)}">
                  <span class="dot-num">0${idx + 1}</span>
                  <span class="dot-label">${escapeHtml(s.id.toUpperCase())}</span>
                </button>
              `).join('')}
            </div>

            <!-- Playback Action Buttons -->
            <div class="video-actions-row">
              <div class="btn-group-left">
                <button class="btn-demo-secondary" onclick="window.demoVideoController.prev()" title="Previous Phase">⏮ Prev</button>
                <button class="btn-demo-primary" id="demoVideoPlayBtn" onclick="window.demoVideoController.togglePlay()">
                  ${this.isPlaying ? '⏸ Pause' : '▶ Play'}
                </button>
                <button class="btn-demo-secondary" onclick="window.demoVideoController.next()" title="Next Phase">Next ⏭</button>
                <button class="btn-demo-secondary" onclick="window.demoVideoController.goToScene(0); window.demoVideoController.play();" title="Restart Video">⟲ Restart</button>
                <button class="btn-demo-secondary" id="demoVideoTtsBtn" onclick="window.demoVideoController.toggleVoiceover()" title="Toggle Real-Time Voiceover Narration" style="${this.voiceNarrationEnabled ? 'background: rgba(16, 185, 129, 0.2); border-color: #10b981; color: #34d399;' : ''}">
                  ${this.voiceNarrationEnabled ? '🔊 Voiceover: ON' : '🔇 Voiceover: OFF'}
                </button>
              </div>

              <div class="btn-group-right">
                <span style="font-size: 0.78rem; color: #94a3b8; margin-right: 6px;">Speed:</span>
                <button class="speed-toggle-btn ${this.playbackSpeed === 1 ? 'active-speed' : ''}" onclick="window.demoVideoController.setSpeed(1)">1x</button>
                <button class="speed-toggle-btn ${this.playbackSpeed === 1.5 ? 'active-speed' : ''}" onclick="window.demoVideoController.setSpeed(1.5)">1.5x</button>
                <button class="speed-toggle-btn ${this.playbackSpeed === 2 ? 'active-speed' : ''}" onclick="window.demoVideoController.setSpeed(2)">2x</button>
              </div>
            </div>
          </div>
        </div>
      `;

      this.updateControlsUI();
      this.updateTimelineUI();

      const realVid = document.getElementById("geminiRealVideoPlayer");
      if (realVid && !realVid._hasNiraListeners) {
        realVid._hasNiraListeners = true;
        realVid.addEventListener("timeupdate", () => {
          if (this.viewMode === "video" && realVid.duration) {
            const fill = document.getElementById('videoProgressFill');
            const timecode = document.getElementById('videoTimecodeText');
            const pct = (realVid.currentTime / realVid.duration) * 100;
            if (fill) fill.style.width = pct.toFixed(1) + '%';
            if (timecode) {
              const curSec = Math.floor(realVid.currentTime);
              const durSec = Math.floor(realVid.duration);
              timecode.innerHTML = `<strong>00:${curSec < 10 ? '0' : ''}${curSec}</strong> / 00:${durSec < 10 ? '0' : ''}${durSec}`;
            }
          }
        });
        realVid.addEventListener("play", () => {
          this.isPlaying = true;
          this.updateControlsUI();
        });
        realVid.addEventListener("pause", () => {
          this.isPlaying = false;
          this.updateControlsUI();
        });
        realVid.addEventListener("ended", () => {
          this.isPlaying = false;
          this.updateControlsUI();
        });
      }

      setTimeout(() => {
        this.init3DReel();
      }, 50);
    }
  };

  // Expose on window for inline handlers
  window.demoVideoController = DemoVideoController;

  // Auto-initialize when DOM is ready
  function initAllControllers() {
    VoiceAssistantController.init();
    DailyCheckinController.init();
    FallSimulationController.init();
    EmergencyAlertController.init();
    LocationMapController.init();
    NotificationCenterController.init();
    IncidentHistoryController.init();
    DemoVideoController.init();
    demoStore.updateHeaderBadges();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllControllers);
  } else {
    initAllControllers();
  }

})();
