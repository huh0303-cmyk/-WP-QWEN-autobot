"""Calendar-only YouTube dispatch selection. No public publication capability."""
from __future__ import annotations

import datetime as dt
from .youtube_registry import load_channels

KST = dt.timezone(dt.timedelta(hours=9))
TAB = "14일_콘텐츠운영캘린더"
READY = "기획확정·자료준비"
ALIASES = {
    "Healing": "healing", "Cafe Music": "starbucks", "MBB": "mbb",
    "K-pop": "kpop", "플리-로맨틱글로벌": "globalmusic",
}


def channel_key(name):
    aliases = dict(ALIASES)
    for c in load_channels():
        aliases.update({c.display_name: c.channel_key, c.channel_key: c.channel_key,
                        c.channel_id: c.channel_key})
    return aliases.get(name.strip())


def parse_calendar(values):
    expected = {0: "schedule_id", 1: "planned_at_kst", 2: "platform",
                3: "channel_site", 7: "planned_title_direction", 12: "current_status",
                13: "review_or_output_url", 14: "notes"}
    if not values or any(len(values[0]) <= i or values[0][i] != v for i, v in expected.items()):
        raise ValueError("Calendar header mismatch")
    result, ids = [], set()
    channels = {c.channel_key: c for c in load_channels()}
    for index, raw in enumerate(values[1:], 2):
        row = [str(v or "") for v in raw] + [""] * max(0, 15 - len(raw))
        if not row[2].startswith("YouTube"):
            continue
        key = channel_key(row[3])
        if not key or not row[0] or row[0] in ids:
            raise ValueError(f"Unknown/duplicate calendar identity at row {index}")
        ids.add(row[0])
        expected_platform = "YouTube Playlist" if channels[key].channel_type == "playlist" else "YouTube Knowledge"
        if row[2] != expected_platform:
            raise ValueError(f"Channel/platform mismatch at row {index}")
        when = dt.datetime.strptime(row[1], "%Y-%m-%d %H:%M KST").replace(tzinfo=KST)
        result.append({"row": index, "id": row[0], "when": when, "key": key,
                       "topic": row[7].strip(), "language": row[5], "status": row[12],
                       "url": row[13], "notes": row[14], "cells": row})
    return result


def select_due(rows, now, enabled, limit=3):
    """Original CAL series wins over accidentally duplicated ROLL series.

    Keep past records, never retry claimed/failed work, and never catch up yesterday's
    dated history automatically. Resolve legacy display names to one channel key.
    """
    original_end = {}
    for r in rows:
        if r["id"].startswith("CAL-"):
            original_end[r["key"]] = max(original_end.get(r["key"], dt.date.min), r["when"].date())
    blocked = {r["key"] for r in rows if r["status"] in {"자료수집", "대본작성", "검수중"}}
    # A claimed/completed row must win even if a duplicate has an earlier clock time.
    occupied = {(r["key"], r["when"].date()) for r in rows
                if r["status"] != READY or r["url"] or "[yt-calendar:" in r["notes"]}
    selected, skipped, seen = [], [], set()
    for r in sorted(rows, key=lambda r: (not r["id"].startswith("CAL-"), r["when"], r["id"])):
        slot = (r["key"], r["when"].date())
        if r["id"].startswith("ROLL-") and r["when"].date() <= original_end.get(r["key"], dt.date.min):
            skipped.append((r["id"], "original-calendar-series-exists"))
            continue
        if slot in seen:
            skipped.append((r["id"], "duplicate-channel-day"))
            continue
        seen.add(slot)
        if (r["status"] != READY or r["url"] or not r["topic"] or slot in occupied
                or r["key"] in blocked or r["key"] not in enabled):
            continue
        if r["when"].date() == now.astimezone(KST).date() and r["when"] <= now:
            selected.append(r)
    return sorted(selected, key=lambda r: (r["when"], r["id"]))[:limit], skipped


def read_calendar(service, spreadsheet_id):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="sheets.properties").execute()
    count = next(s["properties"]["gridProperties"]["rowCount"] for s in meta["sheets"]
                 if s["properties"]["title"] == TAB)
    values = []
    for start in range(1, count + 1, 1000):
        end = min(start + 999, count)
        chunk = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id,
                  range=f"'{TAB}'!A{start}:O{end}").execute().get("values", [])
        values.extend(chunk + [[]] * (end - start + 1 - len(chunk)))
    return parse_calendar(values)


def update_row(service, spreadsheet_id, row, status, url, notes):
    service.spreadsheets().values().update(spreadsheetId=spreadsheet_id,
        range=f"'{TAB}'!M{row['row']}:O{row['row']}", valueInputOption="RAW",
        body={"values": [[status, url, notes]]}).execute()
