"""Select a varied ElevenLabs documentary narrator from available account voices."""
from __future__ import annotations

import os
import random
import requests


FALLBACKS = [
    {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "accent": "american", "gender": "male"},
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "accent": "american", "gender": "female"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "accent": "american", "gender": "female"},
]


def _documentary_candidates(api_key: str) -> list[dict[str, str]]:
    if not api_key:
        return []
    response = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": api_key}, timeout=30,
    )
    response.raise_for_status()
    candidates = []
    for voice in response.json().get("voices", []):
        labels = {str(k).lower(): str(v).lower() for k, v in (voice.get("labels") or {}).items()}
        accent = labels.get("accent", "")
        gender = labels.get("gender", "")
        use_case = " ".join((labels.get("use case", ""), labels.get("use_case", ""), labels.get("description", "")))
        if gender not in {"male", "female"}:
            continue
        if not any(term in accent for term in ("american", "british", "english", "us", "uk")):
            continue
        if use_case and not any(term in use_case for term in ("narrat", "document", "story", "news", "educat")):
            continue
        candidates.append({
            "voice_id": voice["voice_id"], "name": voice.get("name", "Narrator"),
            "accent": accent or "english", "gender": gender,
        })
    return candidates


# Stable channel assignments. IDs are ElevenLabs public premade voices; per-channel
# environment overrides allow the owner to substitute a preferred voice without code changes.
CHANNEL_PROFILES = {
    "nasa": {"env": "ELEVENLABS_VOICE_ID_NASA", "default": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "accent": "american", "gender": "male", "style": "authoritative science documentary"},
    "history": {"env": "ELEVENLABS_VOICE_ID_HISTORY_TODAY", "default": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "accent": "american", "gender": "female", "style": "clear, measured historical narration"},
    "silent_era": {"env": "ELEVENLABS_VOICE_ID_OLD_HOLLYWOOD", "default": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "accent": "american", "gender": "male", "style": "classic cinema documentary"},
    "retro_reels": {"env": "ELEVENLABS_VOICE_ID_RETRO_USA", "default": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "accent": "american", "gender": "female", "style": "warm, conversational nostalgia"},
}


def select_documentary_narrator(channel_key: str = "") -> dict[str, str]:
    """Choose one date-stable narrator per episode, alternating male/female across dates."""
    from voice_rotation import choose_voice

    key = (channel_key or "").strip().lower()
    voice = choose_voice(key)
    profile = CHANNEL_PROFILES.get(key, {})
    return {
        "voice_id": voice["id"], "name": voice["name"],
        "accent": profile.get("accent", "english"), "gender": voice["gender"],
        "style": profile.get("style", "documentary narration"),
        "profile": key, "language": voice["language"], "date": voice["date"],
    }
