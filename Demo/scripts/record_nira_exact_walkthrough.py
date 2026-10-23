"""
NIRA — Exact 75–90s Screen-Recorded Demo Application Walkthrough.
Amazon Developer Hackathon 2026.

Demo sequence & timeline:
- 0–5s: NIRA logo and project introduction.
- 5–12s: Login page.
- 12–22s: Main dashboard and elderly person's health overview.
- 22–30s: Elderly profile and medication reminders.
- 30–40s: Voice assistant and daily check-in.
- 40–50s: Demonstrate the fall-detection simulation.
- 50–62s: Emergency alert and location map.
- 62–72s: Caregiver dashboard and notifications.
- 72–82s: Incident history and acknowledgement.
- 82–90s: Closing screen with the NIRA project name and tagline.

Resolution: 1920x1080 | 30 FPS | MP4 | Output: output/NIRA_Demo_Walkthrough.mp4
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
RAW_VIDEO_DIR = SCRATCH_DIR / "playwright_exact_rec"
AUDIO_DIR = SCRATCH_DIR / "audio_exact_narration"

RAW_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class Segment(TypedDict):
    index: int
    time_range: str
    title: str
    subtitle: str
    narration: str
    duration: float


# 10 Exact Segments matching user specification (Total: 90.0 seconds)
SEGMENTS: List[Segment] = [
    {
        "index": 1,
        "time_range": "0–5s",
        "title": "NIRA Logo & Project Introduction",
        "subtitle": "Never Ignore Risk Assistant • Ambient AI Elder Care",
        "narration": "Welcome to NIRA: Never Ignore Risk Assistant. An ambient AI safety monitoring platform engineered for senior care.",
        "duration": 5.0
    },
    {
        "index": 2,
        "time_range": "5–12s",
        "title": "Secure Portal Login",
        "subtitle": "Role-Based Access for Families, Clinicians & Medics",
        "narration": "Accessing the secure enterprise portal. Users log in through role-based access for family guardians, clinicians, and emergency first responders.",
        "duration": 7.0
    },
    {
        "index": 3,
        "time_range": "12–22s",
        "title": "Main Dashboard & Health Overview",
        "subtitle": "Eleanor Vance • Resting Vitals, Wellbeing & Telemetry",
        "narration": "The main dashboard provides an instant overview of Eleanor Vance's health, presenting normal resting vitals, restful sleep telemetry, active radar pods, and ambient room metrics.",
        "duration": 10.0
    },
    {
        "index": 4,
        "time_range": "22–30s",
        "title": "Elderly Profile & Medication Reminders",
        "subtitle": "Clinical Profile, Smart PIN 8492 & Prescription Dosing",
        "narration": "Opening Eleanor's profile reveals her clinical notes, allergy alerts, and smart deadbolt PIN 8492, followed by the medication module tracking daily prescriptions.",
        "duration": 8.0
    },
    {
        "index": 5,
        "time_range": "30–40s",
        "title": "Voice Assistant & Daily Check-in",
        "subtitle": "Bidirectional Speech Query & Wellness Logging",
        "narration": "The voice assistant provides conversational support with audible replies. During daily check-in, Eleanor submits her wellness response, instantly logging a mild dizziness flag for her family.",
        "duration": 10.0
    },
    {
        "index": 6,
        "time_range": "40–50s",
        "title": "Fall-Detection Simulation",
        "subtitle": "3.42g Impact Spike & Acute Tachycardia Alert",
        "narration": "In the fall detection simulator, multimodal sensors continuously monitor posture and velocity. Triggering Simulate Fall generates a 3.42g impact velocity on bathroom tile with severe tachycardia.",
        "duration": 10.0
    },
    {
        "index": 7,
        "time_range": "50–62s",
        "title": "Emergency Alert & Location Map",
        "subtitle": "Boston EMS Medic 14 En Route & Trauma Hospital Route",
        "narration": "NIRA immediately triggers Ambulance CAD dispatch for Boston EMS Medic 14, automatically unlocking the smart deadbolt with emergency token 8492. The location map routes medics directly to regional Level 1 trauma centers including Mass General Hospital.",
        "duration": 12.0
    },
    {
        "index": 8,
        "time_range": "62–72s",
        "title": "Caregiver Dashboard & Notifications",
        "subtitle": "David Vance Guardian Console & Emergency Feed",
        "narration": "Switching to David Vance's Caregiver Dashboard, family guardians review live tachycardia alarms, location activity, and door lock overrides. Returning to the notification center, the emergency alert is verified and marked read.",
        "duration": 10.0
    },
    {
        "index": 9,
        "time_range": "72–82s",
        "title": "Incident History & Acknowledgment",
        "subtitle": "Forensic Audit Log & Verified Response Milestones",
        "narration": "Incident History maintains an immutable forensic log. Opening the incident details reveals the chronological action timeline, sensor metrics, and verified caregiver acknowledgment milestones.",
        "duration": 10.0
    },
    {
        "index": 10,
        "time_range": "82–90s",
        "title": "Closing — Never Ignore Risk Assistant",
        "subtitle": "NIRA Ambient Healthcare • Amazon Developer Hackathon 2026",
        "narration": "NIRA delivers continuous, privacy-preserving ambient protection: Never Ignore Risk Assistant. Engineered for the Amazon Developer Hackathon 2026.",
        "duration": 8.0
    }
]

TOTAL_DURATION = sum(s["duration"] for s in SEGMENTS)
print(f"[Walkthrough Plan] Total planned duration: {TOTAL_DURATION:.1f} seconds (Target: 75–90s)")


def generate_speech_clip(text: str, out_wav: Path):
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
    print("\n--- Generating Professional English Narration Track ---")
    combined_wav = SCRATCH_DIR / "complete_exact_narration.wav"
    segment_files = []

    for seg in SEGMENTS:
        clip_wav = AUDIO_DIR / f"segment_{seg['index']:02d}.wav"
        generate_speech_clip(seg["narration"], clip_wav)

        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(clip_wav)
        ]
        clip_dur = float(subprocess.check_output(probe_cmd).strip())
        target_dur = seg["duration"]

        padded_wav = AUDIO_DIR / f"padded_segment_{seg['index']:02d}.wav"
        pad_cmd = [
            "ffmpeg", "-y", "-i", str(clip_wav),
            "-af", f"apad=whole_dur={target_dur:.2f}",
            "-t", f"{target_dur:.2f}",
            str(padded_wav)
        ]
        subprocess.run(pad_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        segment_files.append(padded_wav)
        print(f"  Segment {seg['index']:02d} ({seg['time_range']}): {clip_dur:.2f}s speech -> exact {target_dur:.2f}s")

    concat_list = SCRATCH_DIR / "concat_exact_audio_list.txt"
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
    page.evaluate("""
() => {
  if (document.getElementById('niraWalkthroughHud')) return;

  const hud = document.createElement('div');
  hud.id = 'niraWalkthroughHud';
  hud.style.cssText = `
    position: fixed;
    top: 20px;
    right: 28px;
    z-index: 999999;
    background: rgba(11, 17, 32, 0.92);
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
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  `;
  hud.innerHTML = `
    <div style="width: 42px; height: 42px; border-radius: 12px; background: linear-gradient(135deg, rgba(56, 189, 248, 0.25) 0%, rgba(16, 185, 129, 0.25) 100%); border: 1.5px solid rgba(56, 189, 248, 0.5); display: flex; align-items: center; justify-content: center; font-size: 1.3rem;">
      🛡️
    </div>
    <div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <span id="hudStepBadge" style="background: rgba(56, 189, 248, 0.2); border: 1px solid rgba(56, 189, 248, 0.45); color: #38bdf8; font-size: 0.68rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.06em;">
          0–5s • INTRO
        </span>
        <span id="hudStepTitle" style="font-size: 0.92rem; font-weight: 800; color: #ffffff;">
          NIRA Logo & Project Introduction
        </span>
      </div>
      <div id="hudStepSub" style="font-size: 0.76rem; color: #94a3b8; margin-top: 2px;">
        Never Ignore Risk Assistant • Ambient AI Elder Care
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

  window.updateNiraHud = function(range, title, subtitle) {
    const b = document.getElementById('hudStepBadge');
    const t = document.getElementById('hudStepTitle');
    const s = document.getElementById('hudStepSub');
    if (b) b.textContent = `${range}`;
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


def update_hud(page, seg_dict):
    try:
        page.evaluate(
            f"window.updateNiraHud({json.dumps(seg_dict['time_range'])}, {json.dumps(seg_dict['title'])}, {json.dumps(seg_dict['subtitle'])})"
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

    # 2. Build exact narration audio track
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
    # SEGMENT 1 (0–5s): NIRA logo and project introduction
    # ---------------------------------------------------------------------------
    print("[Recording] 0–5s: NIRA logo and project introduction")
    seg_start = time.time()
    page.goto("http://127.0.0.1:8000/", wait_until="domcontentloaded")
    page.evaluate("localStorage.clear();")
    page.reload(wait_until="domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, SEGMENTS[0])

    smooth_move_mouse(page, 960, 260, steps=18)
    smooth_move_mouse(page, 960, 310, steps=16)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[0]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 2 (5–12s): Login page
    # ---------------------------------------------------------------------------
    print("[Recording] 5–12s: Login page")
    seg_start = time.time()
    update_hud(page, SEGMENTS[1])
    click_element(page, "#btnLandingLogin", fallback_x=1110, fallback_y=375)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, SEGMENTS[1])

    smooth_move_mouse(page, 960, 480, steps=14)
    time.sleep(0.5)
    smooth_move_mouse(page, 960, 560, steps=14)
    time.sleep(0.5)
    # Hover over 1-click role buttons
    smooth_move_mouse(page, 960, 720, steps=14)
    time.sleep(0.8)
    # Click Sign In to Portal
    click_element(page, "#btnLogin", fallback_x=960, fallback_y=630)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[1]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 3 (12–22s): Main dashboard and elderly person's health overview
    # ---------------------------------------------------------------------------
    print("[Recording] 12–22s: Main dashboard and elderly person's health overview")
    seg_start = time.time()
    update_hud(page, SEGMENTS[2])
    page.evaluate("if (window.switchTab) window.switchTab('overview');")

    # Focus on Eleanor's elderly card
    smooth_move_mouse(page, 650, 240, steps=16)
    time.sleep(1.8)

    # Focus on Wellbeing Summary metrics (Sleep, Mobility, Devices)
    smooth_move_mouse(page, 620, 380, steps=16)
    time.sleep(2.0)

    # Focus on Apple Health Vitals rings (HR 72 BPM, Apple Watch connected)
    smooth_move_mouse(page, 1280, 380, steps=16)
    time.sleep(2.0)

    # Focus on Monitored Recent Activity
    smooth_move_mouse(page, 960, 560, steps=16)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[2]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 4 (22–30s): Elderly profile and medication reminders
    # ---------------------------------------------------------------------------
    print("[Recording] 22–30s: Elderly profile and medication reminders")
    seg_start = time.time()
    update_hud(page, SEGMENTS[3])
    # Open Eleanor's profile modal
    click_element(page, "#btnOpenElderlyProfile", fallback_x=1340, fallback_y=240)
    time.sleep(0.8)

    # Move across clinical notes, allergy alerts, and smart deadbolt PIN 8492
    smooth_move_mouse(page, 800, 420, steps=12)
    smooth_move_mouse(page, 1120, 420, steps=12)
    time.sleep(0.8)
    # Close modal
    click_element(page, "#residentProfileModal button.btn-demo-primary", fallback_x=1240, fallback_y=710)
    time.sleep(0.6)

    # Switch to Medication Reminders tab
    click_element(page, "#tabBtnMedicationReminders", fallback_x=590, fallback_y=165)
    time.sleep(0.8)
    # Click Take Dose Now for CoQ10
    click_element(page, "#btnMedAction_coq10", fallback_x=1380, fallback_y=520)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[3]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 5 (30–40s): Voice assistant and daily check-in
    # ---------------------------------------------------------------------------
    print("[Recording] 30–40s: Voice assistant and daily check-in")
    seg_start = time.time()
    update_hud(page, SEGMENTS[4])
    # Switch to Voice Assistant
    click_element(page, "#tabBtnVoiceAssistant", fallback_x=320, fallback_y=165)
    time.sleep(0.8)

    # Click prompt pill: "What is my scheduled medication?"
    click_element(page, ".demo-prompt-pill-btn:has-text('scheduled medication')", fallback_x=710, fallback_y=420)
    smooth_move_mouse(page, 960, 540, steps=14)
    time.sleep(2.2)

    # Switch to Daily Check-in tab
    click_element(page, "#tabBtnDailyCheckin", fallback_x=450, fallback_y=165)
    time.sleep(0.8)

    # Select "Feeling Unwell"
    click_element(page, ".demo-checkin-option-card[data-status='unwell']", fallback_x=960, fallback_y=320)
    time.sleep(0.5)

    # Type dizziness note
    try:
        textarea = page.locator("#demoCheckinNotes")
        if textarea.is_visible():
            textarea.fill("Mild morning dizziness upon standing; vitals stable.")
    except Exception:
        pass
    time.sleep(0.5)

    # Submit check-in
    click_element(page, "#panelDailyCheckin button.btn-demo-primary", fallback_x=960, fallback_y=680)
    smooth_move_mouse(page, 960, 820, steps=14)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[4]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 6 (40–50s): Demonstrate the fall-detection simulation
    # ---------------------------------------------------------------------------
    print("[Recording] 40–50s: Demonstrate the fall-detection simulation")
    seg_start = time.time()
    update_hud(page, SEGMENTS[5])
    click_element(page, "#tabBtnFallDetection", fallback_x=730, fallback_y=165)
    time.sleep(0.8)

    # Inspect normal sensor telemetry HUD
    smooth_move_mouse(page, 960, 320, steps=16)
    time.sleep(1.2)

    # Trigger "Simulate Fall Now"
    click_element(page, "#btnTriggerFallSimulation", fallback_x=960, fallback_y=460)
    time.sleep(1.2)

    # Hover over 3.42g acceleration spike and critical incident alert banner
    smooth_move_mouse(page, 960, 580, steps=16)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[5]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 7 (50–62s): Emergency alert and location map
    # ---------------------------------------------------------------------------
    print("[Recording] 50–62s: Emergency alert and location map")
    seg_start = time.time()
    update_hud(page, SEGMENTS[6])
    # Switch to Ambulance CAD
    click_element(page, "#tabBtnEmergencyAlert", fallback_x=880, fallback_y=165)
    time.sleep(1.0)

    # Move over Ambulance CAD banner (Medic 14 en route, Smart Lock Token 8492)
    smooth_move_mouse(page, 960, 260, steps=14)
    time.sleep(1.2)

    # Click Acknowledge Incident button
    click_element(page, "#demoEmergencyAlertContent button.btn-demo-primary", fallback_x=860, fallback_y=620)
    time.sleep(1.2)

    # Switch to Location Map & Hospitals
    click_element(page, "#tabBtnLocationMap", fallback_x=1150, fallback_y=165)
    time.sleep(1.2)

    # Glide over Beacon Hill residence GPS marker and hospital markers
    smooth_move_mouse(page, 960, 410, steps=16)
    time.sleep(1.8)
    smooth_move_mouse(page, 680, 680, steps=16)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[6]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 8 (62–72s): Caregiver dashboard and notifications
    # ---------------------------------------------------------------------------
    print("[Recording] 62–72s: Caregiver dashboard and notifications")
    seg_start = time.time()
    update_hud(page, SEGMENTS[7])
    # Switch to David Vance Admin Console
    click_element(page, ".btn-admin-link", fallback_x=1440, fallback_y=88)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, SEGMENTS[7])

    smooth_move_mouse(page, 960, 260, steps=14)
    time.sleep(1.2)
    smooth_move_mouse(page, 960, 480, steps=14)
    time.sleep(1.2)
    smooth_move_mouse(page, 1260, 310, steps=14)
    time.sleep(1.0)

    # Return to Demo notifications
    click_element(page, "a[href='/#demo']", fallback_x=1600, fallback_y=88)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, SEGMENTS[7])

    click_element(page, "#tabBtnNotificationCenter", fallback_x=1290, fallback_y=165)
    smooth_move_mouse(page, 960, 360, steps=14)
    time.sleep(0.8)
    click_element(page, ".btn-notif-action:has-text('Read')", fallback_x=1420, fallback_y=360)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[7]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 9 (72–82s): Incident history and acknowledgement
    # ---------------------------------------------------------------------------
    print("[Recording] 72–82s: Incident history and acknowledgement")
    seg_start = time.time()
    update_hud(page, SEGMENTS[8])
    click_element(page, "#tabBtnIncidentHistory", fallback_x=1420, fallback_y=165)
    time.sleep(1.0)

    # Hover over top simulated fall incident
    smooth_move_mouse(page, 960, 380, steps=14)
    time.sleep(1.0)

    # Open forensic details modal
    click_element(page, "#demoIncidentHistoryTableBody tr:first-child button.btn-demo-secondary", fallback_x=1440, fallback_y=380)
    time.sleep(1.0)

    # Sweep through forensic sensor timeline
    smooth_move_mouse(page, 960, 480, steps=16)
    time.sleep(1.8)

    # Close modal
    click_element(page, "button:has-text('Close')", fallback_x=1200, fallback_y=680)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[8]["duration"] - elapsed))

    # ---------------------------------------------------------------------------
    # SEGMENT 10 (82–90s): Closing screen with the NIRA project name and tagline
    # ---------------------------------------------------------------------------
    print("[Recording] 82–90s: Closing screen with NIRA name and tagline")
    seg_start = time.time()
    update_hud(page, SEGMENTS[9])
    click_element(page, ".btn-portal-home", fallback_x=870, fallback_y=88)
    page.wait_for_load_state("domcontentloaded")
    inject_visual_hud(page)
    update_hud(page, SEGMENTS[9])

    # Center cursor on glowing shield emblem, NIRA title, and tagline
    smooth_move_mouse(page, 960, 240, steps=18)
    time.sleep(1.5)
    smooth_move_mouse(page, 960, 310, steps=16)
    elapsed = time.time() - seg_start
    time.sleep(max(0.1, SEGMENTS[9]["duration"] - elapsed))

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

    verify_dir = SCRATCH_DIR / "verification_exact_frames"
    verify_dir.mkdir(parents=True, exist_ok=True)
    # Extract frames across the key moments of the requested timeline
    for ts in [3, 8, 17, 26, 35, 45, 56, 67, 77, 86]:
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
