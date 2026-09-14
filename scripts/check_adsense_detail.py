#!/usr/bin/env python3
import os, requests, re

WP_USER = "huh0303@gmail.com"
PUB_ID  = "ca-pub-3456727916386941"

SITES = [
    ("https://k-health365.com",     "KHEALTH365COM"),
    ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM"),
    ("https://kfinance365.com",     "KFINANCE365COM"),
    ("https://k-trip365.com",       "KTRIP365COM"),
]

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    domain = site_url.replace("https://","")
    print(f"\n{'='*50}")
    print(f"{domain}")
    print(f"{'='*50}")

    r = requests.get(site_url, timeout=12,
                    headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
    html = r.text
    count = html.count(PUB_ID)
    print(f"  애드센스 코드 총 {count}개 발견")

    # 각 위치 찾기
    pos = 0
    idx = 1
    while True:
        found = html.find(PUB_ID, pos)
        if found == -1: break
        # 전후 100자
        snippet = html[max(0,found-80):found+100]
        snippet = re.sub(r'\s+',' ',snippet).strip()
        print(f"\n  [{idx}번째] 위치:{found}")
        print(f"  {snippet[:150]}")
        pos = found + 1
        idx += 1

print("\n완료")
