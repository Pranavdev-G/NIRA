"""
NIRA — Professional Demo Application Walkthrough Video Recorder.
Amazon Developer Hackathon 2026.

Automates the complete 14-step NIRA user journey using Playwright (MS Edge)
at 1920x1080 resolution, complete with professional voice narration,
glassmorphic step title cards, and natural cursor movement.
Transcodes the recorded walkthrough into output/NIRA_Demo_Walkthrough.mp4 (75-90s, 30 FPS, 1080p).
"""

import time
import math
import subprocess
import json
from pathlib import Path
from typing import List, TypedDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEMO_DIR = ROOT_DIR / "Demo"
OUTPUT_DIR = ROOT_DIR / "output"
SCRATCH_DIR = ROOT_DIR / "scratch"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

FINAL_VIDEO_PATH = OUTPUT_DIR / "NIRA_Demo_Walkthrough.mp4"
RAW_VIDEO_DIR = SCRATCH_DIR / "playwright_rec"
AUDIO_DIR = SCRATCH_DIR / "audio_narration"

RAW_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class Step(TypedDict):
    step: int
    title: str
    subtitle: str
    narration: str
    duration: float


# 14 Concise Steps (Target duration ~82-85 seconds total, perfectly inside 75–90s)
STEPS: List[Step] = [
    {
        "step": 1,
        "title": "NIRA — Never Ignore Risk Assistant",
        "subtitle": "Ambient AI Elder Safety & Multi-Device Monitoring",
        "narration": "Welcome to NIRA, the Never Ignore Risk Assistant for ambient senior safety and independent living.",
        "duration": 5.8
    },
    {
        "step": 2,
        "title": "Secure Enterprise Portal Login",
        "subtitle": "Role-Based Authentication for Residents & Guardians",
        "narration": "Accessing the secure portal with one-click authentication for family guardians and first responders.",
        "duration": 5.8
    },
    {
        "step": 3,
        "title": "Home Safety Dashboard",
        "subtitle": "Eleanor Vance • Wellbeing Summary & Ambient Vitals",
        "narration": "The Home Dashboard presents Eleanor's baseline vitals, wellbeing summary, and continuous ambient telemetry.",
        "duration": 6.0
    },
    {
        "step": 4,
        "title": "Monitored Resident Profile",
        "subtitle": "Clinical History, Allergies, Guardian & Access PIN",
        "narration": "Her profile details clinical conditions, baseline heart rate, family contacts, and smart deadbolt PIN 8492.",
        "duration": 6.0
    },
    {
        "step": 5,
        "title": "Ambient Voice Assistant",
        "subtitle": "Interactive Bidirectional Speech & Acoustic Triage",
        "narration": "The voice assistant instantly answers medication schedules with audible speech synthesis.",
        "duration": 5.8
    },
    {
        "step": 6,
        "title": "Proactive Daily Check-in",
        "subtitle": "Wellness Logging & Dizziness Flagger",
        "narration": "Eleanor submits her daily check-in, flagging mild dizziness to automatically alert her son David Vance.",
        "duration": 6.2
    },
    {
        "step": 7,
        "title": "Fall Detection & Telemetry HUD",
        "subtitle": "60GHz Radar, IMU Accelerometer & Biometric Matrix",
        "narration": "Simulating a fall captures a 3.42g impact velocity spike on wet bathroom tile.",
        "duration": 6.0
    },
    {
        "step": 8,
        "title": "Emergency Alert & Ambulance CAD",
        "subtitle": "Boston EMS Medic 14 En Route • Smart Lock Unlocked",
        "narration": "NIRA alerts Boston EMS Medic 14, auto-unlocks the smart deadbolt, and logs caregiver acknowledgment.",
        "duration": 6.2
    },
    {
        "step": 9,
        "title": "Residence Location & Trauma Centers",
        "subtitle": "Leaflet GPS Map & Mass General Hospital (MGH)",
        "narration": "The interactive map routes emergency responders directly to Mass General Hospital Level 1 Trauma Center.",
        "duration": 5.8
    },
    {
        "step": 10,
        "title": "Caregiver Guardian Hub",
        "subtitle": "David Vance Admin Portal • Live Telemetry Overrides",
        "narration": "Her son David monitors the active fall and live biometrics from the Family Guardian Hub.",
        "duration": 6.0
    },
    {
        "step": 11,
        "title": "Real-Time Notification Center",
        "subtitle": "Categorized Emergency Alerts & Audit Verification",
        "narration": "The notification center records the critical fall alert, now verified and marked as read.",
        "duration": 5.8
    },
    {
        "step": 12,
        "title": "Forensic Incident History",
        "subtitle": "Comprehensive Sensor Timeline & Impact Forensics",
        "narration": "Incident History provides forensic audit timelines and multi-sensor impact forensics.",
        "duration": 5.8
    },
    {
        "step": 13,
        "title": "Interactive Medication Reminders",
        "subtitle": "Prescription Schedule & Real-Time Dose Confirmation",
        "narration": "Eleanor confirms her evening CoQ10 medication, syncing compliance status across all portals in real time.",
        "duration": 6.2
    },
    {
        "step": 14,
        "title": "Closing — Never Ignore Risk Assistant",
        "subtitle": "Ambient AI Elder Care • Amazon Developer Hackathon 2026",
        "narration": "NIRA delivers proactive, continuous protection for vulnerable seniors: Never Ignore Risk Assistant.",
        "duration": 5.5
    }
]

TOTAL_DURATION = sum(s["duration"] for s in STEPS)
print(f"[Walkthrough Plan] Total planned duration: {TOTAL_DURATION:.1f} seconds (Target: 75–90s)")


def generate_speech_clip(text: str, out_wav: Path):
    """Generate a single WAV audio clip using Windows SpeechSynthesizer via powershell stdin."""
    clean_text = text.replace("'", "").replace('"', '')
    ps_script = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('Microsoft Zira Desktop')
$s.Rate = 1
$s.SetOutputToWaveFile('{out_wav.as_posix()}')
$s.Speak('{clean_text}')
$s.Dispose()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", "-"], input=ps_script.encode("utf-8"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_narration_audio() -> Path:
    """Builds a single synchronized narration audio file matching the step durations."""
    print("\n--- Generating Professional English Narration Track ---")
    combined_wav = SCRATCH_DIR / "complete_narration.wav"
    segment_files = []

    for i, step in enumerate(STEPS):
        clip_wav = AUDIO_DIR / f"step_{step['step']:02d}.wav"
        generate_speech_clip(step["narration"], clip_wav)

        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(clip_wav)
        ]
        clip_dur = float(subprocess.check_output(probe_cmd).strip())
        target_dur = step["duration"]

        padded_wav = AUDIO_DIR / f"padded_step_{step['step']:02d}.wav"
        pad_cmd = [
            "ffmpeg", "-y", "-i", str(clip_wav),
            "-af", f"apad=whole_dur={target_dur:.2f}",
            "-t", f"{target_dur:.2f}",
            str(padded_wav)
        ]
        subprocess.run(pad_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        segment_files.append(padded_wav)
        print(f"  Step {step['step']:02d} narration: {clip_dur:.2f}s speech -> padded to exact {target_dur:.2f}s")

    concat_list = SCRATCH_DIR / "concat_audio_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in segment_files:
            f.write(f"file '{p.as_posix()}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "pcm_s16le", str(combined_wav)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(combined_wav)
    ]
    tot_dur = float(subprocess.check_output(probe_cmd).strip())
    print(f"Total synced narration duration: {tot_dur:.2f}s\n")
    return combined_wav


def inject_visual_hud(page):
    """Injects high-end glassmorphic title card HUD and animated virtual cursor."""
    page.evaluate("""
() => {
  if (document.getElementById('niraWalkthroughHud')) return;

  const hud = document.createElement('div');
  hud.id = 'niraWalkthroughHud';
  hud.style.cssText = `
    position: fixed;
    top: 22px;
    right: 28px;
    z-index: 999999;
    background: rgba(11, 17, 32, 0.90);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1.5px solid rgba(56, 189, 248, 0.45);
    border-radius: 16px;
    padding: 12px 20px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.75), 0 0 24px rgba(56, 189, 248, 0.2);
    display: flex;
    align-items: center;
    gap: 14px;
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    color: #fff;
    pointer-events: none;
    transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  `;
  hud.innerHTML = `
    <div style="width: 40px; height: 40px; border-radius: 10px; background: linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(16, 185, 129, 0.25) 100%); border: 1.5px solid rgba(56, 189, 248, 0.5); display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
      🛡️
    </div>
    <div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <span id="hudStepBadge" style="background: rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.45); color: #38bdf8; font-size: 0.68rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.06em;">
          STEP 1 / 14
        </span>
        <span id="hudStepTitle" style="font-size: 0.92rem; font-weight: 800; color: #ffffff;">
          NIRA — Never Ignore Risk Assistant
        </span>
      </div>
      <div id="hudStepSub" style="font-size: 0.76rem; color: #94a3b8; margin-top: 2px;">
        Ambient AI Elder Safety & Multi-Device Monitoring
      </div>
    </div>
  `;
  document.body.appendChild(hud);

  const cur = document.createElement('div');
  cur.id = 'niraVirtualPointer';
  cur.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 24px;
    height: 24px;
    z-index: 1000000;
    pointer-events: none;
    transform: translate(-100px, -100px);
    transition: transform 0.08s ease-out;
  `;
  cur.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M4 2l16 7-7 2-2 7L4 2z" fill="#38bdf8" stroke="#ffffff" stroke-width="1.8"/>
    </svg>
    <div id="niraClickRipple" style="position: absolute; top: 0; left: 0; width: 24px; height: 24px; border-radius: 50%; border: 2px solid #38bdf8; opacity: 0; pointer-events: none; transform: scale(0.5); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);"></div>
  `;
  document.body.appendChild(cur);

  window.updateNiraHud = function(stepNum, title, subtitle) {
    const b = document.getElementById('hudStepBadge');
    const t = document.getElementById('hudStepTitle');
    const s = document.getElementById('hudStepSub');
    if (b) b.textContent = `STEP ${stepNum} / 14`;
    if (t) t.textContent = title;
    if (s) s.textContent = subtitle;
  };

  window.moveVirtualPointer = function(x, y) {
    const p = document.getElementById('niraVirtualPointer');
    if (p) {
      p.style.transform = `translate(${x}px, ${y}px)`;
    }
  };

  window.triggerClickRipple = function() {
    const r = document.getElementById('niraClickRipple');
    if (r) {
      r.style.transform = 'scale(2.2)';
      r.style.opacity = '1';
      setTimeout(() => {
        r.style.transform = 'scale(0.5)';
        r.style.opacity = '0';
      }, 250);
    }
  };
}
""")


def update_hud(page, step_dict):
    try:
        page.evaluate(
            f"window.updateNiraHud({step_dict['step']}, {json.dumps(step_dict['title'])}, {json.dumps(step_dict['subtitle'])})"
        )
    except Exception:
        pass


def smooth_move_mouse(page, target_x: float, target_y: float, steps: int = 16, delay: float = 0.012):
    current_pos = getattr(page, "_mouse_pos", (960, 540))
    start_x, start_y = current_pos

    for i in range(1, steps + 1):
        t = i / steps
        ease = 0.5 - 0.5 * math.cos(t * math.pi)
        cur_x = start_x + (target_x - start_x) * ease
        cur_y = start_y + (target_y - start_y) * ease

        page.mouse.move(cur_x, cur_y)
        try:
            page.evaluate(f"if (window.moveVirtualPointer) window.moveVirtualPointer({cur_x:.1f}, {cur_y:.1f})")
        except Exception:
            pass
        time.sleep(delay)

    setattr(page, "_mouse_pos", (target_x, target_y))


def click_at(page, target_x: float, target_y: float):
    smooth_move_mouse(page, target_x, target_y, steps=12, delay=0.01)
    try:
        page.evaluate("if (window.triggerClickRipple) window.triggerClickRipple()")
    except Exception:
        pass
    page.mouse.click(target_x, target_y)
    time.sleep(0.2)


def click_element(page, selector: str, fallback_x: float = 960, fallback_y: float = 540):
    try:
        loc = page.locator(selector).first
        if loc.is_visible(timeout=1000):
            box = loc.bounding_box()
            if box:
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                click_at(page, cx, cy)
                return
    except Exception:
        pass
    click_at(page, fallback_x, fallback_y)


def run_recording_walkthrough():
    from playwright.sync_api import sync_playwright

    # 1. Clean previous webm files
    for old_webm in RAW_VIDEO_DIR.glob("*.webm"):
        try:
            old_webm.unlink()
        except Exception:
            pass

    # 2. Build narration audio track
    narration_wav = build_narration_audio()

    print("\n--- Starting Playwright Browser Automation (1920x1080) ---")
    p = sync_playwright().start()

    browser = p.chromium.launch(
        channel="msedge",
        headless=True,
        args=[
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-size=1920,1080",
            "--force-device-scale-factor=1"
        ]
    )

    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        screen={"width": 1920, "height": 1080},
        record_video_dir=str(RAW_VIDEO_DIR),
        record_video_size={"width": 1920, "height": 1080}
    )

    page = context.new_page()
    setattr(page, "_mouse_pos", (960, 540))

    # ---------------------------------------------------------------------------
    # STEP 1: Introduction (Landing Page)
    # ---------------------------------------------------------------------------
    print("[Recording] Step 1: Introduction (NIRA & Tagline)")
    step_start = time.time()
    page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
    page.evaluate("localStorage.clear();")
    page.reload(wait_until="domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, STEPS[0])

    smooth_move_mouse(page, 960, 260, steps=18)
    smooth_move_mouse(page, 960, 310, steps=16)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[0]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 2: Login Flow
    # ---------------------------------------------------------------------------
    print("[Recording] Step 2: Login Flow")
    step_start = time.time()
    update_hud(page, STEPS[1])
    click_element(page, "#btnLandingLogin", fallback_x=1110, fallback_y=375)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, STEPS[1])

    smooth_move_mouse(page, 960, 480, steps=12)
    smooth_move_mouse(page, 960, 560, steps=12)
    click_element(page, "#btnLogin", fallback_x=960, fallback_y=630)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[1]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 3: Home Dashboard
    # ---------------------------------------------------------------------------
    print("[Recording] Step 3: Home Dashboard")
    step_start = time.time()
    update_hud(page, STEPS[2])
    page.evaluate("if (window.switchTab) window.switchTab('overview');")

    smooth_move_mouse(page, 650, 240, steps=15)
    smooth_move_mouse(page, 620, 380, steps=15)
    smooth_move_mouse(page, 1280, 380, steps=15)
    smooth_move_mouse(page, 960, 560, steps=15)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[2]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 4: Elderly Profile Modal
    # ---------------------------------------------------------------------------
    print("[Recording] Step 4: Elderly Profile Modal")
    step_start = time.time()
    update_hud(page, STEPS[3])
    click_element(page, "#btnOpenElderlyProfile", fallback_x=1340, fallback_y=240)

    smooth_move_mouse(page, 800, 420, steps=14)
    smooth_move_mouse(page, 1120, 420, steps=14)
    smooth_move_mouse(page, 960, 570, steps=14)
    click_element(page, "#residentProfileModal button.btn-demo-primary", fallback_x=1240, fallback_y=710)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[3]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 5: Voice Assistant
    # ---------------------------------------------------------------------------
    print("[Recording] Step 5: Voice Assistant")
    step_start = time.time()
    update_hud(page, STEPS[4])
    click_element(page, "#tabBtnVoiceAssistant", fallback_x=320, fallback_y=165)

    click_element(page, ".demo-prompt-pill-btn:has-text('scheduled medication')", fallback_x=710, fallback_y=420)
    smooth_move_mouse(page, 960, 540, steps=16)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[4]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 6: Daily Check-in
    # ---------------------------------------------------------------------------
    print("[Recording] Step 6: Daily Check-in")
    step_start = time.time()
    update_hud(page, STEPS[5])
    click_element(page, "#tabBtnDailyCheckin", fallback_x=450, fallback_y=165)

    click_element(page, ".demo-checkin-option-card[data-status='unwell']", fallback_x=960, fallback_y=320)
    try:
        textarea = page.locator("#demoCheckinNotes")
        if textarea.is_visible():
            textarea.fill("Mild morning dizziness upon standing; vitals stable.")
    except Exception:
        pass

    click_element(page, "#panelDailyCheckin button.btn-demo-primary", fallback_x=960, fallback_y=680)
    smooth_move_mouse(page, 960, 820, steps=16)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[5]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 7: Fall Detection Simulation
    # ---------------------------------------------------------------------------
    print("[Recording] Step 7: Fall Detection Simulation")
    step_start = time.time()
    update_hud(page, STEPS[6])
    click_element(page, "#tabBtnFallDetection", fallback_x=730, fallback_y=165)

    smooth_move_mouse(page, 960, 320, steps=15)
    click_element(page, "#btnTriggerFallSimulation", fallback_x=960, fallback_y=460)
    smooth_move_mouse(page, 960, 580, steps=16)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[6]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 8: Emergency Alert (Ambulance CAD)
    # ---------------------------------------------------------------------------
    print("[Recording] Step 8: Emergency Alert (Ambulance CAD)")
    step_start = time.time()
    update_hud(page, STEPS[7])
    click_element(page, "#tabBtnEmergencyAlert", fallback_x=880, fallback_y=165)

    smooth_move_mouse(page, 960, 260, steps=14)
    smooth_move_mouse(page, 960, 420, steps=14)
    click_element(page, "#demoEmergencyAlertContent button.btn-demo-primary", fallback_x=860, fallback_y=620)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[7]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 9: Location Map & Hospitals
    # ---------------------------------------------------------------------------
    print("[Recording] Step 9: Location Map & Nearby Hospitals")
    step_start = time.time()
    update_hud(page, STEPS[8])
    click_element(page, "#tabBtnLocationMap", fallback_x=1150, fallback_y=165)

    smooth_move_mouse(page, 960, 410, steps=16)
    smooth_move_mouse(page, 680, 680, steps=16)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[8]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 10: Caregiver Dashboard (/admin)
    # ---------------------------------------------------------------------------
    print("[Recording] Step 10: Caregiver Dashboard (/admin)")
    step_start = time.time()
    update_hud(page, STEPS[9])
    click_element(page, ".btn-admin-link", fallback_x=1440, fallback_y=88)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, STEPS[9])

    smooth_move_mouse(page, 960, 260, steps=14)
    smooth_move_mouse(page, 960, 480, steps=14)
    smooth_move_mouse(page, 1260, 310, steps=14)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[9]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 11: Notification Center
    # ---------------------------------------------------------------------------
    print("[Recording] Step 11: Notification Center")
    step_start = time.time()
    update_hud(page, STEPS[10])
    click_element(page, "a[href='/#demo']", fallback_x=1600, fallback_y=88)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, STEPS[10])

    click_element(page, "#tabBtnNotificationCenter", fallback_x=1290, fallback_y=165)
    smooth_move_mouse(page, 960, 360, steps=14)
    click_element(page, ".btn-notif-action:has-text('Read')", fallback_x=1420, fallback_y=360)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[10]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 12: Incident History
    # ---------------------------------------------------------------------------
    print("[Recording] Step 12: Incident History Audit Log")
    step_start = time.time()
    update_hud(page, STEPS[11])
    click_element(page, "#tabBtnIncidentHistory", fallback_x=1420, fallback_y=165)

    smooth_move_mouse(page, 960, 380, steps=14)
    click_element(page, "#demoIncidentHistoryTableBody tr:first-child button.btn-demo-secondary", fallback_x=1440, fallback_y=380)
    smooth_move_mouse(page, 960, 480, steps=14)
    click_element(page, "button:has-text('Close')", fallback_x=1200, fallback_y=680)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[11]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 13: Medication Reminders
    # ---------------------------------------------------------------------------
    print("[Recording] Step 13: Medication Reminders")
    step_start = time.time()
    update_hud(page, STEPS[12])
    click_element(page, "#tabBtnMedicationReminders", fallback_x=590, fallback_y=165)

    smooth_move_mouse(page, 960, 320, steps=14)
    smooth_move_mouse(page, 960, 520, steps=14)
    click_element(page, "#btnMedAction_coq10", fallback_x=1380, fallback_y=520)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[12]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # STEP 14: Closing
    # ---------------------------------------------------------------------------
    print("[Recording] Step 14: Closing (NIRA Portal & Tagline)")
    step_start = time.time()
    update_hud(page, STEPS[13])
    click_element(page, ".btn-portal-home", fallback_x=870, fallback_y=88)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, STEPS[13])

    smooth_move_mouse(page, 960, 240, steps=18)
    smooth_move_mouse(page, 960, 310, steps=16)
    elapsed = time.time() - step_start
    time.sleep(max(0.1, STEPS[13]["duration"] - elapsed))

    print("\n[Recording] Browser walkthrough completed! Finalizing video context...")
    context.close()
    browser.close()
    p.stop()

    webm_files = list(RAW_VIDEO_DIR.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("No recorded WebM file found in RAW_VIDEO_DIR!")

    raw_webm = sorted(webm_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
    print(f"Raw recorded browser video: {raw_webm} ({raw_webm.stat().st_size / 1024 / 1024:.2f} MB)")

    # ---------------------------------------------------------------------------
    # Transcode to MP4 at 1920x1080 @ 30 FPS with synced narration
    # ---------------------------------------------------------------------------
    print("\n--- Transcoding to High Quality MP4 with FFmpeg ---")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_webm),
        "-i", str(narration_wav),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-preset", "slow",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(FINAL_VIDEO_PATH)
    ]
    subprocess.run(ffmpeg_cmd, check=True)

    print(f"\n[SUCCESS] Final Walkthrough Video generated at: {FINAL_VIDEO_PATH}")
    file_size_mb = FINAL_VIDEO_PATH.stat().st_size / 1024 / 1024
    print(f"File Size: {file_size_mb:.2f} MB")

    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=width,height,r_frame_rate,codec_name",
        "-of", "json", str(FINAL_VIDEO_PATH)
    ]
    probe_output = json.loads(subprocess.check_output(probe_cmd))
    duration_sec = float(probe_output["format"]["duration"])
    print(f"Final Video Duration: {duration_sec:.2f} seconds (Target: 75–90 seconds)")

    verify_dir = SCRATCH_DIR / "verification_frames"
    verify_dir.mkdir(parents=True, exist_ok=True)
    for ts in [10, 42, min(int(duration_sec - 4), 78)]:
        frame_path = verify_dir / f"frame_{ts:02d}s.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(ts), "-i", str(FINAL_VIDEO_PATH),
            "-vframes", "1", "-q:v", "2", str(frame_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Verification frame extracted at {ts}s: {frame_path}")

    print("\n=======================================================")
    print(" NIRA DEMO APPLICATION WALKTHROUGH VIDEO READY")
    print(f" Path: {FINAL_VIDEO_PATH}")
    print(f" Duration: {duration_sec:.2f}s | Resolution: 1920x1080 | 30 FPS")
    print("=======================================================\n")


if __name__ == "__main__":
    run_recording_walkthrough()
