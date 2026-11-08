#!/usr/bin/env python3
"""GitHub Actions scheduler for one due YouTube calendar row per run."""
from __future__ import annotations

import argparse
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


def find_due_channel(channel_filter: str = "") -> str:
    """Return the exact enabled channel key for the next due calendar row."""
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
    from seed_knowledge_calendar import seed
    seed(service, spreadsheet_id, enabled)
    if channel_filter:
        if channel_filter not in channels:
            raise ValueError(f"Unknown YouTube channel key: {channel_filter}")
        enabled &= {channel_filter}
    selected, _ = select_due(
        read_calendar(service, spreadsheet_id),
        dt.datetime.now(KST),
        enabled,
        1,
    )
    return selected[0]["key"] if selected else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="", help="Optionally restrict dispatch to one locked channel key")
    args = parser.parse_args()

    channel_key = find_due_channel(args.channel)
    if not channel_key:
        print(f"No due YouTube calendar row for {args.channel or 'enabled channels'}; no job enqueued.")
        return 0

    # Check the actual selected channel, not an empty scheduler placeholder.
    # This is required for narrowly scoped free-only exceptions during cost hold.
    check_cost_hold(channel_key)
    enqueue(channel_key, "Scheduled YouTube calendar item", f"youtube_{channel_key}", run_now=False)
    if not process_one():
        raise RuntimeError("GitHub scheduler did not process the due calendar row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
