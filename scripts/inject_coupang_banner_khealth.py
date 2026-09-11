#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_coupang_banner_khealth.py
─────────────────────────────────────────────────────────────
2026-08-22: 쿠팡파트너스 최종승인용 스크린샷 증빙 — 사용자가 쿠팡파트너스
"링크 생성"에서 직접 뽑은 배너 HTML을 k-health365.com의 실제 발행글
최상단에 삽입해서 "파트너스 링크/배너가 게시된 페이지"임을 인증할 수 있게
한다. 임시 증빙용 — 실제 상품-글 매칭 자동화(coupang_partners.py, API
키 발급 후)와는 별개.
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

SITE_URL = "https://k-health365.com"
TARGET_SLUG = "fasting-glucose-high-health-check"  # 사용자가 지정한 글
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ.get("KHEALTH365COM", "")

BANNER_HTML = (
    '<div class="coupang-partners-banner" style="margin:20px 0;text-align:center;">'
    '<a href="https://link.coupang.com/a/gpMjNZBSBo" target="_blank" rel="nofollow noopener" '
    'referrerpolicy="unsafe-url">'
    '<img src="https://image1.coupangcdn.com/image/affiliate/banner/'
    '1d716c803d6989b32ce370369a986a8e@2x.jpg" '
    'alt="프론트 오픈 캐리어기 18인치 20인치내용 하드 캐리어" width="120" height="240"></a>'
    '<p style="font-size:12px;color:#888;margin-top:6px;">'
    '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'
    '</div>'
)


def main():
    if not WP_PASS:
        print("❌ KHEALTH365COM 시크릿 없음")
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

    if "coupang-partners-banner" in content:
        # 이미 붙어있으면 기존 배너만 새 걸로 교체(중복 삽입 방지)
        content = re.sub(
            r'<div class="coupang-partners-banner"[\s\S]*?</div>\s*</div>',
            BANNER_HTML, content, count=1,
        )
        if "coupang-partners-banner" not in content:
            content = BANNER_HTML + content
    else:
        content = BANNER_HTML + content

    patch = requests.post(f"{SITE_URL}/wp-json/wp/v2/posts/{post['id']}",
                           auth=(WP_USER, WP_PASS), json={"content": content}, timeout=30)
    patch.raise_for_status()
    title = re.sub(r"<[^>]+>", "", post["title"]["rendered"])
    print(f"✅ 배너 삽입 완료: {title}")
    print(f"   {post['link']}")


if __name__ == "__main__":
    main()
