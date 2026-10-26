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


def check_cost_hold() -> None:
    if cost_hold_active():
        raise RuntimeError(
            "YouTube publishing is held: set the GitHub Actions variable "
            "YOUTUBE_COST_HOLD=false only after the owner has approved cost review."
        )


def queue_root() -> Path:
    """Ephemeral per-run queue; durable scheduling state lives in the calendar sheet."""
    return Path(os.environ.get("YOUTUBE_GITHUB_QUEUE_DIR", ROOT / "data" / "youtube_github_queue"))


def enqueue(channel_key: str, label: str, state_group: str, run_now: bool = True) -> dict:
    check_cost_hold()
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
