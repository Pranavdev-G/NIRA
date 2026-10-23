/**
 * NIRA — Operator Simulation & Command Console Engine
 * Person 2: Demo Experience & Live Simulation Lead
 * 
 * Implements:
 * 1. 14-Step Deterministic Presentation Flow (0 to 13)
 * 2. 6 Predefined End-to-End Scenarios with 7-step progression:
 *    EVENT -> RISK -> DECISION -> INCIDENT -> NOTIFICATION -> ESCALATION -> RESOLUTION
 * 3. 13 Sensor Simulation Actions (Calling authoritative backend /api/v1/demo/simulate/{action})
 * 4. Real-time Risk Intelligence & Explainability Breakdown
 * 5. Sensor Health & Redundancy HUD (All labeled SIMULATED)
 * 6. Environmental Context Risk Formula
 * 7. Medication Tracking & Caregiver Alerts
 * 8. Ambulance CAD & Smart Lock Authoritative Controls
 */

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // 14-Step Deterministic Presentation Flow
  // ---------------------------------------------------------------------------
  const DEMO_FLOW_STEPS = [
    {
      step: 0,
      title: "Demo Portal Login & Role Setup",
      subtitle: "Secure role-aware authentication portal",
      action: "login",
      targetTab: "overview",
      description: "Operator logs in via David Vance (Admin), Eleanor Vance (Resident Home View), or Medic 14 (Boston EMS Command). Demonstrates role-aware permissions and session persistence."
    },
    {
      step: 1,
      title: "Normal Ambient Monitoring Baseline",
      subtitle: "Passive non-intrusive elder monitoring",
      action: "normal",
      targetTab: "overview",
      description: "NIRA maintains passive observation across all residence zones. Apple Watch vitals normal (72 BPM), 60GHz mmWave radar active, dry bathroom substrate."
    },
    {
      step: 2,
      title: "Resident Physiological Baseline Verification",
      subtitle: "Resting vitals and diurnal sleep cycle check",
      action: "baseline",
      targetTab: "overview",
      description: "Resident resting heart rate confirmed at 72 BPM. Sleep routine verified. Morning Lisinopril 10mg verified taken. 5 of 5 simulated IoT sensor nodes online."
    },
    {
      step: 3,
      title: "High-Impact Fall Incident Triggered",
      subtitle: "Multimodal sensor detection in bathroom",
      action: "fall",
      targetTab: "falldetection",
      description: "Optical pose skeleton and 3-axis IMU detect rapid descent (2.85 m/s) onto bathroom floor. Torso angle collapses to 12°. Fall confidence: 94%."
    },
    {
      step: 4,
      title: "Aegis Risk Engine Evaluates Situation",
      subtitle: "Multimodal context fusion & risk calculation",
      action: "risk_eval",
      targetTab: "overview",
      description: "Aegis engine fuses optical fall, immobility duration, nocturnal schedule (+4.2h deviation), and wet tile substrate. Risk level surges to CRITICAL (score: 94%)."
    },
    {
      step: 5,
      title: "Ambient Voice Wellness Check Initiated",
      subtitle: "Amazon Echo Show 15 conversational triage",
      action: "wellness_check",
      targetTab: "voiceassistant",
      description: "Echo Show 15 halo illuminates blue. NIRA issues conversational check: 'Eleanor, this is NIRA. I noticed a fall in the bathroom. Are you okay?' 20-second window starts."
    },
    {
      step: 6,
      title: "Resident Unresponsive (Acoustic Timeout)",
      subtitle: "Silence detection confirms silent emergency",
      action: "voice_silence",
      targetTab: "voiceassistant",
      description: "20-second acoustic response window expires without verbal reply. State machine classifies event as NO RESPONSE / Presumed Unconscious. Auto-escalation triggered."
    },
    {
      step: 7,
      title: "Family Caregiver Multi-Channel Priority Alert",
      subtitle: "David Vance notified across 3 channels",
      action: "caregiver_alert",
      targetTab: "overview",
      description: "Caregiver David Vance alerted via Echo Show 15 Drop-In Call (two-way audio), Priority Push Notification, and Automated SMS with temporary smart door PIN (8492)."
    },
    {
      step: 8,
      title: "Emergency CAD Escalation Engaged",
      subtitle: "Automated 911 dispatch triage protocol",
      action: "escalate",
      targetTab: "dispatch",
      description: "System automatically escalates incident to Boston EMS 911 CAD. Incident ID INC-20261019-88192 assigned priority CODE: RED-911 (Priority 1 Trauma)."
    },
    {
      step: 9,
      title: "911 CAD Emergency Packet Transmitted",
      subtitle: "Pre-arrival clinical intelligence package",
      action: "packet",
      targetTab: "dispatch",
      description: "Electronic CAD packet EPK-84920 transmitted to EMS dispatch. Includes exact bathroom room coordinates, acute tachycardia vitals (138 BPM), and allergy warning (Penicillin)."
    },
    {
      step: 10,
      title: "Ambulance Dispatched (Medic-42 En Route)",
      subtitle: "Mobile Data Terminal tracking & ETA",
      action: "ambulance_dispatch",
      targetTab: "locationmap",
      description: "Boston EMS Medic-42 assigned and dispatched. Real-time GPS tracks unit en route along Beacon St (Distance: 1,180 m, ETA: 3 min 40 s)."
    },
    {
      step: 11,
      title: "Smart Lock Automatically Unlocked",
      subtitle: "Perimeter access granted via Matter protocol",
      action: "smart_lock_unlock",
      targetTab: "overview",
      description: "Front door smart deadbolt autonomously unlocks via encrypted Matter protocol. Explanation: 'Emergency responder access enabled (PIN: 8492)'. Pathway lighting illuminated 100%."
    },
    {
      step: 12,
      title: "Ambulance Arrival & Geofence Verification",
      subtitle: "Authorized responders arrive at residence curb",
      action: "ambulance_arrive",
      targetTab: "locationmap",
      description: "Medic-42 crosses 30m geofence perimeter. Badge BEMS-8821 verified cryptographically. Arrival status confirmed on Mobile Data Terminal."
    },
    {
      step: 13,
      title: "First Responder Care & Incident Resolution",
      subtitle: "Care delivered and system restored to baseline",
      action: "resolution",
      targetTab: "overview",
      description: "Paramedics stabilize Eleanor. Incident marked as RESOLVED in immutable database. Door relocked, telemetry restored to NORMAL baseline."
    }
  ];

  // ---------------------------------------------------------------------------
  // Predefined End-to-End Scenarios
  // ---------------------------------------------------------------------------
  const PREDEFINED_SCENARIOS = {
    false_alarm: {
      name: "Scenario 1: False Alarm Recovery",
      description: "Living room stumble/thud -> Resident confirms 'I'm okay' -> De-escalates to RESOLVED",
      backendKey: "false_alarm",
      progressionSteps: [
        "Impact Event Detected in Living Room",
        "Risk Evaluated as ELEVATED (48%)",
        "Decision: Initiate Echo Show Wellness Check",
        "Incident Flagged for Verification",
        "Echo Prompt Delivered: 'Are you okay?'",
        "Resident Responds: 'I am okay, just dropped my book'",
        "Resolution: State Restored to NORMAL Baseline"
      ]
    },
    responsive_emergency: {
      name: "Scenario 2: Responsive Emergency",
      description: "Fall detected -> Inactivity -> Resident cries 'Help me' -> Caregiver Priority Escalation",
      backendKey: "responsive_emergency",
      progressionSteps: [
        "High-Impact Fall Detected in Kitchen",
        "Risk Evaluated as HIGH (78%)",
        "Decision: Initiate Echo Show Wellness Check",
        "Incident Created: INC-RESPONSIVE",
        "Echo Prompt Delivered: 'Are you okay?'",
        "Resident Responds: 'Help me, I fell down!'",
        "Escalation: David Vance Alerted via Echo Drop-In & SMS"
      ]
    },
    silent_emergency: {
      name: "Scenario 3: Silent Emergency",
      description: "Nocturnal bathroom fall on wet tile -> Tachycardia -> Silence (Timeout) -> 911 CAD Dispatched",
      backendKey: "silent_emergency",
      progressionSteps: [
        "Bathroom Fall Detected + Wet Tile Substrate",
        "Risk Evaluated as CRITICAL (94%)",
        "Decision: Urgent Ambient Wellness Check (20s Window)",
        "Incident Created: Active Code Red",
        "Echo Prompt Window Times Out with Zero Speech",
        "Escalation: Boston EMS 911 CAD Dispatched",
        "Access Granted: Front Door Smart Lock UNLOCKED (PIN: 8492)"
      ]
    },
    worsening_condition: {
      name: "Scenario 4: Worsening Condition",
      description: "Minor slip in bedroom -> Increasing immobility -> Tachycardia surge (142 BPM) -> Dynamic Auto-Escalation",
      backendKey: "worsening_condition",
      progressionSteps: [
        "Initial Minor Slip Detected in Bedroom",
        "Initial Risk Evaluated as MODERATE (38%)",
        "Decision: Observation Window Started",
        "Immobility Detected (Radar: Motionless 240s)",
        "Tachycardia Surge: Heart Rate 108 -> 142 BPM",
        "Risk Engine Auto-Escalates: MODERATE -> CRITICAL",
        "Emergency Action: 911 Dispatched & Door Unlocked"
      ]
    },
    environmental_hazard: {
      name: "Scenario 5: Environmental Hazard",
      description: "Standing water leak in dim bathroom -> Pre-fall hazard alert -> Proactive safety intervention",
      backendKey: "environmental_hazard",
      progressionSteps: [
        "Moisture Sensor Detects Standing Water in Bathroom",
        "Context Risk Evaluated: Dark Lux (8 Lux) + Wet Tile",
        "Decision: Pre-Fall Hazard Warning Activated",
        "Resident Radar Tracks Approach to Bathroom",
        "Notification: Echo Show Informs Resident of Hazard",
        "Intervention: Automated Pathway Lighting Engaged",
        "Resolution: Resident Guided Safely Away from Hazard"
      ]
    },
    medication_miss: {
      name: "Scenario 6: Medication Miss",
      description: "Scheduled evening Lisinopril delayed 120min -> Echo reminder -> Caregiver notified -> Taken confirmed",
      backendKey: "medication_miss",
      progressionSteps: [
        "Medication Scheduled for 18:00 (Lisinopril 10mg)",
        "Pill Dispenser Sensor Checks Unopened at 18:30",
        "Decision: Deliver Gentle Echo Show Audio Reminder",
        "Dispenser Remains Unopened at 19:30 (120min Delay)",
        "Notification: Caregiver David Vance Alerted via SMS",
        "Caregiver Follows Up with Eleanor",
        "Resolution: Dose Taken (Marked in Adherence Log)"
      ]
    }
  };

  // ---------------------------------------------------------------------------
  // Operator Console Class Definition
  // ---------------------------------------------------------------------------
  class OperatorConsoleEngine {
    constructor() {
      this.currentFlowStep = 0;
      this.activeScenarioKey = null;
      this.activeProgressionStep = 0;
      this.progressionInterval = null;
      this.isExecutingAction = false;
      this.lastVoiceClassification = "SAFE";
    }

    init() {
      this.renderFlowStepUI();
      this.attachEventListeners();
      this.bindStoreUpdates();
      console.log("[OperatorConsole] Engine initialized with 14 presentation steps and 6 scenarios.");
    }

    bindStoreUpdates() {
      if (window.niraStore && typeof window.niraStore.subscribe === 'function') {
        window.niraStore.subscribe((state) => {
          this.updateRiskIntelligenceFromState(state);
        });
        if (window.niraStore.state) {
          this.updateRiskIntelligenceFromState(window.niraStore.state);
        }
      }
    }

    updateRiskIntelligenceFromState(state) {
      const inc = state?.incident || {};
      const riskLevel = inc.currentRiskLevel || "LOW";
      const scoreEl = document.getElementById("riskScoreVal");
      const tierEl = document.getElementById("riskScoreTier");
      const confEl = document.getElementById("riskConfidenceVal");
      const signalsEl = document.getElementById("riskSignalsList");
      const trendEl = document.getElementById("riskTrendHistory");

      let scoreStr = "8%";
      let tierStr = "LOW RISK";
      let color = "#34d399";
      let confStr = "98%";

      if (riskLevel === "CRITICAL" || inc.status === "ESCALATED_CAD") {
        scoreStr = "94%";
        tierStr = "CRITICAL RISK";
        color = "#f43f5e";
        confStr = Math.round((inc.confidence || 0.94) * 100) + "%";
      } else if (riskLevel === "HIGH" || inc.status === "ESCALATED_CAREGIVER") {
        scoreStr = "78%";
        tierStr = "HIGH RISK";
        color = "#fbbf24";
        confStr = Math.round((inc.confidence || 0.85) * 100) + "%";
      } else if (riskLevel === "MODERATE") {
        scoreStr = "48%";
        tierStr = "ELEVATED RISK";
        color = "#fbbf24";
        confStr = Math.round((inc.confidence || 0.75) * 100) + "%";
      }

      if (scoreEl) {
        scoreEl.textContent = scoreStr;
        scoreEl.style.color = color;
      }
      if (tierEl) {
        tierEl.textContent = tierStr;
        tierEl.style.color = color;
      }
      if (confEl) confEl.textContent = confStr;

      if (signalsEl && Array.isArray(inc.riskReasons) && inc.riskReasons.length > 0) {
        signalsEl.innerHTML = inc.riskReasons.map(r => `
          <div class="risk-factor-item">
            <span style="color: #fda4af;">🚨 ${escapeHtml(r)}</span>
            <span style="color: ${color}; font-weight: 800;">+Risk</span>
          </div>
        `).join("");
      }

      if (trendEl) {
        if (riskLevel === "CRITICAL" || riskLevel === "HIGH") {
          trendEl.textContent = "↑ RISING";
          trendEl.className = "trend-tag rising";
        } else {
          trendEl.textContent = "→ STABLE";
          trendEl.className = "trend-tag stable";
        }
      }
    }

    // -------------------------------------------------------------------------
    // Deterministic Flow Step Navigation (0 to 13)
    // -------------------------------------------------------------------------
    async nextFlowStep() {
      if (this.currentFlowStep < DEMO_FLOW_STEPS.length - 1) {
        await this.jumpToFlowStep(this.currentFlowStep + 1);
      } else {
        this.showToast("Reached final presentation step (13: Incident Resolution). Restarting flow...", "info");
        await this.jumpToFlowStep(0);
      }
    }

    async prevFlowStep() {
      if (this.currentFlowStep > 0) {
        await this.jumpToFlowStep(this.currentFlowStep - 1);
      }
    }

    async jumpToFlowStep(stepIndex) {
      if (stepIndex < 0 || stepIndex >= DEMO_FLOW_STEPS.length) return;
      this.currentFlowStep = stepIndex;
      const stepObj = DEMO_FLOW_STEPS[stepIndex];

      this.renderFlowStepUI();

      // Switch to the relevant dashboard view
      if (stepObj.targetTab && typeof window.switchTab === 'function') {
        window.switchTab(stepObj.targetTab);
      }

      // Execute authoritative backend event corresponding to this step
      await this.executeStepBackendAction(stepObj.action);
    }

    renderFlowStepUI() {
      const stepObj = DEMO_FLOW_STEPS[this.currentFlowStep];
      const counterEl = document.getElementById("flowStepCounter");
      const titleEl = document.getElementById("flowStepTitle");
      const subEl = document.getElementById("flowStepSubtitle");
      const descEl = document.getElementById("flowStepDesc");
      const prevBtn = document.getElementById("btnFlowPrev");
      const nextBtn = document.getElementById("btnFlowNext");
      const progressTrack = document.getElementById("flowProgressTrack");

      if (counterEl) counterEl.textContent = `Step ${stepObj.step} of 13`;
      if (titleEl) titleEl.textContent = stepObj.title;
      if (subEl) subEl.textContent = stepObj.subtitle;
      if (descEl) descEl.textContent = stepObj.description;

      if (prevBtn) prevBtn.disabled = (this.currentFlowStep === 0);
      if (nextBtn) {
        nextBtn.textContent = (this.currentFlowStep === DEMO_FLOW_STEPS.length - 1) ? "Restart Flow ↺" : "Next Step ▶";
      }

      // Update Stepper Dots / Bars
      if (progressTrack) {
        const dots = progressTrack.querySelectorAll(".flow-step-dot");
        dots.forEach((dot, idx) => {
          dot.classList.remove("active", "completed");
          if (idx === this.currentFlowStep) {
            dot.classList.add("active");
          } else if (idx < this.currentFlowStep) {
            dot.classList.add("completed");
          }
        });
      }
    }

    async executeStepBackendAction(actionName) {
      try {
        switch (actionName) {
          case "login":
            this.showToast("Presentation Step 0: Showing Demo Login & Role Architecture.", "info");
            break;
          case "normal":
          case "baseline":
            await this.triggerSimulationAction("normal");
            break;
          case "fall":
            await this.triggerSimulationAction("fall");
            break;
          case "risk_eval":
            // Sync risk intelligence
            if (window.niraStore) await window.niraStore.syncActiveIncidents();
            this.showToast("Risk Engine Evaluated: CRITICAL Risk (94%). Contributing: Fall + Immobility + Nighttime.", "warning");
            break;
          case "wellness_check":
            this.showToast("NIRA Echo Show 15 Voice Prompt Delivered: 'Eleanor, are you okay?'", "info");
            break;
          case "voice_silence":
            await this.triggerSimulationAction("voice_silence");
            break;
          case "caregiver_alert":
            if (window.niraStore) {
              window.niraStore.state.caregiver.status = "DISPATCHED";
              window.niraStore.notify();
            }
            this.showToast("Caregiver Alert: David Vance alerted via Echo Drop-In & Priority Push.", "warning");
            break;
          case "escalate":
          case "packet":
            this.showToast("911 CAD Dispatch Active: Emergency Packet EPK-84920 Transmitted.", "warning");
            break;
          case "ambulance_dispatch":
            if (typeof window.jumpToStage === 'function') {
              window.jumpToStage("DISPATCHED");
            }
            this.showToast("Ambulance Dispatched: Boston EMS Medic-42 En Route (ETA 4.2m).", "info");
            break;
          case "smart_lock_unlock":
            try {
              await fetch("/api/v1/security/lock/unlock", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  responder_badge: "BEMS-8821",
                  auth_token: "AUTH-TOKEN-BEMS-8821-EXP2026"
                })
              });
              if (typeof window.fetchSecurityStatus === 'function') {
                await window.fetchSecurityStatus();
              }
            } catch(e) {}
            this.showToast("Smart Deadbolt UNLOCKED: Authorized Responder Access Granted (PIN: 8492).", "success");
            break;
          case "ambulance_arrive":
            if (typeof window.simulateVerifiedArrival === 'function') {
              await window.simulateVerifiedArrival();
            }
            this.showToast("Medic-42 Arrival Verified at Residence Curb (30m Geofence Confirmed).", "success");
            break;
          case "resolution":
            await this.triggerSimulationAction("normal");
            this.showToast("Incident Resolved: Eleanor stabilized. System returned to baseline NORMAL.", "success");
            break;
        }
      } catch (err) {
        console.warn(`[OperatorConsole] Error executing step action '${actionName}':`, err);
      }
    }

    // -------------------------------------------------------------------------
    // 13 Core Sensor Simulation Actions (Calls /api/v1/demo/simulate/{action})
    // -------------------------------------------------------------------------
    async triggerSimulationAction(actionName) {
      if (this.isExecutingAction) return;
      this.isExecutingAction = true;

      const act = actionName.toLowerCase().replace("-", "_");
      this.showToast(`Broadcasting event: ${act.toUpperCase()} to Demo Event Pipeline...`, "info");

      try {
        const resp = await fetch(`/api/v1/demo/simulate/${encodeURIComponent(act)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });

        if (!resp.ok) {
          throw new Error(`Server returned HTTP ${resp.status}`);
        }

        const data = await resp.json();
        console.log(`[OperatorConsole] Simulation action '${act}' response:`, data);

        // Update local store state immediately
        if (window.niraStore && data.current_state) {
          window.niraStore.handleIncomingStreamMessage({
            type: "SIMULATION_UPDATE",
            state: data.current_state
          });
        }

        // Voice classification updates
        if (act === "voice_safe") {
          this.updateVoiceClassificationUI("SAFE", "Resident verbally confirmed: 'I am okay, false alarm.'");
        } else if (act === "voice_risk") {
          this.updateVoiceClassificationUI("RISK", "Resident reported: 'I feel dizzy and cannot stand.'");
        } else if (act === "voice_help") {
          this.updateVoiceClassificationUI("EMERGENCY", "Resident cried: 'Help me, I fell down!'");
        } else if (act === "voice_silence") {
          this.updateVoiceClassificationUI("NO RESPONSE", "20-second acoustic timeout expired without speech.");
        }

        // Sensor health HUD updates
        if (act === "device_disconnect") {
          const radarBadge = document.querySelector(".sensor-health-item:nth-child(4) .s-badge");
          if (radarBadge) {
            radarBadge.textContent = "SIMULATED OFFLINE";
            radarBadge.className = "s-badge s-sim-offline";
          }
        } else if (act === "environment_hazard") {
          const envBadge = document.querySelector(".sensor-health-item:nth-child(5) .s-badge");
          if (envBadge) {
            envBadge.textContent = "SIMULATED DEGRADED";
            envBadge.className = "s-badge s-sim-degraded";
          }
        } else if (act === "normal" || act === "recovery") {
          document.querySelectorAll(".sensor-health-item .s-badge").forEach(b => {
            b.textContent = "SIMULATED ONLINE";
            b.className = "s-badge s-sim-online";
          });
        }

        this.showToast(`✓ ${data.action} processed: Safety State = ${data.safety_state || 'UPDATED'}, Risk = ${data.risk_level || 'EVALUATED'}`, "success");

        // Sync timeline and active incidents
        if (window.niraStore && typeof window.niraStore.syncActiveIncidents === 'function') {
          await window.niraStore.syncActiveIncidents();
        }

      } catch (err) {
        console.error(`[OperatorConsole] Failed to execute simulation action '${actionName}':`, err);
        this.showToast(`Error invoking /api/v1/demo/simulate/${act}: ${err.message}`, "error");
      } finally {
        this.isExecutingAction = false;
      }
    }

    // -------------------------------------------------------------------------
    // Predefined Scenarios Runner with 7-Step Progression
    // -------------------------------------------------------------------------
    async triggerScenario(scenarioKey) {
      const sc = PREDEFINED_SCENARIOS[scenarioKey];
      if (!sc) return;

      this.activeScenarioKey = scenarioKey;
      this.activeProgressionStep = 0;

      this.renderScenarioProgressionUI(sc);
      this.showToast(`Starting ${sc.name}...`, "info");

      try {
        // Trigger background scenario execution on backend
        const resp = await fetch(`/api/v1/demo/scenario/${encodeURIComponent(sc.backendKey)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });

        if (resp.ok) {
          const result = await resp.json();
          console.log(`[OperatorConsole] Scenario '${scenarioKey}' backend trigger:`, result);
        }
      } catch (e) {
        console.warn(`[OperatorConsole] Scenario backend trigger warning:`, e);
      }

      // Animate the 7-step progression bar visibly
      this.startProgressionAnimation(sc);
    }

    startProgressionAnimation(sc) {
      if (this.progressionInterval) clearInterval(this.progressionInterval);

      const totalSteps = sc.progressionSteps.length;
      let step = 0;

      this.progressionInterval = setInterval(() => {
        step++;
        if (step < totalSteps) {
          this.activeProgressionStep = step;
          this.updateProgressionStepHighlight(sc, step);
        } else {
          clearInterval(this.progressionInterval);
          this.progressionInterval = null;
          this.showToast(`✓ ${sc.name} completed all 7 lifecycle stages.`, "success");
        }
      }, 1400);
    }

    renderScenarioProgressionUI(sc) {
      const modal = document.getElementById("scenarioProgressionBanner");
      if (!modal) return;

      modal.style.display = "block";
      modal.innerHTML = `
        <div class="scenario-progression-box">
          <div class="scen-prog-head">
            <div>
              <strong style="color: #fff; font-size: 0.95rem;">${escapeHtml(sc.name)}</strong>
              <div style="font-size: 0.76rem; color: #94a3b8; margin-top: 2px;">${escapeHtml(sc.description)}</div>
            </div>
            <button class="btn-demo-secondary" style="padding: 4px 10px; font-size: 0.72rem;" onclick="window.operatorConsole.closeProgressionBanner()">✕ Close</button>
          </div>

          <!-- 7-Stage Stepper Ribbon -->
          <div class="scen-step-ribbon" id="scenStepRibbon">
            <div class="scen-step-chip active" id="scenStage-0">1. EVENT</div>
            <div class="scen-step-arrow">→</div>
            <div class="scen-step-chip" id="scenStage-1">2. RISK</div>
            <div class="scen-step-arrow">→</div>
            <div class="scen-step-chip" id="scenStage-2">3. DECISION</div>
            <div class="scen-step-arrow">→</div>
            <div class="scen-step-chip" id="scenStage-3">4. INCIDENT</div>
            <div class="scen-step-arrow">→</div>
            <div class="scen-step-chip" id="scenStage-4">5. NOTIFICATION</div>
            <div class="scen-step-arrow">→</div>
            <div class="scen-step-chip" id="scenStage-5">6. ESCALATION</div>
            <div class="scen-step-arrow">→</div>
            <div class="scen-step-chip" id="scenStage-6">7. RESOLUTION</div>
          </div>

          <div class="scen-current-detail" id="scenCurrentDetail">
            <span class="pulse-dot-cyan"></span>
            <span id="scenCurrentDetailText">${escapeHtml(sc.progressionSteps[0])}</span>
          </div>
        </div>
      `;
    }

    updateProgressionStepHighlight(sc, stepIndex) {
      for (let i = 0; i < 7; i++) {
        const chip = document.getElementById(`scenStage-${i}`);
        if (chip) {
          chip.classList.remove("active", "done");
          if (i === stepIndex) {
            chip.classList.add("active");
          } else if (i < stepIndex) {
            chip.classList.add("done");
          }
        }
      }

      const textEl = document.getElementById("scenCurrentDetailText");
      if (textEl && sc.progressionSteps[stepIndex]) {
        textEl.textContent = sc.progressionSteps[stepIndex];
      }
    }

    closeProgressionBanner() {
      if (this.progressionInterval) {
        clearInterval(this.progressionInterval);
        this.progressionInterval = null;
      }
      const banner = document.getElementById("scenarioProgressionBanner");
      if (banner) banner.style.display = "none";
    }

    // -------------------------------------------------------------------------
    // Voice Check UI (Section 8: Classification from Backend)
    // -------------------------------------------------------------------------
    updateVoiceClassificationUI(classification, description) {
      this.lastVoiceClassification = classification;

      const badge = document.getElementById("voiceCheckClassificationBadge");
      const descEl = document.getElementById("voiceCheckDesc");
      const quoteEl = document.getElementById("voiceCheckResidentReply");

      if (badge) {
        badge.textContent = classification;
        badge.className = `voice-class-badge class-${classification.toLowerCase().replace(/\s+/g, "_")}`;
      }

      if (descEl) descEl.textContent = description || "";
      if (quoteEl && description) quoteEl.textContent = `"${description}"`;
    }

    // -------------------------------------------------------------------------
    // Helper: Toast Notifications
    // -------------------------------------------------------------------------
    showToast(message, type = "info") {
      if (typeof window.showToastNotification === 'function') {
        window.showToastNotification(message, type);
      } else if (typeof window.showToast === 'function') {
        window.showToast(message, type);
      } else {
        console.log(`[TOAST - ${type.toUpperCase()}]: ${message}`);
      }
    }

    attachEventListeners() {
      // Connect keyboard arrow keys for deterministic presentation navigation
      window.addEventListener("keydown", (e) => {
        // Alt + Right = Next Step, Alt + Left = Prev Step
        if (e.altKey && e.key === "ArrowRight") {
          e.preventDefault();
          this.nextFlowStep();
        } else if (e.altKey && e.key === "ArrowLeft") {
          e.preventDefault();
          this.prevFlowStep();
        }
      });
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Instantiate and expose globally
  const operatorConsole = new OperatorConsoleEngine();
  window.operatorConsole = operatorConsole;

  // Auto-init on DOMContentLoaded
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => operatorConsole.init());
  } else {
    operatorConsole.init();
  }

})();
