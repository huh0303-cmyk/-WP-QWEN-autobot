#!/usr/bin/env python3
"""oliveyoungkorea.com GSC 색인/실적 실시간 확인 (읽기 전용)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_site_traffic import get_gsc_token, gsc_get, get_index_coverage, latest_daily_stats  # noqa: E402

SITE = "https://oliveyoungkorea.com"


def main():
    token = get_gsc_token()
    accessible_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])} \
        if accessible_resp.status_code == 200 else set()

    domain = SITE.replace("https://", "")
    domain_property = f"sc-domain:{domain}"
    if SITE in accessible:
        query_site = SITE
    elif domain_property in accessible:
        query_site = domain_property
    else:
        print(f"{domain}: GSC 속성 없음")
        return

    coverage, err = get_index_coverage(token, query_site)
    print(f"coverage: {coverage} / err: {err}")
    stats, err2 = latest_daily_stats(token, query_site)
    print(f"latest daily stats: {stats} / err: {err2}")


if __name__ == "__main__":
    main()
