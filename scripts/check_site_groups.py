#!/usr/bin/env python3
"""One-off read-only check: print group/weekly_min/weekly_max per site
from 자동화_사이트설정, to confirm whether a 특A tier actually exists
as distinct sheet data (not just a calendar-row quality tag)."""
import os

from gsheets_direct import get_sheets_service

SHEET_ID = os.environ.get("SHEET_ID", "").strip()
TAB = "자동화_사이트설정"


def main():
    service = get_sheets_service()
    values = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"'{TAB}'!A1:AE"
    ).execute().get("values", [])
    header = values[0]
    idx = {name: header.index(name) for name in ("site_id", "url", "group", "weekly_min", "weekly_max") if name in header}
    print("columns found:", idx)
    groups_seen = {}
    for row in values[1:]:
        row = list(row) + [""] * max(0, len(header) - len(row))
        group = row[idx["group"]] if "group" in idx else ""
        groups_seen.setdefault(group, []).append((
            row[idx["site_id"]] if "site_id" in idx else "",
            row[idx["url"]] if "url" in idx else "",
            row[idx["weekly_min"]] if "weekly_min" in idx else "",
            row[idx["weekly_max"]] if "weekly_max" in idx else "",
        ))
    for group, members in sorted(groups_seen.items()):
        print(f"\n=== group={group!r} ({len(members)} sites) ===")
        for site_id, url, wmin, wmax in members:
            print(f"  {site_id:30s} {url:35s} weekly {wmin}-{wmax}")


if __name__ == "__main__":
    main()
