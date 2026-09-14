#!/usr/bin/env python3
"""koreanews365.com 실제 글 URL 몇 개를 GSC urlInspection API로 직접 조회해서
구글이 왜 색인 안 했는지 진짜 이유(verdict/coverageState)를 확인한다.
읽기 전용."""
import sys
import os
import json
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_site_traffic import get_gsc_token, gsc_get  # noqa: E402

SITE = "https://koreanews365.com"


def inspect(tok, prop, url):
    r = requests.post(
        "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        json={"inspectionUrl": url, "siteUrl": prop}, timeout=30)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
    s = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
    return {
        "verdict": s.get("verdict"),
        "coverageState": s.get("coverageState"),
        "robotsTxtState": s.get("robotsTxtState"),
        "indexingState": s.get("indexingState"),
        "pageFetchState": s.get("pageFetchState"),
        "lastCrawlTime": s.get("lastCrawlTime"),
        "googleCanonical": s.get("googleCanonical"),
        "userCanonical": s.get("userCanonical"),
        "sitemap": s.get("sitemap"),
        "referringUrls": s.get("referringUrls"),
    }


def main():
    token = get_gsc_token()
    accessible_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])} \
        if accessible_resp.status_code == 200 else set()
    domain = SITE.replace("https://", "")
    domain_property = f"sc-domain:{domain}"
    prop = SITE if SITE in accessible else (domain_property if domain_property in accessible else None)
    if not prop:
        print("GSC 속성 없음")
        return

    r = requests.get(f"{SITE}/wp-json/wp/v2/posts",
                      params={"per_page": 8, "status": "publish", "orderby": "date", "order": "desc",
                              "_fields": "id,link,date"}, timeout=30)
    posts = r.json()

    for p in posts:
        result = inspect(token, prop, p["link"])
        print(f"\n{p['link']} (발행일 {p['date'][:10]})")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        time.sleep(1)


if __name__ == "__main__":
    main()
