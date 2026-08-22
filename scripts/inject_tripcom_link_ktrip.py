#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_tripcom_link_ktrip.py
─────────────────────────────────────────────────────────────
2026-08-22: 사용자가 실제로 발급받은 Trip.com 제휴 트래킹 링크를
k-trip365.com의 경복궁 글에 삽입. 본문 상단에 제휴 고지문 포함 배너 —
쿠팡파트너스와 동일한 원칙(관련 있는 글에만, 법정 고지문 코드로 강제 삽입).
"""
import os
import re
import sys

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SITE_URL = "https://k-trip365.com"
TARGET_SLUG = "planning-for-gyeongbokgung-admission-price-2026-start-here"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ.get("KTRIP365COM", "")

BANNER_HTML = (
    '<div class="tripcom-affiliate-banner" style="margin:20px 0;padding:16px 20px;'
    'background:#eef6ff;border:1px solid #cfe3fb;border-radius:8px;">'
    '<p style="margin:0 0 10px 0;">Book Gyeongbokgung Palace tours and tickets through '
    '<a href="https://www.trip.com/t/6h8k79UF2W2" target="_blank" rel="nofollow noopener">'
    'Trip.com</a>.</p>'
    '<p style="font-size:12px;color:#888;margin:0;">This post contains an affiliate link. '
    'We may earn a commission from qualifying bookings, at no extra cost to you.</p>'
    '</div>'
)


def main():
    if not WP_PASS:
        print("❌ KTRIP365COM 시크릿 없음")
        sys.exit(1)

    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts",
                      auth=(WP_USER, WP_PASS),
                      params={"slug": TARGET_SLUG, "status": "publish,private",
                              "_fields": "id,link,content,title"},
                      timeout=20)
    r.raise_for_status()
    posts = r.json()
    if not posts:
        print(f"❌ 슬러그 '{TARGET_SLUG}' 글을 못 찾음")
        sys.exit(1)
    post = posts[0]
    content = post["content"]["rendered"]

    if "tripcom-affiliate-banner" not in content:
        content = BANNER_HTML + content

    # 이 글은 새 CTA(버튼식, 이메일 평문 노출 안 함) 코드 배포 전에 이미 발행돼서
    # 옛 스타일(이메일 평문 + mailto 텍스트링크)로 박혀있음 — 새 버튼 스타일로 교체.
    old_cta_pattern = re.compile(
        r'<div class="cta-box"[\s\S]*?Get in Touch[\s\S]*?</div>\s*</div>', re.IGNORECASE)
    new_cta = (
        '<div class="cta-box" style="margin:28px 0;padding:20px 24px;'
        'background:#eef4ff;border:1px solid #c7d9f5;border-radius:8px;">'
        '<h3 style="margin-top:0;font-size:1rem;">Get in Touch</h3>'
        '<p style="margin:0;">Have questions about your specific situation? '
        'Reach out anytime for a personal consultation.</p>'
        '<a href="mailto:westlake.ceo@gmail.com" style="display:inline-block;margin-top:10px;'
        'padding:9px 18px;background:#2f6fed;color:#fff;border-radius:6px;'
        'text-decoration:none;font-size:0.9rem;">Contact Us</a></div>'
    )
    if old_cta_pattern.search(content):
        content = old_cta_pattern.sub(new_cta, content, count=1)
        print("   (구버전 CTA를 새 버튼 스타일로 교체)")

    patch = requests.post(f"{SITE_URL}/wp-json/wp/v2/posts/{post['id']}",
                           auth=(WP_USER, WP_PASS), json={"content": content}, timeout=30)
    patch.raise_for_status()
    print(f"✅ 완료: {post['link']}")


if __name__ == "__main__":
    main()
