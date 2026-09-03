#!/usr/bin/env python3
"""Append DRAFT_READY Tistory artifacts to the single Google Sheet queue."""
from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import quote
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.sheet_schema import PUBLISH_QUEUE_HEADER
from gsheets_direct import ensure_tab, get_sheets_service
from sync_automation_hub_to_sheets import QUEUE_TAB


def rows_from_artifact(payload):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    rows = []
    for draft in payload.get("drafts", []):
        if draft.get("status") != "DRAFT_READY" or draft.get("public_allowed") is not False:
            continue
        values = {
            "created_at": now, "job_id": draft["job_id"], "site_id": draft["site_id"],
            "status": "ready", "publish_now": "FALSE", "title": draft["title"],
            "content_html": draft["body_html"], "labels": draft["category"],
            "source_keyword": draft.get("source_keyword", ""), "category": draft["category"],
            "search_description": draft["meta_description"], "visibility": "private",
        }
        values["public_url"] = f"https://control.korea365.org/review/tistory/{quote(str(draft['job_id']), safe='')}"
        rows.append([values.get(column, "") for column in PUBLISH_QUEUE_HEADER])
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drafts", default="artifacts/tistory-daily-drafts.json")
    args = parser.parse_args()
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id:
        raise SystemExit("SHEET_ID is required")
    payload = json.loads(Path(args.drafts).read_text(encoding="utf-8"))
    rows = rows_from_artifact(payload)
    if len(rows) != len(payload.get("drafts", [])):
        raise RuntimeError("Every requested Tistory draft must be DRAFT_READY and private before queueing")
    service = get_sheets_service()
    ensure_tab(service, sheet_id, QUEUE_TAB, PUBLISH_QUEUE_HEADER)
    existing = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:Q"
    ).execute().get("values", [])
    job_index = PUBLISH_QUEUE_HEADER.index("job_id")
    existing_ids = {row[job_index] for row in existing[1:] if len(row) > job_index and row[job_index]}
    unique_rows = [row for row in rows if row[job_index] not in existing_ids]
    if unique_rows:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": unique_rows},
        ).execute()
    verified = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:Q"
    ).execute().get("values", [])
    target_ids = {row[job_index] for row in rows}
    counts = {job_id: sum(len(row) > job_index and row[job_index] == job_id for row in verified[1:]) for job_id in target_ids}
    if len(rows) != len(target_ids) or any(count != 1 for count in counts.values()):
        raise RuntimeError(f"Tistory queue verification failed: {counts}")
    print(json.dumps({"queued": len(unique_rows), "duplicates_blocked": len(rows) - len(unique_rows), "verified": len(counts), "visibility": "private"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
