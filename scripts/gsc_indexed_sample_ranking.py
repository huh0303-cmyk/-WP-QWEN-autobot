#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gsc_indexed_sample_ranking.py
─────────────────────────────────────────────────────────────
27개 사이트 전체 URL을 다 검사하면(수천 건) GSC URL 검사 API 할당량을
바로 태워서 4~5번째 사이트부터 전부 "확인불가"로 뭉개진다(2026-08-17
실제로 겪음). 그래서 사이트당 최근 글 10개만 표본 추출해서 실제 색인
여부를 확인하고, 표본 색인율로 순위를 매긴다 — 전체를 다 안 봐도 사이트간
상대적 순위를 파악하기엔 충분하고, 할당량도 27사이트x10건=270건 정도라
안전하다.

사용법: python scripts/gsc_indexed_sample_ranking.py
필요 환경변수: GSC_SERVICE_ACCOUNT_JSON
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from daily_site_traffic import get_gsc_token, gsc_get, inspect_url_index_status, SITES  # noqa: E402

SAMPLE_SIZE = 10


def log(msg):
    print(msg, flush=True)


def resolve_query_site(domain, accessible):
    domain_property = f"sc-domain:{domain}"
    site_url = f"https://{domain}"
    if site_url in accessible:
        return site_url
    if domain_property in accessible:
        return domain_property
    return None


def fetch_sample_urls(site_url, n=SAMPLE_SIZE):
    try:
        r = requests.get(f"{site_url.rstrip('/')}/wp-json/wp/v2/posts",
                          params={"per_page": n, "_fields": "link"}, timeout=20)
        if r.status_code != 200:
            return []
        return [p["link"] for p in r.json()]
    except Exception:
        return []


def main():
    token = get_gsc_token()
    log("✅ GSC 토큰 발급 성공\n")

    r = gsc_get(token, "/sites")
    accessible = set()
    if r.status_code == 200:
        accessible = {s.get("siteUrl") for s in r.json().get("siteEntry", [])}

    results = []
    consecutive_quota_errors = 0

    for site_url in SITES:
        domain = site_url.rstrip("/").replace("https://", "")
        query_site = resolve_query_site(domain, accessible)
        if not query_site:
            results.append({"domain": domain, "indexed": None, "checked": 0, "status": "권한없음"})
            continue

        urls = fetch_sample_urls(site_url)
        if not urls:
            results.append({"domain": domain, "indexed": None, "checked": 0, "status": "글 조회 실패"})
            continue

        indexed_count = 0
        uncertain = 0
        for u in urls:
            if consecutive_quota_errors >= 5:
                uncertain += 1
                continue
            status = inspect_url_index_status(token, query_site, u)
            if status is None:
                uncertain += 1
                consecutive_quota_errors += 1
            else:
                consecutive_quota_errors = 0
                if status:
                    indexed_count += 1
            time.sleep(0.5)

        checked = len(urls) - uncertain
        results.append({
            "domain": domain, "indexed": indexed_count, "checked": checked,
            "sample": len(urls), "uncertain": uncertain,
            "status": "정상" if uncertain < len(urls) else "확인불가(할당량)",
        })
        log(f"  {domain}: 표본 {len(urls)}건 중 색인 {indexed_count}건 (확인불가 {uncertain}건)")

    def sort_key(r):
        if r["indexed"] is None or r["checked"] == 0:
            return (1, 0)
        return (0, -(r["indexed"] / r["checked"]))

    results.sort(key=sort_key)

    log("\n" + "=" * 70)
    log(f"{'순위':<4} {'도메인':<28} {'색인/표본':>10}  {'색인율':>7}  상태")
    log("=" * 70)
    for i, r in enumerate(results, 1):
        if r["indexed"] is None or r["checked"] == 0:
            log(f"{i:<4} {r['domain']:<28} {'-':>10}  {'-':>7}  {r['status']}")
        else:
            rate = f"{r['indexed']/r['checked']*100:.0f}%"
            log(f"{i:<4} {r['domain']:<28} {str(r['indexed'])+'/'+str(r['checked']):>10}  {rate:>7}  {r['status']}")


if __name__ == "__main__":
    main()
