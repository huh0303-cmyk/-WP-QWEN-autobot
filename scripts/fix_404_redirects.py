#!/usr/bin/env python3
import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM","")
if not pw: exit(1)
auth = (WP_USER, pw)

# 301 리다이렉트할 패턴들
redirects = [
    ("/2025/",           "starts_with"),
    ("/2026/",           "starts_with"),
    ("/p/",              "starts_with"),
    ("/feeds/",          "starts_with"),
    ("/form/",           "starts_with"),
    ("/tools/",          "starts_with"),
    ("/search/",         "starts_with"),
    (".html",            "contains"),
]

added = 0
for pattern, comparison in redirects:
    try:
        r = requests.post(
            f"{SITE}/wp-json/rankmath/v1/redirections",
            auth=auth,
            json={
                "sources": [{"pattern": pattern, "comparison": comparison}],
                "destination": SITE,
                "type": "301",
                "status": "active",
            },
            timeout=10
        )
        if r.status_code in (200, 201, 400):
            added += 1
            print(f"  ✅ {pattern} ({comparison})")
        else:
            print(f"  ❌ {pattern}: {r.status_code}")
    except Exception as e:
        print(f"  ❌ {pattern}: {e}")
    time.sleep(0.3)

print(f"\n완료: {added}개 리다이렉트 설정")
