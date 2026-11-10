"""Six approved documentary/news voices per language; no legacy paid TTS IDs."""
from __future__ import annotations
import json
import os
import random
from pathlib import Path

HISTORY = Path(os.getenv("TTS_VOICE_HISTORY_PATH", "data/tts_voice_history.json"))
LANGUAGES = {"health_usa":"en","health_japan":"ja","shopping":"en","nasa":"en",
             "history":"en","silent_era":"en","retro_reels":"en","seoul_journal":"ko"}

def choose_voice(channel: str, episode_date=None) -> dict[str, str]:
    """Choose an approved voice, excluding the last voice for this channel.

    Configure TTS_APPROVED_VOICES_JSON as a JSON mapping language to exactly
    six audited voice records, three male and three female. Each record must
    have id, name, gender and approved=true. No default or paid-provider IDs.
    """
    key = channel.strip().lower()
    language = LANGUAGES.get(key, os.getenv("CONTENT_LANGUAGE", "en"))
    profiles = json.loads(os.getenv("TTS_APPROVED_VOICES_JSON", "{}"))
    voices = profiles.get(language, [])
    if len(voices) != 6 or sum(v.get("gender") == "male" and v.get("approved") is True for v in voices) != 3 or sum(v.get("gender") == "female" and v.get("approved") is True for v in voices) != 3:
        raise RuntimeError(f"Six approved documentary/news voices required for {language}: 3 male + 3 female")
    if any(not v.get("id") or not v.get("name") or v.get("approved") is not True for v in voices):
        raise RuntimeError("Unapproved or unnamed TTS voice; publication blocked")
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(HISTORY.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        state = {}
    pool = [v for v in voices if v["id"] != state.get(key)]
    voice = random.SystemRandom().choice(pool)
    state[key] = voice["id"]
    tmp = HISTORY.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    tmp.replace(HISTORY)
    return {**voice, "channel":key, "language":language}
