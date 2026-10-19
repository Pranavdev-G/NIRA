/**
 * Aegis Ambient Care - Live Edge Camera & YOLO Pose Estimation Simulator
 * Amazon Developer Hackathon 2026
 * 
 * Renders real-time 30fps canvas camera feed with anatomical YOLO pose skeleton,
 * floor radar ripples, bounding boxes, and fall kinematics.
 */

class CameraSimulator {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    this.currentRoom = "bathroom";
    this.state = "critical"; // 'safe', 'warning', 'critical'
    this.animTime = 0;
    this.fallProgress = 1.0; // 0.0 (upright) -> 1.0 (fallen on floor)
    this.isFalling = false;
    this.radarRipples = [];

    this.resizeCanvas();
    window.addEventListener("resize", () => this.resizeCanvas());

    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  resizeCanvas() {
    if (!this.canvas) return;
    this.canvas.width = this.canvas.parentElement.clientWidth;
    this.canvas.height = this.canvas.parentElement.clientHeight || 380;
  }

  setRoomAndState(room, state) {
    this.currentRoom = room;
    this.state = state;

    if (state === "critical") {
      this.fallProgress = 1.0;
      this.isFalling = false;
    } else if (state === "safe") {
      this.fallProgress = 0.0;
      this.isFalling = false;
    } else if (state === "warning") {
      this.fallProgress = 0.65; // Slumped/sitting on floor
      this.isFalling = false;
    }
  }

  triggerFall() {
    this.fallProgress = 0.0;
    this.isFalling = true;
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
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    // 1. Clear background
    ctx.fillStyle = "#090e17";
    ctx.fillRect(0, 0, w, h);

    // 2. Draw 3D perspective room interior
    this.drawRoomInterior(ctx, w, h);

    // 3. Draw radar ripples on floor
    this.drawRadarRipples(ctx, w, h);

    // 4. Draw Senior Human Figure with YOLO Pose Estimation Skeleton
    this.drawYoloSkeleton(ctx, w, h);

    // 5. Draw HUD telemetry (Blinking REC, Timestamp, FPS, Camera ID)
    this.drawHud(ctx, w, h);
  }

  drawRoomInterior(ctx, w, h) {
    // Horizon line
    const horizon = h * 0.42;

    // Wall gradient
    const wallGrad = ctx.createLinearGradient(0, 0, 0, horizon);
    if (this.currentRoom === "bathroom") {
      wallGrad.addColorStop(0, "#0f172a");
      wallGrad.addColorStop(1, "#1e293b");
    } else if (this.currentRoom === "living") {
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

    // Room props based on currentRoom
    if (this.currentRoom === "bathroom") {
      // Bathtub outline
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillStyle = "rgba(15, 23, 42, 0.6)";
      ctx.strokeRect(w * 0.08, horizon + 20, 140, 100);
      ctx.fillRect(w * 0.08, horizon + 20, 140, 100);

      // Water spill reflection on floor
      if (this.state === "critical") {
        ctx.fillStyle = "rgba(56, 189, 248, 0.15)";
        ctx.beginPath();
        ctx.ellipse(w * 0.52, h * 0.76, 130, 40, 0, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "rgba(56, 189, 248, 0.35)";
        ctx.font = "10px monospace";
        ctx.fillText("💧 WET FLOOR DETECTED (0.82 Mo)", w * 0.44, h * 0.83);
      }
    } else if (this.currentRoom === "living") {
      // Living room sofa
      ctx.fillStyle = "rgba(30, 41, 59, 0.7)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillRect(w * 0.1, horizon + 30, 160, 80);
      ctx.strokeRect(w * 0.1, horizon + 30, 160, 80);
    } else if (this.currentRoom === "kitchen") {
      // Kitchen island
      ctx.fillStyle = "rgba(30, 41, 59, 0.7)";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillRect(w * 0.7, horizon + 20, 120, 90);
      ctx.strokeRect(w * 0.7, horizon + 20, 120, 90);
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
    const t = this.fallProgress; // 0.0 (upright) -> 1.0 (flat on floor)
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

    // Determine colors
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

    // Corner brackets for bounding box
    const corner = 12;
    ctx.lineWidth = 3;
    // Top-left
    ctx.beginPath(); ctx.moveTo(minX, minY + corner); ctx.lineTo(minX, minY); ctx.lineTo(minX + corner, minY); ctx.stroke();
    // Top-right
    ctx.beginPath(); ctx.moveTo(maxX - corner, minY); ctx.lineTo(maxX, minY); ctx.lineTo(maxX, minY + corner); ctx.stroke();
    // Bottom-left
    ctx.beginPath(); ctx.moveTo(minX, maxY - corner); ctx.lineTo(minX, maxY); ctx.lineTo(minX + corner, maxY); ctx.stroke();
    // Bottom-right
    ctx.beginPath(); ctx.moveTo(maxX - corner, maxY); ctx.lineTo(maxX, maxY); ctx.lineTo(maxX, maxY - corner); ctx.stroke();

    // Bounding box tag
    ctx.fillStyle = bboxColor;
    ctx.fillRect(minX, minY - 24, maxX - minX, 22);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px monospace";

    if (this.state === "critical") {
      ctx.fillText("⚠️ FALL DETECTED (CONF: 94%)", minX + 6, minY - 8);
    } else if (this.state === "warning") {
      ctx.fillText("⚠️ DISTRESS / SITTING (CONF: 89%)", minX + 6, minY - 8);
    } else {
      ctx.fillText("✅ NORMAL POSTURE (CONF: 96%)", minX + 6, minY - 8);
    }
  }

  drawHud(ctx, w, h) {
    // Top-left HUD
    ctx.fillStyle = "rgba(15, 23, 42, 0.7)";
    ctx.fillRect(14, 14, 210, 52);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctx.strokeRect(14, 14, 210, 52);

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px monospace";
    ctx.fillText(`CAM-01 • ${this.currentRoom.toUpperCase()}`, 24, 32);

    const now = new Date().toISOString().replace("T", " ").substring(0, 19);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px monospace";
    ctx.fillText(`${now} UTC`, 24, 46);
    ctx.fillText(`30 FPS • 1080p • YOLOv8-Pose`, 24, 58);

    // Top-right REC badge is handled in HTML/CSS overlay
  }
}

// Global Camera Simulation Instance
let cameraSim = null;

document.addEventListener("DOMContentLoaded", () => {
  cameraSim = new CameraSimulator("cameraCanvas");
});
