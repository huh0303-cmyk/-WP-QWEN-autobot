#!/usr/bin/env python3
"""Bridge the 14-day content calendar to the actual write queue.

roll_14day_content_calendar.py plans WHAT/WHEN in 14일_콘텐츠운영캘린더, but
nothing reads that plan - auto_write_and_draft.py only ever picks up rows
already sitting in 자동화_황금키워드. This script closes that gap: once a
day, it looks at tomorrow's WordPress calendar rows and, for any that
aren't already queued, appends them to 자동화_황금키워드 as a normal 대기
row - so by the time tomorrow's scheduled slot arrives, the keyword is
already waiting for whatever dispatches the write.

WordPress only, deliberately: the calendar's Blogger rows are written
"동일 키워드 WP 발행 후" (same keyword, after WP publishes), a sequential
dependency the calendar's own design assumes. The live Blogger pipeline
(original_writer.py via a blogger_ site_id) writes fresh from a keyword
directly and was deliberately built with its own separate keyword queue
per platform, precisely so WordPress and Blogspot never write the same
keyword. Auto-promoting Blogger rows here would silently reintroduce the
same-keyword coupling that design intentionally avoided - so Blogger
calendar rows are left for a human/other-session decision, not promoted
here.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.sheet_schema import KEYWORD_HEADER
from automation_hub.time_utils import iso_kst
from gsheets_direct import ensure_tab, get_sheets_service

CALENDAR_TAB = "14일_콘텐츠운영캘린더"
KEYWORDS_TAB = "자동화_황금키워드"
KST = dt.timezone(dt.timedelta(hours=9))


def _records(values: list[list[str]], header: list[str]) -> list[dict[str, str]]:
    if not values:
        return []
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def _domain_to_site_key() -> dict[str, str]:
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    mapping = {}
    for profile in profiles:
        domain = profile["wordpress"]["url"].removeprefix("https://").removeprefix("http://").rstrip("/")
        mapping[domain] = profile["site_key"]
    return mapping


def main() -> int:
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id:
        raise SystemExit("SHEET_ID is required")
    service = get_sheets_service()
    # Deliberately does NOT call ensure_tab() on the calendar tab: that helper
    # wipes and rewrites a tab whose header doesn't match exactly, and this
    # script only ever reads the calendar - it must never be the thing that
    # clears roll_14day_content_calendar.py's data on a header mismatch.
    ensure_tab(service, sheet_id, KEYWORDS_TAB, KEYWORD_HEADER)

    calendar_values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{CALENDAR_TAB}'!A1:O"
    ).execute().get("values", [])
    calendar_header = calendar_values[0] if calendar_values else []
    calendar_rows = _records(calendar_values, calendar_header)

    keyword_values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!A1:K"
    ).execute().get("values", [])
    existing = {(r.get("site_id"), r.get("keyword")) for r in _records(keyword_values, KEYWORD_HEADER)}

    domain_to_key = _domain_to_site_key()
    tomorrow = (dt.datetime.now(KST) + dt.timedelta(days=1)).date()

    new_rows = []
    skipped_no_mapping = []
    for row in calendar_rows:
        if row.get("platform") != "WordPress":
            continue
        planned_at = row.get("planned_at_kst", "")
        if not planned_at[:10]:
            continue
        try:
            planned_date = dt.date.fromisoformat(planned_at[:10])
        except ValueError:
            continue
        if planned_date != tomorrow:
            continue
        domain = row.get("channel_site", "").strip()
        site_key = domain_to_key.get(domain)
        if not site_key:
            skipped_no_mapping.append(domain)
            continue
        site_id = f"wp_{site_key}"
        keyword = row.get("golden_keyword_candidate", "").strip()
        if not keyword or (site_id, keyword) in existing:
            continue
        intent = row.get("planned_title_direction", "") or row.get("notes", "")
        new_rows.append([iso_kst(), site_id, keyword, intent, "", "", "", "", "", "대기", ""])
        existing.add((site_id, keyword))

    if skipped_no_mapping:
        print(f"no site_key mapping for domains: {sorted(set(skipped_no_mapping))}")
    if not new_rows:
        print(f"nothing new to promote for {tomorrow}")
        return 0

    service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()
    print(f"promoted {len(new_rows)} calendar rows for {tomorrow} into {KEYWORDS_TAB}")
    for row in new_rows:
        print(f"  {row[1]} | {row[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
