#!/usr/bin/env python3
"""26개 활성 사이트 전체에 post-sitemap.xml / page-sitemap.xml / feed/ /
sitemap_index.xml을 GSC Sitemaps API로 자동 제출한다(수동 클릭 대체).
읽기전용 스코프가 아니라 쓰기 가능한 webmasters 스코프로 별도 토큰 발급."""
import json
import os
import time

import jwt
import requests

from site_registry import ACTIVE_SITES

GSC_KEY_JSON = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
CANDIDATE_PATHS = ["sitemap_index.xml", "post-sitemap.xml", "page-sitemap.xml", "feed/"]


def get_write_token():
    key_data = json.loads(GSC_KEY_JSON)
    now = int(time.time())
    payload = {
        "iss": key_data["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }
    token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
    r = requests.post("https://oauth2.googleapis.com/token",
                       data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                             "assertion": token}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def gsc_get(token, path):
    return requests.get(f"https://www.googleapis.com/webmasters/v3{path}",
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)


def gsc_put(token, path):
    return requests.put(f"https://www.googleapis.com/webmasters/v3{path}",
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)


def main():
    if not GSC_KEY_JSON:
        raise SystemExit("Missing GSC_SERVICE_ACCOUNT_JSON")
    token = get_write_token()
    accessible_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])} \
        if accessible_resp.status_code == 200 else set()

    total_submitted = total_skipped = 0
    for site_url, env_key, lifecycle in ACTIVE_SITES:
        domain = site_url.replace("https://", "")
        domain_property = f"sc-domain:{domain}"
        prop = site_url if site_url in accessible else (domain_property if domain_property in accessible else None)
        if not prop:
            print(f"\n{domain}: GSC 속성 없음, 스킵")
            continue

        print(f"\n{domain}")
        enc_prop = requests.utils.quote(prop, safe="")
        for path in CANDIDATE_PATHS:
            full_url = f"{site_url}/{path}"
            try:
                check = requests.head(full_url, timeout=10, allow_redirects=True)
                if check.status_code >= 400:
                    print(f"  스킵({check.status_code}): {path}")
                    total_skipped += 1
                    continue
            except Exception as e:
                print(f"  스킵(접속실패): {path} - {e}")
                total_skipped += 1
                continue
            enc_sitemap = requests.utils.quote(full_url, safe="")
            r = gsc_put(token, f"/sites/{enc_prop}/sitemaps/{enc_sitemap}")
            ok = r.status_code in (200, 204)
            print(f"  {'제출완료' if ok else f'실패({r.status_code})'}: {path}")
            if ok:
                total_submitted += 1
            time.sleep(0.5)

    print(f"\n\n=== 완료: 제출 {total_submitted}건 / 스킵 {total_skipped}건 ===")


if __name__ == "__main__":
    main()
