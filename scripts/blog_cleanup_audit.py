#!/usr/bin/env python3
"""대대적 블로그 정리 작업 준비용 — 26개 활성 사이트 전체의 발행글수/구글색인수를
한 번에 집계한다. 읽기 전용."""
import sys
import os

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_site_traffic import get_gsc_token, gsc_get, get_index_coverage  # noqa: E402
from site_registry import ACTIVE_SITES  # noqa: E402


def get_total_published(site_url):
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                          params={"per_page": 1, "status": "publish"},
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code == 200:
            return int(r.headers.get("X-WP-Total", "0"))
        return f"HTTP{r.status_code}"
    except Exception as e:
        return f"ERR:{str(e)[:30]}"


def main():
    token = get_gsc_token()
    accessible_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])} \
        if accessible_resp.status_code == 200 else set()

    rows = []
    for site_url, env_key, lifecycle in ACTIVE_SITES:
        domain = site_url.replace("https://", "")
        posts = get_total_published(site_url)

        domain_property = f"sc-domain:{domain}"
        if site_url in accessible:
            query_site = site_url
        elif domain_property in accessible:
            query_site = domain_property
        else:
            rows.append((domain, posts, "GSC미등록", None))
            continue

        coverage, err = get_index_coverage(token, query_site)
        indexed = coverage.get("indexed") if coverage else f"실패:{err}"
        submitted = coverage.get("submitted_urls") if coverage else None
        rows.append((domain, posts, indexed, submitted))

    print(f"{'도메인':32s} {'발행글수':>10s} {'색인수':>10s} {'제출URL':>10s}")
    for domain, posts, indexed, submitted in rows:
        print(f"{domain:32s} {str(posts):>10s} {str(indexed):>10s} {str(submitted):>10s}")


if __name__ == "__main__":
    main()
