#!/usr/bin/env python3
"""Record human-completed YouTube publications; never mutate video status."""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.youtube_calendar import KST, read_calendar, update_row
from automation_hub.youtube_identity import verify_authenticated_channel
from automation_hub.youtube_readiness import build_youtube_service
from automation_hub.youtube_registry import load_channels
from gsheets_direct import get_sheets_service


VIDEO_RE = re.compile(r"https://studio\.youtube\.com/video/([A-Za-z0-9_-]{11})/edit(?:[?#].*)?$")


def review_video_id(url: str) -> str:
    match = VIDEO_RE.fullmatch((url or "").strip())
    return match.group(1) if match else ""


def is_public(service, video_id: str, expected_channel_id: str) -> bool:
    response = service.videos().list(part="snippet,status", id=video_id, maxResults=1).execute()
    items = response.get("items", [])
    return (
        len(items) == 1
        and items[0].get("snippet", {}).get("channelId") == expected_channel_id
        and items[0].get("status", {}).get("privacyStatus") == "public"
    )


def append_run_log(service, spreadsheet_id, *, now, channel, status, url="", error=""):
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id, range="'자동화_유튜브실행'!A:I",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [[
            now.isoformat(), channel.channel_key, channel.channel_type, "youtube-public-status-sync.yml",
            status, "", "", url, error[:500],
        ]]},
    ).execute()


def try_append_run_log(service, spreadsheet_id, **kwargs) -> bool:
    try:
        append_run_log(service, spreadsheet_id, **kwargs)
        return True
    except Exception as exc:
        print(f"Run-log append failed for {kwargs['channel'].channel_key}: {type(exc).__name__}")
        return False


def main() -> int:
    spreadsheet_id = os.environ["SHEET_ID"]
    service = get_sheets_service()
    rows = [
        row for row in read_calendar(service, spreadsheet_id)
        if row["status"] == "비공개 업로드" and review_video_id(row["url"])
    ]
    channels = {channel.channel_key: channel for channel in load_channels()}
    youtube_services = {}
    auth_failures = {}
    completed = failures = 0
    for row in rows:
        channel = channels[row["key"]]
        video_id = review_video_id(row["url"])
        now = dt.datetime.now(KST)
        try:
            if channel.channel_key in auth_failures:
                raise RuntimeError(auth_failures[channel.channel_key])
            if channel.channel_key not in youtube_services:
                youtube = build_youtube_service(channel, allow_runtime_alias=False)
                verify_authenticated_channel(youtube, channel.channel_key)
                youtube_services[channel.channel_key] = youtube
            public = is_public(youtube_services[channel.channel_key], video_id, channel.channel_id)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            auth_failures.setdefault(channel.channel_key, error)
            try_append_run_log(service, spreadsheet_id, now=now, channel=channel,
                               status="status_sync_failed", url=row["url"], error=error)
            failures += 1
            continue
        if not public:
            continue
        notes = row["notes"] + f"\n[yt-public-confirmed:{now.isoformat()}] Studio 수동 공개 상태 확인"
        try:
            update_row(service, spreadsheet_id, row, "공개완료", row["url"], notes)
        except Exception as exc:
            error = f"{type(exc).__name__}: calendar public-completion write failed"
            try_append_run_log(service, spreadsheet_id, now=now, channel=channel,
                               status="status_sync_failed", url=row["url"], error=error)
            failures += 1
            continue
        if not try_append_run_log(service, spreadsheet_id, now=now, channel=channel,
                                  status="public_confirmed", url=row["url"]):
            failures += 1
        completed += 1
    print(f"Confirmed {completed} human-published YouTube video(s); failures={failures}; mutation requests=0")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
