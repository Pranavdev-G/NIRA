/**
 * Aegis Ambient Care - Global Multilingual Translation Engine (i18n)
 * Supports 10 Major Global Languages:
 * English (en), Spanish (es), French (fr), German (de), Portuguese (pt),
 * Arabic (ar), Japanese (ja), Russian (ru), Hindi (hi), Chinese (zh)
 */

const TRANSLATIONS = {
  en: {
    appTitle: "Aegis Ambient Care",
    tagline: "Ambient AI Elder Safety",
    seniorName: "Eleanor Vance (Age 79)",
    seniorLoc: "Beacon Hill, Unit 4B",
    userRole: "Family Member / Senior View",
    adminLink: "🛡️ Son / Family Admin Portal",
    seniorLink: "👵 Senior & Home View",
    niraPortalBtn: "NIRA Portal",
    adminPortalLink: "Family Admin Portal →",
    primaryGuardianRole: "Primary Guardian",
    switchUserLink: "Switch",
    yearsOld: "years",
    liveMonitoredSession: "Live Monitored Session • Optical AI Active",

    // Operating Environment
    operatingEnvTitle: "OPERATING ENVIRONMENT:",
    operatingEnvSub: "Switch between Hackathon Interactive Showcase and Real-Time Live Ingestion.",
    demoModeTitle: "1. DEMO MODE",
    demoModeDesc: "Simulated Eleanor Vance (Unit 4B), 3 emergency scenarios, 3D digital twin & radar feeds.",
    demoBadge: "HACKATHON SHOWCASE",
    liveModeTitle: "2. LIVE MODE",
    liveModeDesc: "Live IoT sensor pipeline, browser webcam fall detector, real microphone listener & TextBee SMS.",
    liveBadge: "REAL-TIME INGESTION",

    // Test Scenarios
    testScenarioModes: "Test Scenario Modes:",
    chooseScenario: "👉 Select a Test Scenario:",
    tabScenario1Title: "🟢 Scenario 1: False Alarm",
    tabScenario1Btn: "Normal / Safe (False Alarm)",
    tabScenario1Desc: "Dropped a book. Alexa asks if hurt. Eleanor says \"I'm okay\" ➔ Alert cleared.",
    tabScenario2Title: "🟡 Scenario 2: Calls for Help",
    tabScenario2Btn: "Assisted (Caregiver Alert)",
    tabScenario2Desc: "Eleanor slips in kitchen. Calls \"Help me!\" ➔ Son David alerted via Alexa & Phone.",
    tabScenario3Title: "🔴 Scenario 3: Silent Emergency",
    tabScenario3Btn: "Emergency (911 CAD Dispatch)",
    tabScenario3Desc: "Nighttime bathroom fall. Eleanor is silent ➔ 911 dispatched + Front door unlocked.",

    // Navigation Tabs
    tabOverview: "Overview & Health",
    tabLiveVision: "Live Vision & 3D Floorplan",
    tabVoiceAI: "Voice AI & Alexa+",
    tabCadDispatch: "911 CAD & Caregiver Dispatch",
    tabHistory: "Incident Audit Trail",

    // Live Mode Toolbar & Resident Profile
    liveMonitoringArmed: "LIVE MONITORING ARMED",
    protectionPaused: "PROTECTION PAUSED",
    pauseProtection: "Pause Protection",
    resumeProtection: "Resume Protection",
    realResidentName: "Real Resident Name:",
    residentAge: "Resident Age:",
    monitoredZone: "Monitored Zone:",
    guardianPhone: "Guardian SMS (TextBee):",
    saveLiveProfileBtn: "💾 Save Live Profile",
    slaLatencyLabel: "SLA Latency",
    opticalModelLabel: "Optical Model",
    liveSafetyStateLabel: "Live Safety State",
    zoneLivingRoom: "Living Room",
    zoneBathroom: "Bathroom (High Hazard Tile)",
    zoneBedroom: "Bedroom",
    zoneKitchen: "Kitchen",

    // Live Camera Card
    liveCameraTitle: "1. Live Camera — Trained Fall & Unresponsiveness AI",
    startCameraBtn: "Start Live Camera",
    stopCameraBtn: "Stop Camera",
    cameraInactiveTitle: "Live Camera Inactive",
    cameraInactiveSub: "Click \"Start Live Camera\" to feed real-time video into the custom-trained YOLOv8 fall detector.",
    safetyStatusLabel: "Safety Status",
    detectedActionLabel: "Detected Action",
    unresponsiveTimerLabel: "Unresponsiveness Timer",
    motionDisplacementLabel: "Motion Displacement",
    normalMovementState: "NORMAL MOVEMENT",
    fallDetectedState: "FALL DETECTED",
    unresponsivenessState: "🚨 UNRESPONSIVENESS",

    // Live Voice AI
    liveVoiceTitle: "2. Live Voice AI & Conversational Hub",
    liveVoiceHeader: "LIVE SPEECH RECOGNITION (WEB SPEECH API):",
    liveVoiceInstructions: "Click \"Start Live Mic\" and speak into your microphone. Say \"I'm okay\" or \"Help me, I fell!\" to trigger state transitions in real time.",
    startMicBtn: "Start Live Mic",
    stopMicBtn: "Stop Mic",
    speakPromptBtn: "Speak Alexa Prompt",
    acousticStateLabel: "Acoustic State",
    detectedIntentLabel: "Detected Intent",
    confidenceLabel: "Confidence",
    passiveListeningVal: "Passive Listening",
    micIdleStatus: "MIC IDLE",
    micListeningStatus: "LISTENING...",

    // Live Events & Risk CAD
    liveEventStreamTitle: "Live Event Stream (SSE Transport: /sse)",
    awaitingLiveEvents: "Awaiting real-time events from live camera and microphone...",
    liveRiskCadTitle: "Live Risk & 911 Emergency Packet (EPK)",
    copyEpkBtn: "📋 Copy EPK JSON",

    // Live Geospatial Radar Map
    liveMapRadarTitle: "3. Live Geospatial GIS & Emergency Dispatch Radar",
    detectGpsBtn: "Detect My GPS Location",
    quickPresetsLabel: "Quick City Hubs:",
    mapLocateBtn: "Locate",
    emergencyMatrixTitle: "Nearby Emergency Responders & Healthcare Facilities",


    // Explanations & Overview
    quickExplainer: "Aegis monitors safety via ambient sensors and camera. Alexa checks in gently when movement is irregular. If help is needed, family and 911 are alerted immediately.",
    howItWorks: "⚡ How Aegis AI Protects (4 Steps)",
    playAnimation: "▶️ Play Story Animation",
    step1Title: "👁️ 1. Ambient Sensors See",
    step2Title: "🧠 2. AI Risk Triage",
    step3Title: "🎙️ 3. Alexa Checks In",
    step4Title: "🛡️ 4. Immediate Care Action",
    apartmentMap: "🏠 Apartment Floorplan",
    bathroom: "🚿 Bathroom",
    livingRoom: "🛋️ Living Room",
    kitchen: "🍳 Kitchen",
    bedroom: "🛏️ Bedroom",
    doorLocked: "Front Door Smart Lock: SECURELY LOCKED",
    doorUnlocked: "Front Door Smart Lock: UNLOCKED FOR 911",
    doorPinSub: "Auto-unlocked for Boston EMS First Responders (PIN: 8492)",
    heartRate: "HEART RATE",
    movement: "BODY MOVEMENT",
    appleWatch: "APPLE WATCH",
    connected: "Connected",
    alexaAsks: "🤖 Alexa Asks Eleanor:",
    seniorReply: "👵 Eleanor's Voice Reply:",
    answerForMom: "👉 Try answering for Eleanor (Click any button):",
    btnImOk: "🟢 \"I'm okay\"",
    btnHelpMe: "🟡 \"Help me!\"",
    btnSilent: "🔴 <Silence / 20s>",
    sonTitle: "Son David Vance (Admin)",
    emsTitle: "Boston EMS 911 Dispatch",
    safeStatus: "🟢 ALL CLEAR & SAFE",
    checkingStatus: "🟡 CHECKING IN / CARE ALERT",
    emergencyStatus: "🔴 EMERGENCY DISPATCH ACTIVE",
    videoGuideBtn: "🎬 How to Operate Guide"
  },

  es: {
    appTitle: "Aegis Ambient Care",
    tagline: "IA Ambiental para Seguridad de Adultos Mayores",
    seniorName: "Eleanor Vance (79 años)",
    seniorLoc: "Beacon Hill, Unidad 4B",
    userRole: "Familiar / Vista del Paciente",
    adminLink: "🛡️ Portal de Administrador (Hijo)",
    seniorLink: "👵 Vista Familiar / Mayor",
    niraPortalBtn: "Portal NIRA",
    adminPortalLink: "Portal de Administrador →",
    primaryGuardianRole: "Guardián Principal",
    switchUserLink: "Cambiar",
    yearsOld: "años",
    liveMonitoredSession: "Sesión Monitoreada en Vivo • IA Óptica Activa",

    // Operating Environment
    operatingEnvTitle: "ENTORNO OPERATIVO:",
    operatingEnvSub: "Alterna entre la demostración interactiva y la ingestión en tiempo real.",
    demoModeTitle: "1. MODO DEMOSTRACIÓN",
    demoModeDesc: "Eleanor Vance simulada (Unidad 4B), 3 escenarios de emergencia, gemelo 3D y radar.",
    demoBadge: "DEMOSTRACIÓN INTERACTIVA",
    liveModeTitle: "2. MODO EN VIVO",
    liveModeDesc: "Pipeline de sensores reales, detector de caídas por cámara web, micrófono en vivo y SMS.",
    liveBadge: "INGESTIÓN EN TIEMPO REAL",

    // Test Scenarios
    testScenarioModes: "Modos de Escenario:",
    chooseScenario: "👉 Selecciona un Escenario de Prueba:",
    tabScenario1Title: "🟢 Escenario 1: Falsa Alarma",
    tabScenario1Btn: "Normal / Seguro (Falsa Alarma)",
    tabScenario1Desc: "Se cayó un libro. Alexa pregunta. Eleanor dice \"Estoy bien\" ➔ Alarma cancelada.",
    tabScenario2Title: "🟡 Escenario 2: Pide Ayuda",
    tabScenario2Btn: "Asistido (Alerta Familiar)",
    tabScenario2Desc: "Eleanor resbala en cocina. Grita \"¡Ayuda!\" ➔ Su hijo David es alertado por teléfono y Alexa.",
    tabScenario3Title: "🔴 Escenario 3: Emergencia Silenciosa",
    tabScenario3Btn: "Emergencia (Despacho 911)",
    tabScenario3Desc: "Caída nocturna en baño sin respuesta ➔ 911 enviado + Puerta principal abierta.",

    // Navigation Tabs
    tabOverview: "Resumen y Salud",
    tabLiveVision: "Visión en Vivo y Plano 3D",
    tabVoiceAI: "Voz IA y Alexa+",
    tabCadDispatch: "911 y Despacho de Cuidado",
    tabHistory: "Historial de Incidentes",

    // Live Mode Toolbar & Resident Profile
    liveMonitoringArmed: "MONITOREO EN VIVO ARMADO",
    protectionPaused: "PROTECCIÓN EN PAUSA",
    pauseProtection: "Pausar Protección",
    resumeProtection: "Reanudar Protección",
    realResidentName: "Nombre del Residente Real:",
    residentAge: "Edad del Residente:",
    monitoredZone: "Zona Monitoreada:",
    guardianPhone: "SMS del Guardián (TextBee):",
    saveLiveProfileBtn: "💾 Guardar Perfil en Vivo",
    slaLatencyLabel: "Latencia SLA",
    opticalModelLabel: "Modelo Óptico",
    liveSafetyStateLabel: "Estado de Seguridad en Vivo",
    zoneLivingRoom: "Sala de Estar",
    zoneBathroom: "Baño (Piso Peligroso)",
    zoneBedroom: "Dormitorio",
    zoneKitchen: "Cocina",

    // Live Camera Card
    liveCameraTitle: "1. Cámara en Vivo — IA de Caídas e Inconsciencia",
    startCameraBtn: "Iniciar Cámara en Vivo",
    stopCameraBtn: "Detener Cámara",
    cameraInactiveTitle: "Cámara en Vivo Inactiva",
    cameraInactiveSub: "Haz clic en \"Iniciar Cámara\" para alimentar el video en tiempo real al detector YOLOv8 entrenado.",
    safetyStatusLabel: "Estado de Seguridad",
    detectedActionLabel: "Acción Detectada",
    unresponsiveTimerLabel: "Temporizador de Inconsciencia",
    motionDisplacementLabel: "Desplazamiento de Movimiento",
    normalMovementState: "MOVIMIENTO NORMAL",
    fallDetectedState: "CAÍDA DETECTADA",
    unresponsivenessState: "🚨 INCONSCIENCIA (ALERTA)",

    // Live Voice AI
    liveVoiceTitle: "2. Voz IA en Vivo y Centro de Diálogo",
    liveVoiceHeader: "RECONOCIMIENTO DE VOZ EN VIVO (WEB SPEECH API):",
    liveVoiceInstructions: "Haz clic en \"Iniciar Micrófono\" y habla. Di \"Estoy bien\" o \"¡Ayuda, me caí!\" para activar transiciones en tiempo real.",
    startMicBtn: "Iniciar Micrófono",
    stopMicBtn: "Detener Micrófono",
    speakPromptBtn: "Reproducir Pregunta Alexa",
    acousticStateLabel: "Estado Acústico",
    detectedIntentLabel: "Intención Detectada",
    confidenceLabel: "Confianza",
    passiveListeningVal: "Escucha Pasiva",
    micIdleStatus: "MIC EN ESPERA",
    micListeningStatus: "ESCUCHANDO...",

    // Live Events & Risk CAD
    liveEventStreamTitle: "Flujo de Eventos en Vivo (Transporte SSE: /sse)",
    awaitingLiveEvents: "Esperando eventos en tiempo real de la cámara y el micrófono...",
    liveRiskCadTitle: "Riesgo en Vivo y Paquete de Emergencia 911 (EPK)",
    copyEpkBtn: "📋 Copiar JSON del EPK",

    // Explanations & Overview
    quickExplainer: "Aegis vigila la seguridad mediante sensores ambientales. Alexa pregunta amablemente si todo está bien. Si necesita ayuda, se avisa a la familia y al 911 de inmediato.",
    howItWorks: "⚡ Cómo Protege la IA de Aegis (4 Pasos)",
    playAnimation: "▶️ Reproducir Animación",
    step1Title: "👁️ 1. Sensores Detectan",
    step2Title: "🧠 2. Evaluación de Riesgo IA",
    step3Title: "🎙️ 3. Alexa Pregunta",
    step4Title: "🛡️ 4. Acción de Cuidado Inmediata",
    apartmentMap: "🏠 Mapa del Apartamento de Eleanor",
    bathroom: "🚿 Baño",
    livingRoom: "🛋️ Sala de Estar",
    kitchen: "🍳 Cocina",
    bedroom: "🛏️ Dormitorio",
    doorLocked: "Cerradura Inteligente: BLOQUEADA",
    doorUnlocked: "Cerradura Inteligente: DESBLOQUEADA PARA 911",
    doorPinSub: "Desbloqueada para paramédicos del 911 (PIN: 8492)",
    heartRate: "RITMO CARDÍACO",
    movement: "MOVIMIENTO",
    appleWatch: "APPLE WATCH",
    connected: "Conectado",
    alexaAsks: "🤖 Alexa le pregunta a Eleanor:",
    seniorReply: "👵 Respuesta de Voz de Eleanor:",
    answerForMom: "👉 Prueba responder por Eleanor (Haz clic):",
    btnImOk: "🟢 \"Estoy bien\"",
    btnHelpMe: "🟡 \"¡Ayúdame!\"",
    btnSilent: "🔴 <Silencio / 20s>",
    sonTitle: "Hijo David Vance (Admin)",
    emsTitle: "Despacho EMS 911",
    safeStatus: "🟢 TODO EN ORDEN Y SEGURO",
    checkingStatus: "🟡 VERIFICANDO / ALERTA FAMILIAR",
    emergencyStatus: "🔴 EMERGENCIA 911 ACTIVA",
    videoGuideBtn: "🎬 Guía de Operación"
  },

  fr: {
    appTitle: "Aegis Ambient Care",
    tagline: "IA Ambiante pour la Sécurité des Aînés",
    seniorName: "Eleanor Vance (79 ans)",
    seniorLoc: "Beacon Hill, Unité 4B",
    userRole: "Famille / Vue Patient",
    adminLink: "🛡️ Portail Administrateur (Fils)",
    seniorLink: "👵 Vue Senior & Domicile",
    niraPortalBtn: "Portail NIRA",
    adminPortalLink: "Portail Admin Famille →",
    primaryGuardianRole: "Tuteur Principal",
    switchUserLink: "Changer",
    yearsOld: "ans",
    liveMonitoredSession: "Session Surveillée en Direct • IA Optique Active",

    operatingEnvTitle: "ENVIRONNEMENT OPÉRATIONNEL :",
    operatingEnvSub: "Basculez entre la vitrine interactive et l'ingestion réelle.",
    demoModeTitle: "1. MODE DÉMO",
    demoModeDesc: "Eleanor Vance simulée (Unité 4B), 3 scénarios d'urgence, jumeau 3D & radar.",
    demoBadge: "VITRINE HACKATHON",
    liveModeTitle: "2. MODE EN DIRECT",
    liveModeDesc: "Capteurs réels, détection de chute par webcam, micro en direct & SMS.",
    liveBadge: "INGESTION EN TEMPS RÉEL",

    testScenarioModes: "Modes de Scénario :",
    chooseScenario: "👉 Choisissez un Scénario de Test :",
    tabScenario1Title: "🟢 Scénario 1 : Fausse Alerte",
    tabScenario1Btn: "Normal / Sécurisé (Fausse Alerte)",
    tabScenario1Desc: "Un livre tombe. Alexa demande. Eleanor répond \"Je vais bien\" ➔ Alerte levée.",
    tabScenario2Title: "🟡 Scénario 2 : Appel à l'Aide",
    tabScenario2Btn: "Assisté (Alerte Proche)",
    tabScenario2Desc: "Eleanor glisse en cuisine et appelle à l'aide ➔ David alerté via Alexa et téléphone.",
    tabScenario3Title: "🔴 Scénario 3 : Urgence Silencieuse",
    tabScenario3Btn: "Urgence (Envoi 911 / Samu)",
    tabScenario3Desc: "Chute nocturne sans réponse ➔ 911 envoyé + Porte déverrouillée.",

    tabOverview: "Aperçu & Santé",
    tabLiveVision: "Vision en Direct & Plan 3D",
    tabVoiceAI: "IA Vocale & Alexa+",
    tabCadDispatch: "Urgences 911 & Secours",
    tabHistory: "Historique des Incidents",

    liveMonitoringArmed: "SURVEILLANCE EN DIRECT ACTIVÉE",
    protectionPaused: "PROTECTION EN PAUSE",
    pauseProtection: "Mettre en Pause",
    resumeProtection: "Reprendre la Protection",
    realResidentName: "Nom Réel du Résident :",
    residentAge: "Âge du Résident :",
    monitoredZone: "Zone Surveillée :",
    guardianPhone: "SMS Tuteur (TextBee) :",
    saveLiveProfileBtn: "💾 Enregistrer le Profil",
    slaLatencyLabel: "Latence SLA",
    opticalModelLabel: "Modèle Optique",
    liveSafetyStateLabel: "État de Sécurité en Direct",
    zoneLivingRoom: "Salon",
    zoneBathroom: "Salle de Bain (Sol Dangereux)",
    zoneBedroom: "Chambre",
    zoneKitchen: "Cuisine",

    liveCameraTitle: "1. Caméra en Direct — IA Chute & Inconscience",
    startCameraBtn: "Démarrer la Caméra",
    stopCameraBtn: "Arrêter la Caméra",
    cameraInactiveTitle: "Caméra en Direct Inactive",
    cameraInactiveSub: "Cliquez sur \"Démarrer la Caméra\" pour transmettre le flux vidéo au modèle YOLOv8 entraîné.",
    safetyStatusLabel: "Statut de Sécurité",
    detectedActionLabel: "Action Détectée",
    unresponsiveTimerLabel: "Minuteur d'Inconscience",
    motionDisplacementLabel: "Déplacement de Mouvement",
    normalMovementState: "MOUVEMENT NORMAL",
    fallDetectedState: "CHUTE DÉTECTÉE",
    unresponsivenessState: "🚨 INCONSCIENCE (ALERTE)",

    liveVoiceTitle: "2. IA Vocale en Direct & Hub d'Écoute",
    liveVoiceHeader: "RECONNAISSANCE VOCALE (WEB SPEECH API) :",
    liveVoiceInstructions: "Cliquez sur \"Démarrer le Micro\" et parlez. Dites \"Je vais bien\" ou \"À l'aide, je suis tombé !\" pour tester en direct.",
    startMicBtn: "Démarrer le Micro",
    stopMicBtn: "Arrêter le Micro",
    speakPromptBtn: "Énoncer la Question Alexa",
    acousticStateLabel: "État Acoustique",
    detectedIntentLabel: "Intention Détectée",
    confidenceLabel: "Confiance",
    passiveListeningVal: "Écoute Passive",
    micIdleStatus: "MICRO EN ATTENTE",
    micListeningStatus: "ÉCOUTE EN COURS...",

    liveEventStreamTitle: "Flux d'Événements en Direct (Transport SSE : /sse)",
    awaitingLiveEvents: "En attente d'événements réels de la caméra et du micro...",
    liveRiskCadTitle: "Risque en Direct & Dossier d'Urgence 911 (EPK)",
    copyEpkBtn: "📋 Copier JSON EPK",

    quickExplainer: "Aegis veille sur vos aînés via capteurs discrets et caméras. Alexa intervient avec bienveillance en cas d'anomalie.",
    howItWorks: "⚡ Comment l'IA Aegis Protège (4 Étapes)",
    playAnimation: "▶️ Lancer l'Animation",
    step1Title: "👁️ 1. Les Capteurs Détectent",
    step2Title: "🧠 2. Évaluation du Risque IA",
    step3Title: "🎙️ 3. Vérification par Alexa",
    step4Title: "🛡️ 4. Intervention Immédiate",
    apartmentMap: "🏠 Plan du Logement",
    bathroom: "🚿 Salle de Bain",
    livingRoom: "🛋️ Salon",
    kitchen: "🍳 Cuisine",
    bedroom: "🛏️ Chambre",
    doorLocked: "Serrure Connectée : VERROUILLÉE",
    doorUnlocked: "Serrure Connectée : DÉVERROUILLÉE POUR 911",
    doorPinSub: "Déverrouillage automatique pour les secours (Code: 8492)",
    heartRate: "FRÉQUENCE CARDIAQUE",
    movement: "MOUVEMENT",
    appleWatch: "APPLE WATCH",
    connected: "Connecté",
    alexaAsks: "🤖 Alexa demande :",
    seniorReply: "👵 Réponse Vocale :",
    answerForMom: "👉 Testez une réponse :",
    btnImOk: "🟢 \"Tout va bien\"",
    btnHelpMe: "🟡 \"À l'aide !\"",
    btnSilent: "🔴 <Silence / 20s>",
    sonTitle: "Fils David Vance (Admin)",
    emsTitle: "Régulation Urgences 911",
    safeStatus: "🟢 TOUT VA BIEN & EN SÉCURITÉ",
    checkingStatus: "🟡 VÉRIFICATION / ALERTE FAMILLE",
    emergencyStatus: "🔴 DÉPLOIEMENT D'URGENCE ACTIF",
    videoGuideBtn: "🎬 Guide d'Utilisation"
  },

  de: {
    appTitle: "Aegis Ambient Care",
    tagline: "Ambient-KI Seniorensicherheit",
    seniorName: "Eleanor Vance (79 Jahre)",
    seniorLoc: "Beacon Hill, Einheit 4B",
    userRole: "Familienmitglied / Seniorenansicht",
    adminLink: "🛡️ Sohn / Familien-Admin-Portal",
    seniorLink: "👵 Senioren- & Hauptansicht",
    niraPortalBtn: "NIRA Portal",
    adminPortalLink: "Familien-Admin-Portal →",
    primaryGuardianRole: "Hauptbetreuer",
    switchUserLink: "Wechseln",
    yearsOld: "Jahre",
    liveMonitoredSession: "Live-Überwachungssitzung • Optische KI Aktiv",

    operatingEnvTitle: "BETRIEBSUMGEBUNG:",
    operatingEnvSub: "Wechseln Sie zwischen interaktiver Demonstration und Echtzeit-Erfassung.",
    demoModeTitle: "1. DEMO-MODUS",
    demoModeDesc: "Simulierte Eleanor Vance (Einheit 4B), 3 Notfallszenarien, 3D-Zwilling & Radar.",
    demoBadge: "HACKATHON SHOWCASE",
    liveModeTitle: "2. LIVE-MODUS",
    liveModeDesc: "Echte Sensoren, Webcam-Sturzerkennung, Live-Mikrofon & SMS-Benachrichtigung.",
    liveBadge: "ECHTZEIT-INGESTION",

    testScenarioModes: "Testszenarien:",
    chooseScenario: "👉 Testszenario auswählen:",
    tabScenario1Title: "🟢 Szenario 1: Fehlalarm",
    tabScenario1Btn: "Normal / Sicher (Fehlalarm)",
    tabScenario1Desc: "Buch fallengelassen. Alexa fragt. Eleanor sagt \"Alles gut\" ➔ Alarm aufgehoben.",
    tabScenario2Title: "🟡 Szenario 2: Hilferuf",
    tabScenario2Btn: "Betreut (Angehörigen-Alarm)",
    tabScenario2Desc: "Eleanor rutscht in Küche aus und ruft \"Hilfe!\". Sohn David wird alarmiert.",
    tabScenario3Title: "🔴 Szenario 3: Stiller Notfall",
    tabScenario3Btn: "Notfall (911 Rettungsdienst)",
    tabScenario3Desc: "Nächtlicher Sturz im Bad ohne Antwort ➔ 911 alarmiert + Haustür geöffnet.",

    tabOverview: "Übersicht & Gesundheit",
    tabLiveVision: "Live-Bild & 3D-Grundriss",
    tabVoiceAI: "Sprach-KI & Alexa+",
    tabCadDispatch: "911 Notruf & Rettungsdienst",
    tabHistory: "Ereignis-Protokoll",

    liveMonitoringArmed: "LIVE-ÜBERWACHUNG SCHARFGESCHALTET",
    protectionPaused: "SCHUTZ PAUSIERT",
    pauseProtection: "Schutz Pausieren",
    resumeProtection: "Schutz Fortsetzen",
    realResidentName: "Name der betreuten Person:",
    residentAge: "Alter der Person:",
    monitoredZone: "Überwachter Bereich:",
    guardianPhone: "Angehörigen-SMS (TextBee):",
    saveLiveProfileBtn: "💾 Live-Profil Speichern",
    slaLatencyLabel: "SLA-Latenz",
    opticalModelLabel: "Optisches Modell",
    liveSafetyStateLabel: "Live-Sicherheitsstatus",
    zoneLivingRoom: "Wohnzimmer",
    zoneBathroom: "Badezimmer (Rutschgefahr)",
    zoneBedroom: "Schlafzimmer",
    zoneKitchen: "Küche",

    liveCameraTitle: "1. Live-Kamera — Trainierte Sturz- & Reaktionslosigkeits-KI",
    startCameraBtn: "Live-Kamera Starten",
    stopCameraBtn: "Kamera Stoppen",
    cameraInactiveTitle: "Live-Kamera Inaktiv",
    cameraInactiveSub: "Klicken Sie auf \"Live-Kamera Starten\", um den Echtzeit-Videostream mit dem trainierten YOLOv8-Modell zu analysieren.",
    safetyStatusLabel: "Sicherheitsstatus",
    detectedActionLabel: "Erkannte Aktivität",
    unresponsiveTimerLabel: "Reaktionslosigkeits-Timer",
    motionDisplacementLabel: "Bewegungsrate",
    normalMovementState: "NORMALE BEWEGUNG",
    fallDetectedState: "STURZ ERKANNT",
    unresponsivenessState: "🚨 REAKTIONSLOSIGKEIT (ALARM)",

    liveVoiceTitle: "2. Sprach-KI & Kommunikations-Hub",
    liveVoiceHeader: "LIVE-SPRACHERKENNUNG (WEB SPEECH API):",
    liveVoiceInstructions: "Klicken Sie auf \"Mikrofon Starten\" und sprechen Sie. Sagen Sie \"Mir geht es gut\" oder \"Hilfe!\" für Live-Reaktionen.",
    startMicBtn: "Mikrofon Starten",
    stopMicBtn: "Mikrofon Stoppen",
    speakPromptBtn: "Alexa-Frage Abspielen",
    acousticStateLabel: "Akustik-Status",
    detectedIntentLabel: "Erkannte Absicht",
    confidenceLabel: "Zuverlässigkeit",
    passiveListeningVal: "Passives Zuhören",
    micIdleStatus: "MIKRO IN BEREITSCHAFT",
    micListeningStatus: "HÖRT ZU...",

    liveEventStreamTitle: "Live-Ereignisstrom (SSE-Transport: /sse)",
    awaitingLiveEvents: "Warte auf Echtzeit-Ereignisse von Kamera und Mikrofon...",
    liveRiskCadTitle: "Live-Risiko & 911 Notfall-Datenpaket (EPK)",
    copyEpkBtn: "📋 EPK-JSON Kopieren",

    quickExplainer: "Aegis überwacht die Sicherheit mit Umgebungssensoren. Alexa fragt einfühlsam nach dem Befinden.",
    howItWorks: "⚡ So schützt Aegis KI (4 Schritte)",
    playAnimation: "▶️ Story-Animation abspielen",
    step1Title: "👁️ 1. Sensoren erkennen",
    step2Title: "🧠 2. KI-Risikoanalyse",
    step3Title: "🎙️ 3. Alexa prüft nach",
    step4Title: "🛡️ 4. Sofortige Schutzmaßnahme",
    apartmentMap: "🏠 Grundriss der Wohnung",
    bathroom: "🚿 Badezimmer",
    livingRoom: "🛋️ Wohnzimmer",
    kitchen: "🍳 Küche",
    bedroom: "🛏️ Schlafzimmer",
    doorLocked: "Smart Lock: SICHER VERRIEGELT",
    doorUnlocked: "Smart Lock: FÜR NOTRUF ENTSPERRT",
    doorPinSub: "Automatisch für Notärzte geöffnet (PIN: 8492)",
    heartRate: "HERZFREQUENZ",
    movement: "KÖRPERBEWEGUNG",
    appleWatch: "APPLE WATCH",
    connected: "Verbunden",
    alexaAsks: "🤖 Alexa fragt:",
    seniorReply: "👵 Antwort:",
    answerForMom: "👉 Antworten Sie:",
    btnImOk: "🟢 \"Alles in Ordnung\"",
    btnHelpMe: "🟡 \"Hilf mir!\"",
    btnSilent: "🔴 <Stille / 20 Sek.>",
    sonTitle: "Sohn David Vance (Admin)",
    emsTitle: "Rettungsdienst 911",
    safeStatus: "🟢 ALLES SICHER & WOHLAUF",
    checkingStatus: "🟡 ÜBERPRÜFUNG LÄUFT",
    emergencyStatus: "🔴 NOTFALL-EINSATZ AKTIV",
    videoGuideBtn: "🎬 Video-Bedienungsanleitung"
  },

  pt: {
    appTitle: "Aegis Ambient Care",
    tagline: "IA Ambiente para Segurança de Idosos",
    seniorName: "Eleanor Vance (79 anos)",
    seniorLoc: "Beacon Hill, Apto 4B",
    userRole: "Familiar / Visão do Idoso",
    adminLink: "🛡️ Portal do Administrador (Filho)",
    seniorLink: "👵 Visão Familiar / Idoso",
    niraPortalBtn: "Portal NIRA",
    adminPortalLink: "Portal do Administrador →",
    primaryGuardianRole: "Guardião Principal",
    switchUserLink: "Trocar",
    yearsOld: "anos",
    liveMonitoredSession: "Sessão Monitorada ao Vivo • IA Óptica Ativa",

    operatingEnvTitle: "AMBIENTE OPERACIONAL:",
    operatingEnvSub: "Alterne entre a demonstração interativa e a ingestão em tempo real.",
    demoModeTitle: "1. MODO DEMO",
    demoModeDesc: "Eleanor Vance simulada (Apto 4B), 3 cenários de emergência, gêmeo 3D e radar.",
    demoBadge: "VITRINE DO HACKATHON",
    liveModeTitle: "2. MODO AO VIVO",
    liveModeDesc: "Pipeline de sensores reais, detecção de queda por webcam, microfone ao vivo e SMS.",
    liveBadge: "INGESTÃO EM TEMPO REAL",

    testScenarioModes: "Modos de Cenário:",
    chooseScenario: "👉 Selecione um Cenário de Teste:",
    tabScenario1Title: "🟢 Cenário 1: Alarme Falso",
    tabScenario1Btn: "Normal / Seguro (Alarme Falso)",
    tabScenario1Desc: "Livro caiu. Alexa pergunta. Eleanor diz \"Estou bem\" ➔ Alerta cancelado.",
    tabScenario2Title: "🟡 Cenário 2: Pedido de Ajuda",
    tabScenario2Btn: "Assistido (Alerta Familiar)",
    tabScenario2Desc: "Eleanor escorrega na cozinha e grita \"Socorro!\". Filho David é alertado.",
    tabScenario3Title: "🔴 Cenário 3: Emergência Silenciosa",
    tabScenario3Btn: "Emergência (Resgate 911)",
    tabScenario3Desc: "Queda noturna no banheiro sem resposta ➔ 911 acionado + Porta destrancada.",

    tabOverview: "Visão Geral & Saúde",
    tabLiveVision: "Visão ao Vivo & Planta 3D",
    tabVoiceAI: "Voz IA & Alexa+",
    tabCadDispatch: "Resgate 911 & Socorristas",
    tabHistory: "Histórico de Incidentes",

    liveMonitoringArmed: "MONITORAMENTO AO VIVO ATIVO",
    protectionPaused: "PROTEÇÃO PAUSADA",
    pauseProtection: "Pausar Proteção",
    resumeProtection: "Retomar Proteção",
    realResidentName: "Nome Real do Residente:",
    residentAge: "Idade do Residente:",
    monitoredZone: "Zona Monitorada:",
    guardianPhone: "SMS do Guardião (TextBee):",
    saveLiveProfileBtn: "💾 Salvar Perfil ao Vivo",
    slaLatencyLabel: "Latência SLA",
    opticalModelLabel: "Modelo Óptico",
    liveSafetyStateLabel: "Estado de Segurança ao Vivo",
    zoneLivingRoom: "Sala de Estar",
    zoneBathroom: "Banheiro (Piso Perigoso)",
    zoneBedroom: "Quarto",
    zoneKitchen: "Cozinha",

    liveCameraTitle: "1. Câmera ao Vivo — IA de Queda & Inconsciência",
    startCameraBtn: "Iniciar Câmera ao Vivo",
    stopCameraBtn: "Parar Câmera",
    cameraInactiveTitle: "Câmera ao Vivo Inativa",
    cameraInactiveSub: "Clique em \"Iniciar Câmera\" para analisar o vídeo em tempo real com o modelo YOLOv8 treinado.",
    safetyStatusLabel: "Status de Segurança",
    detectedActionLabel: "Ação Detectada",
    unresponsiveTimerLabel: "Temporizador de Inconsciência",
    motionDisplacementLabel: "Deslocamento de Movimento",
    normalMovementState: "MOVIMENTO NORMAL",
    fallDetectedState: "QUEDA DETECTADA",
    unresponsivenessState: "🚨 INCONSCIÊNCIA (ALERTA)",

    liveVoiceTitle: "2. Voz IA ao Vivo & Central de Diálogo",
    liveVoiceHeader: "RECONHECIMENTO DE VOZ AO VIVO (WEB SPEECH API):",
    liveVoiceInstructions: "Clique em \"Iniciar Microfone\" e fale. Diga \"Estou bem\" ou \"Socorro!\" para disparar eventos.",
    startMicBtn: "Iniciar Microfone",
    stopMicBtn: "Parar Microfone",
    speakPromptBtn: "Reproduzir Pergunta da Alexa",
    acousticStateLabel: "Estado Acústico",
    detectedIntentLabel: "Intenção Detectada",
    confidenceLabel: "Confiança",
    passiveListeningVal: "Escuta Passiva",
    micIdleStatus: "MICROFONE EM ESPERA",
    micListeningStatus: "ESCUTANDO...",

    liveEventStreamTitle: "Fluxo de Eventos ao Vivo (Transporte SSE: /sse)",
    awaitingLiveEvents: "Aguardando eventos em tempo real da câmera e do microfone...",
    liveRiskCadTitle: "Risco ao Vivo & Pacote de Emergência 911 (EPK)",
    copyEpkBtn: "📋 Copiar JSON do EPK",

    quickExplainer: "O Aegis monitora a segurança via sensores ambientais. A Alexa pergunta gentilmente se está tudo bem.",
    howItWorks: "⚡ Como a IA Aegis Protege (4 Etapas)",
    playAnimation: "▶️ Assistir Animação",
    step1Title: "👁️ 1. Sensores Detectam",
    step2Title: "🧠 2. Análise de Risco IA",
    step3Title: "🎙️ 3. Checagem pela Alexa",
    step4Title: "🛡️ 4. Resposta Imediata",
    apartmentMap: "🏠 Planta do Apartamento",
    bathroom: "🚿 Banheiro",
    livingRoom: "🛋️ Sala de Estar",
    kitchen: "🍳 Cozinha",
    bedroom: "🛏️ Quarto",
    doorLocked: "Fechadura Inteligente: TRANCADA",
    doorUnlocked: "Fechadura Inteligente: DESTRANCADA PARA 911",
    doorPinSub: "Destrancada automaticamente para os socorristas (PIN: 8492)",
    heartRate: "FREQUÊNCIA CARDÍACA",
    movement: "MOVIMENTO CORPORAL",
    appleWatch: "APPLE WATCH",
    connected: "Conectado",
    alexaAsks: "🤖 Alexa pergunta:",
    seniorReply: "👵 Resposta:",
    answerForMom: "👉 Tente responder:",
    btnImOk: "🟢 \"Estou bem\"",
    btnHelpMe: "🟡 \"Preciso de ajuda!\"",
    btnSilent: "🔴 <Silêncio / 20s>",
    sonTitle: "Filho David Vance (Admin)",
    emsTitle: "Resgate 911",
    safeStatus: "🟢 TUDO SEGURO E BEM",
    checkingStatus: "🟡 CHECANDO / ALERTA",
    emergencyStatus: "🔴 RESGATE DE EMERGÊNCIA ATIVO",
    videoGuideBtn: "🎬 Guia de Operação"
  },

  ar: {
    appTitle: "إيجيس للرعاية الذكية (Aegis Care)",
    tagline: "الذكاء الاصطناعي لحماية وسلامة كبار السن",
    seniorName: "إليانور فانس (العمر 79)",
    seniorLoc: "بيكون هيل، شقة 4B",
    userRole: "عرض أفراد العائلة / المريض",
    adminLink: "🛡️ بوابة الابن المشرف",
    seniorLink: "👵 واجهة كبير السن والمنزل",
    niraPortalBtn: "بوابة NIRA",
    adminPortalLink: "بوابة العائلة الإدارية ←",
    primaryGuardianRole: "المشرف الأساسي",
    switchUserLink: "تبديل",
    yearsOld: "سنة",
    liveMonitoredSession: "جلسة مراقبة حية • الذكاء البصري نشط",

    operatingEnvTitle: "بيئة التشغيل:",
    operatingEnvSub: "التبديل بين العرض التوضيحي والمراقبة الحية في الوقت الفعلي.",
    demoModeTitle: "1. وضع العرض التجريبي",
    demoModeDesc: "إليانور فانس محاكاة (الوحدة 4B)، 3 سيناريوهات طوارئ، توأم ثلاثي الأبعاد ورادار.",
    demoBadge: "عرض تفاعلي",
    liveModeTitle: "2. الوضع المباشر (حي)",
    liveModeDesc: "كاميرا حية مع كشف السقوط، ميكروفون وتنبيهات SMS حقيقية.",
    liveBadge: "بث حي ومباشر",

    testScenarioModes: "سيناريوهات الاختبار:",
    chooseScenario: "👉 اختر سيناريو للاختبار:",
    tabScenario1Title: "🟢 سيناريو 1: إنذار كاذب",
    tabScenario1Btn: "طبيعي / آمن (إنذار كاذب)",
    tabScenario1Desc: "سقط كتاب. أليكسا تسأل. إليانور تجيب \"أنا بخير\" ➔ إلغاء الإنذار.",
    tabScenario2Title: "🟡 سيناريو 2: طلب المساعدة",
    tabScenario2Btn: "مساعدة (تنبيه العائلة)",
    tabScenario2Desc: "إليانور تنزلق وتطلب النجدة ➔ إشعار فوري للابن ديفيد.",
    tabScenario3Title: "🔴 سيناريو 3: طوارئ صامتة",
    tabScenario3Btn: "طوارئ (إسعاف 911)",
    tabScenario3Desc: "سقوط في الحمام بدون رد ➔ إرسال الإسعاف وفتح قفل الباب تلقائياً.",

    tabOverview: "نظرة عامة وصحة",
    tabLiveVision: "الرؤية الحية والمخطط 3D",
    tabVoiceAI: "الذكاء الصوتي وأليكسا",
    tabCadDispatch: "إسعاف 911 والاستجابة",
    tabHistory: "سجل الأحداث",

    liveMonitoringArmed: "المراقبة الحية مفعلة",
    protectionPaused: "الحماية متوقفة مؤقتاً",
    pauseProtection: "إيقاف مؤقت",
    resumeProtection: "استئناف الحماية",
    realResidentName: "اسم الساكن الفعلي:",
    residentAge: "عمر الساكن:",
    monitoredZone: "المنطقة المراقبة:",
    guardianPhone: "هاتف المشرف (SMS):",
    saveLiveProfileBtn: "💾 حفظ الملف الحي",
    slaLatencyLabel: "زمن الاستجابة SLA",
    opticalModelLabel: "النموذج البصري",
    liveSafetyStateLabel: "حالة السلامة الحية",
    zoneLivingRoom: "غرفة المعيشة",
    zoneBathroom: "الحمام (أرضية رطبة خطرة)",
    zoneBedroom: "غرفة النوم",
    zoneKitchen: "المطبخ",

    liveCameraTitle: "1. الكاميرا الحية — الذكاء الاصطناعي لكشف السقوط وفقدان الوعي",
    startCameraBtn: "تشغيل الكاميرا الحية",
    stopCameraBtn: "إيقاف الكاميرا",
    cameraInactiveTitle: "الكاميرا غير نشطة",
    cameraInactiveSub: "انقر فوق \"تشغيل الكاميرا\" لبدء تحليل الفيديو المباشر عبر نموذج YOLOv8 المدرب.",
    safetyStatusLabel: "حالة الأمان",
    detectedActionLabel: "الحركة المكتشفة",
    unresponsiveTimerLabel: "عداد فقدان الحركة",
    motionDisplacementLabel: "معدل الإزاحة",
    normalMovementState: "حركة طبيعية",
    fallDetectedState: "تم كشف سقوط!",
    unresponsivenessState: "🚨 فقدان استجابة (طوارئ)",

    liveVoiceTitle: "2. الذكاء الصوتي الحي ومركز المحادثة",
    liveVoiceHeader: "التعرف الصوتي المباشر (WEB SPEECH API):",
    liveVoiceInstructions: "انقر فوق \"تشغيل الميكروفون\" وتحدث. قل \"أنا بخير\" أو \"النجدة سقطت!\" لاختبار النظام.",
    startMicBtn: "تشغيل الميكروفون",
    stopMicBtn: "إيقاف الميكروفون",
    speakPromptBtn: "نطق سؤال أليكسا",
    acousticStateLabel: "الحالة الصوتية",
    detectedIntentLabel: "القصد المكتشف",
    confidenceLabel: "الدقة",
    passiveListeningVal: "استماع هادئ",
    micIdleStatus: "الميكروفون في الانتظار",
    micListeningStatus: "جاري الاستماع...",

    liveEventStreamTitle: "بث الأحداث الحية (SSE Transport: /sse)",
    awaitingLiveEvents: "بانتظار الأحداث المباشرة من الكاميرا والميكروفون...",
    liveRiskCadTitle: "تقييم الخطر المباشر وحزمة طوارئ 911 (EPK)",
    copyEpkBtn: "📋 نسخ حزمة EPK",

    quickExplainer: "يراقب إيجيس السلامة بهدوء. أليكسا تطمئن بلطف عند اضطراب الحركة، وتستدعي النجدة فوراً إن لزم.",
    howItWorks: "⚡ كيف يعمل الذكاء الاصطناعي لحمايتك (4 خطوات)",
    playAnimation: "▶️ تشغيل العرض التوضيحي",
    step1Title: "👁️ 1. الحساسات تستشعر",
    step2Title: "🧠 2. تحليل مستوى الخطر",
    step3Title: "🎙️ 3. أليكسا تطمئن صوتياً",
    step4Title: "🛡️ 4. استجابة طوارئ فورية",
    apartmentMap: "🏠 مخطط الشقة",
    bathroom: "🚿 الحمام",
    livingRoom: "🛋️ غرفة المعيشة",
    kitchen: "🍳 المطبخ",
    bedroom: "🛏️ غرفة النوم",
    doorLocked: "القفل الذكي: مغلق بإحكام",
    doorUnlocked: "القفل الذكي: مفتوح لرجال الإسعاف 911",
    doorPinSub: "فتح تلقائي للمسعفين (رمز PIN: 8492)",
    heartRate: "نبضات القلب",
    movement: "حركة الجسم",
    appleWatch: "ساعة آبل",
    connected: "متصل",
    alexaAsks: "🤖 أليكسا تسأل:",
    seniorReply: "👵 إجابة كبير السن:",
    answerForMom: "👉 جرب الرد بالنيابة:",
    btnImOk: "🟢 \"أنا بخير ولله الحمد\"",
    btnHelpMe: "🟡 \"أحتاج للمساعدة!\"",
    btnSilent: "🔴 <صمت وعدم إجابة 20 ثانية>",
    sonTitle: "الابن ديفيد (المشرف)",
    emsTitle: "مركز إسعاف 911 بوسطن",
    safeStatus: "🟢 الوضع آمن ومستقر",
    checkingStatus: "🟡 جاري الاطمئنان / تنبيه",
    emergencyStatus: "🔴 استجابة طوارئ نشطة",
    videoGuideBtn: "🎬 دليل تشغيل النظام"
  },

  ja: {
    appTitle: "Aegis Ambient Care",
    tagline: "環境認識型 高齢者見守りAI",
    seniorName: "エレノア・ヴァンス (79歳)",
    seniorLoc: "ビーコンヒル 4B号室",
    userRole: "家族 / 利用者ビュー",
    adminLink: "🛡️ 管理者ポータル (長男)",
    seniorLink: "👵 ホーム＆高齢者ビュー",
    niraPortalBtn: "NIRAポータル",
    adminPortalLink: "家族管理ポータル →",
    primaryGuardianRole: "主保護者",
    switchUserLink: "切替",
    yearsOld: "歳",
    liveMonitoredSession: "ライブ監視セッション • 光学AI稼働中",

    operatingEnvTitle: "動作環境モード:",
    operatingEnvSub: "インタラクティブデモとリアルタイム本番監視を切り替えます。",
    demoModeTitle: "1. デモモード",
    demoModeDesc: "シミュレーション環境（4B号室）、3つの緊急シナリオ、3Dツイン＆レーダー。",
    demoBadge: "ハッカソン展示",
    liveModeTitle: "2. ライブモード",
    liveModeDesc: "実際のWebカメラ、学習済みYOLOv8骨格・転倒検知、マイク音声、SMS通知。",
    liveBadge: "リアルタイム稼働",

    testScenarioModes: "テストシナリオ:",
    chooseScenario: "👉 シナリオを選択:",
    tabScenario1Title: "🟢 シナリオ1: 誤検知（無事）",
    tabScenario1Btn: "通常 / 無事 (誤検知)",
    tabScenario1Desc: "本を落としただけ。Alexaの問いかけに「大丈夫」と返答 ➔ アラート解除。",
    tabScenario2Title: "🟡 シナリオ2: 助けを呼ぶ",
    tabScenario2Btn: "要支援 (家族通知)",
    tabScenario2Desc: "台所で転倒し「助けて！」と叫ぶ ➔ 息子のスマホとAlexaへ緊急通知。",
    tabScenario3Title: "🔴 シナリオ3: 沈黙の緊急事態",
    tabScenario3Btn: "緊急事態 (救急車・911出動)",
    tabScenario3Desc: "夜間の浴室転倒で応答なし ➔ 救急隊へ自動通報＆玄関自動解錠。",

    tabOverview: "概要と健康状態",
    tabLiveVision: "ライブ映像＆3D間取り",
    tabVoiceAI: "音声AI＆Alexa+",
    tabCadDispatch: "救急指令・自動解錠",
    tabHistory: "インシデント履歴",

    liveMonitoringArmed: "ライブ監視作動中",
    protectionPaused: "監視一時停止中",
    pauseProtection: "保護を一時停止",
    resumeProtection: "保護を再開",
    realResidentName: "実際の利用者名:",
    residentAge: "利用者の年齢:",
    monitoredZone: "監視対象ゾーン:",
    guardianPhone: "家族SMS (TextBee):",
    saveLiveProfileBtn: "💾 ライブ設定を保存",
    slaLatencyLabel: "SLA応答速度",
    opticalModelLabel: "光学モデル",
    liveSafetyStateLabel: "現在の安全ステータス",
    zoneLivingRoom: "リビング",
    zoneBathroom: "浴室・洗面所 (滑り注意)",
    zoneBedroom: "寝室",
    zoneKitchen: "キッチン",

    liveCameraTitle: "1. ライブカメラ — 学習済み転倒・無反応検知AI",
    startCameraBtn: "ライブカメラを開始",
    stopCameraBtn: "カメラを停止",
    cameraInactiveTitle: "ライブカメラ停止中",
    cameraInactiveSub: "「ライブカメラを開始」をクリックすると、学習済みYOLOv8モデルでリアルタイム転倒判定を開始します。",
    safetyStatusLabel: "安全ステータス",
    detectedActionLabel: "検出アクション",
    unresponsiveTimerLabel: "無反応タイマー",
    motionDisplacementLabel: "動作変位量",
    normalMovementState: "正常な動作",
    fallDetectedState: "転倒を検知！",
    unresponsivenessState: "🚨 無反応状態 (緊急通報)",

    liveVoiceTitle: "2. ライブ音声AI＆対話ハブ",
    liveVoiceHeader: "リアルタイム音声認識 (WEB SPEECH API):",
    liveVoiceInstructions: "「マイクを開始」を押して「大丈夫」または「助けて！」と話しかけてください。",
    startMicBtn: "マイクを開始",
    stopMicBtn: "マイクを停止",
    speakPromptBtn: "Alexa音声を再生",
    acousticStateLabel: "音響ステータス",
    detectedIntentLabel: "認識インテント",
    confidenceLabel: "信頼度",
    passiveListeningVal: "常時傾聴中",
    micIdleStatus: "マイク待機中",
    micListeningStatus: "聞き取り中...",

    liveEventStreamTitle: "リアルタイムイベント配信 (SSE: /sse)",
    awaitingLiveEvents: "カメラとマイクからのリアルタイムイベント待機中...",
    liveRiskCadTitle: "ライブリスク評価＆救急医療情報 (EPK)",
    copyEpkBtn: "📋 EPK JSONをコピー",

    quickExplainer: "Aegisは環境センサーで静かに見守ります。異常時はAlexaが優しく安否確認し、必要時は家族や救急へ即時連絡します。",
    howItWorks: "⚡ Aegis AIによる保護の仕組み (4段階)",
    playAnimation: "▶️ アニメーション再生",
    step1Title: "👁️ 1. センサーによる常時監視",
    step2Title: "🧠 2. AIによるリスク判定",
    step3Title: "🎙️ 3. Alexaによる安否確認",
    step4Title: "🛡️ 4. 救急・家族への即時連絡",
    apartmentMap: "🏠 間取り図",
    bathroom: "🚿 浴室",
    livingRoom: "🛋️ リビング",
    kitchen: "🍳 キッチン",
    bedroom: "🛏️ 寝室",
    doorLocked: "スマートロック: 施錠中",
    doorUnlocked: "スマートロック: 救急用に解錠完了",
    doorPinSub: "救急隊員のために自動解錠 (暗証番号: 8492)",
    heartRate: "心拍数",
    movement: "身体動作",
    appleWatch: "Apple Watch",
    connected: "接続済み",
    alexaAsks: "🤖 Alexaの問いかけ:",
    seniorReply: "👵 利用者の返答:",
    answerForMom: "👉 返答をシミュレート:",
    btnImOk: "🟢 「大丈夫よ」",
    btnHelpMe: "🟡 「助けて！」",
    btnSilent: "🔴 <20秒間 応答なし>",
    sonTitle: "長男 デイヴィッド (管理者)",
    emsTitle: "ボストン救急司令室 911",
    safeStatus: "🟢 異常なし・安全",
    checkingStatus: "🟡 安否確認中・家族通知",
    emergencyStatus: "🔴 救急出動要請中",
    videoGuideBtn: "🎬 操作ガイド動画"
  },

  ru: {
    appTitle: "Aegis Ambient Care",
    tagline: "Фоновый ИИ Безопасности Пожилых Людей",
    seniorName: "Элеонор Вэнс (79 лет)",
    seniorLoc: "Бикон-Хилл, Кв. 4B",
    userRole: "Член семьи / Вид подопечного",
    adminLink: "🛡️ Портал сына (Администратор)",
    seniorLink: "👵 Главный экран дома",
    niraPortalBtn: "Портал NIRA",
    adminPortalLink: "Панель администратора →",
    primaryGuardianRole: "Главный опекун",
    switchUserLink: "Сменить",
    yearsOld: "лет",
    liveMonitoredSession: "Живая Сессия Мониторинга • Оптический ИИ Активен",

    operatingEnvTitle: "РЕЖИМ РАБОТЫ:",
    operatingEnvSub: "Переключение между интерактивной демонстрацией и мониторингом в реальном времени.",
    demoModeTitle: "1. ДЕМО-РЕЖИМ",
    demoModeDesc: "Симуляция Элеонор Вэнс (Кв. 4B), 3 экстренных сценария, 3D-двойник и радары.",
    demoBadge: "ДЕМО ХАКАТОНА",
    liveModeTitle: "2. ЖИВОЙ РЕЖИМ (LIVE)",
    liveModeDesc: "Реальная веб-камера, обученный ИИ YOLOv8 детекции падений, микрофон и SMS.",
    liveBadge: "РЕАЛЬНОЕ ВРЕМЯ",

    testScenarioModes: "Тестовые сценарии:",
    chooseScenario: "👉 Выберите тестовый сценарий:",
    tabScenario1Title: "🟢 Сценарий 1: Ложная тревога",
    tabScenario1Btn: "В норме / Безопасно (Ложная тревога)",
    tabScenario1Desc: "Уронила книгу. Alexa спросила. Элеонор: \"Все в порядке\" ➔ Тревога снята.",
    tabScenario2Title: "🟡 Сценарий 2: Просьба о помощи",
    tabScenario2Btn: "Нужна помощь (Сигнал сыну)",
    tabScenario2Desc: "Поскользнулась на кухне. Кричит: \"Помогите!\" ➔ Сын оповещен звонком и через Alexa.",
    tabScenario3Title: "🔴 Сценарий 3: Безмолвная беда",
    tabScenario3Btn: "Экстренная тревога (Вызов 911)",
    tabScenario3Desc: "Ночное падение в ванной без ответа ➔ Вызвана скорая 911 + Дверь открыта.",

    tabOverview: "Обзор и здоровье",
    tabLiveVision: "Видео и 3D-план",
    tabVoiceAI: "Голосовой ИИ и Alexa+",
    tabCadDispatch: "Диспетчерская 911 и доступ",
    tabHistory: "Журнал событий",

    liveMonitoringArmed: "МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ АКТИВЕН",
    protectionPaused: "ЗАЩИТА ПРИОСТАНОВЛЕНА",
    pauseProtection: "Приостановить",
    resumeProtection: "Возобновить защиту",
    realResidentName: "Имя подопечного:",
    residentAge: "Возраст:",
    monitoredZone: "Контролируемая зона:",
    guardianPhone: "Телефон опекуна (SMS):",
    saveLiveProfileBtn: "💾 Сохранить профиль",
    slaLatencyLabel: "Задержка SLA",
    opticalModelLabel: "Оптическая модель",
    liveSafetyStateLabel: "Текущий статус безопасности",
    zoneLivingRoom: "Гостиная",
    zoneBathroom: "Ванная комната (Опасный пол)",
    zoneBedroom: "Спальня",
    zoneKitchen: "Кухня",

    liveCameraTitle: "1. Живая Камера — Обученный ИИ Детекции Падений",
    startCameraBtn: "Включить Камеру",
    stopCameraBtn: "Выключить Камеру",
    cameraInactiveTitle: "Камера отключена",
    cameraInactiveSub: "Нажмите \"Включить Камеру\" для передачи живого видео в обученную нейросеть YOLOv8.",
    safetyStatusLabel: "Статус безопасности",
    detectedActionLabel: "Распознанное действие",
    unresponsiveTimerLabel: "Таймер неподвижности",
    motionDisplacementLabel: "Скорость смещения",
    normalMovementState: "ОБЫЧНОЕ ДВИЖЕНИЕ",
    fallDetectedState: "ОБНАРУЖЕНО ПАДЕНИЕ!",
    unresponsivenessState: "🚨 БЕЗ СОЗНАНИЯ / ТРЕВОГА",

    liveVoiceTitle: "2. Голосовой ИИ и Центр Диалога",
    liveVoiceHeader: "РАСПОЗНАВАНИЕ РЕЧИ (WEB SPEECH API):",
    liveVoiceInstructions: "Включите микрофон и скажите: \"Все в порядке\" или \"Помогите, я упала!\".",
    startMicBtn: "Включить Микрофон",
    stopMicBtn: "Выключить Микрофон",
    speakPromptBtn: "Озвучить вопрос Alexa",
    acousticStateLabel: "Акустический статус",
    detectedIntentLabel: "Распознанное намерение",
    confidenceLabel: "Точность",
    passiveListeningVal: "Фоновое слушание",
    micIdleStatus: "МИКРОФОН ОЖИДАЕТ",
    micListeningStatus: "СЛУШАЕТ...",

    liveEventStreamTitle: "Поток событий в реальном времени (SSE: /sse)",
    awaitingLiveEvents: "Ожидание реальных событий от камеры и микрофона...",
    liveRiskCadTitle: "Оценка риска и карта экстренной помощи (EPK)",
    copyEpkBtn: "📋 Скопировать EPK JSON",

    quickExplainer: "Aegis бережно заботится о близких с помощью фоновых сенсоров и видеоанализа.",
    howItWorks: "⚡ Как защищает система Aegis (4 шага)",
    playAnimation: "▶️ Воспроизвести демонстрацию",
    step1Title: "👁️ 1. Сенсоры фиксируют",
    step2Title: "🧠 2. Анализ риска ИИ",
    step3Title: "🎙️ 3. Запрос через Alexa",
    step4Title: "🛡️ 4. Экстренная помощь",
    apartmentMap: "🏠 План квартиры",
    bathroom: "🚿 Ванная",
    livingRoom: "🛋️ Гостиная",
    kitchen: "🍳 Кухня",
    bedroom: "🛏️ Спальня",
    doorLocked: "Умный замок: НАДЕЖНО ЗАКРЫТ",
    doorUnlocked: "Умный замок: ОТКРЫТ ДЛЯ СКОРОЙ",
    doorPinSub: "Автоматически открыт для спасателей 911 (ПИН: 8492)",
    heartRate: "ПУЛЬС",
    movement: "ДВИЖЕНИЕ",
    appleWatch: "APPLE WATCH",
    connected: "Подключено",
    alexaAsks: "🤖 Alexa спрашивает:",
    seniorReply: "👵 Ответ голосом:",
    answerForMom: "👉 Попробуйте ответить:",
    btnImOk: "🟢 \"Я в порядке\"",
    btnHelpMe: "🟡 \"Помогите!\"",
    btnSilent: "🔴 <Молчание 20 сек>",
    sonTitle: "Сын Дэвид Вэнс (Опекун)",
    emsTitle: "Служба спасения 911",
    safeStatus: "🟢 ВСЕ СПОКОЙНО И В НОРМЕ",
    checkingStatus: "🟡 ПРОВЕРКА / СИГНАЛ СЕМЬЕ",
    emergencyStatus: "🔴 ВЫЗОВ СПАСАТЕЛЕЙ АКТИВЕН",
    videoGuideBtn: "🎬 Видео-инструкция"
  },

  hi: {
    appTitle: "Aegis Ambient Care",
    tagline: "वरिष्ठ नागरिकों की सुरक्षा हेतु एम्बिएंट AI",
    seniorName: "एलेनोर वेंस (आयु 79 वर्ष)",
    seniorLoc: "बीकन हिल, यूनिट 4B",
    userRole: "पारिवारिक सदस्य / वरिष्ठ नागरिक व्यू",
    adminLink: "🛡️ पुत्र / एडमिन पोर्टल",
    seniorLink: "👵 मुख्य व होम व्यू",
    niraPortalBtn: "NIRA पोर्टल",
    adminPortalLink: "परिवार एडमिन पोर्टल →",
    primaryGuardianRole: "मुख्य अभिभावक",
    switchUserLink: "बदलें",
    yearsOld: "वर्ष",
    liveMonitoredSession: "लाइव निगरानी सत्र • ऑप्टिकल AI सक्रिय",

    operatingEnvTitle: "कार्यप्रणाली मोड:",
    operatingEnvSub: "डेमो और वास्तविक समय लाइव निगरानी के बीच स्विच करें।",
    demoModeTitle: "1. डेमो मोड",
    demoModeDesc: "सिम्युलेटेड एलेनोर वेंस (यूनिट 4B), 3 आपातकालीन परिदृश्य, 3D मॉडल व रडार।",
    demoBadge: "इंटरएक्टिव डेमो",
    liveModeTitle: "2. लाइव मोड",
    liveModeDesc: "वास्तविक कैमरा, प्रशिक्षित YOLOv8 फॉल डिटेक्टर, लाइव माइक व SMS अलर्ट।",
    liveBadge: "वास्तविक समय लाइव",

    testScenarioModes: "परीक्षण परिदृश्य:",
    chooseScenario: "👉 परीक्षण परिदृश्य चुनें:",
    tabScenario1Title: "🟢 परिदृश्य 1: गलत अलार्म",
    tabScenario1Btn: "सामान्य / सुरक्षित (गलत अलार्म)",
    tabScenario1Desc: "किताब गिर गई। एलेक्सा ने पूछा। एलेनोर बोलीं \"मैं ठीक हूँ\" ➔ अलार्म रद्द।",
    tabScenario2Title: "🟡 परिदृश्य 2: मदद की पुकार",
    tabScenario2Btn: "सहायता आवश्यक (परिवार को अलर्ट)",
    tabScenario2Desc: "रसोई में फिसलीं और पुकारा \"मदद करो!\" ➔ पुत्र डेविड को फोन व एलेक्सा अलर्ट भेजा गया।",
    tabScenario3Title: "🔴 परिदृश्य 3: शांत आपातकाल",
    tabScenario3Btn: "आपातकाल (911 एम्बुलेंस)",
    tabScenario3Desc: "रात में बाथरूम में गिरीं, कोई आवाज़ नहीं ➔ 911 एम्बुलेंस भेजी गई + दरवाज़ा खुला।",

    tabOverview: "अवलोकन एवं स्वास्थ्य",
    tabLiveVision: "लाइव वीडियो व 3D मैप",
    tabVoiceAI: "वॉयस AI व एलेक्सा",
    tabCadDispatch: "911 आपातकालीन सहायता",
    tabHistory: "घटना इतिहास",

    liveMonitoringArmed: "लाइव निगरानी सक्रिय",
    protectionPaused: "सुरक्षा रोकी गई",
    pauseProtection: "सुरक्षा रोकें",
    resumeProtection: "सुरक्षा पुनः शुरू करें",
    realResidentName: "नागरिक का वास्तविक नाम:",
    residentAge: "नागरिक की आयु:",
    monitoredZone: "निगरानी क्षेत्र:",
    guardianPhone: "अभिभावक SMS (TextBee):",
    saveLiveProfileBtn: "💾 लाइव प्रोफाइल सहेजें",
    slaLatencyLabel: "SLA प्रतिक्रिया समय",
    opticalModelLabel: "ऑप्टिकल मॉडल",
    liveSafetyStateLabel: "वर्तमान सुरक्षा स्थिति",
    zoneLivingRoom: "लिविंग रूम",
    zoneBathroom: "बाथरूम (फिसलन भरा फर्श)",
    zoneBedroom: "शयनकक्ष",
    zoneKitchen: "रसोईघर",

    liveCameraTitle: "1. लाइव कैमरा — प्रशिक्षित फॉल एवं अचेतनता AI",
    startCameraBtn: "लाइव कैमरा शुरू करें",
    stopCameraBtn: "कैमरा बंद करें",
    cameraInactiveTitle: "कैमरा बंद है",
    cameraInactiveSub: "प्रशिक्षित YOLOv8 मॉडल से रीयल-टाइम वीडियो विश्लेषण के लिए \"लाइव कैमरा शुरू करें\" पर क्लिक करें।",
    safetyStatusLabel: "सुरक्षा स्थिति",
    detectedActionLabel: "पहचानी गई क्रिया",
    unresponsiveTimerLabel: "अचेतनता टाइमर",
    motionDisplacementLabel: "गति दर",
    normalMovementState: "सामान्य गतिविधि",
    fallDetectedState: "गिरना पहचाना गया!",
    unresponsivenessState: "🚨 कोई हरकत नहीं (आपातकाल)",

    liveVoiceTitle: "2. लाइव वॉयस AI और संवाद केंद्र",
    liveVoiceHeader: "लाइव आवाज़ पहचान (WEB SPEECH API):",
    liveVoiceInstructions: "\"माइक शुरू करें\" दबाएँ और बोलें। कहें \"मैं ठीक हूँ\" या \"मदद करो!\"।",
    startMicBtn: "माइक शुरू करें",
    stopMicBtn: "माइक बंद करें",
    speakPromptBtn: "एलेक्सा का प्रश्न सुनें",
    acousticStateLabel: "ध्वनि स्थिति",
    detectedIntentLabel: "पहचाना गया आशय",
    confidenceLabel: "सटीकता",
    passiveListeningVal: "सतर्कता से सुन रहा है",
    micIdleStatus: "माइक प्रतीक्षारत",
    micListeningStatus: "सुन रहा है...",

    liveEventStreamTitle: "लाइव इवेंट स्ट्रीम (SSE: /sse)",
    awaitingLiveEvents: "कैमरा और माइक से वास्तविक समय की घटनाओं की प्रतीक्षा...",
    liveRiskCadTitle: "लाइव जोखिम मूल्यांकन और 911 आपातकालीन डेटा (EPK)",
    copyEpkBtn: "📋 EPK JSON कॉपी करें",

    quickExplainer: "Aegis बुजुर्गों की सुरक्षा पर बिना किसी रुकावट के नजर रखता है।",
    howItWorks: "⚡ Aegis AI कैसे रक्षा करता है (4 चरण)",
    playAnimation: "▶️ एनीमेशन देखें",
    step1Title: "👁️ 1. सेंसर पहचानते हैं",
    step2Title: "🧠 2. AI जोखिम मूल्यांकन",
    step3Title: "🎙️ 3. एलेक्सा पूछती है",
    step4Title: "🛡️ 4. तुरंत आपातकालीन कदम",
    apartmentMap: "🏠 घर का नक्शा",
    bathroom: "🚿 बाथरूम",
    livingRoom: "🛋️ लिविंग रूम",
    kitchen: "🍳 रसोईघर",
    bedroom: "🛏️ बेडरूम",
    doorLocked: "स्मार्ट लॉक: सुरक्षित बंद",
    doorUnlocked: "स्मार्ट लॉक: 911 के लिए खुला",
    doorPinSub: "पैरामेडिक्स के लिए स्वतः खुला (पिन: 8492)",
    heartRate: "हृदय गति (हार्ट रेट)",
    movement: "शरीर की हलचल",
    appleWatch: "एप्पल वॉच",
    connected: "कनेक्टेड",
    alexaAsks: "🤖 एलेक्सा ने पूछा:",
    seniorReply: "👵 आवाज़ में उत्तर:",
    answerForMom: "👉 उत्तर देकर देखें:",
    btnImOk: "🟢 \"मैं ठीक हूँ\"",
    btnHelpMe: "🟡 \"मेरी मदद करो!\"",
    btnSilent: "🔴 <20 सेकंड तक खामोशी>",
    sonTitle: "पुत्र डेविड वेंस (एडमिन)",
    emsTitle: "बोस्टन 911 एम्बुलेंस",
    safeStatus: "🟢 सब सुरक्षित एवं कुशल",
    checkingStatus: "🟡 जांच जारी / परिवार सतर्क",
    emergencyStatus: "🔴 आपातकालीन सहायता सक्रिय",
    videoGuideBtn: "🎬 संचालन गाइड वीडियो"
  },

  zh: {
    appTitle: "Aegis Ambient Care",
    tagline: "环境感知型长者安全守护 AI",
    seniorName: "Eleanor Vance (79岁)",
    seniorLoc: "比肯山 4B 单元",
    userRole: "家属 / 长者视角",
    adminLink: "🛡️ 家属管理后台 (儿子)",
    seniorLink: "👵 长者居家主界面",
    niraPortalBtn: "NIRA 门户",
    adminPortalLink: "家属管理后台 →",
    primaryGuardianRole: "主监护人",
    switchUserLink: "切换",
    yearsOld: "岁",
    liveMonitoredSession: "实时监控会话 • 视觉 AI 运行中",

    operatingEnvTitle: "运行环境模式:",
    operatingEnvSub: "在黑客松交互演示模式与真实实时接入模式之间切换。",
    demoModeTitle: "1. 演示模式 (DEMO)",
    demoModeDesc: "模拟 Eleanor Vance (4B单元)，3种紧急场景，3D数字孪生与毫米波雷达。",
    demoBadge: "黑客松交互展示",
    liveModeTitle: "2. 实时模式 (LIVE)",
    liveModeDesc: "真实网络摄像头，自训练 YOLOv8 跌倒与无意识检测，真实麦克风与 SMS 报警。",
    liveBadge: "实时在线接入",

    testScenarioModes: "测试场景模式:",
    chooseScenario: "👉 选择测试场景:",
    tabScenario1Title: "🟢 场景 1: 虚惊一场",
    tabScenario1Btn: "正常 / 安全 (虚惊一场)",
    tabScenario1Desc: "书本掉落。Alexa 关切询问。老人回答\"我没事\" ➔ 警报解除。",
    tabScenario2Title: "🟡 场景 2: 呼救求助",
    tabScenario2Btn: "需要协助 (家属警报)",
    tabScenario2Desc: "厨房滑倒并呼救\"救命!\" ➔ 儿子手机与 Alexa 收到即时警报。",
    tabScenario3Title: "🔴 场景 3: 无声紧急情况",
    tabScenario3Btn: "紧急救援 (呼叫 911)",
    tabScenario3Desc: "夜间浴室跌倒且失去意识 ➔ 自动呼叫 911 急救 + 智能门锁自动解锁。",

    tabOverview: "总览与体征健康",
    tabLiveVision: "实时视觉与 3D 户型",
    tabVoiceAI: "语音 AI 与 Alexa+",
    tabCadDispatch: "911 急救调度与出警",
    tabHistory: "事件审计记录",

    liveMonitoringArmed: "实时守护监控中",
    protectionPaused: "监控已暂停",
    pauseProtection: "暂停守护",
    resumeProtection: "恢复守护",
    realResidentName: "受护人真实姓名:",
    residentAge: "受护人年龄:",
    monitoredZone: "监控区域:",
    guardianPhone: "监护人短信 (TextBee):",
    saveLiveProfileBtn: "💾 保存实时档案",
    slaLatencyLabel: "SLA 响应延迟",
    opticalModelLabel: "视觉模型",
    liveSafetyStateLabel: "实时安全状态",
    zoneLivingRoom: "客厅",
    zoneBathroom: "浴室 (高危湿滑地面)",
    zoneBedroom: "卧室",
    zoneKitchen: "厨房",

    liveCameraTitle: "1. 实时摄像头 — 训练版跌倒与无意识检测 AI",
    startCameraBtn: "开启实时摄像头",
    stopCameraBtn: "关闭摄像头",
    cameraInactiveTitle: "摄像头未开启",
    cameraInactiveSub: "点击\"开启实时摄像头\"，将实时视频画面输入训练好的 YOLOv8 视觉模型进行动作分析。",
    safetyStatusLabel: "安全状态",
    detectedActionLabel: "识别动作",
    unresponsiveTimerLabel: "无意识计时器",
    motionDisplacementLabel: "位移变化速率",
    normalMovementState: "正常活动",
    fallDetectedState: "检测到跌倒!",
    unresponsivenessState: "🚨 无意识 / 昏迷 (紧急报警)",

    liveVoiceTitle: "2. 实时语音 AI 与对话中枢",
    liveVoiceHeader: "实时语音识别 (WEB SPEECH API):",
    liveVoiceInstructions: "点击\"开启麦克风\"并说话。说\"我没事\"或\"救命我摔倒了\"即可触发实时状态转换。",
    startMicBtn: "开启麦克风",
    stopMicBtn: "关闭麦克风",
    speakPromptBtn: "播放 Alexa 问询语音",
    acousticStateLabel: "声学状态",
    detectedIntentLabel: "识别意图",
    confidenceLabel: "置信度",
    passiveListeningVal: "常态被动倾听",
    micIdleStatus: "麦克风就绪",
    micListeningStatus: "正在聆听...",

    liveEventStreamTitle: "实时事件流 (SSE 传输: /sse)",
    awaitingLiveEvents: "等待来自真实摄像头和麦克风的实时事件...",
    liveRiskCadTitle: "实时风险评估与 911 急救病历包 (EPK)",
    copyEpkBtn: "📋 复制 EPK JSON",

    quickExplainer: "Aegis 通过环境传感器与视觉模型静默守护长者。当出现异常动作时，Alexa 会主动询问安危。",
    howItWorks: "⚡ Aegis AI 如何守护长者安全 (4步防护)",
    playAnimation: "▶️ 播放情景动画",
    step1Title: "👁️ 1. 环境感知捕捉异常",
    step2Title: "🧠 2. AI 实时风险研判",
    step3Title: "🎙️ 3. Alexa 拟人关怀问询",
    step4Title: "🛡️ 4. 立即启动紧急救援",
    apartmentMap: "🏠 长者公寓户型图",
    bathroom: "🚿 浴室卫生间",
    livingRoom: "🛋️ 起居客厅",
    kitchen: "🍳 厨房",
    bedroom: "🛏️ 卧室",
    doorLocked: "智能门锁: 安全锁定中",
    doorUnlocked: "智能门锁: 已为 911 急救解锁",
    doorPinSub: "为波士顿急救人员自动解锁 (PIN密钥: 8492)",
    heartRate: "实时心率",
    movement: "肢体活动量",
    appleWatch: "Apple Watch",
    connected: "已连接",
    alexaAsks: "🤖 Alexa 主动询问:",
    seniorReply: "👵 长者语音回复:",
    answerForMom: "👉 代替长者回答测试:",
    btnImOk: "🟢 \"我很好，没事\"",
    btnHelpMe: "🟡 \"快来帮帮我!\"",
    btnSilent: "🔴 <沉默20秒 / 昏迷>",
    sonTitle: "儿子 David Vance (管理员)",
    emsTitle: "波士顿 911 急救调度",
    safeStatus: "🟢 一切正常 安全",
    checkingStatus: "🟡 正在确认 / 家属已通知",
    emergencyStatus: "🔴 紧急救援响应中",
    videoGuideBtn: "🎬 系统操作指南"
  }
};

let currentLang = localStorage.getItem("aegis_lang") || "en";

function setLanguage(langCode) {
  if (!TRANSLATIONS[langCode]) langCode = "en";
  currentLang = langCode;
  localStorage.setItem("aegis_lang", langCode);
  applyTranslations();

  // Re-render dashboard if active to propagate localized strings
  if (window.niraStore && typeof renderDashboard === "function") {
    try {
      renderDashboard(window.niraStore.state);
    } catch (_) {}
  }

  // Handle Right-to-Left for Arabic
  if (langCode === "ar") {
    document.documentElement.setAttribute("dir", "rtl");
  } else {
    document.documentElement.setAttribute("dir", "ltr");
  }

  if (typeof showToast === "function") {
    showToast(`🌐 Language: <strong>${langCode.toUpperCase()}</strong>`);
  }
}

function t(key) {
  const langObj = TRANSLATIONS[currentLang] || TRANSLATIONS.en || {};
  const enObj = TRANSLATIONS.en || {};

  if (langObj[key]) return langObj[key];
  if (enObj[key]) return enObj[key];

  // Key aliases for backward compatibility and clean mapping
  const aliases = {
    tabVision: "tabLiveVision",
    tabVoice: "tabVoiceAI",
    tabDispatch: "tabCadDispatch",
    standbySafe: "safeStatus",
    standbyStatus: "micIdleStatus",
    demoModeShort: "demoBadge",
    liveModeShort: "liveBadge",
    residentNamePlaceholder: "realResidentName"
  };

  const alias = aliases[key];
  if (alias) {
    if (langObj[alias]) return langObj[alias];
    if (enObj[alias]) return enObj[alias];
  }

  return key;
}

function translateModeSelectorElements() {
  const modeHeaderTitle = document.querySelector(".mode-selector-title");
  if (modeHeaderTitle) modeHeaderTitle.textContent = t("operatingEnvTitle");

  const modeHeaderHint = document.querySelector(".mode-selector-hint");
  if (modeHeaderHint) modeHeaderHint.textContent = t("operatingEnvSub");

  const demoPill = document.querySelector("#btnModeDemo .demo-pill");
  if (demoPill) demoPill.textContent = t("demoBadge");

  const demoTitle = document.querySelector("#btnModeDemo .mode-card-title");
  if (demoTitle) demoTitle.textContent = t("demoModeTitle");

  const demoDesc = document.querySelector("#btnModeDemo .mode-card-desc");
  if (demoDesc) demoDesc.textContent = t("demoModeDesc");

  const livePill = document.querySelector("#btnModeLive .live-pill");
  if (livePill) livePill.textContent = t("liveBadge");

  const liveTitle = document.querySelector("#btnModeLive .mode-card-title");
  if (liveTitle) liveTitle.textContent = t("liveModeTitle");

  const liveDesc = document.querySelector("#btnModeLive .mode-card-desc");
  if (liveDesc) liveDesc.textContent = t("liveModeDesc");

  const landingDemo = document.querySelector("#btnLandingDemo .portal-label");
  if (landingDemo) landingDemo.textContent = t("demoModeShort") || "DEMO";

  const landingLive = document.querySelector("#btnLandingLive .portal-label");
  if (landingLive) landingLive.textContent = t("liveModeShort") || "LIVE MODEL";

  const portalBtn = document.querySelector(".btn-portal-home span");
  if (portalBtn) portalBtn.textContent = t("niraPortalBtn");

  const adminLink = document.querySelector(".btn-admin-link span");
  if (adminLink) adminLink.textContent = t("adminPortalLink");

  // Scenario Buttons Strip
  const sc1 = document.querySelector("#tabScenario1 span:last-child");
  if (sc1) sc1.textContent = t("tabScenario1Btn");
  const sc2 = document.querySelector("#tabScenario2 span:last-child");
  if (sc2) sc2.textContent = t("tabScenario2Btn");
  const sc3 = document.querySelector("#tabScenario3 span:last-child");
  if (sc3) sc3.textContent = t("tabScenario3Btn");

  // Tab Navigation Strip
  const t1 = document.querySelector("#tabBtnOverview span");
  if (t1) t1.textContent = t("tabOverview");
  const t2 = document.querySelector("#tabBtnVision span") || document.querySelector("#tabBtnLiveVision span");
  if (t2) t2.textContent = t("tabLiveVision") || t("tabVision");
  const t3 = document.querySelector("#tabBtnVoice span") || document.querySelector("#tabBtnVoiceAI span");
  if (t3) t3.textContent = t("tabVoiceAI") || t("tabVoice");
  const t4 = document.querySelector("#tabBtnDispatch span") || document.querySelector("#tabBtnCadDispatch span");
  if (t4) t4.textContent = t("tabCadDispatch") || t("tabDispatch");

  // Live Mode Elements
  const armText = document.getElementById("liveArmStatusText");
  if (armText) armText.textContent = t("liveMonitoringArmed");

  const toggleArm = document.getElementById("btnToggleArmText");
  if (toggleArm) toggleArm.textContent = t("pauseProtection");

  const saveProfileBtn = document.querySelector("#btnSaveLiveProfile span");
  if (saveProfileBtn) saveProfileBtn.textContent = t("saveLiveProfileBtn");

  const startCam = document.querySelector("#btnStartLiveCam span");
  if (startCam) startCam.textContent = t("startCameraBtn");

  const stopCam = document.querySelector("#btnStopLiveCam span");
  if (stopCam) stopCam.textContent = t("stopCameraBtn");

  const startMic = document.querySelector("#btnStartLiveMic span");
  if (startMic) startMic.textContent = t("startMicBtn");

  const stopMic = document.querySelector("#btnStopLiveMic span");
  if (stopMic) stopMic.textContent = t("stopMicBtn");

  // Room Select Options
  const optLiving = document.querySelector('#liveRoomSelect option[value="living_room"]');
  if (optLiving) optLiving.textContent = t("zoneLivingRoom");
  const optBath = document.querySelector('#liveRoomSelect option[value="bathroom"]');
  if (optBath) optBath.textContent = t("zoneBathroom");
  const optBed = document.querySelector('#liveRoomSelect option[value="bedroom"]');
  if (optBed) optBed.textContent = t("zoneBedroom");
  const optKit = document.querySelector('#liveRoomSelect option[value="kitchen"]');
  if (optKit) optKit.textContent = t("zoneKitchen");
}

function applyTranslations() {
  const elements = document.querySelectorAll("[data-i18n]");
  elements.forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (!key) return;
    const translated = t(key);
    if (translated && translated !== key) {
      el.innerHTML = translated;
    }
  });

  // Handle placeholders
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (key) {
      const translated = t(key);
      if (translated && translated !== key) {
        el.placeholder = translated;
      }
    }
  });

  // Handle titles
  document.querySelectorAll("[data-i18n-title]").forEach(el => {
    const key = el.getAttribute("data-i18n-title");
    if (key) {
      const translated = t(key);
      if (translated && translated !== key) {
        el.title = translated;
      }
    }
  });

  // Translate mode selector elements & buttons explicitly
  translateModeSelectorElements();

  // Handle Senior Capsule Header depending on active mode:
  const isLive = (localStorage.getItem("nira_system_mode") === "live") || 
                 (document.getElementById("btnModeLive") && document.getElementById("btnModeLive").classList.contains("active"));
  const seniorEl = document.querySelector("[data-i18n='seniorName']");
  const seniorLoc = document.querySelector("[data-i18n='seniorLoc']");

  if (isLive) {
    const liveName = (document.getElementById("liveResidentName") || {}).value || "Live Resident";
    const liveAge = (document.getElementById("liveResidentAge") || {}).value || 75;
    if (seniorEl) seniorEl.textContent = `${liveName} (${liveAge} ${t("yearsOld") || "years"})`;
    if (seniorLoc) seniorLoc.textContent = t("liveMonitoredSession");
  } else {
    if (seniorEl) seniorEl.textContent = t("seniorName");
    if (seniorLoc) seniorLoc.textContent = t("seniorLoc");
  }

  // Update language selector dropdown value
  const langSelect = document.getElementById("langSelector");
  if (langSelect) langSelect.value = currentLang;

  // RTL for Arabic
  if (currentLang === "ar") {
    document.documentElement.setAttribute("dir", "rtl");
  } else {
    document.documentElement.setAttribute("dir", "ltr");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem("aegis_lang");
  if (saved && TRANSLATIONS[saved]) {
    currentLang = saved;
  }
  applyTranslations();
});
