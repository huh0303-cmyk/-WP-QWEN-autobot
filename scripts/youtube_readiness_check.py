#!/usr/bin/env python3
"""Preflight YouTube OAuth, channel identity, and optional Sheet readiness."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.youtube_readiness import check_channel, validate_sheet_registry
from automation_hub.youtube_registry import load_channels
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import YOUTUBE_CHANNEL_TAB


def main() -> int:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--channel")
    target.add_argument("--all", action="store_true")
    parser.add_argument("--config-only", action="store_true", help="Validate registry only; do not require credentials")
    parser.add_argument("--sheet", action="store_true", help="Also validate the central Google Sheet registry")
    args = parser.parse_args()

    channels = load_channels()
    if len(channels) != 10 or sum(c.channel_type == "playlist" for c in channels) != 5 or sum(c.channel_type == "knowledge" for c in channels) != 5:
        raise SystemExit("canonical YouTube registry must contain exactly five playlist and five knowledge channels")
    selected = channels if args.all else [c for c in channels if c.channel_key == args.channel]
    if not selected:
        raise SystemExit(f"unknown channel: {args.channel}")

    reports = []
    for channel in selected:
        if args.config_only:
            errors = channel.validate()
            reports.append({
                "channel_key": channel.channel_key,
                "ready": not errors,
                "config_ready": not errors,
                "credentials_ready": None,
                "upload_scope_ready": None,
                "oauth_ready": None,
                "expected_channel_id": channel.channel_id,
                "verified_channel_id": "",
                "errors": errors,
            })
        else:
            reports.append(check_channel(channel, allow_runtime_alias=not args.all).as_dict())

    sheet_errors: list[str] = []
    if args.sheet:
        spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
        if not spreadsheet_id:
            sheet_errors.append("SHEET_ID is required for --sheet")
        else:
            service = get_sheets_service()
            values = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=f"'{YOUTUBE_CHANNEL_TAB}'!A1:R20",
            ).execute().get("values", [])
            sheet_errors.extend(validate_sheet_registry(values, channels))

    payload = {
        "ready": all(report["ready"] for report in reports) and not sheet_errors,
        "checked": len(reports),
        "expected_total": 10,
        "public_allowed": False,
        "channels": reports,
        "sheet_errors": sheet_errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
