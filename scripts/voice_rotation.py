"""Stable channel voice profiles for narration pipelines.

This module supplies voice metadata; free-only pipelines use Fish Audio first and
Microsoft Edge neural TTS as fallback. It must not require an ElevenLabs ID when
the actual channel pipeline uses a free TTS voice.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import random

# Public ElevenLabs premade voices used as multilingual fallbacks. Account-specific
# channel pools can override these IDs without changing code.
DEFAULT_VOICES = [
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male"},
    {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "gender": "male"},
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female"},
]

CHANNELS = {
    "health_usa": {"env": "ELEVENLABS_VOICE_IDS_HEALTH_USA", "single_env": "ELEVENLABS_VOICE_ID_HEALTH_USA", "lang": "en"},
    "health_japan": {"env": "ELEVENLABS_VOICE_IDS_HEALTH_JAPAN", "single_env": "ELEVENLABS_VOICE_ID_HEALTH_JAPAN", "lang": "ja"},
    "shopping": {"env": "ELEVENLABS_VOICE_IDS_SEOUL_JISOO1", "single_env": "ELEVENLABS_VOICE_ID_SEOUL_JISOO1", "lang": "en"},
    "nasa": {"env": "ELEVENLABS_VOICE_IDS_NASA", "single_env": "ELEVENLABS_VOICE_ID_NASA", "lang": "en"},
    "history": {"env": "ELEVENLABS_VOICE_IDS_HISTORY_TODAY", "single_env": "ELEVENLABS_VOICE_ID_HISTORY_TODAY", "lang": "en"},
    "silent_era": {"env": "ELEVENLABS_VOICE_IDS_OLD_HOLLYWOOD", "single_env": "ELEVENLABS_VOICE_ID_OLD_HOLLYWOOD", "lang": "en"},
    "retro_reels": {"env": "ELEVENLABS_VOICE_IDS_RETRO_USA", "single_env": "ELEVENLABS_VOICE_ID_RETRO_USA", "lang": "en"},
    "seoul_journal": {"env": "ELEVENLABS_VOICE_IDS_SEOUL_JOURNAL", "single_env": "SEOUL_JOURNAL_VOICE_ID", "lang": "ko"},
}

def _episode_date() -> dt.date:
    for key in ("EPISODE_DATE", "VIDEO_DATE", "DATE"):
        value = os.getenv(key, "").strip()
        if value:
            try:
                return dt.date.fromisoformat(value[:10])
            except ValueError:
                pass
    return dt.datetime.now(dt.timezone.utc).date()

def choose_voice(channel: str, episode_date: dt.date | None = None) -> dict[str, str]:
    """Return the channel's fixed approved ElevenLabs voice; never rotate silently."""
    key = channel.strip().lower()
    cfg = CHANNELS.get(key, {"env": "", "single_env": "", "lang": "en"})
    date = episode_date or _episode_date()

    # A single channel-specific voice always wins. A configured list is treated as
    # an explicitly ordered approved list; use its first entry to keep assignments stable.
    single = os.getenv(cfg.get("single_env", ""), "").strip() if cfg.get("single_env") else ""
    pool = [v.strip() for v in os.getenv(cfg.get("env", ""), "").split(",") if v.strip()] if cfg.get("env") else []
    voice_id = single or (pool[0] if pool else "")

    fallback = {
        # The production Japan pipeline uses ja-JP-NanamiNeural through free Edge TTS;
        # this stable female profile prevents an unrelated ElevenLabs-ID gate from aborting it.
        "health_japan": {"id": "ja-JP-NanamiNeural", "name": "Nanami (Microsoft Edge TTS)", "gender": "female"},
        "seoul_journal": {"id": "ko-KR-SunHiNeural", "name": "SunHi (Microsoft Edge TTS)", "gender": "female"},
        "health_usa": {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male"},
        "shopping": {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female"},
        "nasa": {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male"},
        "history": {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female"},
        "silent_era": {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male"},
        "retro_reels": {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female"},
    }
    known = {v["id"]: v for v in DEFAULT_VOICES}
    if not voice_id:
        # Use a channel-specific, language-matched free voice profile when no account voice is configured.
        voice = fallback.get(key)
        if not voice:
            raise RuntimeError(f"No fixed ElevenLabs voice configured for {key}; refusing to rotate to an unrelated voice.")
    else:
        voice = dict(known.get(voice_id, {"id": voice_id, "name": "Approved account voice", "gender": "unknown"}))

    return {**voice, "channel": key, "language": cfg.get("lang", "en"), "date": date.isoformat()}
