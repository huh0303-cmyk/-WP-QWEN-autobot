#!/usr/bin/env python3
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

from automation_hub.status_schema import SHEET_HEADER
from gsheets_direct import replace_tab_rows

TAB_NAME = "자동화_종합상황실"
DEFAULT_STATUS_PATH = ROOT / "artifacts" / "automation-room-status.json"


def _sheet_row(row: dict) -> list:
    values = []
    for key in SHEET_HEADER:
        value = row.get(key, "")
        if key == "details" and isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        values.append(value)
    return values


def main() -> int:
    spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
    if not spreadsheet_id:
        raise SystemExit("SHEET_ID is required")

    status_path = Path(os.environ.get("ROOM_STATUS_PATH", str(DEFAULT_STATUS_PATH)))
    if not status_path.exists():
        raise SystemExit(f"room status snapshot not found: {status_path}")

    payload = json.loads(status_path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    if not isinstance(rows, list):
        raise SystemExit("invalid room status payload: rows must be a list")

    replace_tab_rows(
        spreadsheet_id,
        TAB_NAME,
        SHEET_HEADER,
        [_sheet_row(row) for row in rows],
    )
    summary = payload.get("summary") or {}
    print(json.dumps({"tab": TAB_NAME, "rows": len(rows), "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
