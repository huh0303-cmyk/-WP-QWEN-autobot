#!/usr/bin/env python3
"""Generate Fish Audio Free voice samples for the seven locked channel profiles.
This script never uploads to YouTube. Output is intended for human listening/approval.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/youtube_voice_profiles.json").read_text(encoding="utf-8"))
API_KEY = os.getenv("FISH_AUDIO_API_KEY", "").strip()
MODEL = "s2.1-pro-free"
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
        raise SystemExit("FISH_AUDIO_API_KEY is missing; no audio was generated.")
    manifest = {"model_id": MODEL, "uploads_performed": False, "clips": []}
    for key, profile in CONFIG["channels"].items():
        out_path = OUT / f"{key}.mp3"
        response = requests.post(
            "https://api.fish.audio/v1/tts",
            headers={"Authorization": f"Bearer {API_KEY}", "model": MODEL,
                     "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json={"text": SAMPLES[key], "format": "mp3"},
            timeout=120,
        )
        if not response.ok:
            raise RuntimeError(f"{key} TTS failed with HTTP {response.status_code}: {response.text[:250]}")
        if len(response.content) < 2000:
            raise RuntimeError(f"{key} returned an unexpectedly short audio file.")
        out_path.write_bytes(response.content)
        manifest["clips"].append({
            "channel_key": key, "display_name": profile["display_name"],
            "provider": "Fish Audio", "model": MODEL, "voice_name": "Fish Audio default multilingual voice",
            "direction": profile.get("direction", ""), "file": out_path.name,
            "bytes": len(response.content), "status": "generated; human listening required"
        })
        print(f"Generated audition: {key} ({profile.get('voice_name')})")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Done. Fish Audio Free samples generated; no videos were rendered or uploaded.")

if __name__ == "__main__":
    main()
