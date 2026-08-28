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
import sys

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WP_USER = "huh0303@gmail.com"

# (site_url, wp_password_env_var)
SITES = [
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://k-trip365.com", "KTRIP365COM"),
]

BANNER_HTML = (
    '<div class="coupang-partners-banner" style="margin:20px 0;text-align:center;">'
    '<iframe src="https://coupa.ng/co45VZ" width="120" height="240" frameborder="0" '
    'scrolling="no" referrerpolicy="unsafe-url"></iframe>'
    '<p style="font-size:12px;color:#888;margin-top:6px;">'
    '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.</p>'
    '</div>'
)


def inject(site_url: str, wp_pass_env: str) -> dict:
    wp_pass = os.environ.get(wp_pass_env, "")
    if not wp_pass:
        return {"site": site_url, "ok": False, "error": f"{wp_pass_env} 시크릿 없음"}

    r = requests.get(
        f"{site_url}/wp-json/wp/v2/posts",
        auth=(WP_USER, wp_pass),
        params={"per_page": 5, "status": "publish", "orderby": "date", "order": "desc",
                "_fields": "id,link,content,title,status"},
        timeout=20,
    )
    r.raise_for_status()
    posts = r.json()
    if not posts:
        return {"site": site_url, "ok": False, "error": "발행된(publish) 글이 없음"}
    post = posts[0]
    content = post["content"]["rendered"]

    if "coupang-partners-banner" in content:
        return {"site": site_url, "ok": True, "skipped": True, "url": post["link"],
                "status": post.get("status"), "note": "이미 배너가 삽입되어 있음"}

    content = BANNER_HTML + content
    patch = requests.post(
        f"{site_url}/wp-json/wp/v2/posts/{post['id']}",
        auth=(WP_USER, wp_pass), json={"content": content}, timeout=30,
    )
    patch.raise_for_status()
    title = post["title"]["rendered"]
    return {"site": site_url, "ok": True, "skipped": False, "url": post["link"],
            "status": post.get("status"), "title": title}


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
