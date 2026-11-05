#!/usr/bin/env python3
"""Append one verified CAFE_ROMANTIC canary row; idempotent and never edits old rows."""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from gsheets_direct import get_sheets_service
from automation_hub.youtube_calendar import KST, read_calendar, select_next_ready, update_row

SHEET_TAB = "14일_콘텐츠운영캘린더"
SCHEDULE_ID = "CAL-20261107-GLOBALMUSIC-03"
PLANNED_AT = "2026-11-07 20:30 KST"
TOPIC = "A Sunset Table for Two | French and Japanese Romantic Acoustic Love Songs"


def main() -> int:
    spreadsheet_id = os.environ["SHEET_ID"]
    service = get_sheets_service()
    rows = read_calendar(service, spreadsheet_id)

    # Release only the exact claim whose GitHub worker run is confirmed failed.
    stale = next((row for row in rows if row["id"] == "CAL-20261106-GLOBALMUSIC-01"), None)
    stale_worker = "[yt-worker:42054528245]"
    if stale and stale["status"] in {"자료수집", "대본작성", "검수중"} and not stale["url"] and stale_worker in stale["notes"]:
        reason = "GitHub worker 42054528245 failed before YouTube upload; no public video receipt. Claim released for recovery."
        update_row(service, spreadsheet_id, stale, "실패", "", stale["notes"] + "\\n" + reason)
        print("STALE_CAFE_ROMANTIC_CLAIM_RELEASED", stale["id"], "run=42054528245")
        rows = read_calendar(service, spreadsheet_id)

    existing = next((row for row in rows if row["id"] == SCHEDULE_ID), None)
    if existing:
        print(f"CALENDAR_ROW_ALREADY_EXISTS id={SCHEDULE_ID} status={existing['status']!r}")
    else:
        now = dt.datetime.now(KST)
        future_ready, _ = select_next_ready(rows, now, {"globalmusic"}, 20)
        if future_ready:
            raise RuntimeError(
                "A future CAFE_ROMANTIC ready row already exists; refusing to append a duplicate: "
                + ",".join(row["id"] for row in future_ready)
            )
        row = [
            SCHEDULE_ID,
            PLANNED_AT,
            "YouTube Playlist",
            "Cafe_Romantic",
            "Playlist",
            "mixed",
            "Owner-paid Suno vocal tracks",
            TOPIC,
            "Romantic acoustic café playlist",
            "50–70 minutes",
            "Balanced French + Japanese",
            "Pexels couple photo; LOVE SONGS thumbnail",
            "기획확정·자료준비",
            "",
            "Owner-paid Suno Drive manifest; 50–70 min; free Pexels thumbnail; free-only API mode; verify exact channel and public receipt.",
        ]
        response = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{SHEET_TAB}'!A:O",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
        print("CALENDAR_ROW_APPENDED", response.get("updates", {}).get("updatedRange", "range_unknown"))

    refreshed = read_calendar(service, spreadsheet_id)
    selected, _ = select_next_ready(refreshed, dt.datetime.now(KST), {"globalmusic"}, 20)
    selected_ids = [row["id"] for row in selected]
    if SCHEDULE_ID not in selected_ids:
        raise RuntimeError(
            f"New row is not selectable by the worker; selected={selected_ids}"
        )
    print(
        "CAFE_ROMANTIC_CALENDAR_SEED_PASS "
        f"id={SCHEDULE_ID} planned={PLANNED_AT} "
        f"topic={TOPIC!r} selectable=true"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"CAFE_ROMANTIC_CALENDAR_SEED_FAILED: {exc}", file=sys.stderr)
        raise
