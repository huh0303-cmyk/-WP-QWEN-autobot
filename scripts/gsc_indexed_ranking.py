#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gsc_indexed_ranking.py
─────────────────────────────────────────────────────────────
27개 사이트를 Search Console Sitemaps API로 실제 색인 페이지 수를 조회해서
많은 순으로 순위를 매긴다. GSC Sitemaps API의 sitemaps().list() 응답에
contents[].indexed 필드가 사이트맵별 실제 색인 수를 담고 있음(같은 화면이
GSC UI의 "Sitemaps" 탭에 표시되는 데이터와 동일 소스).

사용법: python scripts/gsc_indexed_ranking.py
필요 환경변수: GSC_SERVICE_ACCOUNT_JSON
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from daily_site_traffic import get_gsc_token, gsc_get, SITES  # noqa: E402


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


def main():
    token = get_gsc_token()
    log("✅ GSC 토큰 발급 성공\n")

    r = gsc_get(token, "/sites")
    accessible = set()
    if r.status_code == 200:
        accessible = {s.get("siteUrl") for s in r.json().get("siteEntry", [])}
    log(f"접근 가능한 GSC 사이트: {len(accessible)}개\n")

    results = []
    for site_url in SITES:
        domain = site_url.rstrip("/").replace("https://", "")
        query_site = resolve_query_site(domain, accessible)
        if not query_site:
            results.append({"domain": domain, "indexed": None, "submitted": None, "status": "권한없음"})
            continue

        try:
            from urllib.parse import quote
            encoded = quote(query_site, safe="")
            resp = requests.get(
                f"https://searchconsole.googleapis.com/webmasters/v3/sites/{encoded}/sitemaps",
                headers={"Authorization": f"Bearer {token}"}, timeout=20,
            )
            if resp.status_code != 200:
                results.append({"domain": domain, "indexed": None, "submitted": None,
                                 "status": f"HTTP {resp.status_code}"})
                continue
            sitemaps = resp.json().get("sitemap", [])
            total_indexed = 0
            total_submitted = 0
            for sm in sitemaps:
                for c in sm.get("contents", []):
                    total_indexed += int(c.get("indexed", 0) or 0)
                    total_submitted += int(c.get("submitted", 0) or 0)
            results.append({"domain": domain, "indexed": total_indexed,
                             "submitted": total_submitted, "status": "정상"})
        except Exception as e:
            results.append({"domain": domain, "indexed": None, "submitted": None, "status": str(e)[:80]})

    results.sort(key=lambda r: (r["indexed"] is None, -(r["indexed"] or 0)))

    log("=" * 70)
    log(f"{'순위':<4} {'도메인':<28} {'색인수':>8} {'제출수':>8}  상태")
    log("=" * 70)
    for i, r in enumerate(results, 1):
        idx = r["indexed"] if r["indexed"] is not None else "-"
        sub = r["submitted"] if r["submitted"] is not None else "-"
        log(f"{i:<4} {r['domain']:<28} {str(idx):>8} {str(sub):>8}  {r['status']}")


if __name__ == "__main__":
    main()
