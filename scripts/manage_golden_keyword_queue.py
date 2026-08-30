#!/usr/bin/env python3
"""Add or update rows in the 자동화_황금키워드 (golden keyword) tab.

Gives the account owner a live view of what topic is planned next for
each site, instead of that plan living only inside a Gemini chat. Used
as the visibility step before a Gemini Gem session starts, and updated
as that keyword moves through the manual write/review pipeline.
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

from automation_hub.sheet_schema import KEYWORD_HEADER
from automation_hub.time_utils import iso_kst
from gsheets_direct import ensure_tab, get_sheets_service

KEYWORDS_TAB = "자동화_황금키워드"
VALID_STATUSES = {"대기", "작성중", "검수중", "초안완료", "발행완료", "보류"}


def _records(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def add_keyword(service, sheet_id: str, *, site_id: str, keyword: str, intent: str) -> None:
    row = [iso_kst(), site_id, keyword, intent, "", "", "", "", "", "대기", ""]
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
    print(f"added: {site_id} | {keyword} | status=대기")


def update_status(service, sheet_id: str, *, site_id: str, keyword: str, status: str) -> None:
    if status not in VALID_STATUSES:
        raise SystemExit(f"invalid status {status!r}; must be one of {sorted(VALID_STATUSES)}")
    values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!A1:K",
    ).execute().get("values", [])
    records = _records(values)
    match_index = None
    for index, record in enumerate(records):
        if record.get("site_id") == site_id and record.get("keyword") == keyword:
            match_index = index
    if match_index is None:
        raise SystemExit(f"no queued row found for site_id={site_id!r} keyword={keyword!r}")
    sheet_row = match_index + 2  # header row + 1-indexed
    status_col = KEYWORD_HEADER.index("status") + 1
    used_at_col = KEYWORD_HEADER.index("used_at") + 1
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!{_col(status_col)}{sheet_row}",
        valueInputOption="RAW", body={"values": [[status]]},
    ).execute()
    if status in {"초안완료", "발행완료"}:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!{_col(used_at_col)}{sheet_row}",
            valueInputOption="RAW", body={"values": [[iso_kst()]]},
        ).execute()
    print(f"updated: {site_id} | {keyword} | status={status}")


def _col(index_1based: int) -> str:
    letters = ""
    n = index_1based
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def main() -> int:
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    action = os.environ.get("GOLDEN_ACTION", "").strip()
    site_id = os.environ.get("GOLDEN_SITE_ID", "").strip()
    keyword = os.environ.get("GOLDEN_KEYWORD", "").strip()
    if not all((sheet_id, action, site_id, keyword)):
        raise SystemExit("SHEET_ID, GOLDEN_ACTION, GOLDEN_SITE_ID and GOLDEN_KEYWORD are required")
    service = get_sheets_service()
    ensure_tab(service, sheet_id, KEYWORDS_TAB, KEYWORD_HEADER)
    if action == "add":
        intent = os.environ.get("GOLDEN_INTENT", "").strip()
        add_keyword(service, sheet_id, site_id=site_id, keyword=keyword, intent=intent)
    elif action == "update_status":
        status = os.environ.get("GOLDEN_STATUS", "").strip()
        update_status(service, sheet_id, site_id=site_id, keyword=keyword, status=status)
    else:
        raise SystemExit(f"unknown GOLDEN_ACTION {action!r}; must be 'add' or 'update_status'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
