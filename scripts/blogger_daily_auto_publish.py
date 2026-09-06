#!/usr/bin/env python3
"""Daily auto-publish for every connected Blogspot site, independent of the
fragile 14-day-calendar scheduler (blogger_daily_scheduler.py), which only
dispatches a site when a matching calendar row AND its paired WordPress
source post already exist and are live - if that Sheet tab is stale or
mismatched, the whole chain silently produces nothing.

2026-09-06 CEO: "33개 블로그스팟에 매일 좋은 글들이 올라가야해, 확실히 좀
해줘." This reuses the exact dispatch shape the CEO's own manual
'바이럴자동발행'/bulk buttons already use (auto topic selection, no
calendar dependency), proven working today across many live test runs.

Tracks which sites already posted today in a small state file committed
back to the repo (see the workflow's own commit step), and dispatches
several sites per invocation - GitHub's own scheduled-cron firing is known
to be unreliable at high frequency on repos with many scheduled workflows
(this one included), so each tick does more than the bare minimum to make
up for ticks that never actually fire.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from control_center.app import _build_draft_workflow_call, get_blogger_data  # noqa: E402

KST = timezone(timedelta(hours=9))
STATE_FILE = ROOT / "data" / "blogspot_daily_auto_state.json"
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "12"))


def load_state() -> dict:
    today = datetime.now(KST).date().isoformat()
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if state.get("date") == today:
                return state
        except (OSError, ValueError):
            pass
    return {"date": today, "posted": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_DISPATCH_TOKEN"]
    state = load_state()
    sites = [blog for blog in get_blogger_data() if blog["connected"]]
    random.shuffle(sites)
    remaining = [site for site in sites if site["site_id"] not in state["posted"]]
    if not remaining:
        print(f"오늘 {len(state['posted'])}/{len(sites)}개 전부 발행 요청 완료")
        return 0

    batch = remaining[:MAX_PER_RUN]
    print(f"오늘 진행: {len(state['posted'])}/{len(sites)} 완료 · 이번 실행에서 {len(batch)}개 발행 요청")
    for site in batch:
        site_id = site["site_id"]
        try:
            workflow_name, inputs = _build_draft_workflow_call({
                "platform": "blogger", "selection_mode": "auto", "site_id": site_id, "keyword": "",
            })
        except RuntimeError as exc:
            print(f"  {site_id}: 스킵 ({exc})")
            continue
        response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_name}/dispatches",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"ref": "main", "inputs": inputs}, timeout=20,
        )
        ok = response.status_code == 204
        print(f"  {site_id}: HTTP {response.status_code}{'' if ok else ' ' + response.text[:200]}")
        if ok:
            state["posted"].append(site_id)
            save_state(state)
        time.sleep(10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
