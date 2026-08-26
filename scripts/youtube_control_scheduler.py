#!/usr/bin/env python3
"""Dispatch due YouTube channels from the Google Sheets control plane."""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.sheet_schema import YOUTUBE_CHANNEL_HEADER
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import YOUTUBE_CHANNEL_TAB, YOUTUBE_RUN_TAB

KST = dt.timezone(dt.timedelta(hours=9))


def parse_rows(values: list[list[object]]) -> list[dict[str, str]]:
    if not values or values[0] != YOUTUBE_CHANNEL_HEADER:
        raise RuntimeError("YouTube channel sheet header mismatch")
    return [
        dict(zip(values[0], [*(str(value) for value in row), *([""] * (len(values[0]) - len(row)))]))
        for row in values[1:] if row and str(row[0]).strip()
    ]


def next_run(channel: dict[str, str], now: dt.datetime) -> dt.datetime:
    low = int(channel["interval_days_min"])
    high = int(channel["interval_days_max"])
    rng = random.Random(f"{channel['channel_key']}:{now.date().isoformat()}:youtube-control")
    day = now.date() + dt.timedelta(days=rng.randint(low, high))
    hour = rng.randint(int(channel["allowed_hour_start"]), int(channel["allowed_hour_end"]))
    minute = rng.choice([7, 17, 27, 37, 47, 57])
    return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=KST)


def is_due(channel: dict[str, str], now: dt.datetime) -> bool:
    if channel.get("enabled", "ON").upper() not in {"ON", "TRUE", "1", "YES"}:
        return False
    raw = channel.get("next_run_at", "").strip()
    if not raw:
        return True
    try:
        due = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if due.tzinfo is None:
            due = due.replace(tzinfo=KST)
        return now >= due.astimezone(KST)
    except ValueError:
        raise RuntimeError(f"invalid next_run_at for {channel['channel_key']}: {raw}")


def dispatch(channel: dict[str, str], repo: str, token: str) -> requests.Response:
    inputs = {"channel": channel["channel_key"]}
    if channel["channel_type"] == "playlist":
        inputs.update({"publish_delay_hours": channel["publish_delay_hours"], "topic": "", "language": channel["language"]})
    else:
        inputs.update({"topic": "", "publish_delay_hours": channel["publish_delay_hours"]})
    return requests.post(
        f"https://api.github.com/repos/{repo}/actions/workflows/{channel['workflow']}/dispatches",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        json={"ref": "main", "inputs": inputs}, timeout=20,
    )


def main() -> int:
    spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GH_DISPATCH_TOKEN", "").strip()
    max_dispatch = max(1, int(os.environ.get("MAX_DISPATCH", "1")))
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    if not all((spreadsheet_id, repo, token)):
        raise SystemExit("SHEET_ID, GITHUB_REPOSITORY and GH_DISPATCH_TOKEN are required")

    now = dt.datetime.now(KST)
    service = get_sheets_service()
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{YOUTUBE_CHANNEL_TAB}'!A1:R",
    ).execute().get("values", [])
    channels = parse_rows(values)
    dispatched = 0
    for row_index, channel in enumerate(channels, start=2):
        if not is_due(channel, now):
            continue
        planned = next_run(channel, now)
        if dry_run:
            print(json.dumps({"channel": channel["channel_key"], "due": True, "next": planned.isoformat()}, ensure_ascii=False))
            dispatched += 1
            if dispatched >= max_dispatch:
                break
            continue
        response = dispatch(channel, repo, token)
        ok = response.status_code == 204
        status = "dispatched" if ok else f"dispatch_failed_{response.status_code}"
        if ok:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"'{YOUTUBE_CHANNEL_TAB}'!P{row_index}:R{row_index}", valueInputOption="RAW",
                body={"values": [[planned.isoformat(), now.isoformat(), status]]},
            ).execute()
        log_row = [
            now.isoformat(), channel["channel_key"], channel["channel_type"], channel["workflow"], status,
            f"https://github.com/{repo}/actions/workflows/{channel['workflow']}", "", "", "" if ok else response.text[:500],
        ]
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=f"'{YOUTUBE_RUN_TAB}'!A:I", valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": [log_row]},
        ).execute()
        print(json.dumps({"channel": channel["channel_key"], "status": status, "next_run_at": planned.isoformat()}, ensure_ascii=False))
        if not ok:
            return 1
        dispatched += 1
        if dispatched >= max_dispatch:
            break
    print(f"Dispatched {dispatched} YouTube channel(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

