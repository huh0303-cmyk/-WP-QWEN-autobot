#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dispatch due WordPress calendar rows through the existing A/B draft pipeline.

The 14-day calendar is the source of WHAT/WHEN.  The automation hub registry remains
source of truth for WHICH sites are active and for A/B weekly cadence.  Every dispatch
keeps publication_approved=false, so this scheduler can only create review drafts.
Only destinations with a non-empty runtime WordPress credential are eligible.
The workflow polls every 15 minutes; this script enforces the per-dispatch spacing.
"""
from __future__ import annotations

import datetime
import json
import os
import random
from typing import Any

import requests

from gsheets_direct import get_sheets_service
from load_automation_hub_from_sheets import load_runtime_registry

KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)
today = now.strftime("%Y-%m-%d")
SHEET_ID = os.getenv("SHEET_ID", "12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI")
CALENDAR_TAB = "14일_콘텐츠운영캘린더"
STATE_FILE = "scheduler_state.json"

_registry = load_runtime_registry()
ALL_BLOG_CONFIG = {
    site.url.rstrip("/"): site
    for site in _registry.enabled("wordpress")
    if site.content_type == "blog" and site.publish_mode == "automatic"
}
# Do not spend generation calls on destinations that cannot accept a draft.  The
# credential itself is never logged; only non-empty presence is used.
BLOG_CONFIG = {
    url: site for url, site in ALL_BLOG_CONFIG.items()
    if site.secret_name and os.getenv(site.secret_name, "").strip()
}
SITES = sorted(BLOG_CONFIG)


def weekly_publish_days(site_url: str) -> list[int]:
    """Return 0=Mon..6=Sun for the site's deterministic current-week A/B plan."""
    iso = now.date().isocalendar()
    rng = random.Random(f"{iso.year}-W{iso.week}-{site_url}-weekly-cadence-v1")
    config = BLOG_CONFIG[site_url]
    count = rng.randint(config.weekly_min, config.weekly_max)
    weekend_day = rng.choice([5, 6])
    remaining = [day for day in range(7) if day != weekend_day]
    return sorted([weekend_day] + rng.sample(remaining, count - 1))


TODAY_SITES = {site for site in SITES if now.weekday() in weekly_publish_days(site)}

GH_TOKEN = os.environ["GH_DISPATCH_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]


def load_state() -> dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
            if state.get("date") == today:
                return state
        except Exception:
            pass
    return {"date": today, "fired": {}, "last_dispatch_at": None}


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def _parse_planned_at(value: str) -> datetime.datetime | None:
    raw = value.strip().removesuffix(" KST")
    try:
        return datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    except ValueError:
        return None


def load_due_calendar_rows(service) -> list[dict[str, Any]]:
    rows = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range=f"'{CALENDAR_TAB}'!A1:O2000"
    ).execute().get("values", [])
    if not rows:
        raise RuntimeError("14-day content calendar is empty")

    header = rows[0]
    required = {
        "schedule_id", "planned_at_kst", "platform", "destination_url",
        "golden_keyword_candidate", "current_status", "review_or_output_url", "notes",
    }
    missing = required.difference(header)
    if missing:
        raise RuntimeError(f"calendar header missing: {sorted(missing)}")
    index = {name: header.index(name) for name in required}

    due: list[dict[str, Any]] = []
    for sheet_row, raw in enumerate(rows[1:], start=2):
        row = list(raw) + [""] * max(0, len(header) - len(raw))
        planned = _parse_planned_at(str(row[index["planned_at_kst"]]))
        destination = _normalize_url(str(row[index["destination_url"]]))
        status = str(row[index["current_status"]]).strip()
        if (
            str(row[index["platform"]]).strip() == "WordPress"
            and planned is not None
            and planned.date() == now.date()
            and planned <= now
            and destination in TODAY_SITES
            and status == "황금키워드 검증대기"
        ):
            due.append({
                "sheet_row": sheet_row,
                "schedule_id": str(row[index["schedule_id"]]).strip(),
                "planned": planned,
                "site_url": destination,
                "keyword": str(row[index["golden_keyword_candidate"]]).strip(),
                "review_url": str(row[index["review_or_output_url"]]).strip(),
                "notes": str(row[index["notes"]]).strip(),
            })
    return sorted(due, key=lambda item: (item["planned"], item["schedule_id"]))


def mark_dispatched(service, item: dict[str, Any]) -> None:
    stamp = now.strftime("%Y-%m-%d %H:%M KST")
    note = item["notes"]
    dispatch_note = f"파이프라인 연결·초안 생성 요청 {stamp}"
    if dispatch_note not in note:
        note = (note + " | " + dispatch_note).strip(" |")
    service.spreadsheets().values().update(
        spreadsheetId=SHEET_ID,
        range=f"'{CALENDAR_TAB}'!M{item['sheet_row']}:O{item['sheet_row']}",
        valueInputOption="RAW",
        body={"values": [["자료수집", item["review_url"], note]]},
    ).execute()


def main() -> None:
    state = load_state()
    fired = state.get("fired", {})

    last_dispatch_raw = state.get("last_dispatch_at")
    elapsed_minutes = 30.0
    if last_dispatch_raw:
        try:
            last_dispatch = datetime.datetime.fromisoformat(last_dispatch_raw)
            if last_dispatch.tzinfo is None:
                last_dispatch = last_dispatch.replace(tzinfo=KST)
            elapsed_minutes = (now - last_dispatch.astimezone(KST)).total_seconds() / 60
        except Exception:
            pass

    if elapsed_minutes < 30:
        print(f"⏳ 마지막 디스패치 후 {elapsed_minutes:.1f}분 — 최소 30분 간격 대기")
        _save_state(state, fired, changed=False)
        return

    service = get_sheets_service()
    due = load_due_calendar_rows(service)
    print(
        f"캘린더 기반 오늘 발행 대상: due={len(due)}, "
        f"A/B cadence credentialed sites={len(TODAY_SITES)}/{len(SITES)} "
        f"(registry total={len(ALL_BLOG_CONFIG)})"
    )

    changed = False
    for item in due:
        schedule_id = item["schedule_id"]
        if not schedule_id or fired.get(schedule_id):
            continue
        response = requests.post(
            f"https://api.github.com/repos/{REPO}/actions/workflows/daily-network-publish.yml/dispatches",
            headers={
                "Authorization": f"token {GH_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
            json={
                "ref": "main",
                "inputs": {
                    "room_id": schedule_id,
                    "target_site_url": item["site_url"],
                    "force_keyword": item["keyword"],
                    "publication_approved": "false",
                },
            },
            timeout=20,
        )
        print(
            f"▶ {schedule_id} {item['site_url']} / {item['keyword']} "
            f"→ HTTP {response.status_code}"
        )
        if response.status_code not in (200, 201, 204):
            print("⚠️ dispatch 실패 — 다음 스케줄러 실행에서 재시도")
            continue

        # Record the successful dispatch first.  The OAuth identity currently used by
        # Actions may have read-only Sheets access; a calendar write failure must never
        # turn a successful draft request into a duplicate dispatch on the next poll.
        fired[schedule_id] = True
        state["last_dispatch_at"] = now.isoformat()
        changed = True
        try:
            mark_dispatched(service, item)
        except Exception as exc:
            print(f"⚠️ draft dispatch succeeded; calendar status write deferred: {exc}")
        break

    _save_state(state, fired, changed)


def _save_state(state: dict[str, Any], fired: dict[str, Any], changed: bool) -> None:
    state["fired"] = fired
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a", encoding="utf-8") as out:
        out.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()
