#!/usr/bin/env python3
"""Create the Google Sheets control tabs and seed the destination registry.

By default existing user-edited rows are preserved. Set FORCE_SEED=true only when
the registry must intentionally replace the Settings tab.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from automation_hub.registry import SiteRegistry
from automation_hub.sheet_schema import (
    KEYWORD_HEADER, PLATFORM_ACCOUNT_HEADER, PUBLISH_QUEUE_HEADER, RSS_HEADER,
    RUN_LOG_HEADER, SITE_SETTINGS_HEADER, YOUTUBE_CHANNEL_HEADER, YOUTUBE_RUN_HEADER,
)
from automation_hub.youtube_registry import load_channels
from gsheets_direct import ensure_tab, get_sheets_service


SETTINGS_TAB = "자동화_사이트설정"
RUNS_TAB = "자동화_실행현황"
KEYWORDS_TAB = "자동화_황금키워드"
RSS_TAB = "자동화_RSS"
ACCOUNTS_TAB = "자동화_플랫폼계정"
QUEUE_TAB = "자동화_발행대기"
YOUTUBE_CHANNEL_TAB = "자동화_유튜브채널"
YOUTUBE_RUN_TAB = "자동화_유튜브실행"


def _ensure_log_tab(service, spreadsheet_id: str, tab_name: str, header: list[str]) -> None:
    ensure_tab(service, spreadsheet_id, tab_name, header)


def _ensure_queue_tab_without_data_loss(service, spreadsheet_id: str) -> None:
    """Append new queue columns without clearing live/pending commands."""
    existing = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!A1:Z1",
    ).execute().get("values", [[]])
    current = existing[0] if existing else []
    if not current:
        ensure_tab(service, spreadsheet_id, QUEUE_TAB, PUBLISH_QUEUE_HEADER)
        return
    missing = [column for column in PUBLISH_QUEUE_HEADER if column not in current]
    if not missing:
        return
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{QUEUE_TAB}'!{chr(65 + len(current))}1",
        valueInputOption="RAW", body={"values": [missing]},
    ).execute()


def _seed_tistory_accounts(service, spreadsheet_id: str) -> int:
    """Add the canonical five Tistory accounts; never overwrite user rows."""
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I",
    ).execute().get("values", [])
    header = values[0] if values else PLATFORM_ACCOUNT_HEADER
    site_index = header.index("site_id")
    existing_site_ids = {row[site_index] for row in values[1:] if len(row) > site_index}
    portfolio = json.loads((ROOT / "config" / "tistory_portfolio.json").read_text(encoding="utf-8"))
    rows = []
    for site in portfolio["sites"]:
        if not site.get("launch_enabled") or site["site_id"] in existing_site_ids:
            continue
        blog_name = site["url"].split("//", 1)[-1].split(".", 1)[0]
        item = {
            "account_id": f"tistory:{blog_name}", "platform": "tistory",
            "site_id": site["site_id"], "display_name": site["title"],
            "destination_id": blog_name, "editor_url": site["url"],
            "auth_profile": "tistory-local-persistent", "enabled": "ON",
            "notes": "private-only local registrar",
        }
        rows.append([item.get(column, "") for column in PLATFORM_ACCOUNT_HEADER])
    if rows:
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=f"'{ACCOUNTS_TAB}'!A1",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": rows},
        ).execute()
    return len(rows)


def main() -> int:
    spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
    if not spreadsheet_id:
        raise SystemExit("SHEET_ID is required")

    registry = SiteRegistry.load()
    problems = registry.validate()
    if problems:
        raise SystemExit(f"invalid registry: {problems}")

    service = get_sheets_service()
    ensure_tab(service, spreadsheet_id, SETTINGS_TAB, SITE_SETTINGS_HEADER)
    current = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{SETTINGS_TAB}'!A2:AE",
    ).execute().get("values", [])
    force_seed = os.environ.get("FORCE_SEED", "false").strip().lower() == "true"
    if force_seed or not current:
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{SETTINGS_TAB}'!A2:AE",
        ).execute()
        rows = [site.to_sheet_row() for site in registry.sites]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{SETTINGS_TAB}'!A2",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()
        print(f"Seeded {len(rows)} destinations into {SETTINGS_TAB}")
    else:
        print(f"Preserved {len(current)} existing destination rows in {SETTINGS_TAB}")

    _ensure_log_tab(service, spreadsheet_id, RUNS_TAB, RUN_LOG_HEADER)
    _ensure_log_tab(service, spreadsheet_id, KEYWORDS_TAB, KEYWORD_HEADER)
    _ensure_log_tab(service, spreadsheet_id, RSS_TAB, RSS_HEADER)
    _ensure_log_tab(service, spreadsheet_id, ACCOUNTS_TAB, PLATFORM_ACCOUNT_HEADER)
    tistory_added = _seed_tistory_accounts(service, spreadsheet_id)
    _ensure_queue_tab_without_data_loss(service, spreadsheet_id)
    _ensure_log_tab(service, spreadsheet_id, YOUTUBE_CHANNEL_TAB, YOUTUBE_CHANNEL_HEADER)
    _ensure_log_tab(service, spreadsheet_id, YOUTUBE_RUN_TAB, YOUTUBE_RUN_HEADER)
    youtube_rows = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{YOUTUBE_CHANNEL_TAB}'!A2:R",
    ).execute().get("values", [])
    if not youtube_rows:
        rows = [channel.to_row() for channel in load_channels()]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=f"'{YOUTUBE_CHANNEL_TAB}'!A2",
            valueInputOption="RAW", body={"values": rows},
        ).execute()
        print(f"Seeded {len(rows)} YouTube channels")
    print(f"Control tabs ready: {SETTINGS_TAB}, {RUNS_TAB}, {KEYWORDS_TAB}, {RSS_TAB}, {ACCOUNTS_TAB}, {QUEUE_TAB}, {YOUTUBE_CHANNEL_TAB}, {YOUTUBE_RUN_TAB}; Tistory accounts added={tistory_added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
