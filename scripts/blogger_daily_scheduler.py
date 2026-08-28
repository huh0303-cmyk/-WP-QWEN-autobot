#!/usr/bin/env python3
"""Dispatch at most one Gemini Blogger post per connected site and KST day."""
from __future__ import annotations

import datetime as dt
import json
import os
import random
from pathlib import Path

import requests

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
    now_minute = NOW.hour * 60 + NOW.minute
    last_raw = state.get("last_dispatch_at")
    if last_raw:
        elapsed = (NOW - dt.datetime.fromisoformat(last_raw).astimezone(KST)).total_seconds() / 60
        if elapsed < 20:
            print(f"Minimum dispatch gap: wait ({elapsed:.1f}/20 minutes).")
            return 0

    for site in sorted(bloggers, key=lambda item: (target_minutes(item["site_id"]), item["site_id"])):
        site_id = site["site_id"]
        target = target_minutes(site_id)
        print(f"{site_id}: target={target // 60:02d}:{target % 60:02d} KST fired={bool(state['fired'].get(site_id))}")
        if state["fired"].get(site_id) or now_minute < target:
            continue
        source = wordpress.get(site.get("keyword_rules", {}).get("source_site_id", ""))
        if not source:
            print(f"Skip {site_id}: source WordPress mapping is missing.")
            continue
        response = requests.post(
            f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/workflows/blogger-rewrite.yml/dispatches",
            headers={"Authorization": f"Bearer {os.environ['GH_DISPATCH_TOKEN']}", "Accept": "application/vnd.github+json"},
            json={"ref": "main", "inputs": {"source_wp_url": source["url"], "blogger_site_id": site_id,
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
