#!/usr/bin/env python3
"""kskin365.com을 포함한 27개 활성 사이트에 daily_visitor_counter.php를 Code Snippets 플러그인
REST API로 배포(생성 또는 업데이트)한다. 사용자 지시(2026-08-21) — 푸터에
일일 방문자수 표시 + 종합상황실이 조회할 공개 REST 엔드포인트."""
import os
from pathlib import Path

import requests

from site_registry import ACTIVE_SITES

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
NAME = "Daily visitor counter v2"
SOURCE = Path(__file__).with_name("daily_visitor_counter.php")


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
        matches = [s for s in snippets if "daily_visitor_count_" in s.get("code", "")]
        payload = {"name": NAME, "desc": "Footer daily visitor count + site-stats/v1/visitors REST route.",
                   "code": code, "scope": "global", "active": True, "priority": 10,
                   "tags": ["visitor-counter", "footer"]}
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
    if ok != len(ACTIVE_SITES) or skip or fail:
        raise SystemExit(f"27개 전체 배포 미완료: 성공={ok}, 스킵={skip}, 실패={fail}")


if __name__ == "__main__":
    main()
