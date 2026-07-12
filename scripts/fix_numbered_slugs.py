#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_numbered_slugs.py
─────────────────────────────────────────────────────────────
k-health365.com에서 /post-N/ 형태의 번호형 슬러그를 가진 글을 찾아
제목 기반 한글 슬러그로 재설정합니다.

WordPress 기본 sanitize_title()이 실패해 post-{ID}로 떨어진 글들을
대상으로, 제목에서 직접 안전한 슬러그를 만들어 PATCH 요청으로 교체합니다.
"""

import os, re, time
import requests

WP_USER = "huh0303@gmail.com"
SITE_URL = "https://k-health365.com"
WP_PASS = os.getenv("KHEALTH365COM", "")

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def make_slug_from_title(title: str, max_len: int = 60) -> str:
    """제목에서 안전한 슬러그 생성 (한글 유지, 특수문자/HTML엔티티 제거)"""
    t = re.sub(r'&#\d+;', '', title)          # &#8216; 같은 HTML 엔티티 제거
    t = re.sub(r'&[a-zA-Z]+;', '', t)          # &amp; 같은 named entity 제거
    t = re.sub(r'[\[\]\(\)"\'“”‘’『』「」]', '', t)  # 괄호/따옴표류 제거
    t = re.sub(r'[^\w\s가-힣ㄱ-ㅎㅏ-ㅣ-]', ' ', t)     # 한글/영문/숫자/공백/하이픈만 남김
    t = re.sub(r'\s+', '-', t.strip())
    t = re.sub(r'-{2,}', '-', t).strip('-')
    if not t:
        t = "post"
    return t[:max_len].rstrip('-')


def fetch_numbered_slug_posts():
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{SITE_URL}/wp-json/wp/v2/posts",
            auth=(WP_USER, WP_PASS),
            params={"per_page": 100, "page": page, "status": "publish",
                    "_fields": "id,link,slug,title"},
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
    return [p for p in posts if re.match(r'^post-\d+$', p.get("slug", ""))]


def main():
    lines = []
    def log(msg):
        print(msg)
        lines.append(msg)

    if not WP_PASS:
        log("❌ KHEALTH365COM 환경변수가 없습니다.")
        return

    log(f"🔧 번호형 슬러그 수정 {'(DRY_RUN)' if DRY_RUN else ''}")
    targets = fetch_numbered_slug_posts()
    log(f"📋 대상 {len(targets)}건 발견\n")

    used_slugs = set()
    fixed, failed = 0, 0

    for post in targets:
        post_id = post["id"]
        old_link = post.get("link", "")
        title = re.sub(r'<[^>]+>', '', post.get("title", {}).get("rendered", "")).strip()
        new_slug = make_slug_from_title(title)

        # 슬러그 중복 방지 (이번 실행 내에서)
        base_slug = new_slug
        n = 2
        while new_slug in used_slugs:
            new_slug = f"{base_slug}-{n}"
            n += 1
        used_slugs.add(new_slug)

        if DRY_RUN:
            log(f"   🔍 [DRY_RUN] {old_link} → /{new_slug}/  (제목: {title[:40]})")
            fixed += 1
            continue

        try:
            r = requests.post(
                f"{SITE_URL}/wp-json/wp/v2/posts/{post_id}",
                auth=(WP_USER, WP_PASS),
                json={"slug": new_slug},
                timeout=20,
            )
            if r.status_code in (200, 201):
                new_link = r.json().get("link", "")
                log(f"   ✅ {old_link} → {new_link}")
                fixed += 1
            else:
                log(f"   ❌ 실패 ({r.status_code}): {old_link} — {r.text[:150]}")
                failed += 1
        except Exception as e:
            log(f"   ❌ 오류: {old_link} — {e}")
            failed += 1

        time.sleep(0.5)

    log(f"\n✅ 완료 — 수정 {fixed}건 / 실패 {failed}건")

    with open("fix_numbered_slugs_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
