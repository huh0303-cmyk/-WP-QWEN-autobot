#!/usr/bin/env python3
"""Run all YouTube generation/render/upload jobs on the VPS, one at a time."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from automation_hub.youtube_calendar import KST, read_calendar, select_due, select_next_ready, update_row
from automation_hub.youtube_registry import load_channels
from automation_hub.youtube_vps_queue import enqueue, queue_root
from gsheets_direct import get_sheets_service


def _run(command: list[str], env: dict[str, str], log_handle) -> None:
    subprocess.run(command, cwd=ROOT, env=env, stdout=log_handle, stderr=subprocess.STDOUT, check=True)


def _state_path(group: str) -> Path:
    return ROOT / "data" / f"bulk_publish_state_{group}.json"


def _update_dashboard(job: dict, status: str, conclusion=None, reason="") -> None:
    path = _state_path(job["state_group"])
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {"status": "polling", "started_at": None, "finished_at": None, "items": []}
    for item in state.get("items", []):
        if item.get("job_id") == job["job_id"]:
            item.update(status=status, conclusion=conclusion, reason=reason)
            break
    items = state.get("items", [])
    if items and all(item.get("status") == "done" for item in items):
        state.update(status="done", finished_at=dt.datetime.now(dt.timezone.utc).isoformat())
    else:
        state["status"] = "polling"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _claim(job: dict) -> tuple[object, str]:
    sid = os.environ["SHEET_ID"]
    service = get_sheets_service()
    channels = {channel.channel_key: channel for channel in load_channels() if channel.enabled}
    settings = service.spreadsheets().values().get(
        spreadsheetId=sid, range="'자동화_유튜브채널'!A1:R20"
    ).execute().get("values", [])
    if not settings or settings[0][:7] != ["channel_key", "channel_type", "display_name", "channel_id", "secret_profile", "workflow", "enabled"]:
        raise RuntimeError("YouTube settings header mismatch")
    sheet_enabled = {row[0] for row in settings[1:] if len(row) >= 7 and row[6] in {"ON", "TRUE", "1"}}
    requested = job.get("channel_key", "")
    enabled = ({requested} if requested else set(channels)) & sheet_enabled
    if requested and requested not in enabled:
        raise RuntimeError(f"YouTube channel is disabled in the control Sheet: {requested}")
    rows = read_calendar(service, sid)
    selector = select_next_ready if job.get("run_now") and requested else select_due
    selected, _ = selector(rows, dt.datetime.now(KST), enabled, 1)
    if not selected:
        raise RuntimeError(f"No eligible calendar row for {requested or 'current due channels'}")
    row = selected[0]
    token = uuid.uuid4().hex
    marker = f"[yt-calendar:{row['id']}:{token}]"
    note = "운영자 VPS 즉시 제작 요청" if job.get("run_now") else "VPS 예약 비공개 제작 요청"
    update_row(service, sid, row, "자료수집", "", row["notes"] + f"\n{marker} {note}; 업로드 상태 PRIVATE")
    return row, token


def _playlist(env: dict[str, str], log_handle) -> str:
    output = ROOT / "playlist_output"
    if output.exists():
        shutil.rmtree(output)
    env.update(AUTO_TOPIC="false", TOPIC_KEYWORD=env["TOPIC"], LANGUAGE_KEYWORD=env.get("LANGUAGE", ""),
               PLAYLIST_VIDEO_GENERATION_ENABLED="true", ROOM_RESULT_SOURCE="artifacts/youtube_playlist_result.json")
    _run([sys.executable, "scripts/youtube_playlist_maker.py"], env, log_handle)
    meta = json.loads((output / "upload_meta.json").read_text(encoding="utf-8"))
    thumbnails = list(output.glob("thumbnail.*"))
    env.update(VIDEO_DRIVE_ID=meta["video_drive_id"], THUMB_DRIVE_ID=meta.get("thumb_drive_id", ""),
               YT_TITLE=meta["title"], YT_DESCRIPTION=meta["description"], YT_TAGS=",".join(meta.get("tags") or []),
               LOCAL_VIDEO_PATH=str(output / "final.mp4"), LOCAL_THUMB_PATH=str(thumbnails[0]) if thumbnails else "")
    upper = env["CHANNEL_KEY"].upper()
    for key in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"):
        channel_value = env.get(f"YOUTUBE_OAUTH_{key}_{upper}", "")
        if channel_value:
            env[f"YOUTUBE_OAUTH_{key}"] = channel_value
    _run([sys.executable, "scripts/youtube_calendar_result.py", "upload-start"], env, log_handle)
    _run([sys.executable, "scripts/youtube_publish_approved.py"], env, log_handle)
    return "artifacts/youtube_playlist_result.json"


def _knowledge(env: dict[str, str], log_handle) -> str:
    channel = env["CHANNEL_KEY"]
    output = ROOT / "curio_longform_output" / channel / "en"
    if output.exists():
        shutil.rmtree(output)
    env.update(CH=channel, ROOM_RESULT_SOURCE="artifacts/youtube_curio_result.json")
    command = ([sys.executable, "scripts/nasa_archive_longform.py"] if channel == "nasa" else
               [sys.executable, "scripts/archive_footage_longform.py", env["TOPIC"], "en", "", channel])
    _run(command, env, log_handle)
    _run([sys.executable, "scripts/youtube_calendar_result.py", "upload-start"], env, log_handle)
    _run([sys.executable, "scripts/curio_upload.py", channel, "en"], env, log_handle)
    return "artifacts/youtube_curio_result.json"


def run_job(job: dict) -> None:
    _update_dashboard(job, "running")
    log_dir = queue_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    result_path = ""
    claimed = False
    try:
        row, token = _claim(job)
        channel = next(c for c in load_channels() if c.channel_key == row["key"])
        env.update(CHANNEL_KEY=row["key"], TOPIC=row["topic"], LANGUAGE=row.get("language", ""),
                   TOPIC_KEYWORD=row["topic"], LANGUAGE_KEYWORD=row.get("language", ""), SCHEDULE_ID=row["id"],
                   CLAIM_TOKEN=token, VPS_JOB_ID=job["job_id"], WORKER_WORKFLOW="youtube-vps-worker",
                   GITHUB_RUN_ATTEMPT="1")
        result_path = "artifacts/youtube_playlist_result.json" if channel.channel_type == "playlist" else "artifacts/youtube_curio_result.json"
        target = ROOT / result_path
        target.unlink(missing_ok=True)
        with (log_dir / f"{job['job_id']}.log").open("a", encoding="utf-8") as log_handle:
            _run([sys.executable, "scripts/youtube_calendar_result.py", "start"], env, log_handle)
            claimed = True
            result_path = _playlist(env, log_handle) if channel.channel_type == "playlist" else _knowledge(env, log_handle)
            _run([sys.executable, "scripts/youtube_calendar_result.py", "finish", "--result", result_path], env, log_handle)
        _update_dashboard(job, "done", "success", "")
    except Exception as exc:
        if claimed:
            try:
                with (log_dir / f"{job['job_id']}.log").open("a", encoding="utf-8") as log_handle:
                    _run([sys.executable, "scripts/youtube_calendar_result.py", "finish", "--result", result_path], env, log_handle)
            except Exception:
                pass
        _update_dashboard(job, "done", "failure", str(exc)[:500])
        raise


def process_one() -> bool:
    root = queue_root()
    for name in ("pending", "running", "completed", "failed", "logs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    lock_path = root / "worker.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        pending = sorted((root / "pending").glob("*.json"))
        if not pending:
            return False
        source = pending[0]
        running = root / "running" / source.name
        os.replace(source, running)
        job = json.loads(running.read_text(encoding="utf-8"))
        try:
            run_job(job)
        except Exception:
            os.replace(running, root / "failed" / running.name)
        else:
            os.replace(running, root / "completed" / running.name)
        return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--enqueue-due", action="store_true")
    parser.add_argument("--enqueue-channel", choices=[channel.channel_key for channel in load_channels()])
    args = parser.parse_args()
    if args.enqueue_due:
        try:
            enqueue("", "예약 YouTube 작업", "youtube_scheduler", run_now=False)
        except RuntimeError:
            pass
        return 0
    if args.enqueue_channel:
        channel = next(item for item in load_channels() if item.channel_key == args.enqueue_channel)
        enqueue(channel.channel_key, channel.official_name or channel.display_name,
                f"youtube_{channel.channel_key}", run_now=True)
        return 0
    while True:
        worked = process_one()
        if not args.daemon:
            return 0
        if not worked:
            time.sleep(3)


if __name__ == "__main__":
    raise SystemExit(main())
