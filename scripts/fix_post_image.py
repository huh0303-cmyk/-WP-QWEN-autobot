#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_post_image.py
─────────────────────────────────────────────────────────────
이미 발행된 글 하나의 대표(hero) 이미지만 다시 뽑아서 교체한다.
2026-08-17: k-health365.com "파킨슨병 초기증상" 글에 손씻는 사진처럼
무관한 이미지가 들어간 사고 수정용 — autopost_mega.py의 이미지 검색/삽입
로직(get_multiple_images, build_img_html)을 그대로 재사용해서, 고쳐진
검색어 로직으로 새 이미지를 받아 본문 첫 <figure> 블록만 치환한다.

사용법:
    python scripts/fix_post_image.py <site_url> <post_slug> <keyword> <theme>
    예: python scripts/fix_post_image.py https://k-health365.com \
        파킨슨병-초기증상-시간과-비용을-아끼는-방법 "파킨슨병 초기증상" 건강과 의학
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from autopost_mega import (  # noqa: E402
    get_multiple_images, build_img_html, WP_USER,
)


def log(msg):
    print(msg, flush=True)


def main():
    if len(sys.argv) < 5:
        log("사용법: python fix_post_image.py <site_url> <post_slug> <keyword> <theme>")
        raise SystemExit(1)
    site_url = sys.argv[1].rstrip("/")
    slug = sys.argv[2]
    keyword = sys.argv[3]
    theme = sys.argv[4]

    site_secret_env = {
        "https://k-health365.com": "KHEALTH365COM",
    }.get(site_url)
    if not site_secret_env:
        log(f"❌ 이 사이트의 비밀번호 환경변수 매핑이 없음: {site_url}")
        raise SystemExit(1)
    pw = os.environ.get(site_secret_env, "")
    if not pw:
        log(f"❌ {site_secret_env} 비밀번호 없음")
        raise SystemExit(1)

    log(f"1/4 글 조회 중 (slug={slug})...")
    r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"slug": slug}, timeout=20)
    r.raise_for_status()
    posts = r.json()
    if not posts:
        log("❌ 해당 slug의 글을 못 찾음")
        raise SystemExit(1)
    post = posts[0]
    post_id = post["id"]
    content = post["content"]["rendered"]
    log(f"   글 ID {post_id} 확인됨")

    log(f"2/4 새 이미지 검색 중 (키워드: {keyword!r}, 테마: {theme!r})...")
    images = get_multiple_images(keyword, count=1, theme=theme)
    if not images:
        log("❌ 새 이미지도 못 찾음 — 중단(기존 이미지 그대로 둠)")
        raise SystemExit(1)
    log(f"   새 이미지: {images[0]}")

    new_hero = build_img_html(images[:1], keyword)

    log("3/4 본문의 기존 대표이미지 블록 교체 중...")
    m = re.search(r'<figure[^>]*>.*?</figure>\s*', content, re.DOTALL)
    if not m:
        log("❌ 본문에서 기존 <figure> 블록을 못 찾음 — 중단")
        raise SystemExit(1)
    new_content = content[:m.start()] + new_hero + content[m.end():]

    log("4/4 워드프레스에 업데이트 중...")
    ur = requests.post(f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                        auth=(WP_USER, pw), json={"content": new_content}, timeout=30)
    if ur.status_code in (200, 201):
        log(f"✅ 이미지 교체 완료: {site_url}/?p={post_id}")
    else:
        log(f"❌ 업데이트 실패: {ur.status_code} {ur.text[:300]}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
