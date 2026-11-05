#!/usr/bin/env python3
"""Create missing, randomized CAFE HEALING calendar slots without touching existing rows."""
from __future__ import annotations

import datetime as dt
import hashlib
import random
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation_hub.youtube_calendar import KST, parse_calendar
from automation_hub.youtube_github_runtime import check_cost_hold
from gsheets_direct import get_sheets_service

CALENDAR_TAB = "14일_콘텐츠운영캘린더"
SETTINGS_TAB = "자동화_유튜브채널"
READY = "기획확정·자료준비"
EXPECTED_CHANNEL_ID = "UC7yEsLM-HoXudngrD-4FIqg"


def main() -> int:
    check_cost_hold("healing")
    spreadsheet_id = os.environ["SHEET_ID"]
    service = get_sheets_service()

    settings = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{SETTINGS_TAB}'!A1:R20"
    ).execute().get("values", [])
    expected_settings = [
        "channel_key", "channel_type", "display_name", "channel_id",
        "secret_profile", "workflow", "enabled",
    ]
    if not settings or settings[0][:7] != expected_settings:
        raise RuntimeError("YouTube channel settings header mismatch")
    channel_rows = [row for row in settings[1:] if row and row[0] == "healing"]
    if len(channel_rows) != 1:
        raise RuntimeError("Exactly one locked healing channel row is required")
    channel_row = channel_rows[0]
    if len(channel_row) < 7 or channel_row[3] != EXPECTED_CHANNEL_ID:
        raise RuntimeError("Healing channel ID in control Sheet does not match the locked channel ID")
    if channel_row[6] not in {"ON", "TRUE", "1"}:
        raise RuntimeError("Healing channel is not ON in the control Sheet; no rows were created")

    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{CALENDAR_TAB}'!A1:O2000"
    ).execute().get("values", [])
    rows = parse_calendar(values)
    now = dt.datetime.now(KST)
    existing_ids = {row["id"] for row in rows}
    healing_rows = [row for row in rows if row["key"] == "healing"]
    additions = []

    for window in range(2):
        start = now.date() + dt.timedelta(days=1 + window * 7)
        end = start + dt.timedelta(days=7)
        current = [row for row in healing_rows if start <= row["when"].date() < end]
        occupied_days = {row["when"].date() for row in current}
        target_seed = hashlib.sha256(f"{EXPECTED_CHANNEL_ID}:{start.isoformat()}".encode()).hexdigest()
        rng = random.Random(int(target_seed[:16], 16))
        target_count = rng.randint(2, 3)
        missing = max(0, target_count - len(current))
        if not missing:
            continue

        candidates = [start + dt.timedelta(days=offset) for offset in range(7)
                      if start + dt.timedelta(days=offset) not in occupied_days]
        rng.shuffle(candidates)
        for day in candidates[:missing]:
            hour = rng.choice([8, 10, 12, 14, 16, 18, 20, 22])
            minute = rng.choice([0, 15, 30, 45])
            planned = dt.datetime.combine(day, dt.time(hour, minute), tzinfo=KST)
            schedule_id = f"HEALING-{day:%Y%m%d}-{hour:02d}{minute:02d}"
            if schedule_id in existing_ids:
                continue
            topic = "CAFE HEALING — five-theme natural ambience rotation"
            notes = "Auto-created randomized slot; one main scene; no music or narration; theme advances only after verified release."
            additions.append([
                schedule_id, planned.strftime("%Y-%m-%d %H:%M KST"), "YouTube Playlist",
                "Healing", "", "", "", topic, "", "", "", "", READY, "", notes,
            ])
            existing_ids.add(schedule_id)

    if additions:
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{CALENDAR_TAB}'!A:O",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": additions},
        ).execute()
        print("HEALING_RANDOM_SLOTS_ADDED", len(additions), result.get("updates", {}).get("updatedRange", ""), flush=True)
    else:
        print("HEALING_RANDOM_SLOTS_ALREADY_COVERED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
