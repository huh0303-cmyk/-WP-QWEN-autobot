#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_khealth_indexing.py
─────────────────────────────────────────────────────────────
k-health365.com 전체 발행글을 대상으로 "왜 구글이 색인을 안 하는지"
기술적 원인을 실제로 열어보고 진단합니다.

체크 항목:
  1) 슬러그 패턴 — post-40, post-73 같은 자동 생성 번호 슬러그인지
     (한글 제목 슬러그화 실패 / 중복 슬러그 충돌 의심 신호)
  2) robots 메타태그 / X-Robots-Tag 헤더 — Googlebot User-Agent로 직접
     접속해서 noindex 여부 실제 확인 (일반 브라우저와 다르게 응답하는
     사이트가 있을 수 있어서 Googlebot UA로 확인해야 정확함)
  3) 실제 페이지 글자수 — WP API 상 글자수와 실제 렌더링된 페이지
     글자수가 크게 다르면 테마/캐시 문제 의심
  4) 중복/유사 제목 — 같은 사이트 내 제목이 겹치는 글이 있는지
  5) HTTP 상태 코드 — 200이 아닌 경우 (404, 30x, 5xx)

결과는 audit_khealth_results.txt 로 저장됩니다.
"""

import os, re, time
import requests

WP_USER = "huh0303@gmail.com"
SITE_URL = "https://k-health365.com"
WP_PASS = os.getenv("KHEALTH365COM", "")

GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def fetch_all_posts():
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{SITE_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_PASS),
            params={"per_page": 100, "page": page, "status": "publish",
                    "_fields": "id,link,slug,title,content,date"},
            timeout=20,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.3)
    return posts


def check_live_page(url):
    """Googlebot UA로 실제 접속해서 robots 상태 + 상태코드 + 글자수 확인"""
    result = {
        "status_code": None, "x_robots_tag": None, "meta_robots": None,
        "is_noindex": False, "word_count": 0, "error": None,
    }
    try:
        r = requests.get(url, headers={"User-Agent": GOOGLEBOT_UA}, timeout=15, allow_redirects=True)
        result["status_code"] = r.status_code
        result["x_robots_tag"] = r.headers.get("X-Robots-Tag", "")

        if "noindex" in result["x_robots_tag"].lower():
            result["is_noindex"] = True

        m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
        if m:
            result["meta_robots"] = m.group(1)
            if "noindex" in m.group(1).lower():
                result["is_noindex"] = True

        # 본문 텍스트만 대략 추출해서 글자수 계산 (article/main 태그 우선)
        body_match = re.search(r'<article[^>]*>(.*?)</article>', r.text, re.DOTALL | re.IGNORECASE)
        raw = body_match.group(1) if body_match else r.text
        plain = re.sub(r'<[^>]+>', '', raw)
        plain = re.sub(r'\s+', '', plain)
        result["word_count"] = len(plain)
    except Exception as e:
        result["error"] = str(e)[:150]
    return result


def main():
    lines = []
    def log(msg):
        print(msg)
        lines.append(msg)

    if not WP_PASS:
        log("❌ KHEALTH365COM 환경변수(비밀번호)가 없습니다.")
        with open("audit_khealth_results.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return

    log("=" * 60)
    log("🔍 k-health365.com 색인 문제 전수조사 시작")
    log("=" * 60)

    posts = fetch_all_posts()
    log(f"📋 전체 발행글 {len(posts)}건 확인됨\n")

    numbered_slug_posts = []
    noindex_posts = []
    thin_content_posts = []
    error_posts = []
    non200_posts = []
    title_seen = {}
    duplicate_title_posts = []

    for i, post in enumerate(posts):
        link = post.get("link", "")
        slug = post.get("slug", "")
        title = re.sub(r'<[^>]+>', '', post.get("title", {}).get("rendered", "")).strip()

        # 1) 번호형 슬러그 체크
        if re.match(r'^post-\d+$', slug):
            numbered_slug_posts.append((title, link, slug))

        # 4) 중복 제목 체크
        title_key = title.lower().strip()
        if title_key in title_seen:
            duplicate_title_posts.append((title, link, title_seen[title_key]))
        else:
            title_seen[title_key] = link

        # 2)+3)+5) 실제 페이지 체크 (Googlebot UA)
        live = check_live_page(link)
        if live["error"]:
            error_posts.append((title, link, live["error"]))
        else:
            if live["status_code"] != 200:
                non200_posts.append((title, link, live["status_code"]))
            if live["is_noindex"]:
                noindex_posts.append((title, link, live["x_robots_tag"], live["meta_robots"]))
            if 0 < live["word_count"] < 500:
                thin_content_posts.append((title, link, live["word_count"]))

        if (i + 1) % 50 == 0:
            log(f"   ... {i+1}/{len(posts)}건 확인 중")
        time.sleep(0.2)

    log("\n" + "=" * 60)
    log("📊 진단 결과 요약")
    log("=" * 60)

    log(f"\n1) 번호형 슬러그(post-N) — {len(numbered_slug_posts)}건")
    log("   (한글 제목 슬러그화 실패 또는 중복 슬러그 충돌 의심)")
    for t, l, s in numbered_slug_posts[:15]:
        log(f"   - [{s}] {t[:50]} → {l}")
    if len(numbered_slug_posts) > 15:
        log(f"   ... 외 {len(numbered_slug_posts)-15}건 더")

    log(f"\n2) 실제 noindex 응답 — {len(noindex_posts)}건")
    for t, l, xr, mr in noindex_posts[:15]:
        log(f"   - {t[:50]} → X-Robots-Tag:'{xr}' meta:'{mr}' ({l})")

    log(f"\n3) 200 이외 상태코드 — {len(non200_posts)}건")
    for t, l, code in non200_posts[:15]:
        log(f"   - [{code}] {t[:50]} → {l}")

    log(f"\n4) 중복 제목 — {len(duplicate_title_posts)}건")
    for t, l, orig in duplicate_title_posts[:15]:
        log(f"   - '{t[:50]}' 중복 → {l} (원본: {orig})")

    log(f"\n5) 얇은 콘텐츠(실제 렌더링 500자 미만) — {len(thin_content_posts)}건")
    for t, l, wc in thin_content_posts[:15]:
        log(f"   - {t[:50]} ({wc}자) → {l}")

    log(f"\n6) 접속 오류(타임아웃 등) — {len(error_posts)}건")
    for t, l, err in error_posts[:15]:
        log(f"   - {t[:50]} → {err}")

    log("\n" + "=" * 60)
    log("✅ 전수조사 완료")
    log("=" * 60)

    with open("audit_khealth_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
