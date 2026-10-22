/**
 * NIRA — Live Edge Camera, YOLO Pose Estimation & 60GHz mmWave Privacy Radar Simulator
 * 
 * Supports:
 * 1. Optical Edge Camera View with YOLOv8 17-Keypoint Anatomical Pose Skeleton
 * 2. Privacy-Preserving 60GHz FMCW mmWave Radar View (Used automatically in Bathroom/Bedroom
 *    where optical cameras are prohibited for elderly privacy, or when toggled)
 * 3. Fall Kinematics, Doppler Point Cloud, Centroid Elevation, and Micro-Doppler Respiration
 */

class CameraSimulator {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    this.currentRoom = "bathroom";
    this.state = "critical"; // 'safe', 'warning', 'critical'
    this.postureCode = "fallen"; // 'fallen', 'sitting', 'upright'
    this.animTime = 0;
    this.fallProgress = 1.0; // 0.0 (upright) -> 1.0 (fallen on floor)
    this.isFalling = false;
    this.isManualRadar = false; // User toggle override
    this.viewMode = "radar"; // 'radar' | 'camera' | 'auto'
    this.radarRipples = [];
    this.pointCloud = [];
    this.respWaveform = [];

    window.cameraSim = this;
    this.resizeCanvas();
    window.addEventListener("resize", () => this.resizeCanvas());

    this.initPointCloud();
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const parent = this.canvas.parentElement;
    let w = parent ? parent.clientWidth : 0;
    let h = parent ? parent.clientHeight : 0;

    // Never collapse to 0 if container is hidden or initializing
    if (w < 80) {
      w = this.canvas.clientWidth > 80 ? this.canvas.clientWidth : 580;
    }
    if (h < 80) {
      h = this.canvas.clientHeight > 80 ? this.canvas.clientHeight : 380;
    }

    this.canvas.width = w;
    this.canvas.height = h;
  }

  isRadarActive() {
    if (this.viewMode === "radar") return true;
    if (this.viewMode === "camera") return false;
    // Auto fallback: bathroom and bedroom protect privacy with mmWave radar
    return this.isManualRadar || this.currentRoom === "bathroom" || this.currentRoom === "bedroom";
  }

  toggleRadarMode() {
    if (this.isRadarActive()) {
      this.setViewMode("camera");
    } else {
      this.setViewMode("radar");
    }
    return this.isRadarActive();
  }

  setManualRadar(active) {
    this.isManualRadar = !!active;
    this.viewMode = active ? "radar" : "camera";
  }

  setViewMode(mode) {
    this.viewMode = mode;
    if (mode === "radar") {
      this.isManualRadar = true;
    } else if (mode === "camera") {
      this.isManualRadar = false;
    }
  }

  setRoomAndState(room, state, postureCode) {
    this.currentRoom = room;
    this.state = state;

    if (postureCode) {
      this.postureCode = postureCode;
    } else {
      if (state === "critical") this.postureCode = "fallen";
      else if (state === "warning") this.postureCode = "sitting";
      else this.postureCode = "upright";
    }

    if (this.postureCode === "fallen" || state === "critical") {
      this.fallProgress = 1.0;
      this.isFalling = false;
    } else if (this.postureCode === "sitting" || state === "warning") {
      this.fallProgress = 0.65;
      this.isFalling = false;
    } else {
      this.fallProgress = 0.0;
      this.isFalling = false;
    }

    this.initPointCloud();
  }

  triggerFall() {
    this.fallProgress = 0.0;
    this.isFalling = true;
    this.postureCode = "fallen";
  }

  initPointCloud() {
    this.pointCloud = [];
    const count = 48;
    for (let i = 0; i < count; i++) {
      this.pointCloud.push({
        offsetX: (Math.random() - 0.5) * 80,
        offsetY: (Math.random() - 0.5) * 40,
        radius: 2 + Math.random() * 2.5,
        speed: 0.5 + Math.random() * 1.5,
        phase: Math.random() * Math.PI * 2,
        dopplerIntensity: 0.4 + Math.random() * 0.6
      });
    }
  }

  animate() {
    this.animTime += 0.03;
    if (this.isFalling && this.fallProgress < 1.0) {
      this.fallProgress += 0.04;
      if (this.fallProgress >= 1.0) {
        this.fallProgress = 1.0;
        this.isFalling = false;
      }
    }

    this.render();
    requestAnimationFrame(this.animate);
  }

  render() {
    if (!this.canvas || !this.ctx) return;
    const parent = this.canvas.parentElement;
    if (parent && parent.clientWidth > 50 && Math.abs(this.canvas.width - parent.clientWidth) > 4) {
      this.resizeCanvas();
    }
    const ctx = this.ctx;
    const w = this.canvas.width || 640;
    const h = this.canvas.height || 380;
    if (w < 10 || h < 10) return;

    if (this.isRadarActive()) {
      this.drawRadarPresence(ctx, w, h);
    } else {
      // 1. Clear background
      ctx.fillStyle = "#090e17";
      ctx.fillRect(0, 0, w, h);

      // 2. Draw 3D perspective room interior
      this.drawRoomInterior(ctx, w, h);

      // 3. Draw radar ripples on floor
      this.drawRadarRipples(ctx, w, h);

      // 4. Draw Senior Human Figure with YOLO Pose Estimation Skeleton
      this.drawYoloSkeleton(ctx, w, h);

      // 5. Draw HUD telemetry (Camera ID, FPS, Resolution)
      this.drawHud(ctx, w, h);
    }
  }

  // =========================================================================
  // PRIVACY-PRESERVING 60GHz mmWAVE RADAR RENDERING
  // =========================================================================
  drawRadarPresence(ctx, w, h) {
    const t = this.animTime;

    // 1. Deep Space Radar Background with subtle radial glow
    const bgGrad = ctx.createRadialGradient(w * 0.5, 40, 10, w * 0.5, h * 0.5, Math.max(20, w * 0.8));
    bgGrad.addColorStop(0, "#081326");
    bgGrad.addColorStop(0.6, "#040814");
    bgGrad.addColorStop(1, "#020409");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // 2. Polar mmWave Radar Grid (Ceiling-Mounted Pod Perspective)
    const originX = w * 0.5;
    const originY = 32; // Ceiling pod position
    const maxR = Math.max(20, h * 0.88);

    // Range Arcs (1m, 2m, 3m, 4m)
    const ranges = [0.25, 0.5, 0.75, 1.0];
    const rangeLabels = ["1.0m", "2.0m", "3.0m", "4.0m"];
    ctx.lineWidth = 1;

    ranges.forEach((frac, idx) => {
      const r = Math.max(5, maxR * frac);
      ctx.strokeStyle = idx === 3 ? "rgba(56, 189, 248, 0.25)" : "rgba(56, 189, 248, 0.12)";
      ctx.beginPath();
      ctx.arc(originX, originY, r, 0.15 * Math.PI, 0.85 * Math.PI);
      ctx.stroke();

      // Range text
      ctx.fillStyle = "rgba(56, 189, 248, 0.5)";
      ctx.font = "9px monospace";
      ctx.fillText(rangeLabels[idx], originX + 8, originY + r - 4);
    });

    // Azimuth Radial Rays (-60°, -30°, 0°, +30°, +60°)
    const angles = [-0.33 * Math.PI, -0.16 * Math.PI, 0, 0.16 * Math.PI, 0.33 * Math.PI];
    angles.forEach(ang => {
      const radAngle = ang + Math.PI / 2;
      const ex = originX + Math.cos(radAngle) * maxR;
      const ey = originY + Math.sin(radAngle) * maxR;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.1)";
      ctx.beginPath();
      ctx.moveTo(originX, originY);
      ctx.lineTo(ex, ey);
      ctx.stroke();
    });

    // Sweeping Radar Scanner Beam
    const sweepAngle = Math.sin(t * 1.8) * 0.36 + Math.PI / 2;
    const sweepX = originX + Math.cos(sweepAngle) * maxR;
    const sweepY = originY + Math.sin(sweepAngle) * maxR;

    const sweepGrad = ctx.createRadialGradient(originX, originY, 5, originX, originY, Math.max(10, maxR));
    sweepGrad.addColorStop(0, "rgba(56, 189, 248, 0.35)");
    sweepGrad.addColorStop(1, "rgba(56, 189, 248, 0.0)");
    ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(originX, originY);
    ctx.lineTo(sweepX, sweepY);
    ctx.stroke();

    // Ceiling Pod Emitter Symbol
    ctx.fillStyle = "#38bdf8";
    ctx.beginPath();
    ctx.arc(originX, originY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    ctx.stroke();

    // 3. Privacy Compliance Header Banner
    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.fillRect(w * 0.12, 10, w * 0.76, 26);
    ctx.strokeStyle = "rgba(16, 185, 129, 0.4)";
    ctx.strokeRect(w * 0.12, 10, w * 0.76, 26);

    ctx.fillStyle = "#10b981";
    ctx.font = "bold 10px monospace";
    ctx.textAlign = "center";
    ctx.fillText("🔒 PRIVACY SHIELD ACTIVE • 60GHz mmWAVE RADAR • ZERO OPTICAL IMAGERY RECORDED", w * 0.5, 26);
    ctx.textAlign = "left";

    // 4. Target Posture & Point Cloud Calculation
    let targetX = w * 0.52;
    let targetY = h * 0.78;
    let spreadX = 90;
    let spreadY = 25;
    let elevationM = 0.18;
    let elevationLabel = "0.18m (FLOOR LEVEL - FALL OCCURRED)";
    let postureText = "FALLEN (HORIZONTAL CENTROID)";
    let statusColor = "#ef4444";
    let dopplerVelocity = "0.02 m/s (IMMOBILE)";

    if (this.postureCode === "sitting" || this.state === "warning") {
      targetY = h * 0.62;
      spreadX = 55;
      spreadY = 55;
      elevationM = 0.62;
      elevationLabel = "0.62m (CHAIR / MID-HEIGHT)";
      postureText = "SITTING (LIMITED MOBILITY)";
      statusColor = "#f59e0b";
      dopplerVelocity = "0.14 m/s (LOW RESIDUAL)";
    } else if (this.postureCode === "upright" || this.state === "safe") {
      targetY = h * 0.46;
      spreadX = 40;
      spreadY = 85;
      elevationM = 1.48;
      elevationLabel = "1.48m (UPRIGHT AMBULATION)";
      postureText = "UPRIGHT (NORMAL GAIT)";
      statusColor = "#10b981";
      dopplerVelocity = "0.85 m/s (NORMAL)";
    }

    // Draw Target Body Cluster Bounding Ellipse
    const safeSpreadX = Math.max(10, spreadX);
    const safeSpreadY = Math.max(10, spreadY);
    ctx.strokeStyle = statusColor;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.ellipse(targetX, targetY, safeSpreadX, safeSpreadY, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);

    // Fill semi-transparent heat zone
    const heatGrad = ctx.createRadialGradient(targetX, targetY, 5, targetX, targetY, safeSpreadX);
    heatGrad.addColorStop(0, this.state === "critical" ? "rgba(239, 68, 68, 0.25)" : (this.state === "warning" ? "rgba(245, 158, 11, 0.2)" : "rgba(16, 185, 129, 0.2)"));
    heatGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = heatGrad;
    ctx.beginPath();
    ctx.ellipse(targetX, targetY, safeSpreadX, safeSpreadY, 0, 0, Math.PI * 2);
    ctx.fill();

    // Draw Individual Radar Reflection Point Cloud (Doppler points)
    this.pointCloud.forEach((pt, idx) => {
      const px = targetX + pt.offsetX * (spreadX / 55) + Math.sin(t * pt.speed + pt.phase) * 6;
      const py = targetY + pt.offsetY * (spreadY / 40) + Math.cos(t * pt.speed + pt.phase) * 6;

      ctx.fillStyle = this.state === "critical"
        ? (idx % 3 === 0 ? "#ef4444" : "#fca5a5")
        : (this.state === "warning" ? (idx % 2 === 0 ? "#f59e0b" : "#fde68a") : "#38bdf8");
      ctx.beginPath();
      ctx.arc(px, py, pt.radius, 0, Math.PI * 2);
      ctx.fill();
    });

    // Centroid Crosshair (+)
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(targetX - 10, targetY);
    ctx.lineTo(targetX + 10, targetY);
    ctx.moveTo(targetX, targetY - 10);
    ctx.lineTo(targetX, targetY + 10);
    ctx.stroke();

    // Centroid Tag
    ctx.fillStyle = statusColor;
    ctx.fillRect(targetX - 70, targetY - spreadY - 24, 140, 20);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 9px monospace";
    ctx.textAlign = "center";
    ctx.fillText(`TARGET: ${postureText}`, targetX, targetY - spreadY - 10);
    ctx.textAlign = "left";

    // 5. Centroid Elevation & Kinematics Bar (Top-Left HUD)
    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.fillRect(14, 46, 260, 68);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctx.strokeRect(14, 46, 260, 68);

    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 10px monospace";
    ctx.fillText(`60GHz mmWAVE RADAR: ${this.currentRoom.toUpperCase()}`, 24, 62);

    ctx.fillStyle = "#ffffff";
    ctx.font = "9.5px monospace";
    ctx.fillText(`Elevation: ${elevationLabel}`, 24, 78);
    ctx.fillText(`Kinematics: ${dopplerVelocity}`, 24, 92);
    ctx.fillText(`Substrate: ${this.currentRoom === "bathroom" ? "Wet Tile (Moisture High)" : "Dry Floor"}`, 24, 106);

    // 6. Micro-Doppler Respiration Monitor (Bottom-Right HUD)
    const waveBoxW = 230;
    const waveBoxH = 68;
    const waveBoxX = w - waveBoxW - 14;
    const waveBoxY = h - waveBoxH - 14;

    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.fillRect(waveBoxX, waveBoxY, waveBoxW, waveBoxH);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.3)";
    ctx.strokeRect(waveBoxX, waveBoxY, waveBoxW, waveBoxH);

    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 9px monospace";
    const bpmResp = this.state === "critical" ? "26 bpm (Tachypnea / Distress)" : (this.state === "warning" ? "20 bpm (Elevated)" : "14 bpm (Normal)");
    ctx.fillText(`CHEST DISPLACEMENT: ${bpmResp}`, waveBoxX + 10, waveBoxY + 16);

    // Draw Live Oscillating Respiration Sine Wave
    ctx.strokeStyle = this.state === "critical" ? "#ef4444" : (this.state === "warning" ? "#f59e0b" : "#10b981");
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    const waveSpeed = this.state === "critical" ? 4.5 : 2.2;
    for (let x = 0; x < waveBoxW - 20; x += 4) {
      const waveVal = Math.sin((x * 0.08) + (t * waveSpeed)) * 14 * (this.state === "critical" ? 0.8 : 1.0);
      const drawY = waveBoxY + 42 + waveVal;
      if (x === 0) ctx.moveTo(waveBoxX + 10 + x, drawY);
      else ctx.lineTo(waveBoxX + 10 + x, drawY);
    }
    ctx.stroke();

    // 7. Sensor Pod Specs (Bottom-Left)
    ctx.fillStyle = "rgba(148, 163, 184, 0.7)";
    ctx.font = "9px monospace";
    ctx.fillText("TI IWR6843 60-64 GHz FMCW • 3Tx/4Rx MIMO • 3.75cm Res • 20 Hz", 16, h - 14);
  }

  // =========================================================================
  // OPTICAL CAMERA & YOLO SKELETON RENDERING
  // =========================================================================
  drawRoomInterior(ctx, w, h) {
    const horizon = h * 0.42;

    // Wall gradient
    const wallGrad = ctx.createLinearGradient(0, 0, 0, horizon);
    if (this.currentRoom === "kitchen") {
      wallGrad.addColorStop(0, "#131b2e");
      wallGrad.addColorStop(1, "#1e293b");
    } else {
      wallGrad.addColorStop(0, "#0f172a");
      wallGrad.addColorStop(1, "#1a2538");
    }
    ctx.fillStyle = wallGrad;
    ctx.fillRect(0, 0, w, horizon);

    // Floor gradient (tiles)
    const floorGrad = ctx.createLinearGradient(0, horizon, 0, h);
    floorGrad.addColorStop(0, "#111827");
    floorGrad.addColorStop(1, "#070b12");
    ctx.fillStyle = floorGrad;
    ctx.fillRect(0, horizon, w, h - horizon);

    // Floor perspective grid lines
    ctx.strokeStyle = "rgba(56, 189, 248, 0.06)";
    ctx.lineWidth = 1;
    for (let x = -w * 0.5; x <= w * 1.5; x += 60) {
      ctx.beginPath();
      ctx.moveTo(w * 0.5, horizon);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = horizon; y <= h; y += 35) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Room props
    if (this.currentRoom === "living") {
      ctx.fillStyle = "rgba(30, 41, 59, 0.7)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillRect(w * 0.08, horizon + 30, 160, 80);
      ctx.strokeRect(w * 0.08, horizon + 30, 160, 80);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px monospace";
      ctx.fillText("SOFA SEATING", w * 0.1, horizon + 55);
    } else if (this.currentRoom === "kitchen") {
      ctx.fillStyle = "rgba(30, 41, 59, 0.7)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillRect(w * 0.68, horizon + 20, 130, 95);
      ctx.strokeRect(w * 0.68, horizon + 20, 130, 95);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px monospace";
      ctx.fillText("PREP ISLAND / STOVE", w * 0.7, horizon + 50);
    } else if (this.currentRoom === "bathroom") {
      ctx.fillStyle = "rgba(30, 41, 59, 0.7)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillRect(w * 0.08, horizon + 20, 120, 80);
      ctx.strokeRect(w * 0.08, horizon + 20, 120, 80);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px monospace";
      ctx.fillText("VANITY / SINK", w * 0.1, horizon + 45);
      // Shower partition
      ctx.strokeStyle = "rgba(56, 189, 248, 0.25)";
      ctx.fillStyle = "rgba(56, 189, 248, 0.06)";
      ctx.fillRect(w * 0.75, horizon - 20, 100, 140);
      ctx.strokeRect(w * 0.75, horizon - 20, 100, 140);
      ctx.fillStyle = "rgba(56, 189, 248, 0.6)";
      ctx.font = "9px monospace";
      ctx.fillText("SHOWER (WET FLOOR)", w * 0.76, horizon + 20);
    } else if (this.currentRoom === "bedroom") {
      ctx.fillStyle = "rgba(30, 41, 59, 0.7)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillRect(w * 0.08, horizon + 25, 150, 90);
      ctx.strokeRect(w * 0.08, horizon + 25, 150, 90);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "10px monospace";
      ctx.fillText("BED / NIGHTSTAND", w * 0.1, horizon + 50);
    }
  }

  drawRadarRipples(ctx, w, h) {
    if (Math.random() < 0.04) {
      this.radarRipples.push({
        x: w * 0.52,
        y: h * 0.75,
        radius: 10,
        alpha: 0.6
      });
    }

    for (let i = this.radarRipples.length - 1; i >= 0; i--) {
      const r = this.radarRipples[i];
      r.radius += 1.8;
      r.alpha -= 0.012;

      ctx.strokeStyle = this.state === "critical" 
        ? `rgba(239, 68, 68, ${r.alpha})`
        : `rgba(56, 189, 248, ${r.alpha})`;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.ellipse(r.x, r.y, r.radius * 2, r.radius, 0, 0, Math.PI * 2);
      ctx.stroke();

      if (r.alpha <= 0) {
        this.radarRipples.splice(i, 1);
      }
    }
  }

  drawYoloSkeleton(ctx, w, h) {
    const t = this.fallProgress;
    const centerX = w * 0.52;
    const baseY = h * 0.76;

    // Upright keypoint coordinates
    const upright = {
      head: { x: centerX, y: baseY - 160 },
      neck: { x: centerX, y: baseY - 135 },
      leftShoulder: { x: centerX - 24, y: baseY - 125 },
      rightShoulder: { x: centerX + 24, y: baseY - 125 },
      leftElbow: { x: centerX - 36, y: baseY - 90 },
      rightElbow: { x: centerX + 36, y: baseY - 90 },
      leftWrist: { x: centerX - 32, y: baseY - 60 },
      rightWrist: { x: centerX + 32, y: baseY - 60 },
      midHip: { x: centerX, y: baseY - 75 },
      leftHip: { x: centerX - 18, y: baseY - 70 },
      rightHip: { x: centerX + 18, y: baseY - 70 },
      leftKnee: { x: centerX - 20, y: baseY - 35 },
      rightKnee: { x: centerX + 20, y: baseY - 35 },
      leftAnkle: { x: centerX - 22, y: baseY },
      rightAnkle: { x: centerX + 22, y: baseY }
    };

    // Fallen on floor coordinates (horizontal bounding box)
    const fallen = {
      head: { x: centerX - 120, y: baseY + 5 },
      neck: { x: centerX - 95, y: baseY + 5 },
      leftShoulder: { x: centerX - 85, y: baseY - 10 },
      rightShoulder: { x: centerX - 85, y: baseY + 18 },
      leftElbow: { x: centerX - 55, y: baseY - 18 },
      rightElbow: { x: centerX - 55, y: baseY + 26 },
      leftWrist: { x: centerX - 25, y: baseY - 14 },
      rightWrist: { x: centerX - 25, y: baseY + 22 },
      midHip: { x: centerX, y: baseY + 8 },
      leftHip: { x: centerX + 5, y: baseY - 6 },
      rightHip: { x: centerX + 5, y: baseY + 20 },
      leftKnee: { x: centerX + 55, y: baseY - 10 },
      rightKnee: { x: centerX + 60, y: baseY + 14 },
      leftAnkle: { x: centerX + 110, y: baseY - 8 },
      rightAnkle: { x: centerX + 115, y: baseY + 12 }
    };

    // Interpolate keypoints
    const lerp = (a, b, f) => a + (b - a) * f;
    const current = {};
    for (const k in upright) {
      current[k] = {
        x: lerp(upright[k].x, fallen[k].x, t),
        y: lerp(upright[k].y, fallen[k].y, t)
      };
    }

    let boneColor = "#38bdf8";
    let jointColor = "#00cae0";
    let bboxColor = "rgba(56, 189, 248, 0.4)";

    if (this.state === "critical") {
      boneColor = "#ef4444";
      jointColor = "#fca5a5";
      bboxColor = "rgba(239, 68, 68, 0.8)";
    } else if (this.state === "warning") {
      boneColor = "#f59e0b";
      jointColor = "#fde68a";
      bboxColor = "rgba(245, 158, 11, 0.7)";
    }

    // 1. Draw Skeleton Bones
    const bones = [
      ["head", "neck"],
      ["neck", "leftShoulder"], ["neck", "rightShoulder"],
      ["leftShoulder", "leftElbow"], ["rightShoulder", "rightElbow"],
      ["leftElbow", "leftWrist"], ["rightElbow", "rightWrist"],
      ["neck", "midHip"],
      ["midHip", "leftHip"], ["midHip", "rightHip"],
      ["leftHip", "leftKnee"], ["rightHip", "rightKnee"],
      ["leftKnee", "leftAnkle"], ["rightKnee", "rightAnkle"]
    ];

    ctx.lineWidth = 3;
    ctx.strokeStyle = boneColor;
    for (const [p1, p2] of bones) {
      ctx.beginPath();
      ctx.moveTo(current[p1].x, current[p1].y);
      ctx.lineTo(current[p2].x, current[p2].y);
      ctx.stroke();
    }

    // 2. Draw Keypoint Joints
    ctx.fillStyle = jointColor;
    for (const k in current) {
      ctx.beginPath();
      ctx.arc(current[k].x, current[k].y, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    // Head circle
    ctx.strokeStyle = boneColor;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(current.head.x, current.head.y, 14, 0, Math.PI * 2);
    ctx.stroke();

    // 3. Draw YOLO Pose Detection Bounding Box
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const k in current) {
      minX = Math.min(minX, current[k].x);
      maxX = Math.max(maxX, current[k].x);
      minY = Math.min(minY, current[k].y);
      maxY = Math.max(maxY, current[k].y);
    }
    minX -= 20; maxX += 20; minY -= 25; maxY += 15;

    ctx.strokeStyle = bboxColor;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);

    // Corner brackets
    const corner = 12;
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(minX, minY + corner); ctx.lineTo(minX, minY); ctx.lineTo(minX + corner, minY); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(maxX - corner, minY); ctx.lineTo(maxX, minY); ctx.lineTo(maxX, minY + corner); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(minX, maxY - corner); ctx.lineTo(minX, maxY); ctx.lineTo(minX + corner, maxY); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(maxX - corner, maxY); ctx.lineTo(maxX, maxY); ctx.lineTo(maxX, maxY - corner); ctx.stroke();

    // Bounding box tag
    ctx.fillStyle = bboxColor;
    ctx.fillRect(minX, minY - 24, maxX - minX, 22);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px monospace";

    if (this.state === "critical") {
      ctx.fillText("[FALL DETECTED • CONF: 94%]", minX + 6, minY - 8);
    } else if (this.state === "warning") {
      ctx.fillText("[DISTRESS / SITTING • CONF: 89%]", minX + 6, minY - 8);
    } else {
      ctx.fillText("[NORMAL POSTURE • CONF: 96%]", minX + 6, minY - 8);
    }
  }

  drawHud(ctx, w, h) {
    ctx.fillStyle = "rgba(15, 23, 42, 0.75)";
    ctx.fillRect(14, 14, 230, 52);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctx.strokeRect(14, 14, 230, 52);

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px monospace";
    ctx.fillText(`CAM-01 • ${this.currentRoom.toUpperCase()}`, 24, 32);

    const now = new Date().toISOString().replace("T", " ").substring(0, 19);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px monospace";
    ctx.fillText(`${now} UTC`, 24, 46);
    ctx.fillText(`30 FPS • 1080p • YOLOv8-Pose [SIMULATED]`, 24, 58);
  }
}

// Global Camera Simulation Instance
window.CameraSimulator = CameraSimulator;
window.cameraSim = null;

function initCameraSim() {
  if (!window.cameraSim) {
    const el = document.getElementById("cameraCanvas");
    if (el) {
      window.cameraSim = new CameraSimulator("cameraCanvas");
    }
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initCameraSim);
} else {
  initCameraSim();
}
