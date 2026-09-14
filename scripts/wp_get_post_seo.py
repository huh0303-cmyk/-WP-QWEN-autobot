#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wp_get_post_seo.py
─────────────────────────────────────────────────────────────
특정 사이트의 특정 글 하나의 Rank Math SEO 점수와 핵심 메타 정보를 조회한다.

사용법:
    python scripts/wp_get_post_seo.py <site_url> <post_id>

환경변수:
    WP_APP_PASSWORD  — 해당 사이트 REST 읽기 권한 앱 비밀번호
    WP_USER          — 기본값 huh0303@gmail.com
"""
import os
import sys
import requests

WP_USER = os.environ.get("WP_USER", "huh0303@gmail.com")


def log(msg):
    print(msg, flush=True)


def main():
    site = sys.argv[1].rstrip("/")
    post_id = sys.argv[2]

    pw = os.environ.get("WP_APP_PASSWORD")
    if not pw:
        log("❌ WP_APP_PASSWORD 없음")
        raise SystemExit(1)
    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)

    r = requests.get(
        f"{site}/wp-json/wp/v2/posts/{post_id}",
        auth=auth,
        params={"context": "edit", "_fields": "id,title,link,meta,status"},
        timeout=20,
    )
    r.raise_for_status()
    d = r.json()
    meta = d.get("meta", {})

    score = meta.get("rank_math_seo_score", "")
    keyword = meta.get("rank_math_focus_keyword", "")
    meta_desc = meta.get("rank_math_description", "")

    log(f"제목: {d.get('title', {}).get('rendered', '')}")
    log(f"링크: {d.get('link', '')}")
    log(f"상태: {d.get('status', '')}")
    log(f"Rank Math SEO 점수: {score if score else '(측정 안 됨/0점)'}")
    log(f"포커스 키워드: {keyword if keyword else '(미설정)'}")
    log(f"메타 설명: {meta_desc if meta_desc else '(미설정)'}")


if __name__ == "__main__":
    main()
