#!/usr/bin/env python3
"""Generate private ElevenLabs voice audition clips for the seven locked channel profiles.
This script never uploads to YouTube. Output is intended for human listening/approval.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/youtube_voice_profiles.json").read_text(encoding="utf-8"))
API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
MODEL = os.getenv("ELEVENLABS_MODEL_ID", CONFIG.get("model_id", "eleven_multilingual_v2"))
OUT = ROOT / "artifacts" / "voice-audit"
OUT.mkdir(parents=True, exist_ok=True)

SAMPLES = {
    "health_clinic_usa": "As we get older, small daily habits can make a meaningful difference. Today, we will look at what the evidence says, what remains uncertain, and when it is important to speak with your healthcare professional.",
    "health_clinic_japan": "年齢を重ねるにつれて、毎日の小さな習慣が健康を支えることがあります。今日は、現在わかっていることと、まだはっきりしていないことを、わかりやすく確認しましょう。",
    "nasa": "The universe is full of discoveries that change how we see our place in space. To understand this mission, we need to look beyond the headline and follow the evidence, one remarkable detail at a time.",
    "history_today": "History is not just a list of dates. It is a series of decisions, discoveries, and turning points whose consequences can still be felt today.",
    "retro_usa": "Remember the little details that made everyday American life feel different? From the sounds in the living room to the trends on the high street, these memories tell a bigger story about how culture changed.",
    "old_hollywood": "Before modern blockbusters, cinema pioneers built a new visual language with light, movement, and unforgettable performances. Their experiments helped shape the movies we watch today.",
    "seoul_jisoo1": "Planning a trip to Seoul? Let us make it easier. I will show you what to look for in a hotel, how to compare locations, and a few practical details that can make your Korea trip smoother.",
}

def main():
    if not API_KEY:
        raise SystemExit("ELEVENLABS_API_KEY is missing; no audio was generated.")
    manifest = {"model_id": MODEL, "uploads_performed": False, "clips": []}
    for key, profile in CONFIG["channels"].items():
        voice_env = profile.get("voice_id_env", "")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID_" + key.upper(), "").strip()
        # Backwards-compatible secret/variable names recorded in the voice profile.
        if not voice_id and voice_env:
            voice_id = os.getenv(voice_env, "").strip()
        if not voice_id:
            voice_id = profile.get("fallback_voice_id", "").strip()
        if not voice_id:
            raise RuntimeError(f"No approved voice ID configured for {key}; refusing to synthesize with a mismatched voice.")
        out_path = OUT / f"{key}.mp3"
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json={"text": SAMPLES[key], "model_id": MODEL,
                  "voice_settings": CONFIG.get("voice_settings", {})},
            timeout=90,
        )
        if not response.ok:
            raise RuntimeError(f"{key} TTS failed with HTTP {response.status_code}: {response.text[:250]}")
        if len(response.content) < 2000:
            raise RuntimeError(f"{key} returned an unexpectedly short audio file.")
        out_path.write_bytes(response.content)
        manifest["clips"].append({
            "channel_key": key, "display_name": profile["display_name"],
            "voice_id": voice_id, "voice_name": profile.get("voice_name", ""),
            "direction": profile.get("direction", ""), "file": out_path.name,
            "bytes": len(response.content), "status": "generated; human listening required"
        })
        print(f"Generated audition: {key} ({profile.get('voice_name')})")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Done. No videos were rendered or uploaded. Listen to the artifact clips before approving production.")

if __name__ == "__main__":
    main()
