#!/usr/bin/env python3
"""Create the Google Sheets control tabs and seed the destination registry.

By default existing user-edited rows are preserved. Set FORCE_SEED=true only when
the registry must intentionally replace the Settings tab.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from automation_hub.registry import SiteRegistry
from automation_hub.sheet_schema import KEYWORD_HEADER, RSS_HEADER, RUN_LOG_HEADER, SITE_SETTINGS_HEADER
from gsheets_direct import ensure_tab, get_sheets_service


SETTINGS_TAB = "자동화_사이트설정"
RUNS_TAB = "자동화_실행현황"
KEYWORDS_TAB = "자동화_황금키워드"
RSS_TAB = "자동화_RSS"


def _ensure_log_tab(service, spreadsheet_id: str, tab_name: str, header: list[str]) -> None:
    ensure_tab(service, spreadsheet_id, tab_name, header)


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
        range=f"'{SETTINGS_TAB}'!A2:AC",
    ).execute().get("values", [])
    force_seed = os.environ.get("FORCE_SEED", "false").strip().lower() == "true"
    if force_seed or not current:
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{SETTINGS_TAB}'!A2:AC",
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
    print(f"Control tabs ready: {SETTINGS_TAB}, {RUNS_TAB}, {KEYWORDS_TAB}, {RSS_TAB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
