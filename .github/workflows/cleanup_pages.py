#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_pages.py — 각 사이트 중복/불필요 페이지 정리
- 중복 페이지 삭제 (오래된 것 휴지통)
- Best Deals, Tools 등 불필요 페이지 삭제
- 최신 privacy-policy / disclaimer / contact / about 1개씩만 유지
"""

import os, time, requests
from datetime import datetime

WP_USER = "huh0303@gmail.com"

SITES_CONFIG = [
    {"url": "https://k-health365.com",        "wp_pass_env": "KHEALTH365COM"},
    {"url": "https://koreamedicaltour.com",    "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://koreainvest365.com",      "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://ki-korea.com",            "wp_pass_env": "KIKOREACOM"},
    {"url": "https://koreainsurance365.com",   "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://kfinance365.com",         "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreataxnlaw.com",        "wp_pass_env": "KOREATAXNLAWCOM"},
    {"url": "https://koreacrypto365.com",      "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://krealestate365.com",      "wp_pass_env": "KREALESTATE365COM"},
    {"url": "https://ktech365.com",            "wp_pass_env": "KTECH365COM"},
    {"url": "https://kskin365.com",            "wp_pass_env": "KSKIN365COM"},
    {"url": "https://oliveyoungkorea.com",     "wp_pass_env": "OLIVEYOUNGKOREACOM"},
    {"url": "https://kworld365.com",           "wp_pass_env": "KWORLD365COM"},
    {"url": "https://k-trip365.com",           "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",           "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreawedding365.com",     "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://kstudy365.com",           "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea365.com",     "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kieca-korea.org",         "wp_pass_env": "KIECAKOREAORG"},
    {"url": "https://ksa-korea.org",           "wp_pass_env": "KSAKOREAORG"},
    {"url": "https://sis-korea.com",           "wp_pass_env": "SISKOREACOM"},
    {"url": "https://jobkorea365.com",         "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobinkorea365.com",       "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",      "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://korea365.org",            "wp_pass_env": "KOREA365ORG"},
    {"url": "https://koreanews365.com",        "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",     "wp_pass_env": "THESEOULJOURNALCOM"},
]

# 유지할 슬러그 (이 4개만 남기고 중복은 정리)
KEEP_SLUGS = {"privacy-policy", "disclaimer", "contact", "about"}

# 무조건 삭제할 슬러그 키워드
DELETE_KEYWORDS = [
    "best-deals", "best_deals", "tools", "sample-page",
    "cart", "checkout", "my-account", "shop",
]

def get_all_pages(site_url, wp_pass):
    pages = []
    page_num = 1
    while True:
        try:
            r = requests.get(
                f"{site_url}/wp-json/wp/v2/pages",
                auth=(WP_USER, wp_pass),
                params={"per_page": 100, "page": page_num,
                        "_fields": "id,slug,title,status,date,modified",
                        "status": "any"},
                timeout=10
            )
            if r.status_code != 200 or not r.json():
                break
            batch = r.json()
            pages.extend(batch)
            if len(batch) < 100:
                break
            page_num += 1
        except Exception as e:
            print(f"  ⚠️ 페이지 조회 오류: {e}")
            break
    return pages

def trash_page(site_url, wp_pass, page_id, title):
    try:
        r = requests.delete(
            f"{site_url}/wp-json/wp/v2/pages/{page_id}",
            auth=(WP_USER, wp_pass),
            timeout=10
        )
        if r.status_code in (200, 201):
            print(f"  🗑️  휴지통: [{page_id}] {title}")
            return True
        else:
            print(f"  ❌ 삭제 실패 [{page_id}] {title}: HTTP {r.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ 삭제 오류 [{page_id}] {title}: {e}")
        return False

def normalize_slug(slug):
    """슬러그 정규화 — about-us → about, contact-us → contact 등"""
    slug = slug.lower().strip()
    if slug in ("about-us", "about_us", "about-2", "about-3", "사이트-소개"):
        return "about"
    if slug in ("contact-us", "contact-2", "contact-3", "문의하기"):
        return "contact"
    if slug in ("privacy-policy-2", "privacy-policy-3", "개인정보처리방침",
                "privacy-policy-draft", "privacy"):
        return "privacy-policy"
    if slug in ("disclaimer-2", "면책공고"):
        return "disclaimer"
    return slug

def process_site(site):
    site_url = site["url"]
    wp_pass  = os.getenv(site["wp_pass_env"], "")

    if not wp_pass:
        print(f"  ⚠️  비밀번호 없음 → 스킵")
        return 0

    pages = get_all_pages(site_url, wp_pass)
    if not pages:
        print(f"  ℹ️  페이지 없음")
        return 0

    print(f"  📋 전체 페이지 {len(pages)}개 조회됨")

    # 슬러그별 그룹핑
    groups = {}
    for p in pages:
        raw_slug  = p.get("slug", "")
        norm      = normalize_slug(raw_slug)
        title     = p.get("title", {}).get("rendered", raw_slug)
        pid       = p["id"]
        modified  = p.get("modified", p.get("date", ""))
        status    = p.get("status", "")

        groups.setdefault(norm, []).append({
            "id": pid, "slug": raw_slug, "title": title,
            "modified": modified, "status": status, "norm": norm
        })

    trash_count = 0

    for norm_slug, group in groups.items():
        # 1. 무조건 삭제 키워드
        if any(kw in norm_slug for kw in DELETE_KEYWORDS):
            for p in group:
                if p["status"] != "trash":
                    if trash_page(site_url, wp_pass, p["id"], p["title"]):
                        trash_count += 1
                    time.sleep(0.5)
            continue

        # 2. 핵심 4개 슬러그 — 최신 1개만 유지, 나머지 삭제
        if norm_slug in KEEP_SLUGS:
            if len(group) <= 1:
                continue
            # 최신순 정렬 (modified 기준)
            group_sorted = sorted(group, key=lambda x: x["modified"], reverse=True)
            keep = group_sorted[0]
            print(f"  ✅ 유지: [{keep['id']}] {keep['title']} ({keep['modified'][:10]})")
            for p in group_sorted[1:]:
                if p["status"] != "trash":
                    if trash_page(site_url, wp_pass, p["id"], p["title"]):
                        trash_count += 1
                    time.sleep(0.5)
            continue

        # 3. draft 상태 불필요 페이지
        for p in group:
            if p["status"] == "draft":
                if trash_page(site_url, wp_pass, p["id"], p["title"]):
                    trash_count += 1
                time.sleep(0.5)

    return trash_count


def main():
    print(f"\n{'='*60}")
    print(f"🧹 페이지 정리 시작 — {len(SITES_CONFIG)}개 사이트")
    print(f"   유지: privacy-policy / disclaimer / contact / about (각 최신 1개)")
    print(f"   삭제: 중복 / draft / best-deals / tools / sample-page 등")
    print(f"{'='*60}\n")

    total = 0
    for idx, site in enumerate(SITES_CONFIG, 1):
        print(f"\n[{idx:02d}/{len(SITES_CONFIG)}] {site['url']}")
        count = process_site(site)
        total += count
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"✅ 완료 — 총 {total}개 페이지 휴지통 처리")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
