#!/usr/bin/env python3
import os, requests, time

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM", "")

if not pw:
    print("NO PASSWORD"); exit(1)

auth     = (WP_USER, pw)
all_urls = []
page     = 1

print(f"URL 수집 시작: {SITE}")
while True:
    r = requests.get(
        f"{SITE}/wp-json/wp/v2/posts",
        auth=auth,
        params={"per_page": 100, "page": page,
                "status": "publish", "_fields": "link"},
        timeout=20
    )
    if r.status_code != 200 or not r.json():
        break
    posts = r.json()
    for p in posts:
        if p.get("link"):
            all_urls.append(p["link"].strip())
    print(f"  페이지 {page}: {len(posts)}개 (누적 {len(all_urls)}개)")
    if len(posts) < 100:
        break
    page += 1
    time.sleep(0.3)

print(f"\n총 {len(all_urls)}개 URL")

# 10,000개씩 출력 (IndexNow URL 전송용)
chunk = all_urls[:10000]
print("\n=== INDEXNOW_URLS_START ===")
for u in chunk:
    print(u)
print("=== INDEXNOW_URLS_END ===")

# IndexNow 직접 전송
KEY = os.getenv("INDEXNOW_KEY", "907ae08aa52b45239490ed2407df835d")
ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
    "https://searchadvisor.naver.com/indexnow",
    "https://yandex.com/indexnow",
]
batch_size = 100
submitted  = 0
for i in range(0, len(all_urls), batch_size):
    batch   = all_urls[i:i+batch_size]
    payload = {
        "host": "k-health365.com",
        "key":  KEY,
        "keyLocation": f"{SITE}/{KEY}.txt",
        "urlList": batch
    }
    for ep in ENDPOINTS:
        try:
            r2 = requests.post(ep, json=payload,
                               headers={"Content-Type": "application/json"},
                               timeout=15)
            eng = ep.split('/')[2]
            print(f"  [{eng}] {len(batch)}개: HTTP {r2.status_code}")
        except Exception as e:
            print(f"  [{ep}] 오류: {e}")
    submitted += len(batch)
    time.sleep(0.5)

print(f"\n✅ IndexNow {submitted}개 URL 전송 완료")
