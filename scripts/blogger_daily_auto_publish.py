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

KST = timezone(timedelta(hours=9))
STATE_FILE = ROOT / "data" / "blogspot_daily_auto_state.json"
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "12"))


def load_state() -> dict:
    today = datetime.now(KST).date().isoformat()
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            # Legacy 'posted' meant HTTP 204 only, not public publication.
            if state.get('version') != 2:
                state['pending'] = {sid: {'status': 'legacy_unverified', 'requested_at': None}
                                    for sid in state.get('posted', [])}
                state['posted'] = []
            if state.get('date') != today:
                state['posted'] = []
            state.update(version=2, date=today)
            state.setdefault('pending', {})
            return state
        except (OSError, ValueError):
            raise RuntimeError('Unreadable dispatch state; reconcile before sending more requests')
    return {"version": 2, "date": today, "posted": [], "pending": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(STATE_FILE)


def reconcile(state, sites):
    from concurrent.futures import ThreadPoolExecutor
    from publication_health_audit import check
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, [{'platform': 'blogger', 'url': s['url']} for s in sites]))
    verified = set()
    readable = set()
    for site, result in zip(sites, results):
        sid = site['site_id']
        if result['status'] not in {'public_post_found', 'no_public_post_in_response'}:
            continue
        readable.add(sid)
        if not result.get('latest_published'):
            continue
        published = datetime.fromisoformat(result['latest_published'].replace('Z', '+00:00'))
        if published.astimezone(KST).date().isoformat() == state['date']:
            verified.add(sid)
            state['pending'].pop(sid, None)
    state['posted'] = sorted(verified)
    return readable


def main() -> int:
    from control_center.app import _build_draft_workflow_call, get_blogger_data
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_DISPATCH_TOKEN"]
    state = load_state()
    sites = [blog for blog in get_blogger_data() if blog["connected"]]
    readable = reconcile(state, sites)
    save_state(state)
    random.shuffle(sites)
    remaining = [site for site in sites if site['site_id'] in readable
                 and site['site_id'] not in state['posted'] and site['site_id'] not in state['pending']]
    if not remaining:
        print(f"공개 확인 {len(state['posted'])}/{len(sites)} · 요청 결과 확인 필요 {len(state['pending'])} · 조회 실패 {len(sites)-len(readable)}")
        return 0

    batch = remaining[:MAX_PER_RUN]
    print(f"오늘 공개 확인: {len(state['posted'])}/{len(sites)} · 이번 실행 {len(batch)}개 요청 · 기존 미확인 {len(state['pending'])}")
    for site in batch:
        site_id = site["site_id"]
        try:
            workflow_name, inputs = _build_draft_workflow_call({
                "platform": "blogger", "selection_mode": "auto", "site_id": site_id, "keyword": "",
                "jitter_max_seconds": "60",
            })
        except RuntimeError as exc:
            print(f"  {site_id}: 스킵 ({exc})")
            continue
        # Save before dispatch: a timeout may occur after GitHub accepted the request.
        state['pending'][site_id] = {'status': 'dispatch_uncertain', 'requested_at': datetime.now(timezone.utc).isoformat()}
        save_state(state)
        try:
            response = requests.post(
            f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_name}/dispatches",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"ref": "main", "inputs": inputs}, timeout=20,
            )
        except requests.RequestException:
            print(f'  {site_id}: 요청 결과 불확실; 중복 전송 보류')
            continue
        ok = response.status_code == 204
        print(f"  {site_id}: HTTP {response.status_code}")
        if ok:
            state['pending'][site_id]['status'] = 'dispatched_not_verified'
        elif 400 <= response.status_code < 500:
            state['pending'].pop(site_id, None)
        save_state(state)
        time.sleep(10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
