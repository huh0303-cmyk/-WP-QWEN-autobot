"""Durable single-owner queue shared by the VPS control room and worker."""
from __future__ import annotations

import json
import fcntl
import os
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def cost_hold_active() -> bool:
    """Server-owned pause survives code deployments and preserves queued work."""
    return Path(os.environ.get("YOUTUBE_COST_HOLD_FILE", "/etc/korea365/youtube-cost-hold")).exists()


def check_cost_hold() -> None:
    if cost_hold_active():
        raise RuntimeError("비용 점검으로 YouTube 제작을 일시중지했습니다. 추가 과금 방지 설정 해제 후 재개할 수 있습니다.")


def queue_root() -> Path:
    return Path(os.environ.get("YOUTUBE_VPS_QUEUE_DIR", ROOT / "data" / "youtube_vps_queue"))


def enqueue(channel_key: str, label: str, state_group: str, run_now: bool = True) -> dict:
    check_cost_hold()
    root = queue_root()
    pending, running = root / "pending", root / "running"
    pending.mkdir(parents=True, exist_ok=True)
    running.mkdir(parents=True, exist_ok=True)
    with (root / "enqueue.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for path in (*pending.glob("*.json"), *running.glob("*.json")):
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if existing.get("channel_key") == channel_key:
                raise RuntimeError(f"{channel_key or 'scheduled job'} is already queued or running on the VPS")
        job_id = f"vps-{int(time.time())}-{uuid.uuid4().hex[:10]}"
        job = {"job_id": job_id, "channel_key": channel_key, "label": label,
               "state_group": state_group, "run_now": bool(run_now), "queued_at": time.time()}
        tmp = pending / f".{job_id}.tmp"
        target = pending / f"{job_id}.json"
        tmp.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, target)
    return job


def pending_count() -> int:
    return len(list((queue_root() / "pending").glob("*.json")))
