"""
Helper script to generate real spoken WAV files for Whisper large-v3-turbo validation.
"""

import os
import win32com.client

phrases = {
    "Live/test_speech_safe.wav": "Yes, I am okay.",
    "Live/test_speech_emergency.wav": "Help me! I fell down and cannot get up!",
    "Live/test_speech_negated.wav": "I am not okay.",
    "Live/test_speech_mixed.wav": "Yes, I am okay, but I fell down and I cannot get up."
}

for path, text in phrases.items():
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    stream = win32com.client.Dispatch("SAPI.SpFileStream")
    stream.Open(path, 3)
    speaker.AudioOutputStream = stream
    speaker.Speak(text)
    stream.Close()
    print(f"Generated {path} ({os.path.getsize(path)} bytes)")
