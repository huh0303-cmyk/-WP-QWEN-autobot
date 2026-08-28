#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_coupang_banner.py
─────────────────────────────────────────────────────────────
쿠팡파트너스 "웹사이트 목록" 추가 사이트들의 최종승인용 스크린샷 증빙 —
inject_coupang_banner_khealth.py를 여러 사이트에 재사용할 수 있게 일반화한 버전.
각 사이트의 가장 최근 발행글 최상단에 파트너스 배너를 삽입해서
"파트너스 링크/배너가 게시된 페이지"임을 인증할 수 있게 한다.
"""
import os
import re
import sys
from datetime import datetime, timedelta

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WP_USER = "huh0303@gmail.com"
KST = timedelta(hours=9)

# (site_url, wp_password_env_var)
SITES = [
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://k-trip365.com", "KTRIP365COM"),
]

# 사용자가 새로 생성한 삼성 갤럭시북5 링크. 실제 상품 이미지는 iframe 리다이렉트
# Location 헤더의 image= 파라미터에서 추출한 CDN 경로(vendor_inventory/...).
BANNER_HTML = (
    '<div class="coupang-partners-banner" '
    'style="margin:20px 0;padding:16px;border:1px solid #eee;border-radius:8px;'
    'text-align:center;max-width:240px;">'
    '<div style="font-weight:bold;color:#111;margin-bottom:8px;">coupang</div>'
    '<a href="https://link.coupang.com/a/gzPzPsdM4W" target="_blank" '
    'rel="nofollow noopener" referrerpolicy="unsafe-url">'
    '<img src="https://image1.coupangcdn.com/image/vendor_inventory/34bb/'
    '38c01cdb6310146361fa09c3026a64ab5736dd150f2cd416bca9589e6c3e.jpg" '
    'alt="삼성 갤럭시북5 인텔 울트라5 15.6인치" width="200" '
    'style="border-radius:6px;max-width:100%;height:auto;"></a>'
    '<div style="font-size:13px;color:#333;margin-top:8px;">삼성 갤럭시북5&hellip;</div>'
    '<a href="https://link.coupang.com/a/gzPzPsdM4W" target="_blank" '
    'rel="nofollow noopener" referrerpolicy="unsafe-url" '
    'style="display:inline-block;margin-top:8px;padding:8px 20px;background:#0074e8;'
    'color:#fff;border-radius:20px;text-decoration:none;font-size:14px;">'
    '쇼핑하기</a>'
    '<p style="font-size:12px;color:#888;margin-top:8px;margin-bottom:0;">'
    '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'
    '</div>'
)


def inject(site_url: str, wp_pass_env: str) -> dict:
    wp_pass = os.environ.get(wp_pass_env, "")
    if not wp_pass:
        return {"site": site_url, "ok": False, "error": f"{wp_pass_env} 시크릿 없음"}

    # 이전 실행에서 이미 오늘 날짜로 공개 전환+배너 삽입된 글이 있으면 그 글의
    # 배너만 최신 BANNER_HTML로 교체. 없으면 가장 최근 private 글을 승격.
    r = requests.get(
        f"{site_url}/wp-json/wp/v2/posts",
        auth=(WP_USER, wp_pass),
        params={"per_page": 1, "status": "publish", "orderby": "date", "order": "desc",
                "_fields": "id,link,content,title,status"},
        timeout=20,
    )
    r.raise_for_status()
    latest_publish = r.json()
    post = None
    if latest_publish and "coupang-partners-banner" in latest_publish[0]["content"]["rendered"]:
        post = latest_publish[0]

    if post is None:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=(WP_USER, wp_pass),
            params={"per_page": 1, "status": "private", "orderby": "date", "order": "desc",
                    "_fields": "id,link,content,title,status"},
            timeout=20,
        )
        r.raise_for_status()
        posts = r.json()
        if not posts:
            return {"site": site_url, "ok": False, "error": "승격할 private 글이 없음"}
        post = posts[0]
    content = post["content"]["rendered"]

    if "coupang-partners-banner" in content:
        replaced = re.sub(
            r'<div class="coupang-partners-banner"[\s\S]*?</div>',
            BANNER_HTML, content, count=1,
        )
        content = replaced if replaced != content else BANNER_HTML + content
    else:
        content = BANNER_HTML + content

    now_kst = datetime.utcnow() + KST
    now_gmt = now_kst - KST
    patch = requests.post(
        f"{site_url}/wp-json/wp/v2/posts/{post['id']}",
        auth=(WP_USER, wp_pass),
        json={
            "content": content,
            "status": "publish",
            "date": now_kst.strftime("%Y-%m-%dT%H:%M:%S"),
            "date_gmt": now_gmt.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        timeout=30,
    )
    patch.raise_for_status()
    result = patch.json()
    title = post["title"]["rendered"]
    return {"site": site_url, "ok": True, "skipped": False, "url": result.get("link", post["link"]),
            "status": result.get("status"), "title": title}


def list_pending(site_url: str, wp_pass_env: str, limit: int = 5) -> None:
    """Report-only: show the most recent draft/private posts (not touched)."""
    wp_pass = os.environ.get(wp_pass_env, "")
    if not wp_pass:
        return
    r = requests.get(
        f"{site_url}/wp-json/wp/v2/posts",
        auth=(WP_USER, wp_pass),
        params={"per_page": limit, "status": "draft,private,pending", "orderby": "date",
                "order": "desc", "_fields": "id,slug,date,status,title"},
        timeout=20,
    )
    if r.status_code != 200:
        return
    posts = r.json()
    if not posts:
        print(f"   (draft/private 대기글 없음)")
        return
    for p in posts:
        title = p["title"]["rendered"]
        print(f"   - [{p.get('status')}] {p.get('date','')[:10]} {title} (id={p['id']})")


def main():
    results = [inject(url, env_var) for url, env_var in SITES]
    for res in results:
        if not res.get("ok"):
            print(f"❌ {res['site']}: {res.get('error')}")
        elif res.get("skipped"):
            print(f"⏭️  {res['site']}: {res.get('note')} [status={res.get('status')}] — {res['url']}")
        else:
            print(f"✅ {res['site']}: 배너 삽입 완료 [status={res.get('status')}] — {res['url']}")
    if any(not r.get("ok") for r in results):
        sys.exit(1)

    if os.environ.get("REPORT_PENDING", "").strip().lower() == "true":
        print("\n--- 최근 draft/private 대기글 (참고용, 변경 없음) ---")
        for url, env_var in SITES:
            print(f"{url}:")
            list_pending(url, env_var)


if __name__ == "__main__":
    main()
