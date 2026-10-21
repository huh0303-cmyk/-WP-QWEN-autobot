#!/usr/bin/env python3
"""Generate a Seoul Journal Korean voice sample with ElevenLabs; no publishing."""
import os
import sys
from pathlib import Path
import requests

api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
text = os.environ.get("SEOUL_JOURNAL_TEXT", "").strip()

if not api_key:
    sys.exit("ERROR: GitHub Actions secret ELEVENLABS_API_KEY is missing.")
if not text:
    sys.exit("ERROR: enter the Korean script in the workflow input.")

from voice_rotation import choose_voice
voice = choose_voice("seoul_journal")
voice_id = voice["id"]
print(f"VOICE_ROTATION channel=seoul_journal language=ko gender={voice['gender']} name={voice['name']} id={voice_id}")
endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
response = requests.post(
    endpoint,
    headers={
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    },
    json={
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.55,
            "similarity_boost": 0.8,
            "style": 0.2,
            "use_speaker_boost": True,
        },
    },
    timeout=120,
)
if not response.ok:
    # Do not print headers or secrets.
    sys.exit(f"ElevenLabs request failed ({response.status_code}): {response.text[:1000]}")

out = Path("artifacts/seoul-journal")
out.mkdir(parents=True, exist_ok=True)
audio = out / "seoul-journal-korean-voice-test.mp3"
audio.write_bytes(response.content)
(out / "script.txt").write_text(text + "\n", encoding="utf-8")
import json
(out / "voice-selection.json").write_text(json.dumps(voice, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Created {audio} ({len(response.content)} bytes). No YouTube upload was attempted.")
