#!/usr/bin/env python3
"""Owner-authorized first CAFE HEALING upload when the calendar has no READY row."""
from __future__ import annotations

import datetime as dt
import json
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from automation_hub.youtube_github_runtime import check_cost_hold
from automation_hub.youtube_calendar import KST
from gsheets_direct import get_sheets_service

EXPECTED_CHANNEL_ID = "UC7yEsLM-HoXudngrD-4FIqg"
CALENDAR_TAB = "14일_콘텐츠운영캘린더"
SETTINGS_TAB = "자동화_유튜브채널"


def main() -> int:
    check_cost_hold("healing")

    for key in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"):
        value = os.environ.get(f"YOUTUBE_OAUTH_{key}_HEALING", "").strip()
        if not value:
            raise RuntimeError(f"Missing channel-scoped YouTube OAuth setting: YOUTUBE_OAUTH_{key}_HEALING")
        os.environ[f"YOUTUBE_OAUTH_{key}"] = value

    spreadsheet_id = os.environ["SHEET_ID"]
    service = get_sheets_service()
    settings = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{SETTINGS_TAB}'!A1:R20"
    ).execute().get("values", [])
    expected = [
        "channel_key", "channel_type", "display_name", "channel_id",
        "secret_profile", "workflow", "enabled",
    ]
    if not settings or settings[0][:7] != expected:
        raise RuntimeError("YouTube channel settings header mismatch")
    matches = [row for row in settings[1:] if row and row[0] == "healing"]
    if len(matches) != 1 or len(matches[0]) < 7:
        raise RuntimeError("Exactly one complete CAFE HEALING settings row is required")
    if matches[0][3] != EXPECTED_CHANNEL_ID:
        raise RuntimeError("Control Sheet healing channel ID does not match the locked channel ID")
    if matches[0][6] not in {"ON", "TRUE", "1"}:
        raise RuntimeError("CAFE HEALING is not ON in the control Sheet; refusing direct upload")

    run_id = os.environ.get("HEALING_START_RUN_ID", os.environ.get("GITHUB_RUN_ID", "manual"))
    os.environ["SCHEDULE_ID"] = f"HEALING-START-{run_id}"
    os.environ["HEALING_VARIANT"] = "sequential"
    os.environ["ROOM_RESULT_SOURCE"] = "artifacts/youtube_playlist_result.json"

    # healing_motion -> healing_rain_review verifies mine=true channel ID, public privacy,
    # upload processing status, duration, and the stable marker before returning.
    runpy.run_path(str(ROOT / "scripts" / "healing_motion.py"), run_name="__main__")

    receipt_path = ROOT / "artifacts/youtube_playlist_result.json"
    if not receipt_path.is_file():
        raise RuntimeError("No verified YouTube upload receipt was produced")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("verified_channel_id") != EXPECTED_CHANNEL_ID
            or receipt.get("privacy_status") != "public"
            or receipt.get("public_allowed") is not True
            or not receipt.get("video_id")
            or not receipt.get("public_url")):
        raise RuntimeError("The first healing upload receipt failed identity/publication verification")

    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{CALENDAR_TAB}'!A1:O2000"
    ).execute().get("values", [])
    if not values or len(values[0]) < 15 or values[0][0] != "schedule_id":
        raise RuntimeError("Healing calendar header mismatch after upload; receipt remains saved as artifact")
    schedule_id = f"HEALING-START-{run_id}"
    if not any(row and row[0] == schedule_id for row in values[1:]):
        title_direction = f"CAFE HEALING first release — {receipt.get('variant', 'nature ambience')}"
        notes = (
            "Owner-requested immediate first release; YouTube processing and public status verified; "
            f"channel_id={EXPECTED_CHANNEL_ID}; video_id={receipt['video_id']}"
        )
        audit_row = [
            schedule_id,
            dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
            "YouTube Playlist", "Healing", "", "", "", title_direction,
            "", "", "", "", "발행완료", receipt["public_url"], notes,
        ]
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"'{CALENDAR_TAB}'!A:O",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [audit_row]},
        ).execute()

    print("HEALING_FIRST_PUBLIC_UPLOAD_VERIFIED", receipt["video_id"], receipt["public_url"], receipt.get("variant"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
