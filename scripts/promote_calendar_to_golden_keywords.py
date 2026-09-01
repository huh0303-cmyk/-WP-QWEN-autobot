#!/usr/bin/env python3
"""Keep seven days of WP and Blogger keywords ready in the write queue.

roll_14day_content_calendar.py plans WHAT/WHEN in 14일_콘텐츠운영캘린더, but
nothing reads that plan - auto_write_and_draft.py only ever picks up rows
already sitting in 자동화_황금키워드. This script closes that gap: once a
week, it looks at the next seven calendar days and, for any rows that
aren't already queued, appends them to 자동화_황금키워드 as a normal 대기
row - so by the time tomorrow's scheduled slot arrives, the keyword is
already waiting for whatever dispatches the write.

Both platforms get their own site_id queue. Blogger receives a distinct
reader-Q&A/practical-example angle so it never duplicates the paired
WordPress article even when both calendar rows share a core topic.
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


def _blogspot_to_site_key() -> dict[str, str]:
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    return {
        profile["blogspot"]["url"].removeprefix("https://").removeprefix("http://").rstrip("/"): profile["site_key"]
        for profile in profiles if profile.get("blogspot", {}).get("url")
    }


def _blogger_channel_to_site_key() -> dict[str, str]:
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    return {
        profile["wordpress"]["url"].removeprefix("https://").removeprefix("http://").rstrip("/").rsplit(".", 1)[0]: profile["site_key"]
        for profile in profiles
    }


def _blogger_angle(keyword: str, language: str) -> str:
    suffix = " — 독자 질문과 실전 예시" if language == "ko" else " — reader questions and practical examples"
    return keyword + suffix


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
    blogspot_to_key = _blogspot_to_site_key()
    blogger_channel_to_key = _blogger_channel_to_site_key()
    tomorrow = (dt.datetime.now(KST) + dt.timedelta(days=1)).date()
    horizon = tomorrow + dt.timedelta(days=6)

    new_rows = []
    skipped_no_mapping = []
    for row in calendar_rows:
        platform = row.get("platform")
        if platform not in {"WordPress", "Blogger"}:
            continue
        planned_at = row.get("planned_at_kst", "")
        if not planned_at[:10]:
            continue
        try:
            planned_date = dt.date.fromisoformat(planned_at[:10])
        except ValueError:
            continue
        if not tomorrow <= planned_date <= horizon:
            continue
        if platform == "WordPress":
            identity = row.get("channel_site", "").strip()
            site_key = domain_to_key.get(identity)
            site_id = f"wp_{site_key}" if site_key else ""
        else:
            identity = row.get("destination_url", "").strip().removeprefix("https://").removeprefix("http://").rstrip("/")
            site_key = blogspot_to_key.get(identity) or blogger_channel_to_key.get(row.get("channel_site", "").strip())
            site_id = f"blogger_{site_key}" if site_key else ""
        if not site_key:
            skipped_no_mapping.append(f"{platform}:{identity}")
            continue
        keyword = row.get("golden_keyword_candidate", "").strip()
        if platform == "Blogger" and keyword:
            keyword = _blogger_angle(keyword, row.get("language", ""))
        if not keyword or (site_id, keyword) in existing:
            continue
        intent = row.get("planned_title_direction", "") or row.get("notes", "")
        new_rows.append([iso_kst(), site_id, keyword, intent, "", "", "", "", "", "대기", ""])
        existing.add((site_id, keyword))

    if skipped_no_mapping:
        print(f"no site_key mapping for domains: {sorted(set(skipped_no_mapping))}")
    if not new_rows:
        print(f"nothing new to promote for {tomorrow} through {horizon}")
        return 0

    service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": new_rows},
    ).execute()
    print(f"promoted {len(new_rows)} WP+Blogger rows for {tomorrow} through {horizon} into {KEYWORDS_TAB}")
    for row in new_rows:
        print(f"  {row[1]} | {row[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
