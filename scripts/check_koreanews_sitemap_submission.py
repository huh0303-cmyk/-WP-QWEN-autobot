#!/usr/bin/env python3
"""koreanews365.com에 GSC 사이트맵이 실제로 '제출'되어 있는지 확인.
사이트맵 URL이 접속 가능한 것과 GSC에 등록된 건 별개 문제."""
import sys
import os
import json

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_site_traffic import get_gsc_token, gsc_get  # noqa: E402

SITE = "https://koreanews365.com"


def main():
    token = get_gsc_token()
    accessible_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])} \
        if accessible_resp.status_code == 200 else set()
    domain = SITE.replace("https://", "")
    domain_property = f"sc-domain:{domain}"
    prop = SITE if SITE in accessible else (domain_property if domain_property in accessible else None)
    print(f"사용 property: {prop}")
    if not prop:
        print("GSC 속성 없음")
        return

    encoded = requests.utils.quote(prop, safe="")
    r = gsc_get(token, f"/sites/{encoded}/sitemaps")
    print(f"HTTP {r.status_code}")
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
