"""Approved six-voice documentary/news narrator selection, free TTS only."""
from __future__ import annotations
from voice_rotation import choose_voice

def select_documentary_narrator(channel_key: str = "") -> dict[str, str]:
    voice = choose_voice((channel_key or "").strip().lower())
    return {
        "voice_id": voice["id"], "name": voice["name"],
        "accent": voice.get("accent", "language-matched"),
        "gender": voice["gender"],
        "style": "authoritative deep documentary or professional news anchor",
        "profile": voice["channel"], "language": voice["language"],
        "date": voice.get("date", ""),
    }
