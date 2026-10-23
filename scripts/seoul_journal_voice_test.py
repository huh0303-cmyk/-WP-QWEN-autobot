#!/usr/bin/env python3
"""Generate a free Korean Edge neural TTS sample; no API key and no publishing."""
import os
import sys
import asyncio
from pathlib import Path
import edge_tts

text = os.environ.get("SEOUL_JOURNAL_TEXT", "").strip()
voice = os.environ.get("SEOUL_JOURNAL_EDGE_VOICE", "ko-KR-SunHiNeural").strip()
rate = os.environ.get("SEOUL_JOURNAL_TTS_RATE", "+15%").strip()

if not text:
    sys.exit("ERROR: enter the Korean script in the workflow input.")

out = Path("artifacts/seoul-journal")
out.mkdir(parents=True, exist_ok=True)
audio = out / "seoul-journal-korean-voice-test.mp3"

async def main():
    await edge_tts.Communicate(text=text, voice=voice, rate=rate).save(str(audio))

try:
    asyncio.run(main())
except Exception as exc:
    sys.exit(f"Free Edge TTS request failed ({voice}): {exc}")

if not audio.exists() or audio.stat().st_size < 2000:
    sys.exit("ERROR: generated audio is missing or too small.")
(out / "script.txt").write_text(text + "\\n", encoding="utf-8")
(out / "voice-selection.json").write_text(
    __import__("json").dumps({"engine": "edge-tts", "voice": voice, "rate": rate}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"TTS_ENGINE=edge-tts voice={voice} rate={rate}")
print(f"Created {audio} ({audio.stat().st_size} bytes). No YouTube upload was attempted.")
