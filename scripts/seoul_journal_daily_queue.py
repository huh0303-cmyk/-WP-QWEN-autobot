#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a source-auditable Seoul Journal daily Shorts editorial queue.

This is intentionally a planning/preflight stage. It never uploads to YouTube.
"""
from __future__ import annotations
import csv, datetime as dt, json, os, re, sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SHEET_CSV_URL = os.getenv(
    "SEOUL_JOURNAL_GOLDEN_CALENDAR_CSV_URL",
    "https://docs.google.com/spreadsheets/d/1lGKkvLxKOi9pufCuzvYpylqnK7apLx8f/export?format=csv&gid=796729184",
)
OUT = Path(os.getenv("SEOUL_JOURNAL_QUEUE_PATH", "artifacts/seoul-journal-daily-queue.json"))
KST = dt.timezone(dt.timedelta(hours=9))
TODAY = dt.datetime.now(KST).date()

def get_csv(url: str) -> str:
    req = Request(url, headers={"User-Agent": "SeoulJournalEditorialBot/1.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8-sig", errors="replace")

def rows_from_csv(raw: str):
    rows = list(csv.reader(raw.splitlines()))
    header_i = next((i for i, row in enumerate(rows) if row and row[0].strip() == "날짜"), None)
    if header_i is None:
        raise ValueError("Could not find a row whose first column is '날짜'.")
    header = [v.strip() for v in rows[header_i]]
    for row in rows[header_i + 1:]:
        if not row or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[0].strip()):
            continue
        yield dict(zip(header, row + [""] * max(0, len(header)-len(row))))

def main():
    calendar_date = TODAY - dt.timedelta(days=4)
    result = {
        "date_kst": TODAY.isoformat(),
        "calendar_target_date": calendar_date.isoformat(),
        "calendar_source": SHEET_CSV_URL,
        "source_note": "Calendar candidates are not proof of current search volume. DataLab/media validation must be attached before scripts are approved.",
        "thumbnail_policy": {
            "scope": "all YouTube channels",
            "style": "bold high-contrast newsroom headline; dark background; yellow/white/red typography; mobile-first; genuine/licensed subjects only",
            "avoid": ["fabricated likenesses", "unverified allegations stated as fact", "copying competitor creative verbatim"]
        },
        "voice_policy": {"provider": "ElevenLabs only", "tempo_target": 1.2, "delivery": "energetic, higher-pitched, tense newsroom; never sleepy", "fallback_tts": False},
        "competitor_gate": {"minimum_videos": 5, "minimum_views": 200000, "required_analysis": ["title_hook", "first_2_seconds", "pacing", "caption_density", "thumbnail_structure", "comment_cta"], "copying_allowed": False},
        "golden_keyword_items": [],
        "reactive_items": [
            {"slot": "morning", "status": "needs_live_evidence", "required_daily_politics": ["이재명", "한동훈"]},
            {"slot": "afternoon", "status": "needs_live_evidence", "required_daily_politics": ["이재명", "한동훈"]}
        ],
        "daily_target_count": 7,
        "upload_policy": "PRIVATE only; upload stage must verify exact Seoul Journal channel OAuth before any write",
        "upload_performed": False
    }
    try:
        raw = get_csv(SHEET_CSV_URL)
        calendar_rows = list(rows_from_csv(raw))
        match = next((r for r in calendar_rows if r.get("날짜", "").strip() == calendar_date.isoformat()), None)
        rule_override = False
        if match is None:
            # Owner-approved policy (2026-10-22): when the target date is absent,
            # use the closest dated row containing at least one keyword, and expose
            # the selected date so editors can validate freshness before approval.
            usable_rows = []
            for row in calendar_rows:
                row_date_text = row.get("날짜", "").strip()
                if not re.fullmatch(r"\\d{4}-\\d{2}-\\d{2}", row_date_text):
                    continue
                keywords = [row.get(f"키워드 {i}", "").strip() for i in range(1, 6)]
                if not any(keywords):
                    continue
                try:
                    row_date = dt.date.fromisoformat(row_date_text)
                except ValueError:
                    continue
                usable_rows.append((abs((row_date - calendar_date).days), row_date, row, keywords))
            if usable_rows:
                usable_rows.sort(key=lambda item: (item[0], item[1] > calendar_date, item[1]))
                _, selected_date, match, selected_keywords = usable_rows[0]
                rule_override = True
                result["calendar_rule_override"] = {
                    "approved_on": "2026-10-22",
                    "reason": "Owner approved use of a valid keyword row from another date when the target date is missing.",
                    "target_date": calendar_date.isoformat(),
                    "selected_calendar_date": selected_date.isoformat(),
                    "date_distance_days": abs((selected_date - calendar_date).days),
                    "freshness_validation_required": True
                }
        if match:
            selected_date_text = match.get("날짜", "").strip()
            candidates = [match.get(f"키워드 {i}", "").strip() for i in range(1, 6)]
            result["golden_keyword_items"] = [
                {"slot": f"golden_{i}", "keyword": kw, "calendar_date": selected_date_text,
                 "target_calendar_date": calendar_date.isoformat(),
                 "status": "awaiting_datalab_and_media_validation",
                 "calendar_rule_override": rule_override}
                for i, kw in enumerate(candidates, 1) if kw
            ]
            result["calendar_match"] = selected_date_text == calendar_date.isoformat()
            result["calendar_row_selected"] = selected_date_text
        else:
            result["calendar_match"] = False
            result["golden_keyword_blocker"] = (
                f"No usable dated row with keywords found; target was {calendar_date.isoformat()}."
            )
    except Exception as exc:
        result["calendar_match"] = False
        result["calendar_error"] = f"{type(exc).__name__}: {exc}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # Missing calendar row is a visible warning, not a reason to lose the reactive slots.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
