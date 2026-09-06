#!/usr/bin/env python3
"""One-shot GSC diagnosis for a single property: sitemap processing status
(errors/warnings/last fetch, not just "submitted OK") plus real Search
Analytics clicks. Submitting a sitemap always returns 200 whether Google
actually likes it or not - this reads back what Google did with it.

Usage: python scripts/gsc_sitemap_diagnosis.py https://k-health365.com/
"""
import json
import sys
import time

import jwt
import requests

GSC_KEY_JSON = __import__("os").environ.get("GSC_SERVICE_ACCOUNT_JSON", "")


def get_token():
    key_data = json.loads(GSC_KEY_JSON)
    now = int(time.time())
    payload = {
        "iss": key_data["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }
    assertion = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
    r = requests.post("https://oauth2.googleapis.com/token",
                       data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
                       timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def gsc_get(token, path):
    return requests.get(f"https://www.googleapis.com/webmasters/v3{path}",
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)


def gsc_post(token, path, body):
    return requests.post(f"https://www.googleapis.com/webmasters/v3{path}",
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                          json=body, timeout=20)


def main():
    if not GSC_KEY_JSON:
        raise SystemExit("Missing GSC_SERVICE_ACCOUNT_JSON")
    site_url = sys.argv[1] if len(sys.argv) > 1 else "https://k-health365.com/"
    domain = site_url.rstrip("/").replace("https://", "").replace("http://", "")
    token = get_token()

    sites_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl"): s.get("permissionLevel") for s in sites_resp.json().get("siteEntry", [])} \
        if sites_resp.status_code == 200 else {}
    print("=== 접근 가능한 GSC 속성 (전체) ===")
    for url, perm in accessible.items():
        print(f"  {url} ({perm})")

    domain_property = f"sc-domain:{domain}"
    prop = site_url if site_url in accessible else (domain_property if domain_property in accessible else None)
    print(f"\n=== {domain} 사용 속성: {prop or '접근 불가'} ===")
    if not prop:
        return

    enc = requests.utils.quote(prop, safe="")
    sm_resp = gsc_get(token, f"/sites/{enc}/sitemaps")
    sitemaps = sm_resp.json().get("sitemap", []) if sm_resp.status_code == 200 else []
    print(f"\n=== 등록된 사이트맵 {len(sitemaps)}개 ===")
    for sm in sitemaps:
        print(json.dumps(sm, ensure_ascii=False, indent=2))

    print("\n=== 최근 검색 실적 (Search Analytics, 최근 확정치) ===")
    body = {"startDate": "2026-08-01", "endDate": "2026-09-05", "dimensions": ["date"], "rowLimit": 40}
    sa = gsc_post(token, f"/sites/{enc}/searchAnalytics/query", body)
    print(sa.status_code, json.dumps(sa.json(), ensure_ascii=False)[:2000])

    print("\n=== URL 검사 (홈페이지) ===")
    # URL Inspection lives on a different API (searchconsole v1, not webmasters v3).
    ui = requests.post(
        "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"inspectionUrl": site_url, "siteUrl": prop}, timeout=20,
    )
    print(ui.status_code, json.dumps(ui.json(), ensure_ascii=False, indent=2)[:3000])


if __name__ == "__main__":
    main()
