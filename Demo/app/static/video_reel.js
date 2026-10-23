/**
 * Aegis Ambient Care - 3D WebGL Operational Video Reel Engine
 * Powered by Three.js (r128)
 * Amazon Developer Hackathon 2026
 * 
 * Renders a full 3D Digital Twin of Eleanor's apartment with an articulated
 * 3D humanoid character model, cinematic camera movements, 3D fall kinematics,
 * 3D volumetric radar cones, and synchronized voiceover narration.
 */

class OperationalVideoReel {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;

    this.isPlaying = false;
    this.currentTime = 0;
    this.duration = 50; // 50 seconds comprehensive walkthrough
    this.animFrameId = null;
    this.isAudioMuted = false;
    this.currentSceneIndex = -1;

    // Operational Walkthrough Scenes
    this.scenes = [
      {
        id: 0,
        start: 0,
        end: 10,
        title: "1. Ambient Non-Invasive Protection",
        room: "Beacon Hill Unit 4B",
        subtitle: "Eleanor Vance (Age 79) lives independently. Ceiling micro-radar continuously monitors movement with zero cameras for 100% privacy.",
        narration: "Welcome to Aegis Ambient Care. Eleanor Vance, age 79, lives independently at Beacon Hill Unit 4B. The apartment is continuously protected by ceiling micro-radar and ambient sensors, preserving total privacy without invasive cameras.",
        camPos: { x: 0, y: 14, z: 22 },
        camLook: { x: 0, y: 1.5, z: 0 },
        speaker: "narrator"
      },
      {
        id: 1,
        start: 10,
        end: 20,
        title: "2. Sudden Fall Detected & Biometrics",
        room: "Bathroom",
        subtitle: "Sudden downward drop at 2:14 AM on wet bathroom tiles. AI flags 94% fall probability with heart rate surge to 138 BPM.",
        narration: "At 2:14 AM, the ceiling radar detects a sudden downward drop in the bathroom. The multimodal AI confirms a 94 percent probability of a fall on wet tile, while Apple Watch telemetry captures acute tachycardia surging to 138 beats per minute.",
        camPos: { x: -6, y: 7, z: 8 },
        camLook: { x: -6, y: 0.8, z: 0 },
        speaker: "narrator"
      },
      {
        id: 2,
        start: 20,
        end: 30,
        title: "3. Alexa Echo Show 15 Voice Check-In",
        room: "Echo Show 15",
        subtitle: "Echo Show checks in: \"Eleanor, are you okay?\". The system listens for 20 seconds. Zero response = Presumed Unconscious.",
        narration: "Within sub-500 milliseconds, the Echo Show 15 activates an ambient voice check-in: 'Eleanor, this is Aegis. I noticed a fall in the bathroom. Are you okay?'. Aegis listens for 20 seconds. With zero verbal response, the AI flags Eleanor as presumed unconscious.",
        camPos: { x: 0, y: 4, z: 9 },
        camLook: { x: 0, y: 3.5, z: 0 },
        speaker: "alexa"
      },
      {
        id: 3,
        start: 30,
        end: 40,
        title: "4. Son David Alerted & Echo Drop-In",
        room: "Guardian Voice Stream",
        subtitle: "Primary Guardian David Vance receives immediate mobile priority push and live 2-way Echo Drop-In audio.",
        narration: "Aegis immediately connects her primary guardian and son, David Vance. His phone receives an instant priority notification and opens a live Echo Drop-In audio stream, allowing David to speak directly to his mother and hear the room in real time.",
        camPos: { x: 4, y: 6, z: 12 },
        camLook: { x: 2, y: 2, z: 0 },
        speaker: "son"
      },
      {
        id: 4,
        start: 40,
        end: 50,
        title: "5. 911 Dispatch & Smart Door Unlocked",
        room: "Boston EMS 911",
        subtitle: "Boston EMS Medic-14 dispatched with vital summary. Front door smart lock auto-unlocks with PIN 8492 for first responders.",
        narration: "Simultaneously, Aegis dispatches Boston EMS Medic 14 with Eleanor's clinical vitals and floor status. The front door smart lock is automatically unlocked with emergency PIN 8492, allowing paramedics to enter instantly without delay.",
        camPos: { x: 9, y: 6, z: 12 },
        camLook: { x: 8, y: 2, z: 0 },
        speaker: "narrator"
      }
    ];

    this.initThreeJS();
  }

  // -------------------------------------------------------------------------
  // 3D Scene Initialization
  // -------------------------------------------------------------------------
  initThreeJS() {
    if (typeof THREE === "undefined") {
      console.warn("Three.js not loaded, video reel running in 2D mode.");
      return;
    }

    const parent = this.canvas.parentElement;
    const w = (parent && parent.clientWidth > 100) ? parent.clientWidth : (this.canvas.clientWidth || 760);
    const h = (parent && parent.clientHeight > 200) ? parent.clientHeight : (this.canvas.clientHeight || 400);

    // 1. Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x050813);
    this.scene.fog = new THREE.FogExp2(0x050813, 0.025);

    // 2. Camera
    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    this.camera.position.set(0, 14, 22);
    this.camera.lookAt(0, 1.5, 0);

    // 3. WebGL Renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: false
    });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(0x1e293b, 1.5);
    this.scene.add(ambientLight);

    this.mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
    this.mainLight.position.set(10, 20, 15);
    this.mainLight.castShadow = true;
    this.scene.add(this.mainLight);

    // Cyan Radar Spotlight
    this.radarLight = new THREE.PointLight(0x00cae0, 2, 25);
    this.radarLight.position.set(0, 6, 0);
    this.scene.add(this.radarLight);

    // Red Emergency Beacon Light
    this.emergencyLight = new THREE.PointLight(0xef4444, 0, 30);
    this.emergencyLight.position.set(-6, 4, 0);
    this.scene.add(this.emergencyLight);

    // 5. Build 3D Apartment Architecture & Models
    this.build3DApartment();
    this.build3DHumanoidEleanor();
    this.build3DEchoShow();
    this.build3DSmartDoor();
    this.build3DAmbulance();

    this.renderer.render(this.scene, this.camera);
  }

  // -------------------------------------------------------------------------
  // 3D Apartment Digital Twin Architecture
  // -------------------------------------------------------------------------
  build3DApartment() {
    this.apartmentGroup = new THREE.Group();

    // 3D Perspective Floor Grid
    const grid = new THREE.GridHelper(36, 36, 0x00cae0, 0x1e293b);
    grid.position.y = 0;
    this.apartmentGroup.add(grid);

    // Room Floors
    // 1. Living Room Floor (Center)
    const livingGeo = new THREE.BoxGeometry(10, 0.2, 10);
    const livingMat = new THREE.MeshStandardMaterial({ color: 0x0d1527, roughness: 0.8 });
    const livingFloor = new THREE.Mesh(livingGeo, livingMat);
    livingFloor.position.set(0, -0.1, 0);
    livingFloor.receiveShadow = true;
    this.apartmentGroup.add(livingFloor);

    // 2. Bathroom Floor (Left: glossy wet tile sheen)
    const bathGeo = new THREE.BoxGeometry(8, 0.2, 8);
    const bathMat = new THREE.MeshStandardMaterial({ color: 0x0a2a38, roughness: 0.2, metalness: 0.4 });
    const bathFloor = new THREE.Mesh(bathGeo, bathMat);
    bathFloor.position.set(-8, -0.1, 0);
    bathFloor.receiveShadow = true;
    this.apartmentGroup.add(bathFloor);

    // Wet puddle disc in bathroom
    const puddleGeo = new THREE.CylinderGeometry(2, 2, 0.05, 32);
    const puddleMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.5, roughness: 0.1 });
    this.puddleMesh = new THREE.Mesh(puddleGeo, puddleMat);
    this.puddleMesh.position.set(-6, 0.02, 0);
    this.apartmentGroup.add(this.puddleMesh);

    // 3. Front Door Hallway (Right)
    const hallGeo = new THREE.BoxGeometry(6, 0.2, 8);
    const hallMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.8 });
    const hallFloor = new THREE.Mesh(hallGeo, hallMat);
    hallFloor.position.set(8, -0.1, 0);
    hallFloor.receiveShadow = true;
    this.apartmentGroup.add(hallFloor);

    // Translucent Glass Interior Partition Walls
    const wallMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.22,
      roughness: 0.1,
      metalness: 0.5
    });

    // Divider: Bathroom / Living Room
    const wallBathGeo = new THREE.BoxGeometry(0.2, 3.5, 7);
    const wallBath = new THREE.Mesh(wallBathGeo, wallMat);
    wallBath.position.set(-4, 1.75, 0);
    this.apartmentGroup.add(wallBath);

    // Divider: Living Room / Hallway
    const wallHallGeo = new THREE.BoxGeometry(0.2, 3.5, 7);
    const wallHall = new THREE.Mesh(wallHallGeo, wallMat);
    wallHall.position.set(5, 1.75, 0);
    this.apartmentGroup.add(wallHall);

    // Back Wall
    const backWallGeo = new THREE.BoxGeometry(26, 3.5, 0.2);
    const backWall = new THREE.Mesh(backWallGeo, wallMat);
    backWall.position.set(0, 1.75, -5);
    this.apartmentGroup.add(backWall);

    // 3D Furniture: Living Room Sofa
    const sofaMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, roughness: 0.7 });
    const sofaBase = new THREE.Mesh(new THREE.BoxGeometry(3.5, 0.8, 1.6), sofaMat);
    sofaBase.position.set(0, 0.4, -3.8);
    this.apartmentGroup.add(sofaBase);
    const sofaBack = new THREE.Mesh(new THREE.BoxGeometry(3.5, 1.2, 0.4), sofaMat);
    sofaBack.position.set(0, 1.2, -4.4);
    this.apartmentGroup.add(sofaBack);

    // 3D Ceiling Radar Pod (Center living room)
    const radarGeo = new THREE.CylinderGeometry(0.6, 0.6, 0.2, 32);
    const radarMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.8, roughness: 0.2 });
    this.radarPod = new THREE.Mesh(radarGeo, radarMat);
    this.radarPod.position.set(0, 4.5, 0);
    this.apartmentGroup.add(this.radarPod);

    // Volumetric 3D Radar Wave Cones
    this.radarWaves = [];
    for (let i = 0; i < 3; i++) {
      const ringGeo = new THREE.RingGeometry(0.5, 0.8, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x10b981,
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.set(0, 4.2, 0);
      this.apartmentGroup.add(ring);
      this.radarWaves.push(ring);
    }

    // Shockwave Rings on Floor for Fall Impact
    this.shockwaveRing = new THREE.Mesh(
      new THREE.RingGeometry(0.2, 0.5, 32),
      new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0, side: THREE.DoubleSide })
    );
    this.shockwaveRing.rotation.x = -Math.PI / 2;
    this.shockwaveRing.position.set(-6, 0.05, 0);
    this.apartmentGroup.add(this.shockwaveRing);

    this.scene.add(this.apartmentGroup);
  }

  // -------------------------------------------------------------------------
  // 3D Articulated Humanoid Model (Eleanor Vance)
  // -------------------------------------------------------------------------
  build3DHumanoidEleanor() {
    this.eleanor = new THREE.Group();

    const skinMat = new THREE.MeshStandardMaterial({ color: 0xfbd0b8, roughness: 0.6 });
    const clothesMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.5 }); // Blue cardigan
    const pantsMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.8 });
    const hairMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.4 }); // Silver hair

    // Head
    const headGeo = new THREE.SphereGeometry(0.42, 24, 24);
    const head = new THREE.Mesh(headGeo, skinMat);
    head.position.y = 2.7;
    head.castShadow = true;
    this.eleanor.add(head);

    // Hair cap
    const hairGeo = new THREE.SphereGeometry(0.44, 24, 24, 0, Math.PI * 2, 0, Math.PI / 2);
    const hair = new THREE.Mesh(hairGeo, hairMat);
    hair.position.y = 2.72;
    this.eleanor.add(hair);

    // Torso (Cardigan)
    const torsoGeo = new THREE.CylinderGeometry(0.48, 0.42, 1.2, 16);
    this.torso = new THREE.Mesh(torsoGeo, clothesMat);
    this.torso.position.y = 1.85;
    this.torso.castShadow = true;
    this.eleanor.add(this.torso);

    // Pelvis
    const pelvisGeo = new THREE.CylinderGeometry(0.42, 0.38, 0.3, 16);
    const pelvis = new THREE.Mesh(pelvisGeo, pantsMat);
    pelvis.position.y = 1.15;
    this.eleanor.add(pelvis);

    // Left Leg
    this.leftLeg = new THREE.Group();
    const legGeo = new THREE.CylinderGeometry(0.16, 0.14, 1.1, 12);
    const legMesh1 = new THREE.Mesh(legGeo, pantsMat);
    legMesh1.position.y = -0.55;
    legMesh1.castShadow = true;
    this.leftLeg.add(legMesh1);
    this.leftLeg.position.set(-0.22, 1.05, 0);
    this.eleanor.add(this.leftLeg);

    // Right Leg
    this.rightLeg = new THREE.Group();
    const legMesh2 = new THREE.Mesh(legGeo, pantsMat);
    legMesh2.position.y = -0.55;
    legMesh2.castShadow = true;
    this.rightLeg.add(legMesh2);
    this.rightLeg.position.set(0.22, 1.05, 0);
    this.eleanor.add(this.rightLeg);

    // Left Arm
    this.leftArm = new THREE.Group();
    const armGeo = new THREE.CylinderGeometry(0.12, 0.1, 1.0, 12);
    const armMesh1 = new THREE.Mesh(armGeo, clothesMat);
    armMesh1.position.y = -0.45;
    armMesh1.castShadow = true;
    this.leftArm.add(armMesh1);
    this.leftArm.position.set(-0.55, 2.3, 0);
    this.eleanor.add(this.leftArm);

    // Right Arm with Walking Cane
    this.rightArm = new THREE.Group();
    const armMesh2 = new THREE.Mesh(armGeo, clothesMat);
    armMesh2.position.y = -0.45;
    armMesh2.castShadow = true;
    this.rightArm.add(armMesh2);

    // Walking Cane
    const caneMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.8 });
    const caneGeo = new THREE.CylinderGeometry(0.04, 0.04, 1.4, 8);
    const cane = new THREE.Mesh(caneGeo, caneMat);
    cane.position.set(0.15, -0.6, 0.35);
    this.rightArm.add(cane);

    this.rightArm.position.set(0.55, 2.3, 0);
    this.eleanor.add(this.rightArm);

    // Initial position in Living Room
    this.eleanor.position.set(0, 0, 0);
    this.scene.add(this.eleanor);
  }

  // -------------------------------------------------------------------------
  // 3D Echo Show 15 Smart Display
  // -------------------------------------------------------------------------
  build3DEchoShow() {
    this.echoShow = new THREE.Group();

    // Black frame
    const frameGeo = new THREE.BoxGeometry(2.0, 1.3, 0.15);
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x090d16, roughness: 0.2 });
    const frame = new THREE.Mesh(frameGeo, frameMat);
    this.echoShow.add(frame);

    // Glass display screen
    const screenGeo = new THREE.PlaneGeometry(1.8, 1.1);
    const screenMat = new THREE.MeshBasicMaterial({ color: 0x0284c7 });
    const screen = new THREE.Mesh(screenGeo, screenMat);
    screen.position.z = 0.08;
    this.echoShow.add(screen);

    // Holographic Cyan Ambient Halo Ring
    const haloGeo = new THREE.TorusGeometry(0.4, 0.06, 16, 32);
    const haloMat = new THREE.MeshBasicMaterial({ color: 0x00cae0, wireframe: true });
    this.echoHalo = new THREE.Mesh(haloGeo, haloMat);
    this.echoHalo.position.set(0, 1.0, 0);
    this.echoShow.add(this.echoHalo);

    // Mounted on living room back wall
    this.echoShow.position.set(0, 3.2, -4.8);
    this.scene.add(this.echoShow);
  }

  // -------------------------------------------------------------------------
  // 3D Smart Door with Deadbolt Mechanism
  // -------------------------------------------------------------------------
  build3DSmartDoor() {
    this.smartDoor = new THREE.Group();

    // Wooden Door
    const doorGeo = new THREE.BoxGeometry(2.2, 4.2, 0.2);
    const doorMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.6 });
    const door = new THREE.Mesh(doorGeo, doorMat);
    door.position.y = 2.1;
    this.smartDoor.add(door);

    // Smart Keypad Housing
    const keypadGeo = new THREE.BoxGeometry(0.5, 0.8, 0.1);
    const keypadMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.8 });
    const keypad = new THREE.Mesh(keypadGeo, keypadMat);
    keypad.position.set(0.7, 2.1, 0.12);
    this.smartDoor.add(keypad);

    // Status Indicator Light (Red = Locked, Green = Unlocked)
    const ledGeo = new THREE.SphereGeometry(0.08, 16, 16);
    this.lockLedMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    this.lockLed = new THREE.Mesh(ledGeo, this.lockLedMat);
    this.lockLed.position.set(0.7, 2.4, 0.18);
    this.smartDoor.add(this.lockLed);

    this.smartDoor.position.set(8.5, 0, -2);
    this.scene.add(this.smartDoor);
  }

  // -------------------------------------------------------------------------
  // 3D Boston EMS Ambulance Model
  // -------------------------------------------------------------------------
  build3DAmbulance() {
    this.ambulance = new THREE.Group();

    // Body
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.3 });
    const stripeMat = new THREE.MeshStandardMaterial({ color: 0xef4444 });
    const bodyGeo = new THREE.BoxGeometry(3.5, 1.6, 1.8);
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 1.1;
    this.ambulance.add(body);

    const stripeGeo = new THREE.BoxGeometry(3.55, 0.35, 1.82);
    const stripe = new THREE.Mesh(stripeGeo, stripeMat);
    stripe.position.y = 1.1;
    this.ambulance.add(stripe);

    // Flashing Emergency Lightbar
    const beaconGeo = new THREE.BoxGeometry(0.8, 0.25, 1.2);
    this.beaconMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const beacon = new THREE.Mesh(beaconGeo, this.beaconMat);
    beacon.position.set(0.5, 2.05, 0);
    this.ambulance.add(beacon);

    // Wheels
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.8 });
    const wheelGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.3, 16);
    wheelGeo.rotateZ(Math.PI / 2);

    const w1 = new THREE.Mesh(wheelGeo, wheelMat); w1.position.set(-1.0, 0.4, 0.95); this.ambulance.add(w1);
    const w2 = new THREE.Mesh(wheelGeo, wheelMat); w2.position.set(1.0, 0.4, 0.95); this.ambulance.add(w2);
    const w3 = new THREE.Mesh(wheelGeo, wheelMat); w3.position.set(-1.0, 0.4, -0.95); this.ambulance.add(w3);
    const w4 = new THREE.Mesh(wheelGeo, wheelMat); w4.position.set(1.0, 0.4, -0.95); this.ambulance.add(w4);

    this.ambulance.position.set(8.5, 0, 7);
    this.scene.add(this.ambulance);
  }

  // -------------------------------------------------------------------------
  // Playback & Animation Loop
  // -------------------------------------------------------------------------
  play() {
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    this.isPlaying = true;

    const playBtn = document.getElementById("btnVideoPlayPause");
    if (playBtn) playBtn.textContent = "⏸️ Pause";

    let lastTimestamp = performance.now();

    const loop = (timestamp) => {
      if (!this.isPlaying) return;
      const deltaSec = Math.min((timestamp - lastTimestamp) / 1000, 0.1);
      lastTimestamp = timestamp;

      this.currentTime += deltaSec;
      if (this.currentTime >= this.duration) {
        this.currentTime = 0;
        this.currentSceneIndex = -1;
      }

      this.checkSceneTransition();
      this.updateUI();
      this.update3DAnimations(this.currentTime, deltaSec);

      if (this.renderer && this.scene && this.camera) {
        this.renderer.render(this.scene, this.camera);
      }

      this.animFrameId = requestAnimationFrame(loop);
    };

    this.animFrameId = requestAnimationFrame(loop);
    this.checkSceneTransition(true);
  }

  pause() {
    this.isPlaying = false;
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
    const playBtn = document.getElementById("btnVideoPlayPause");
    if (playBtn) playBtn.textContent = "▶️ Play Video";

    if (window.voiceAudio) {
      window.voiceAudio.stop();
    }
  }

  togglePlay() {
    if (this.isPlaying) this.pause();
    else this.play();
  }

  toggleMute() {
    this.isAudioMuted = !this.isAudioMuted;
    const muteBtn = document.getElementById("btnVideoMute");
    if (muteBtn) {
      muteBtn.textContent = this.isAudioMuted ? "🔇 Audio: Muted" : "🔊 Audio: ON";
      muteBtn.style.color = this.isAudioMuted ? "#f87171" : "#38bdf8";
    }
    if (this.isAudioMuted && window.voiceAudio) {
      window.voiceAudio.stop();
    } else if (!this.isAudioMuted) {
      this.speakSceneNarration(this.getCurrentScene());
    }
  }

  seek(timeInSec) {
    this.currentTime = Math.max(0, Math.min(this.duration - 0.1, timeInSec));
    this.updateUI();
    this.update3DAnimations(this.currentTime, 0.016);
    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
    this.checkSceneTransition(true);
  }

  getCurrentScene() {
    return this.scenes.find(s => this.currentTime >= s.start && this.currentTime < s.end) || this.scenes[0];
  }

  checkSceneTransition(force = false) {
    const scene = this.getCurrentScene();
    if (scene.id !== this.currentSceneIndex || force) {
      this.currentSceneIndex = scene.id;
      this.onSceneEnter(scene);
    }
  }

  onSceneEnter(scene) {
    if (this.isAudioMuted || !window.voiceAudio) return;

    if (scene.id === 0) {
      window.voiceAudio.playAlexaChime();
    } else if (scene.id === 1) {
      window.voiceAudio.playEmergencyTone();
    } else if (scene.id === 2) {
      window.voiceAudio.playAlexaChime();
    } else if (scene.id === 3) {
      window.voiceAudio.playPhoneRing();
    } else if (scene.id === 4) {
      window.voiceAudio.playEmergencyTone();
    }

    this.speakSceneNarration(scene);
  }

  speakSceneNarration(scene) {
    if (this.isAudioMuted || !window.voiceAudio) return;
    const role = scene.speaker === "alexa" ? "alexa" : (scene.speaker === "son" ? "son" : "alexa");
    window.voiceAudio.playSceneNarration(scene.id, scene.narration, role);
  }

  // -------------------------------------------------------------------------
  // 3D Real-Time Animations & Camera Dynamics
  // -------------------------------------------------------------------------
  update3DAnimations(t, delta) {
    if (!this.scene) return;
    const scene = this.getCurrentScene();
    const elapsed = t - scene.start;

    // 1. Smooth 3D Camera Path Interpolation
    const targetCamPos = scene.camPos;
    const targetCamLook = scene.camLook;

    this.camera.position.lerp(new THREE.Vector3(targetCamPos.x, targetCamPos.y, targetCamPos.z), 0.05);
    this.camera.lookAt(targetCamLook.x, targetCamLook.y, targetCamLook.z);

    // 2. Volumetric 3D Ceiling Radar Waves
    if (this.radarWaves) {
      this.radarWaves.forEach((ring, idx) => {
        const rad = ((t * 2 + idx * 1.5) % 4.5) + 0.5;
        ring.scale.set(rad, rad, 1);
        ring.position.y = 4.2 - rad * 0.7;
        ring.material.opacity = Math.max(0, 0.7 - rad / 5);
      });
    }

    // 3. Echo Show 3D Halo Rotation
    if (this.echoHalo) {
      this.echoHalo.rotation.z += 0.04;
      this.echoHalo.rotation.y += 0.02;
    }

    // 4. Scene-Specific 3D Kinematics
    if (scene.id === 0) {
      // Scene 1: Eleanor walking smoothly in living room
      this.emergencyLight.intensity = 0;
      this.lockLedMat.color.setHex(0xef4444);
      this.shockwaveRing.material.opacity = 0;

      const walkZ = Math.sin(t * 1.5) * 2.2;
      this.eleanor.position.set(0, 0, walkZ);
      this.eleanor.rotation.set(0, walkZ > 0 ? 0 : Math.PI, 0);

      // Walking limb swing
      const swing = Math.sin(t * 6) * 0.5;
      this.leftLeg.rotation.x = swing;
      this.rightLeg.rotation.x = -swing;
      this.leftArm.rotation.x = -swing * 0.8;
      this.rightArm.rotation.x = swing * 0.8;
      this.torso.rotation.z = Math.sin(t * 6) * 0.05;

    } else if (scene.id === 1) {
      // Scene 2: 3D Bathroom Fall Kinematics
      this.emergencyLight.intensity = 2.5 + Math.sin(t * 8) * 1.5;
      this.eleanor.position.set(-6, 0, 0);

      const fallProgress = Math.min(1, elapsed / 2.0); // 0 (upright) -> 1 (fallen on floor)
      const fallAngle = fallProgress * (Math.PI / 2);

      // Body tilts backward onto floor
      this.eleanor.rotation.x = -fallAngle;
      this.eleanor.position.y = (1 - fallProgress) * 0 + fallProgress * 0.4;
      this.leftLeg.rotation.x = 0;
      this.rightLeg.rotation.x = 0;
      this.leftArm.rotation.z = fallProgress * 0.8;
      this.rightArm.rotation.z = -fallProgress * 0.8;

      // Red expanding shockwave ring
      const shockScale = ((elapsed * 4) % 6) + 0.5;
      this.shockwaveRing.scale.set(shockScale, shockScale, 1);
      this.shockwaveRing.material.opacity = Math.max(0, 1 - shockScale / 6);

    } else if (scene.id === 2) {
      // Scene 3: Alexa Voice Check-In (Eleanor still, Echo pulsing cyan)
      this.eleanor.position.set(-6, 0.4, 0);
      this.eleanor.rotation.x = -Math.PI / 2;
      this.shockwaveRing.material.opacity = 0;

    } else if (scene.id === 3) {
      // Scene 4: Son David Alerted
      this.eleanor.position.set(-6, 0.4, 0);
      this.eleanor.rotation.x = -Math.PI / 2;

    } else if (scene.id === 4) {
      // Scene 5: Smart Door Unlocked (turns green) & Ambulance drives in
      this.eleanor.position.set(-6, 0.4, 0);
      this.eleanor.rotation.x = -Math.PI / 2;

      // Smart door unlock indicator
      this.lockLedMat.color.setHex(0x10b981);

      // Ambulance beacon flashing
      const strobe = Math.floor(t * 8) % 2;
      this.beaconMat.color.setHex(strobe ? 0xef4444 : 0x00cae0);

      // Ambulance moves towards entrance
      this.ambulance.position.z = Math.max(1, 7 - elapsed * 1.2);
    }
  }

  updateUI() {
    const timeDisplay = document.getElementById("videoTimeDisplay");
    const scrub = document.getElementById("videoProgressBar");
    const captionTitle = document.getElementById("videoCaptionTitle");
    const captionSub = document.getElementById("videoCaptionSub");

    const curM = Math.floor(this.currentTime / 60);
    const curS = Math.floor(this.currentTime % 60);
    const durM = Math.floor(this.duration / 60);
    const durS = Math.floor(this.duration % 60);

    if (timeDisplay) {
      timeDisplay.textContent = `${String(curM).padStart(2, "0")}:${String(curS).padStart(2, "0")} / ${String(durM).padStart(2, "0")}:${String(durS).padStart(2, "0")}`;
    }

    if (scrub) {
      scrub.value = (this.currentTime / this.duration) * 100;
    }

    const scene = this.getCurrentScene();
    if (captionTitle) captionTitle.innerHTML = `<strong>${scene.title}</strong> &bull; <span style="color: var(--neon-cyan);">3D Model: ${scene.room}</span>`;
    if (captionSub) captionSub.textContent = scene.subtitle;

    const chapterButtons = document.querySelectorAll(".btn-chapter");
    chapterButtons.forEach((btn, idx) => {
      if (idx === scene.id) {
        btn.style.borderColor = "var(--neon-blue)";
        btn.style.color = "var(--neon-blue)";
        btn.style.background = "rgba(56, 189, 248, 0.2)";
      } else {
        btn.style.borderColor = "var(--border-glass)";
        btn.style.color = "var(--text-secondary)";
        btn.style.background = "rgba(255, 255, 255, 0.06)";
      }
    });
  }

  resize() {
    if (!this.renderer || !this.camera || !this.canvas) return;
    const parent = this.canvas.parentElement;
    const w = (parent && parent.clientWidth > 100) ? parent.clientWidth : (this.canvas.clientWidth || 760);
    const h = (parent && parent.clientHeight > 200) ? parent.clientHeight : (this.canvas.clientHeight || 400);

    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.renderer.render(this.scene, this.camera);
  }
}

// Global Video Reel Instance
let videoReel = null;

function initVideoReel() {
  if (!videoReel) {
    videoReel = new OperationalVideoReel("demoVideoCanvas");
  }
}

function switchModalVideoMode(mode) {
  const vid = document.getElementById("modalGeminiVideoPlayer");
  const canvas = document.getElementById("demoVideoCanvas");
  const btnVid = document.getElementById("btnModalModeGeminiVideo");
  const btn3D = document.getElementById("btnModalMode3DReel");
  const controlsBar = document.querySelector("#videoDemoModal .video-controls-bar");
  const subsBar = document.querySelector("#videoDemoModal .video-subtitles-bar");

  if (mode === "video") {
    if (vid) {
      vid.style.display = "block";
      vid.play().catch(() => {});
    }
    if (canvas) canvas.style.display = "none";
    if (controlsBar) controlsBar.style.display = "none";
    if (subsBar) subsBar.style.display = "none";
    if (btnVid) btnVid.classList.add("active");
    if (btn3D) btn3D.classList.remove("active");
    if (videoReel) videoReel.pause();
  } else {
    if (vid) {
      vid.pause();
      vid.style.display = "none";
    }
    if (canvas) canvas.style.display = "block";
    if (controlsBar) controlsBar.style.display = "block";
    if (subsBar) subsBar.style.display = "block";
    if (btnVid) btnVid.classList.remove("active");
    if (btn3D) btn3D.classList.add("active");
    initVideoReel();
    if (videoReel) {
      videoReel.resize();
      videoReel.seek(0);
      videoReel.play();
    }
  }
}
window.switchModalVideoMode = switchModalVideoMode;

function openVideoDemoModal() {
  const modal = document.getElementById("videoDemoModal");
  if (modal) {
    modal.style.display = "flex";
    if (window.voiceAudio) {
      window.voiceAudio.getAudioContext();
      if (window.speechSynthesis && window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }
    }
    switchModalVideoMode("video");
  }
}

function closeVideoDemoModal() {
  const modal = document.getElementById("videoDemoModal");
  if (modal) {
    modal.style.display = "none";
    const vid = document.getElementById("modalGeminiVideoPlayer");
    if (vid) vid.pause();
    if (videoReel) videoReel.pause();
  }
}

function seekVideoToScene(sceneIndex) {
  if (!videoReel) initVideoReel();
  if (!videoReel) return;
  const times = [0, 10.5, 20.5, 30.5, 40.5];
  videoReel.seek(times[sceneIndex] || 0);
  videoReel.play();
}

window.addEventListener("resize", () => {
  if (videoReel) {
    videoReel.resize();
  }
});
