#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_kworld_posts.py
─────────────────────────────────────────────────────────────
2026-08-28: kworld365.com은 발행글 0개(전부 draft/private)라서 "안 열린다"는
소리를 들음. k-health365의 43개 벌크 발행 사고를 겪은 직후라, 여기서는
한꺼번에 다 풀지 않고 오늘 1개 + 이후 2일 간격으로 최대 4개만 순차 공개.
"""
import os
import sys
from datetime import datetime, timedelta

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SITE_URL = "https://kworld365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ.get("KWORLD365COM", "")
KST = timedelta(hours=9)
MAX_POSTS = 5
DAY_STEP = 2


def main():
    if not WP_PASS:
        print("❌ KWORLD365COM 시크릿 없음")
        sys.exit(1)

    r = requests.get(
        f"{SITE_URL}/wp-json/wp/v2/posts",
        auth=(WP_USER, WP_PASS),
        params={"per_page": MAX_POSTS, "status": "draft,private,pending", "orderby": "date",
                "order": "desc", "_fields": "id,title,date,status"},
        timeout=20,
    )
    r.raise_for_status()
    posts = r.json()
    if not posts:
        print("❌ 공개 전환할 draft/private 글이 없음")
        sys.exit(1)

    now_kst = datetime.utcnow() + KST
    base = now_kst.replace(hour=10, minute=0, second=0, microsecond=0)

    for i, post in enumerate(posts):
        pid = post["id"]
        title = post["title"]["rendered"]
        if i == 0:
            target = now_kst
            status = "publish"
        else:
            target = base + timedelta(days=i * DAY_STEP)
            status = "future"
        date_gmt = target - KST
        patch = requests.post(
            f"{SITE_URL}/wp-json/wp/v2/posts/{pid}",
            auth=(WP_USER, WP_PASS),
            json={
                "status": status,
                "date": target.strftime("%Y-%m-%dT%H:%M:%S"),
                "date_gmt": date_gmt.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            timeout=30,
        )
        patch.raise_for_status()
        tag = "publish(오늘)" if status == "publish" else f"future({target.strftime('%Y-%m-%d')})"
        print(f"✅ id={pid} → {tag} — {title}")


if __name__ == "__main__":
    main()
