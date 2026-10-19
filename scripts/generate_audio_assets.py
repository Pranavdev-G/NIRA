import os
import subprocess

def main():
    audio_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static", "audio")
    os.makedirs(audio_dir, exist_ok=True)

    clips = {
        "scene_0.wav": (
            "Microsoft Zira Desktop",
            "Welcome to Aegis Ambient Care. Eleanor Vance, age 79, lives independently at Beacon Hill Unit 4B. The apartment is continuously protected by ceiling micro-radar and ambient sensors, preserving total privacy without invasive cameras."
        ),
        "scene_1.wav": (
            "Microsoft Zira Desktop",
            "At 2:14 AM, the ceiling radar detects a sudden downward drop in the bathroom. The multimodal AI confirms a 94 percent probability of a fall on wet tile, while Apple Watch telemetry captures acute tachycardia surging to 138 beats per minute."
        ),
        "scene_2.wav": (
            "Microsoft Zira Desktop",
            "Within sub-500 milliseconds, the Echo Show 15 activates an ambient voice check-in: Eleanor, this is Aegis. I noticed a fall in the bathroom. Are you okay? Aegis listens for 20 seconds. With zero verbal response, the AI flags Eleanor as presumed unconscious."
        ),
        "scene_3.wav": (
            "Microsoft David Desktop",
            "Aegis immediately connects her primary guardian and son, David Vance. His phone receives an instant priority notification and opens a live Echo Drop-In audio stream, allowing David to speak directly to his mother and hear the room in real time."
        ),
        "scene_4.wav": (
            "Microsoft Zira Desktop",
            "Simultaneously, Aegis dispatches Boston EMS Medic 14 with Eleanor's clinical vitals and floor status. The front door smart lock is automatically unlocked with emergency PIN 8492, allowing paramedics to enter instantly without delay."
        ),
        "alexa_checkin.wav": (
            "Microsoft Zira Desktop",
            "Eleanor, this is Aegis. I noticed a fall in the bathroom. Are you okay? Please tell me if you need help."
        ),
        "eleanor_reply.wav": (
            "Microsoft Zira Desktop",
            "I'm okay, Alexa! I just dropped my glasses."
        ),
        "eleanor_distress.wav": (
            "Microsoft Zira Desktop",
            "Help me, Alexa! I slipped and hurt my wrist, I can't get up!"
        ),
        "eleanor_silent.wav": (
            "Microsoft Zira Desktop",
            "No response for twenty seconds. Eleanor is presumed unconscious."
        ),
        "son_memo.wav": (
            "Microsoft David Desktop",
            "Mom! This is David. Aegis just alerted me on Alexa. I see your heart rate spiked. Are you okay? I'm rushing over right now!"
        ),
        "test_audio.wav": (
            "Microsoft Zira Desktop",
            "Aegis Ambient Care audio system is active. High fidelity voice narration is ready."
        ),
    }

    for filename, (voice, text) in clips.items():
        out_path = os.path.abspath(os.path.join(audio_dir, filename))
        ps_script = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('{voice}')
$s.SetOutputToWaveFile('{out_path}')
$s.Speak("{text}")
$s.Dispose()
"""
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error generating {filename}: {res.stderr}")
        else:
            print(f"Generated {filename} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    main()
