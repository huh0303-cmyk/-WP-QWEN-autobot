#!/usr/bin/env python3
"""The last piece connecting the calendar to real output.

roll_14day_content_calendar.py plans, promote_calendar_to_golden_keywords.py
queues - but until now nothing ever called sheet-triggered-auto-write.yml,
so a queued keyword just sat at 대기 forever unless someone dispatched it
by hand (exactly what this session spent today doing manually).

Runs hourly. Finds every site_id with at least one 대기 row in
자동화_황금키워드, and - at most one per run, at least 30 minutes apart,
in a daily-shuffled order so sites don't fire in a predictable sequence -
dispatches sheet-triggered-auto-write.yml for it. Mirrors
publish_scheduler.py's proven state-file/min-gap/one-per-run pattern.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.sheet_schema import KEYWORD_HEADER
from gsheets_direct import get_sheets_service

KEYWORDS_TAB = "자동화_황금키워드"
STATE_FILE = "write_dispatch_state.json"
KST = dt.timezone(dt.timedelta(hours=9))
MIN_GAP_MINUTES = 30


def _records(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def load_state(today: str) -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
            if state.get("date") == today:
                return state
        except Exception:
            pass
    return {"date": today, "fired": {}, "last_dispatch_at": None}


def main() -> int:
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    token = os.environ.get("GH_DISPATCH_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not all((sheet_id, token, repo)):
        raise SystemExit("SHEET_ID, GH_DISPATCH_TOKEN and GITHUB_REPOSITORY are required")

    now = dt.datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    state = load_state(today)
    fired = state.get("fired", {})

    last_raw = state.get("last_dispatch_at")
    elapsed_minutes = MIN_GAP_MINUTES
    if last_raw:
        try:
            last = dt.datetime.fromisoformat(last_raw)
            if last.tzinfo is None:
                last = last.replace(tzinfo=KST)
            elapsed_minutes = (now - last.astimezone(KST)).total_seconds() / 60
        except Exception:
            elapsed_minutes = MIN_GAP_MINUTES

    def save():
        state["fired"] = fired
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    if elapsed_minutes < MIN_GAP_MINUTES:
        print(f"마지막 디스패치 후 {elapsed_minutes:.1f}분 - 최소 {MIN_GAP_MINUTES}분 간격 대기")
        save()
        return 0

    service = get_sheets_service()
    values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!A1:K"
    ).execute().get("values", [])
    records = _records(values)
    due_site_ids = sorted({r.get("site_id") for r in records if r.get("status") == "대기" and r.get("site_id")})
    due_site_ids = [s for s in due_site_ids if not fired.get(s)]

    if not due_site_ids:
        print("대기 중인 사이트 없음 (전부 오늘 이미 발사됐거나 큐가 비어있음)")
        save()
        return 0

    random.Random(f"{today}-write-dispatch-v1").shuffle(due_site_ids)

    for site_id in due_site_ids:
        try:
            r = requests.post(
                f"https://api.github.com/repos/{repo}/actions/workflows/sheet-triggered-auto-write.yml/dispatches",
                headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
                json={"ref": "main", "inputs": {"site_id": site_id}},
                timeout=20,
            )
            print(f"{site_id} 글쓰기 트리거 -> HTTP {r.status_code}")
            if r.status_code in (200, 201, 204):
                fired[site_id] = True
                state["last_dispatch_at"] = now.isoformat()
                save()
                return 0
            print(f"  실패 (HTTP {r.status_code}) - 다음 실행에서 재시도: {r.text[:300]}")
        except Exception as exc:
            print(f"  예외: {exc} - 다음 실행에서 재시도")

    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
