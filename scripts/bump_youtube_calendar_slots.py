"""One-off: move the earliest READY calendar row for each requested YouTube
channel into the current 30-minute dispatch slot, so the existing central
scheduler (youtube_calendar_dispatch.py) can legitimately claim it on its
next run. Only column B (planned_at_kst) is touched; nothing else about the
row (topic, format, id) changes.
"""
import datetime as dt
import json
import os

from automation_hub.youtube_calendar import KST, READY, TAB, read_calendar
from automation_hub.youtube_registry import load_channels
from gsheets_direct import get_sheets_service


def main():
    sid = os.environ["SHEET_ID"]
    service = get_sheets_service()
    channels = {c.channel_key: c for c in load_channels()}
    requested = [k.strip() for k in os.environ.get("CHANNEL_KEYS", "").split(",") if k.strip()] or list(channels)
    unknown = [k for k in requested if k not in channels]
    if unknown:
        raise RuntimeError(f"Unknown channel keys: {unknown}")
    rows = read_calendar(service, sid)
    now = dt.datetime.now(KST)
    bumped, missing = [], []
    for key in requested:
        candidates = [r for r in rows if r["key"] == key and r["status"] == READY and not r["url"] and r["topic"]]
        if not candidates:
            missing.append(key)
            continue
        row = min(candidates, key=lambda r: r["when"])
        new_when = now.strftime("%Y-%m-%d %H:%M KST")
        service.spreadsheets().values().update(
            spreadsheetId=sid, range=f"'{TAB}'!B{row['row']}",
            valueInputOption="RAW", body={"values": [[new_when]]},
        ).execute()
        bumped.append({"channel": key, "schedule_id": row["id"], "new_when": new_when, "topic": row["topic"]})
    print(json.dumps({"bumped": bumped, "missing_ready_row": missing}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
