#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kill_self_pingbacks.py
─────────────────────────────────────────────────────────────
자기 사이트끼리 내부링크 걸 때마다 워드프레스가 자동 생성하는 셀프
핑백 댓글을 정리하고, 앞으로 아예 안 생기게 막는다.

1. 대기중(pending) 상태 핑백/트랙백 댓글을 전부 완전삭제(휴지통 경유 없이)
2. 전체 발행글의 ping_status를 closed로 일괄 변경(이미 있는 글들)
3. 사이트 기본 설정(default_ping_status)도 closed로(앞으로 쓸 새 글)

사용법: python scripts/kill_self_pingbacks.py <site_url> <wp_pass_env_name>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from autopost_mega import WP_USER  # noqa: E402


def log(msg):
    print(msg, flush=True)


def main():
    if len(sys.argv) < 3:
        log("사용법: python kill_self_pingbacks.py <site_url> <wp_pass_env_name>")
        raise SystemExit(1)
    site = sys.argv[1].rstrip("/")
    pw_env = sys.argv[2]
    pw = os.environ.get(pw_env, "")
    if not pw:
        log(f"❌ {pw_env} 비밀번호 없음")
        raise SystemExit(1)
    auth = (WP_USER, pw)

    log("1/3 대기중 핑백/트랙백 댓글 삭제 중...")
    deleted = 0
    page = 1
    while True:
        r = requests.get(f"{site}/wp-json/wp/v2/comments",
                          auth=auth, params={"status": "hold", "per_page": 100, "page": page,
                                              "type": "pingback", "_fields": "id"}, timeout=30)
        if r.status_code != 200:
            break
        comments = r.json()
        if not comments:
            break
        for c in comments:
            dr = requests.delete(f"{site}/wp-json/wp/v2/comments/{c['id']}",
                                  auth=auth, params={"force": "true"}, timeout=20)
            if dr.status_code in (200, 201):
                deleted += 1
        page += 1
        if page > 20:
            break
    log(f"   삭제된 핑백: {deleted}개")

    log("2/3 기존 발행글 전체 ping_status → closed...")
    updated = 0
    page = 1
    while True:
        r = requests.get(f"{site}/wp-json/wp/v2/posts",
                          auth=auth, params={"per_page": 100, "page": page,
                                              "status": "publish,private",
                                              "_fields": "id,ping_status"}, timeout=30)
        if r.status_code != 200:
            break
        posts = r.json()
        if not posts:
            break
        for p in posts:
            if p.get("ping_status") == "closed":
                continue
            ur = requests.post(f"{site}/wp-json/wp/v2/posts/{p['id']}",
                                auth=auth, json={"ping_status": "closed"}, timeout=20)
            if ur.status_code in (200, 201):
                updated += 1
        page += 1
        if page > 20:
            break
    log(f"   ping_status 닫은 글: {updated}개")

    log("3/3 사이트 기본 핑백 설정 → closed (앞으로 쓸 새 글)...")
    try:
        sr = requests.post(f"{site}/wp-json/wp/v2/settings", auth=auth,
                            json={"default_ping_status": "closed"}, timeout=20)
        log(f"   default_ping_status: HTTP {sr.status_code}")
    except Exception as e:
        log(f"   ⚠️ {e}")

    log("\n✅ 완료")


if __name__ == "__main__":
    main()
