#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_ai_looking_images.py
─────────────────────────────────────────────────────────────
2026-08-28: 사용자가 koreamedicaltour.com / k-trip365.com의 쿠팡 증빙용
글 대표이미지가 딱 봐도 AI 생성 티가 난다고 지적("FLUX야?"). 스톡사진
(Pexels) 검색이 실패했을 때만 AI 이미지로 폴백하는 파이프라인인데, 이
두 건은 검색어가 너무 추상적이라 폴백이 걸린 것으로 보임 — 더 구체적인
검색어로 Pexels에서 실제 사진을 받아와 대표이미지를 교체한다.
"""
import hashlib
import os
import sys

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WP_USER = "huh0303@gmail.com"
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")

TARGETS = [
    {
        "site": "https://koreamedicaltour.com",
        "wp_pass_env": "KOREAMEDICALTOURCOM",
        "post_id": 1640,
        "query": "wallet empty money Asian woman shopping",
        "title": "VAT Refund Elimination Impact Korea",
    },
    {
        "site": "https://k-trip365.com",
        "wp_pass_env": "KTRIP365COM",
        "post_id": 4649,
        "query": "movie theater cinema entrance crowd",
        "title": "Korea August 2026 Film Screenings",
    },
]


def search_pexels(query: str) -> str:
    if not PEXELS_KEY:
        return ""
    r = requests.get(
        "https://api.pexels.com/v1/search",
        params={"query": query, "per_page": 5, "orientation": "landscape"},
        headers={"Authorization": PEXELS_KEY}, timeout=15,
    )
    if r.status_code != 200:
        return ""
    photos = r.json().get("photos", [])
    if not photos:
        return ""
    src = photos[0].get("src", {})
    return src.get("large") or src.get("medium", "")


def upload_media(site_url: str, wp_pass: str, image_url: str, title: str) -> int:
    image = requests.get(image_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    image.raise_for_status()
    mime = image.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
    ext = ".png" if "png" in mime else ".jpg"
    filename = "real-photo-" + hashlib.md5(image_url.encode()).hexdigest()[:12] + ext
    uploaded = requests.post(
        f"{site_url}/wp-json/wp/v2/media", auth=(WP_USER, wp_pass),
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime},
        data=image.content, timeout=35,
    )
    uploaded.raise_for_status()
    media_id = uploaded.json().get("id", 0)
    if media_id:
        requests.post(
            f"{site_url}/wp-json/wp/v2/media/{media_id}", auth=(WP_USER, wp_pass),
            json={"alt_text": title, "caption": ""}, timeout=15,
        )
    return media_id


def fix_one(target: dict) -> None:
    site, wp_pass_env, post_id, query, title = (
        target["site"], target["wp_pass_env"], target["post_id"], target["query"], target["title"],
    )
    wp_pass = os.environ.get(wp_pass_env, "")
    if not wp_pass:
        print(f"❌ {site}: {wp_pass_env} 시크릿 없음")
        return
    image_url = search_pexels(query)
    if not image_url:
        print(f"❌ {site}: Pexels 검색 실패 ('{query}')")
        return
    media_id = upload_media(site, wp_pass, image_url, title)
    if not media_id:
        print(f"❌ {site}: 미디어 업로드 실패")
        return
    r = requests.post(
        f"{site}/wp-json/wp/v2/posts/{post_id}", auth=(WP_USER, wp_pass),
        json={"featured_media": media_id}, timeout=30,
    )
    r.raise_for_status()
    print(f"✅ {site}: 대표이미지 교체 완료 (media_id={media_id}, query='{query}')")


def main():
    if not PEXELS_KEY:
        print("❌ PEXELS_KEY 시크릿 없음")
        sys.exit(1)
    for t in TARGETS:
        fix_one(t)


if __name__ == "__main__":
    main()
