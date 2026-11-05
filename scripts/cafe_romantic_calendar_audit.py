#!/usr/bin/env python3
"""Read-only audit of CAFE_ROMANTIC's Google Sheets publication calendar."""
from __future__ import annotations

import datetime as dt
import os
import sys

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from gsheets_direct import get_sheets_service
from automation_hub.youtube_calendar import KST, read_calendar, select_next_ready

def main() -> int:
    sid = os.environ["SHEET_ID"]
    service = get_sheets_service()
    settings = service.spreadsheets().values().get(
        spreadsheetId=sid, range="'자동화_유튜브채널'!A1:R20"
    ).execute().get("values", [])
    if not settings:
        raise RuntimeError("YouTube control sheet is empty")
    print("SETTINGS_HEADER", settings[0])
    for row in settings[1:]:
        if row and row[0] == "globalmusic":
            print("GLOBALMUSIC_CONTROL_ROW", row)
    rows = read_calendar(service, sid)
    now = dt.datetime.now(KST)
    print("NOW_KST", now.isoformat())
    print("CALENDAR_ROWS_TOTAL", len(rows))
    global_rows = sorted([r for r in rows if r["key"] == "globalmusic"],
                         key=lambda r: (r["when"], r["id"]))
    print("GLOBALMUSIC_ROWS", len(global_rows))
    for row in global_rows[-30:]:
        cells = row["cells"]
        print(
            "ROW",
            f"sheet_row={row['row']}",
            f"id={row['id']}",
            f"planned={row['when'].strftime('%Y-%m-%d %H:%M KST')}",
            f"platform={cells[2]}",
            f"channel={cells[3]}",
            f"language={row['language']}",
            f"title={row['topic']!r}",
            f"status={row['status']!r}",
            f"url={row['url']!r}",
            f"notes={row['notes']!r}",
        )
    ready, _ = select_next_ready(rows, now, {"globalmusic"}, 20)
    print("NEXT_READY_COUNT", len(ready))
    for row in ready:
        print("NEXT_READY", row["id"], row["when"].isoformat(), row["topic"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
