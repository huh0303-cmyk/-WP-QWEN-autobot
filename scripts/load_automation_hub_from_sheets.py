#!/usr/bin/env python3
"""Load and validate the runtime site registry from the Google Sheets dashboard."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.registry import SiteRegistry
from automation_hub.sheet_schema import SITE_SETTINGS_HEADER
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import SETTINGS_TAB


def load_runtime_registry() -> SiteRegistry:
    spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
    if not spreadsheet_id:
        raise RuntimeError("SHEET_ID is required")
    service = get_sheets_service()
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{SETTINGS_TAB}'!A1:AE",
    ).execute().get("values", [])
    if not values:
        raise RuntimeError(f"{SETTINGS_TAB} is empty")
    if values[0] != SITE_SETTINGS_HEADER:
        raise RuntimeError("Google Sheets site-settings header does not match this code version")
    registry = SiteRegistry.from_sheet_rows(values[0], values[1:])
    problems = registry.validate()
    if problems:
        raise RuntimeError(f"invalid Google Sheets registry: {json.dumps(problems, ensure_ascii=False)}")
    return registry


def main() -> int:
    registry = load_runtime_registry()
    print(json.dumps(registry.summary(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
