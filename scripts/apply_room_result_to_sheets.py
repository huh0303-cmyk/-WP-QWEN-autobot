#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from gsheets_direct import ensure_tab, get_sheets_service

TAB_NAME = "자동화_종합상황실"


def _details(existing: str, result: dict) -> str:
    base = {}
    if existing:
        try:
            base = json.loads(existing)
        except Exception:
            base = {"previous_details": existing}
    base["last_worker_result"] = {
        "run_attempt": result.get("run_attempt", ""),
        "source_path": result.get("source_path", ""),
        "public_allowed": False,
    }
    return json.dumps(base, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
    if not spreadsheet_id:
        raise SystemExit("SHEET_ID is required")

    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    room_id = str(result.get("room_id") or "").strip()
    if not room_id:
        print("ROOM_RESULT_SKIPPED=no_room_id")
        return 0

    service = get_sheets_service()
    ensure_tab(service, spreadsheet_id, TAB_NAME, SHEET_HEADER)
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{TAB_NAME}'!A1:Q",
    ).execute().get("values", [])
    if not values:
        raise SystemExit("situation room tab is empty")

    header = values[0]
    try:
        room_idx = header.index("room_id")
    except ValueError as exc:
        raise SystemExit("room_id column missing") from exc

    target_row_num = None
    current = []
    for row_num, row in enumerate(values[1:], start=2):
        if len(row) > room_idx and row[room_idx] == room_id:
            target_row_num = row_num
            current = row
            break
    if target_row_num is None:
        raise SystemExit(f"room not found in situation room: {room_id}")

    padded = current + [""] * (len(SHEET_HEADER) - len(current))
    row_map = dict(zip(SHEET_HEADER, padded))
    row_map.update({
        "timestamp": result.get("timestamp", row_map.get("timestamp", "")),
        "room_id": room_id,
        "platform": result.get("platform", row_map.get("platform", "")),
        "workflow": result.get("workflow", row_map.get("workflow", "")),
        "run_id": result.get("run_id", ""),
        "completed_at": result.get("timestamp", ""),
        "status": result.get("status", "FAILED"),
        "artifact_id": result.get("artifact_id", ""),
        "artifact_url": result.get("artifact_url", ""),
        "failure_reason": result.get("failure_reason", ""),
        "details": _details(row_map.get("details", ""), result),
    })
    row = [row_map.get(key, "") for key in SHEET_HEADER]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{TAB_NAME}'!A{target_row_num}",
        valueInputOption="RAW",
        body={"values": [row]},
    ).execute()
    print(json.dumps({"room_id": room_id, "status": row_map["status"], "artifact_id": row_map["artifact_id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
