#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wp_set_post_tags.py
─────────────────────────────────────────────────────────────
특정 사이트의 특정 글에 태그를 지정/추가하는 1회성 유틸.
태그 이름이 이미 있으면 재사용, 없으면 새로 생성 후 글에 연결.

사용법:
    python scripts/wp_set_post_tags.py <site_url> <post_id> <tag1,tag2,tag3,...>

환경변수:
    WP_APP_PASSWORD  — 해당 사이트 REST 쓰기 권한 앱 비밀번호
    WP_USER          — 기본값 huh0303@gmail.com
"""
import os
import sys
import requests

WP_USER = os.environ.get("WP_USER", "huh0303@gmail.com")


def log(msg):
    print(msg, flush=True)


def get_or_create_tag(site, name, auth):
    r = requests.get(f"{site}/wp-json/wp/v2/tags", auth=auth,
                      params={"search": name, "per_page": 10}, timeout=20)
    r.raise_for_status()
    for t in r.json():
        if t["name"].strip().lower() == name.strip().lower():
            return t["id"]
    r = requests.post(f"{site}/wp-json/wp/v2/tags", auth=auth,
                       json={"name": name}, timeout=20)
    r.raise_for_status()
    return r.json()["id"]


def main():
    site = sys.argv[1].rstrip("/")
    post_id = sys.argv[2]
    tag_names = [t.strip() for t in sys.argv[3].split(",") if t.strip()]

    pw = os.environ.get("WP_APP_PASSWORD")
    if not pw:
        log("❌ WP_APP_PASSWORD 없음")
        raise SystemExit(1)
    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)

    tag_ids = []
    for name in tag_names:
        tid = get_or_create_tag(site, name, auth)
        tag_ids.append(tid)
        log(f"   태그 확보: {name} (id={tid})")

    r = requests.post(f"{site}/wp-json/wp/v2/posts/{post_id}", auth=auth,
                       json={"tags": tag_ids}, timeout=20)
    r.raise_for_status()
    log(f"✅ 글 #{post_id}에 태그 {tag_names} 적용 완료")


if __name__ == "__main__":
    main()
