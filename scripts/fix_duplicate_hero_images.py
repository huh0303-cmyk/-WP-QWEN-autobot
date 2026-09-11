#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_duplicate_hero_images.py
─────────────────────────────────────────────────────────────
이미 발행된 글 중, "대표이미지(Featured Image)"와 "본문 최상단 첫 이미지"가
중복으로 나오는 예전 글들을 찾아서 본문 쪽 중복 이미지만 제거합니다.

★ 안전장치: 아래 조건을 모두 만족하는 글만 수정합니다.
   1) featured_media가 설정되어 있음 (대표이미지 있음)
   2) 본문(content) 맨 앞이 build_image_html()이 생성하는 것과
      정확히 똑같은 <figure style="margin:20px 0;padding:0;background:#f8f9fa;...
      로 시작함 (우리 코드가 만든 hero_img가 100% 확실할 때만 삭제)
   → 이 조건에 안 맞으면 절대 건드리지 않습니다.

실행: GitHub Actions에서 workflow_dispatch로 수동 실행
      (같은 저장소의 WP_PASS 환경변수/시크릿을 그대로 재사용)
"""

import os, re, time
from typing import Optional
import requests

WP_USER = "huh0303@gmail.com"

# autopost_mega.py의 SITES_CONFIG에서 url / wp_pass_env만 가져온 목록
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

# build_image_html()이 만드는 hero figure의 고유 지문 (이 정확한 문자열로 시작해야만 매치)
HERO_FIGURE_SIGNATURE = '<figure style="margin:20px 0;padding:0;background:#f8f9fa;'

# 미리보기만 하고 실제로는 수정하지 않으려면 True로 변경
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def strip_leading_duplicate_figure(content: str) -> Optional[str]:
    """본문 맨 앞이 hero figure 지문으로 시작하면 그 <figure>...</figure> 블록만 제거.
    매치되지 않으면 None 반환 (수정 대상 아님)."""
    stripped = content.lstrip()
    if not stripped.startswith(HERO_FIGURE_SIGNATURE):
        return None
    end = stripped.find("</figure>")
    if end == -1:
        return None
    end += len("</figure>")
    new_content = stripped[end:].lstrip("\n").lstrip()
    return new_content


def fix_site(site: dict) -> dict:
    url = site["url"]
    wp_pass = os.getenv(site["wp_pass_env"], "")
    stats = {"scanned": 0, "fixed": 0, "skipped": 0, "errors": 0}

    if not wp_pass:
        print(f"  ⚠️  {url}: 비밀번호 환경변수 '{site['wp_pass_env']}' 없음 → 건너뜀")
        return stats

    page = 1
    while True:
        try:
            r = requests.get(
                f"{url}/wp-json/wp/v2/posts",
                auth=(WP_USER, wp_pass),
                params={"per_page": 50, "page": page, "status": "publish",
                        "_fields": "id,link,content,featured_media"},
                timeout=20,
            )
        except Exception as e:
            print(f"  ❌ {url} 페이지 {page} 요청 실패: {e}")
            stats["errors"] += 1
            break

        if r.status_code != 200:
            if r.status_code == 400:  # 마지막 페이지 초과
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

            new_content = strip_leading_duplicate_figure(content)
            if new_content is None:
                stats["skipped"] += 1
                continue

            if DRY_RUN:
                print(f"  🔍 [DRY_RUN] 중복 발견: {link}")
                stats["fixed"] += 1
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
                else:
                    print(f"  ❌ 수정 실패 ({pr.status_code}): {link}")
                    stats["errors"] += 1
            except Exception as e:
                print(f"  ❌ 수정 요청 오류: {link} — {e}")
                stats["errors"] += 1

            time.sleep(0.5)  # WP 서버 부하 방지

        if len(posts) < 50:
            break
        page += 1
        time.sleep(1)

    return stats


def main():
    lines = []
    def log(msg):
        print(msg)
        lines.append(msg)

    log(f"{'='*60}")
    log(f"🔧 중복 이미지 일괄 수정 결과 {'(DRY_RUN — 미리보기만)' if DRY_RUN else ''}")
    log(f"{'='*60}\n")

    grand_total = {"scanned": 0, "fixed": 0, "skipped": 0, "errors": 0}

    for site in SITES:
        log(f"🌐 {site['url']}")
        stats = fix_site(site)
        for k in grand_total:
            grand_total[k] += stats[k]
        log(f"   → 스캔 {stats['scanned']}건 | 수정 {stats['fixed']}건 | "
            f"해당없음 {stats['skipped']}건 | 오류 {stats['errors']}건\n")

    log(f"{'='*60}")
    log(f"✅ 전체 완료 — 스캔 {grand_total['scanned']}건 | "
        f"수정 {grand_total['fixed']}건 | 오류 {grand_total['errors']}건")
    log(f"{'='*60}")

    with open("fix_duplicate_images_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
