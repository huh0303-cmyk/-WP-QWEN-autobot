#!/usr/bin/env python3
import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM","")
if not pw: exit(1)
auth = (WP_USER, pw)

# http:// 와 www. 리다이렉트 설정
patterns = [
    ("http://k-health365.com/",     "exact",       "https://k-health365.com/"),
    ("http://www.k-health365.com/", "exact",       "https://k-health365.com/"),
    ("https://www.k-health365.com/","exact",       "https://k-health365.com/"),
    ("http://k-health365.com",      "starts_with", "https://k-health365.com"),
    ("http://www.k-health365.com",  "starts_with", "https://k-health365.com"),
]

for pattern, comparison, destination in patterns:
    try:
        r = requests.post(
            f"{SITE}/wp-json/rankmath/v1/redirections",
            auth=auth,
            json={
                "sources": [{"pattern": pattern, "comparison": comparison}],
                "destination": destination,
                "type": "301",
                "status": "active",
            },
            timeout=10
        )
        ok = r.status_code in (200,201,400)
        print(f"  {'✅' if ok else '❌'} {pattern} → {destination}")
    except Exception as e:
        print(f"  ❌ {e}")
    time.sleep(0.3)

print("\n완료")
