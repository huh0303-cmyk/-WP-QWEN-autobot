"""GitHub Actions-only runtime state for the London Project YouTube worker."""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cost_hold_active() -> bool:
    """Fail closed unless an owner explicitly sets YOUTUBE_COST_HOLD=false."""
    value = os.environ.get("YOUTUBE_COST_HOLD", "").strip().lower()
    return value not in {"false", "0", "no", "off"}


def free_only_channel_allowed(channel_key: str) -> bool:
    """Permit only isolated no-paid-API playlist paths while the global cost hold remains active."""
    channel = channel_key.strip().lower()
    if channel not in {"globalmusic", "mbb", "healing"}:
        return False
    if os.environ.get("PLAYLIST_FREE_ONLY_CHANNEL", "").strip().lower() != channel:
        return False
    if os.environ.get("PLAYLIST_PAID_API_ENABLED", "false").strip().lower() not in {"false", "0", "no", "off"}:
        return False

    if channel == "healing":
        paid_keys = ("GEMINI_API_KEY", "OPENAI_API_KEY", "LYRIA_API_KEY",
                     "FISH_AUDIO_API_KEY", "PIXABAY_KEY", "PEXELS_API_KEY")
        if any(os.environ.get(key, "").strip() for key in paid_keys):
            return False
        if os.environ.get("PLAYLIST_MUSIC_SOURCE", "") != "free_natural_ambience":
            return False
        if os.environ.get("PLAYLIST_IMAGE_SOURCE", "") != "pexels_direct_free":
            return False
        if os.environ.get("AUTO_TOPIC", "").strip().lower() != "false":
            return False
        if os.environ.get("HEALING_VARIANT", "") != "sequential":
            return False
        required_free = (
            "SHEET_ID", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
            "GOOGLE_OAUTH_REFRESH_TOKEN", "YOUTUBE_OAUTH_CLIENT_ID_HEALING",
            "YOUTUBE_OAUTH_CLIENT_SECRET_HEALING", "YOUTUBE_OAUTH_REFRESH_TOKEN_HEALING",
        )
        return all(os.environ.get(key, "").strip() for key in required_free)

    if any(os.environ.get(key, "").strip() for key in ("GEMINI_API_KEY", "OPENAI_API_KEY", "LYRIA_API_KEY")):
        return False
    if channel == "globalmusic":
        if os.environ.get("PLAYLIST_MUSIC_SOURCE", "") != "owner_drive":
            return False
        if os.environ.get("PLAYLIST_IMAGE_SOURCE", "") != "pexels_api":
            return False
        if os.environ.get("AUTO_TOPIC", "").strip().lower() != "false":
            return False
        if not os.environ.get("CAPTION_TEXT", "").strip():
            return False
        required_free = (
            "GOOGLE_OAUTH_REFRESH_TOKEN", "MUSIC_SOURCE_FOLDER_ID_GLOBALMUSIC",
            "THUMBNAIL_FOLDER_ID_GLOBALMUSIC", "PEXELS_API_KEY",
            "YOUTUBE_OAUTH_REFRESH_TOKEN_GLOBALMUSIC",
        )
    else:
        # Mozart: fetch verified public-domain classical recordings directly; no MBB music Drive folder.
        if os.environ.get("PLAYLIST_MUSIC_SOURCE", "") != "owner_local":
            return False
        if os.environ.get("PLAYLIST_IMAGE_SOURCE", "") != "pexels_api":
            return False
        if os.environ.get("AUTO_TOPIC", "").strip().lower() != "false":
            return False
        required_free = (
            "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_OAUTH_REFRESH_TOKEN",
            "THUMBNAIL_FOLDER_ID_MBB", "PEXELS_API_KEY",
            "YOUTUBE_OAUTH_CLIENT_ID_MBB", "YOUTUBE_OAUTH_CLIENT_SECRET_MBB",
            "YOUTUBE_OAUTH_REFRESH_TOKEN_MBB",
        )
    return all(os.environ.get(key, "").strip() for key in required_free)

def check_cost_hold(channel_key: str = "") -> None:
    if cost_hold_active():
        if free_only_channel_allowed(channel_key):
            print(f"COST_HOLD_FREE_ONLY_EXCEPTION channel={channel_key} paid_apis=disabled", flush=True)
            return
        raise RuntimeError(
            "YouTube publishing is held: set YOUTUBE_COST_HOLD=false only after owner-approved cost review, "
            "or use the strictly validated Globalmusic free-only pipeline."
        )


def queue_root() -> Path:
    """Ephemeral per-run queue; durable scheduling state lives in the calendar sheet."""
    return Path(os.environ.get("YOUTUBE_GITHUB_QUEUE_DIR", ROOT / "data" / "youtube_github_queue"))


def enqueue(channel_key: str, label: str, state_group: str, run_now: bool = True) -> dict:
    check_cost_hold(channel_key)
    root = queue_root()
    pending, running = root / "pending", root / "running"
    pending.mkdir(parents=True, exist_ok=True)
    running.mkdir(parents=True, exist_ok=True)
    for path in (*pending.glob("*.json"), *running.glob("*.json")):
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if existing.get("channel_key") == channel_key:
            raise RuntimeError(f"{channel_key or 'scheduled job'} is already queued or running in this run")
    run_id = os.environ.get("GITHUB_RUN_ID", str(int(time.time())))
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    job_id = f"gh-{run_id}-{attempt}-{uuid.uuid4().hex[:8]}"
    job = {
        "job_id": job_id,
        "channel_key": channel_key,
        "label": label,
        "state_group": state_group,
        "run_now": bool(run_now),
        "queued_at": time.time(),
        "runner": "github-actions",
    }
    target = pending / f"{job_id}.json"
    target.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    return job


def pending_count() -> int:
    return len(list((queue_root() / "pending").glob("*.json")))
