#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_low_seo_posts.py
─────────────────────────────────────────────────────────────
27개 사이트 전체를 대상으로, 실제로 삭제하지 않고
SEO 90점 미만 글이 몇 건씩 있는지만 집계합니다.
(delete_low_seo_posts와 동일한 판정 로직, 삭제 없음)
"""

import os, time
import requests

WP_USER = "huh0303@gmail.com"
MIN_SCORE = 90

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


def count_site(site_url, wp_pass):
    base = f"{site_url}/wp-json/wp/v2"
    total, low, untracked = 0, 0, 0
    low_samples = []
    page = 1
    while True:
        try:
            r = requests.get(f"{base}/posts",
                             auth=(WP_USER, wp_pass),
                             params={"per_page": 100, "page": page, "status": "publish",
                                     "_fields": "id,title,meta,link"},
                             timeout=20)
            if r.status_code != 200:
                break
            posts = r.json()
            if not posts:
                break
        except Exception as e:
            print(f"   ⚠️ 오류: {e}")
            break

        for post in posts:
            total += 1
            meta = post.get("meta", {})
            score = meta.get("rank_math_seo_score", "")
            try:
                score_int = int(float(str(score))) if score else 0
            except Exception:
                score_int = 0

            if score_int == 0:
                untracked += 1
            elif score_int < MIN_SCORE:
                low += 1
                if len(low_samples) < 5:
                    t = post.get("title", {}).get("rendered", "")[:40]
                    low_samples.append(f"{score_int}점 - {t}")

        if len(posts) < 100:
            break
        page += 1
        time.sleep(0.2)

    return total, low, untracked, low_samples


def main():
    lines = []
    def log(m):
        print(m); lines.append(m)

    log("=" * 70)
    log(f"📊 SEO {MIN_SCORE}점 미만 글 집계 (삭제 없음, 카운트만)")
    log("=" * 70)

    grand_total = grand_low = grand_untracked = 0
    rows = []

    for site in SITES:
        url = site["url"]
        wp_pass = os.getenv(site["wp_pass_env"], "")
        if not wp_pass:
            log(f"⚠️ {url}: 비밀번호 없음 → 건너뜀")
            continue
        total, low, untracked, samples = count_site(url, wp_pass)
        grand_total += total
        grand_low += low
        grand_untracked += untracked
        rows.append((url, total, low, untracked))
        log(f"\n🌐 {url}")
        log(f"   전체 {total}건 | 90점 미만 {low}건 | 점수 미기록 {untracked}건")
        for s in samples:
            log(f"     - {s}")

    log("\n" + "=" * 70)
    log("📋 요약표 (사이트 | 전체 | 90점미만 | 점수미기록)")
    log("=" * 70)
    for url, total, low, untracked in sorted(rows, key=lambda r: -r[2]):
        log(f"  {url:32s} | {total:4d}건 | {low:4d}건 미달 | {untracked:4d}건 미기록")

    log(f"\n총합 — 전체 {grand_total}건 | 90점 미만 {grand_low}건 | 점수 미기록 {grand_untracked}건")

    with open("count_low_seo_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
