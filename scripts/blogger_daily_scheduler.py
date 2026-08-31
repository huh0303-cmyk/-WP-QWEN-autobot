#!/usr/bin/env python3
"""Dispatch at most one Gemini Blogger post per connected site and KST day."""
from __future__ import annotations

import datetime as dt
import json
import os
import random
from pathlib import Path

import requests
from urllib.parse import urlparse, parse_qs
from gsheets_direct import get_sheets_service

ROOT = Path(__file__).resolve().parents[1]
KST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(KST)
TODAY = NOW.date().isoformat()
STATE_FILE = ROOT / "blogger_scheduler_state.json"
REGISTRY_FILE = ROOT / "config" / "automation_hub_sites.json"


def load_sites() -> tuple[list[dict], dict[str, dict]]:
    raw = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))["sites"]
    wordpress = {site["site_id"]: site for site in raw if site["platform"] == "wordpress"}
    bloggers = [site for site in raw if site["platform"] == "blogger" and site.get("enabled", True)
                and site.get("publish_mode") in {"automatic", "review"} and site.get("daily_max", 0) == 1]
    return bloggers, wordpress


def target_minutes(site_id: str) -> int:
    """Stable site anchor plus a different deterministic +/-4-hour jitter each day."""
    anchor_rng = random.Random(f"{site_id}-blogger-anchor-v1")
    anchor = anchor_rng.randint(8 * 60, 16 * 60)
    day_rng = random.Random(f"{TODAY}-{site_id}-blogger-jitter-v1")
    minute = max(4 * 60 + 3, min(22 * 60 + 47, anchor + day_rng.randint(-240, 240)))
    if minute % 15 == 0:
        minute += day_rng.choice([-7, -4, 4, 7])
    return minute


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if state.get("date") == TODAY:
                return state
        except (OSError, ValueError):
            pass
    return {"date": TODAY, "fired": {}, "last_dispatch_at": None}


def main() -> int:
    bloggers, wordpress = load_sites()
    state = load_state()
    service = get_sheets_service()
    sheet_id = os.environ["SHEET_ID"]
    tab = "14일_콘텐츠운영캘린더"
    values = service.spreadsheets().values().get(spreadsheetId=sheet_id,
        range=f"'{tab}'!A1:O2000").execute().get("values", [])
    calendar = [dict(zip(values[0], r)) | {"_row": i} for i, r in enumerate(values[1:], 2)] if values else []
    due = {}
    for site in bloggers:
        rows = [r for r in calendar if r.get("platform") == "Blogger"
                and r.get("destination_url", "").rstrip("/") == site["url"].rstrip("/")
                and r.get("planned_at_kst", "").startswith(TODAY)
                and r.get("current_status") == "WP 선행대기"
                and not r.get("review_or_output_url")]
        if len(rows) != 1:
            continue
        item = rows[0]
        when = dt.datetime.strptime(item["planned_at_kst"].removesuffix(" KST"), "%Y-%m-%d %H:%M").replace(tzinfo=KST)
        if when > NOW:
            continue
        source = wordpress.get(site.get("keyword_rules", {}).get("source_site_id", ""))
        if not source:
            continue
        matches = [r for r in calendar if r.get("platform") == "WordPress"
                   and r.get("destination_url", "").rstrip("/") == source["url"].rstrip("/")
                   and r.get("planned_at_kst", "").startswith(TODAY)
                   and r.get("golden_keyword_candidate") == item.get("golden_keyword_candidate")
                   and r.get("review_or_output_url")]
        if len(matches) != 1:
            continue
        parsed = urlparse(matches[0]["review_or_output_url"])
        ids = parse_qs(parsed.query).get("post") or parse_qs(parsed.query).get("p") or []
        if parsed.netloc != urlparse(source["url"]).netloc or not ids or not ids[0].isdigit():
            continue
        try:
            public = requests.get(f"{source['url'].rstrip('/')}/wp-json/wp/v2/posts/{ids[0]}", timeout=20)
            public.raise_for_status()
            if public.json().get("status") != "publish":
                continue
        except (requests.RequestException, ValueError):
            print(f"{site['site_id']}: exact calendar WP post awaits human publication")
            continue
        due[site["site_id"]] = (item, f"{source['url'].rstrip('/')}/?p={ids[0]}")
    now_minute = NOW.hour * 60 + NOW.minute
    last_raw = state.get("last_dispatch_at")
    if last_raw:
        elapsed = (NOW - dt.datetime.fromisoformat(last_raw).astimezone(KST)).total_seconds() / 60
        if elapsed < 20:
            print(f"Minimum dispatch gap: wait ({elapsed:.1f}/20 minutes).")
            return 0

    for site in sorted((s for s in bloggers if s["site_id"] in due), key=lambda s: due[s["site_id"]][0]["planned_at_kst"]):
        site_id = site["site_id"]
        item, exact_source = due[site_id]
        target = 0  # The calendar due-time check above replaces random timing.
        print(f"{site_id}: target={target // 60:02d}:{target % 60:02d} KST fired={bool(state['fired'].get(site_id))}")
        if state["fired"].get(site_id) or now_minute < target:
            continue
        source = wordpress.get(site.get("keyword_rules", {}).get("source_site_id", ""))
        if not source:
            print(f"Skip {site_id}: source WordPress mapping is missing.")
            continue
        service.spreadsheets().values().update(spreadsheetId=sheet_id,
            range=f"'{tab}'!M{item['_row']}:O{item['_row']}", valueInputOption="RAW",
            body={"values": [["자료수집", "", item.get("notes", "") + "\n시트 지정 WP 원문 확인·블팟 초안 요청"]]}).execute()
        response = requests.post(
            f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/workflows/blogger-rewrite.yml/dispatches",
            headers={"Authorization": f"Bearer {os.environ['GH_DISPATCH_TOKEN']}", "Accept": "application/vnd.github+json"},
            json={"ref": "main", "inputs": {"source_wp_url": exact_source, "blogger_site_id": site_id,
                  "language": site.get("language", "en"), "persona": site.get("persona", "helpful specialist editor"),
                  "tone": site.get("tone", "practical and clear"), "target_chars": str(site.get("target_chars", 2400)),
                  "publish_now": "false"}}, timeout=20)
        print(f"Dispatch {site_id}: HTTP {response.status_code}")
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(f"GitHub dispatch failed: {response.status_code} {response.text[:300]}")
        state["fired"][site_id] = {"target_kst": f"{target // 60:02d}:{target % 60:02d}", "dispatched_at": NOW.isoformat()}
        state["last_dispatch_at"] = NOW.isoformat()
        break
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
