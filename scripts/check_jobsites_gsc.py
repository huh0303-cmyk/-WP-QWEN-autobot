#!/usr/bin/env python3
"""GSC에서 job 계열 3개 사이트의 실시간 색인 커버리지를 직접 조회한다.
읽기 전용."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_site_traffic import get_gsc_token, gsc_get, get_index_coverage  # noqa: E402

SITES = [
    "https://jobinkorea365.com",
    "https://jobkorea365.com",
    "https://jobkoreaglobal.com",
]


def main():
    token = get_gsc_token()
    accessible_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])} \
        if accessible_resp.status_code == 200 else set()
    print(f"GSC 접근 가능 사이트 목록에 포함된 속성: {len(accessible)}개 전체 중 확인")

    for site_url in SITES:
        domain = site_url.replace("https://", "")
        domain_property = f"sc-domain:{domain}"
        if site_url in accessible:
            query_site = site_url
        elif domain_property in accessible:
            query_site = domain_property
        else:
            print(f"\n{domain}: GSC 속성 자체가 없음(등록 안 됐거나 권한 없음)")
            continue

        coverage, err = get_index_coverage(token, query_site)
        print(f"\n{domain} (property={query_site})")
        if coverage:
            print(f"  색인됨: {coverage.get('indexed')}")
            print(f"  전체: {coverage}")
        else:
            print(f"  조회 실패: {err}")


if __name__ == "__main__":
    main()
