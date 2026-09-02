#!/usr/bin/env python3
"""Append DRAFT_READY Tistory artifacts to the single Google Sheet queue."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.sheet_schema import PUBLISH_QUEUE_HEADER
from gsheets_direct import append_tab_rows
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
            "source_keyword": "", "category": draft["category"],
            "search_description": draft["meta_description"], "visibility": "private",
        }
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
    append_tab_rows(sheet_id, QUEUE_TAB, PUBLISH_QUEUE_HEADER, rows)
    print(json.dumps({"queued": len(rows), "visibility": "private"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
