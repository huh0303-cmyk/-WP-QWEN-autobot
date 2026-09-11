#!/usr/bin/env python3
"""26개 활성 사이트 전체에 댓글/답글 전면 비활성화 스니펫을 배포한다.
사용자 지시(2026-08-22) — 모든 사이트에서 답글을 아예 못 달게."""
import os
from pathlib import Path

import requests

from site_registry import ACTIVE_SITES

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
NAME = "Disable comments everywhere v1"
SOURCE = Path(__file__).with_name("disable_comments_everywhere.php")


def call(site, pw, method, path, **kwargs):
    r = requests.request(method, f"{site}/wp-json/code-snippets/v1/{path}",
                          auth=(WP_USER, pw), timeout=30, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def deploy_one(site, env_key, code):
    pw = os.environ.get(env_key, "")
    if not pw:
        return "skip", f"{env_key} 시크릿 없음"
    try:
        resp = call(site, pw, "GET", "snippets", params={"per_page": 100})
        snippets = resp if isinstance(resp, list) else resp.get("data", resp.get("items", []))
        matches = [s for s in snippets if s.get("name") == NAME]
        payload = {"name": NAME, "desc": "Force-disables comments/pings on all posts.",
                   "code": code, "scope": "global", "active": True, "priority": 1,
                   "tags": ["comments", "disable"]}
        if matches:
            result = call(site, pw, "POST", f"snippets/{matches[0]['id']}", json=payload)
            action = "updated"
        else:
            result = call(site, pw, "POST", "snippets", json=payload)
            action = "created"
        if not result.get("active", False):
            return "fail", f"snippet not active: {result}"
        return action, None
    except Exception as e:
        return "fail", str(e)


def main():
    code = SOURCE.read_text(encoding="utf-8")
    print(f"{'사이트':35s} {'결과':10s} 비고")
    ok = fail = skip = 0
    for site, env_key, lifecycle in ACTIVE_SITES:
        action, err = deploy_one(site, env_key, code)
        print(f"{site:35s} {action:10s} {err or ''}")
        if action in ("created", "updated"):
            ok += 1
        elif action == "skip":
            skip += 1
        else:
            fail += 1
    print(f"\n완료: 성공 {ok} / 스킵 {skip} / 실패 {fail} (총 {len(ACTIVE_SITES)}개)")


if __name__ == "__main__":
    main()
