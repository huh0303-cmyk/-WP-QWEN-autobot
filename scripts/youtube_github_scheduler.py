#!/usr/bin/env python3
"""GitHub Actions scheduler for one due YouTube calendar row per run."""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from automation_hub.youtube_calendar import KST, read_calendar, select_due
from automation_hub.youtube_registry import load_channels
from automation_hub.youtube_github_runtime import check_cost_hold, enqueue
from gsheets_direct import get_sheets_service
from youtube_github_worker import process_one


def has_due_calendar_row() -> bool:
    """Read calendar and channel enablement without claiming or changing a row."""
    spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
    if not spreadsheet_id:
        raise RuntimeError("SHEET_ID is required for the GitHub YouTube scheduler")

    service = get_sheets_service()
    channels = {channel.channel_key: channel for channel in load_channels() if channel.enabled}
    settings = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="'자동화_유튜브채널'!A1:R20",
    ).execute().get("values", [])
    expected_header = [
        "channel_key", "channel_type", "display_name", "channel_id",
        "secret_profile", "workflow", "enabled",
    ]
    if not settings or settings[0][:7] != expected_header:
        raise RuntimeError("YouTube settings header mismatch")
    sheet_enabled = {
        row[0] for row in settings[1:]
        if len(row) >= 7 and row[6] in {"ON", "TRUE", "1"}
    }
    enabled = set(channels) & sheet_enabled
    selected, _ = select_due(
        read_calendar(service, spreadsheet_id),
        dt.datetime.now(KST),
        enabled,
        1,
    )
    return bool(selected)


def main() -> int:
    check_cost_hold()
    if not has_due_calendar_row():
        print("No due YouTube calendar row; no job enqueued.")
        return 0

    enqueue("", "Scheduled YouTube calendar item", "youtube_scheduler", run_now=False)
    if not process_one():
        raise RuntimeError("GitHub scheduler did not process the due calendar row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
