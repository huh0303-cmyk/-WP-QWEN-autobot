#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_duplicate_hero_images_v2.py
─────────────────────────────────────────────────────────────
General-purpose duplicate-hero-image cleanup.

Unlike fix_duplicate_hero_images.py (which only matched ONE hardcoded
<figure style="margin:20px 0;padding:0;background:#f8f9fa;...> signature
from an older pipeline), this version works for ANY pipeline's HTML shape.

Logic, per published post:
  1) Skip if featured_media == 0 (no featured image set).
  2) Fetch the featured image's real source_url from /wp/v2/media/<id>.
  3) Look at the FIRST content block only (must start with <figure ...>
     or a bare <img ...> as the very first thing in the post body).
  4) If that first block's <img src="..."> equals the featured image's
     source_url (or the same file basename, to tolerate protocol/CDN
     rewrites), strip that leading block from the content.
  5) Otherwise leave the post untouched.

This directly compares real URLs instead of guessing at literal HTML,
so it catches every known figure/img variant (with or without inline
style, with or without figcaption) produced by any generation script
in this repo, including the k-trip365.com case reported 2026-09-28
(<figure><img decoding="async" src="...">…</figure> with no inline style).

Run: GitHub Actions workflow_dispatch only (reuses this repo's WP_*
secrets). Defaults to DRY_RUN=true — must be explicitly set to
DRY_RUN=false to actually PATCH posts.
"""

import os
import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests

WP_USER = "huh0303@gmail.com"

SITES = [
    {"url": "https://k-health365.com",        "wp_pass_env": "KHEALTH365COM"},
    {"url": "https://koreamedicaltour.com",   "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://koreainvest365.com",     "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://ki-korea.com",           "wp_pass_env": "KIKOREACOM"},
    {"url": "https://koreainsurance365.com",  "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://kfinance365.com",        "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreataxnlaw.com",       "wp_pass_env": "KOREATAXNLAWCOM"},
    {"url": "https://koreacrypto365.com",     "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://krealestate365.com",     "wp_pass_env": "KREALESTATE365COM"},
    {"url": "https://ktech365.com",           "wp_pass_env": "KTECH365COM"},
    {"url": "https://kskin365.com",           "wp_pass_env": "KSKIN365COM"},
    {"url": "https://oliveyoungkorea.com",    "wp_pass_env": "OLIVEYOUNGKOREACOM"},
    {"url": "https://kworld365.com",          "wp_pass_env": "KWORLD365COM"},
    {"url": "https://k-trip365.com",          "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",          "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreawedding365.com",    "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://kstudy365.com",          "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea365.com",    "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kieca-korea.org",        "wp_pass_env": "KIECAKOREAORG"},
    {"url": "https://ksa-korea.org",          "wp_pass_env": "KSAKOREAORG"},
    {"url": "https://sis-korea.com",          "wp_pass_env": "SISKOREACOM"},
    {"url": "https://jobkorea365.com",        "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobinkorea365.com",      "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",     "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://korea365.org",           "wp_pass_env": "KOREA365ORG"},
    {"url": "https://koreanews365.com",       "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",    "wp_pass_env": "THESEOULJOURNALCOM"},
]

# Only sites present in this env var (comma-separated domains) are processed.
# Empty/unset = all sites in SITES.
SITE_FILTER = {
    d.strip().lower()
    for d in os.getenv("SITE_FILTER", "").split(",")
    if d.strip()
}

# Only posts published on/after this date (YYYY-MM-DD) are scanned.
# Empty/unset = no lower bound.
SINCE_DATE = os.getenv("SINCE_DATE", "").strip()

DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"


def _basename(url: str) -> str:
    return os.path.basename(urlparse(url).path)


def strip_leading_duplicate_block(content: str, hero_url: str) -> Optional[str]:
    """If the content's first block is a <figure>...</figure> or a bare
    <img ...> that embeds hero_url (exact URL or same filename), return the
    content with that block removed. Otherwise return None (no match)."""
    stripped = content.lstrip()

    if stripped.startswith("<figure"):
        end = stripped.find("</figure>")
        if end == -1:
            return None
        end += len("</figure>")
        block = stripped[:end]
        rest = stripped[end:]
    elif stripped.startswith("<img"):
        end = stripped.find(">")
        if end == -1:
            return None
        end += 1
        block = stripped[:end]
        rest = stripped[end:]
    else:
        return None

    m = re.search(r'src="([^"]+)"', block)
    if not m:
        return None
    img_src = m.group(1)

    if img_src == hero_url or _basename(img_src) == _basename(hero_url):
        return rest.lstrip("\n").lstrip()
    return None


def fix_site(site: dict) -> dict:
    url = site["url"]
    wp_pass = os.getenv(site["wp_pass_env"], "")
    stats = {"scanned": 0, "fixed": 0, "skipped": 0, "errors": 0}
    fixed_links = []

    if not wp_pass:
        print(f"  ⚠️  {url}: 비밀번호 환경변수 '{site['wp_pass_env']}' 없음 → 건너뜀")
        return stats

    media_cache: dict[int, str] = {}

    def media_source_url(media_id: int) -> str:
        if media_id in media_cache:
            return media_cache[media_id]
        try:
            r = requests.get(
                f"{url}/wp-json/wp/v2/media/{media_id}",
                auth=(WP_USER, wp_pass),
                params={"_fields": "source_url"},
                timeout=20,
            )
            r.raise_for_status()
            src = r.json().get("source_url", "")
        except Exception:
            src = ""
        media_cache[media_id] = src
        return src

    page = 1
    while True:
        params = {
            "per_page": 50,
            "page": page,
            "status": "publish",
            "_fields": "id,link,date,content,featured_media",
        }
        if SINCE_DATE:
            params["after"] = f"{SINCE_DATE}T00:00:00"

        try:
            r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                              params=params, timeout=20)
        except Exception as e:
            print(f"  ❌ {url} 페이지 {page} 요청 실패: {e}")
            stats["errors"] += 1
            break

        if r.status_code != 200:
            if r.status_code == 400:
                break
            print(f"  ❌ {url} 페이지 {page} HTTP {r.status_code}")
            stats["errors"] += 1
            break

        posts = r.json()
        if not posts:
            break

        for post in posts:
            stats["scanned"] += 1
            post_id = post["id"]
            link = post.get("link", "")
            featured_media = post.get("featured_media", 0)
            content = post.get("content", {}).get("rendered", "")

            if not featured_media:
                stats["skipped"] += 1
                continue

            hero_url = media_source_url(featured_media)
            if not hero_url:
                stats["skipped"] += 1
                continue

            new_content = strip_leading_duplicate_block(content, hero_url)
            if new_content is None:
                stats["skipped"] += 1
                continue

            if DRY_RUN:
                print(f"  🔍 [DRY_RUN] 중복 발견: {link}")
                stats["fixed"] += 1
                fixed_links.append(link)
                continue

            try:
                pr = requests.post(
                    f"{url}/wp-json/wp/v2/posts/{post_id}",
                    auth=(WP_USER, wp_pass),
                    json={"content": new_content},
                    timeout=20,
                )
                if pr.status_code in (200, 201):
                    print(f"  ✅ 수정됨: {link}")
                    stats["fixed"] += 1
                    fixed_links.append(link)
                else:
                    print(f"  ❌ 수정 실패 ({pr.status_code}): {link}")
                    stats["errors"] += 1
            except Exception as e:
                print(f"  ❌ 수정 요청 오류: {link} — {e}")
                stats["errors"] += 1

            time.sleep(0.5)

        if len(posts) < 50:
            break
        page += 1
        time.sleep(1)

    stats["fixed_links"] = fixed_links
    return stats


def main():
    lines = []

    def log(msg):
        print(msg)
        lines.append(msg)

    log(f"{'='*60}")
    log(f"🔧 중복 대표이미지 일괄 수정 v2 {'(DRY_RUN — 미리보기만)' if DRY_RUN else '(실제 수정)'}")
    if SITE_FILTER:
        log(f"   대상 사이트 필터: {', '.join(sorted(SITE_FILTER))}")
    if SINCE_DATE:
        log(f"   발행일 필터: {SINCE_DATE} 이후")
    log(f"{'='*60}\n")

    grand_total = {"scanned": 0, "fixed": 0, "skipped": 0, "errors": 0}
    all_fixed_links = []

    for site in SITES:
        domain = urlparse(site["url"]).netloc.lower()
        if SITE_FILTER and domain not in SITE_FILTER:
            continue
        log(f"🌐 {site['url']}")
        stats = fix_site(site)
        for k in ("scanned", "fixed", "skipped", "errors"):
            grand_total[k] += stats[k]
        all_fixed_links.extend(stats.get("fixed_links", []))
        log(f"   → 스캔 {stats['scanned']}건 | 수정 {stats['fixed']}건 | "
            f"해당없음 {stats['skipped']}건 | 오류 {stats['errors']}건\n")

    log(f"{'='*60}")
    log(f"✅ 전체 완료 — 스캔 {grand_total['scanned']}건 | "
        f"수정 {grand_total['fixed']}건 | 오류 {grand_total['errors']}건")
    log(f"{'='*60}")

    if all_fixed_links:
        log("\n수정된(또는 DRY_RUN에서 발견된) 글 목록:")
        for link in all_fixed_links:
            log(f"  - {link}")

    with open("fix_duplicate_hero_images_v2_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
