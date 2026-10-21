"""Language-aware multi-voice rotation for ElevenLabs narration.

A voice is chosen once per video/episode, not per scene, so the narration stays
consistent inside an episode while different uploads alternate male/female voices.
Set ELEVENLABS_VOICE_IDS_<CHANNEL> to a comma-separated list of 3-4 voice IDs to
override the public multilingual defaults for a channel.
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
    """Choose a date-stable, gender-alternating voice for one channel's episode."""
    key = channel.strip().lower()
    cfg = CHANNELS.get(key, {"env": "", "single_env": "", "lang": "en"})
    date = episode_date or _episode_date()
    configured = [v.strip() for v in os.getenv(cfg["env"], "").split(",") if v.strip()]
    if not configured and cfg.get("single_env"):
        one = os.getenv(cfg["single_env"], "").strip()
        if one:
            # Keep the account's existing voice in the pool while adding multilingual
            # fallbacks so the channel still varies if only one ID was configured.
            configured = [one] + [v["id"] for v in DEFAULT_VOICES if v["id"] != one]
    if configured:
        # Resolve known names when possible; custom IDs are retained as custom voices.
        known = {v["id"]: v for v in DEFAULT_VOICES}
        pool = [dict(known.get(vid, {"id": vid, "name": "Account voice", "gender": "unknown"})) for vid in configured]
    else:
        pool = [dict(v) for v in DEFAULT_VOICES]

    # Rotate male/female on alternating episode dates, with channel offsets to avoid
    # every channel using the same gender on the same day. If the pool is custom and
    # gender metadata is unknown, rotate through the full pool instead.
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    offset = digest[0] % 2
    target_gender = "male" if (date.toordinal() + offset) % 2 == 0 else "female"
    matching = [v for v in pool if v.get("gender") == target_gender]
    candidates = matching or pool
    # Date/channel-seeded choice is repeatable on reruns, yet rotates across episodes.
    seed = int.from_bytes(hashlib.sha256(f"{key}:{date.isoformat()}".encode()).digest()[:8], "big")
    selected = random.Random(seed).choice(candidates)
    return {**selected, "channel": key, "language": cfg.get("lang", "en"), "date": date.isoformat()}
