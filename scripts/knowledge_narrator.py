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


def select_documentary_narrator() -> dict[str, str]:
    """Prefer account voices spanning US/UK and male/female; never select a blank ID."""
    configured = []
    for profile in ("US_MALE", "US_FEMALE", "UK_MALE", "UK_FEMALE"):
        voice_id = os.getenv(f"KNOWLEDGE_VOICE_{profile}_ID", "").strip()
        if voice_id:
            country, gender = profile.lower().split("_")
            configured.append({"voice_id": voice_id, "name": profile, "accent": country, "gender": gender})
    try:
        available = _documentary_candidates(os.getenv("ELEVENLABS_API_KEY", "").strip())
    except Exception:
        available = []
    pool = configured or available or FALLBACKS
    return random.SystemRandom().choice(pool)
