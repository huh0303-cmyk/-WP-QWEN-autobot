#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
submit_sitemaps.py — 27개 사이트 전체 검색엔진 등록
Google / Bing / Yandex / Naver / Daum(Kakao) / DuckDuckGo
+ IndexNow 전체 URL 일괄 제출
"""
import os, requests, time

WP_USER      = "huh0303@gmail.com"
INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "")

SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
    ("https://koreamedicaltour.com",    "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",      "KOREAINVEST365COM"),
    ("https://ki-korea.com",            "KIKOREACOM"),
    ("https://koreainsurance365.com",   "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",         "KFINANCE365COM"),
    ("https://koreataxnlaw.com",        "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",      "KOREACRYPTO365COM"),
    ("https://krealestate365.com",      "KREALESTATE365COM"),
    ("https://ktech365.com",            "KTECH365COM"),
    ("https://kskin365.com",            "KSKIN365COM"),
    ("https://oliveyoungkorea.com",     "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",           "KWORLD365COM"),
    ("https://k-trip365.com",           "KTRIP365COM"),
    ("https://k-visa365.com",           "KVISA365COM"),
    ("https://koreawedding365.com",     "KOREAWEDDING365COM"),
    ("https://kstudy365.com",           "KSTUDY365COM"),
    ("https://studyinkorea365.com",     "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",         "KIECAKOREAORG"),
    ("https://ksa-korea.org",           "KSAKOREAORG"),
    ("https://sis-korea.com",           "SISKOREACOM"),
    ("https://jobkorea365.com",         "JOBKOREA365COM"),
    ("https://jobinkorea365.com",       "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",      "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",            "KOREA365ORG"),
    ("https://koreanews365.com",        "KOREANEWS365COM"),
    ("https://theseouljournal.com",     "THESEOULJOURNALCOM"),
]

# 사이트맵 ping 엔진
PING_ENGINES = {
    "Google":  "https://www.google.com/ping?sitemap=",
    "Bing":    "https://www.bing.com/ping?sitemap=",
    "Yandex":  "https://webmaster.yandex.com/ping?sitemap=",
    "Naver":   "https://searchadvisor.naver.com/xml/submit?url=",
}

# IndexNow 엔진
INDEXNOW_ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
    "https://searchadvisor.naver.com/indexnow",
    "https://yandex.com/indexnow",
]

total_ping_ok = 0
total_ping_fail = 0
total_urls_submitted = 0

print("=" * 60)
print("27개 사이트 전체 검색엔진 등록 시작")
print("=" * 60)

for site_url, env_key in SITES:
    wp_pass = os.getenv(env_key, "")
    domain  = site_url.replace("https://","").replace("http://","")
    print(f"\n{'─'*50}")
    print(f"🌐 {site_url}")

    # ── 사이트맵 ping ────────────────────────────────────
    sitemaps = [
        f"{site_url}/sitemap_index.xml",
        f"{site_url}/post-sitemap.xml",
    ]
    for sm in sitemaps:
        enc = requests.utils.quote(sm, safe="")
        for engine, ping_url in PING_ENGINES.items():
            try:
                r = requests.get(f"{ping_url}{enc}", timeout=10)
                status = r.status_code
                if status in (200, 201, 202):
                    total_ping_ok += 1
                    print(f"  ✅ {engine} ← {sm.split('/')[-1]}: {status}")
                else:
                    total_ping_fail += 1
                    print(f"  ⚠️ {engine} ← {sm.split('/')[-1]}: {status}")
            except Exception as e:
                total_ping_fail += 1
                print(f"  ❌ {engine}: {str(e)[:60]}")
            time.sleep(0.2)

    # ── IndexNow 처리 ────────────────────────────────────
    if not INDEXNOW_KEY:
        print(f"  ⚠️ INDEXNOW_KEY 없음 → IndexNow 스킵")
        continue

    if not wp_pass:
        print(f"  ⚠️ WP 패스워드 없음 → URL 수집 스킵")
        # 사이트맵 URL만으로 IndexNow
        urls = sitemaps
    else:
        # WP REST API로 실제 발행된 URL 수집
        urls = []
        base = f"{site_url}/wp-json/wp/v2"
        auth = (WP_USER, wp_pass)
        page = 1
        while True:
            try:
                r = requests.get(f"{base}/posts", auth=auth,
                                 params={"per_page": 100, "page": page,
                                         "status": "publish", "_fields": "link"},
                                 timeout=20)
                if r.status_code != 200 or not r.json():
                    break
                posts = r.json()
                for p in posts:
                    if p.get("link"):
                        urls.append(p["link"])
                if len(posts) < 100:
                    break
                page += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"  ⚠️ URL 수집 오류: {e}")
                break

    if not urls:
        print(f"  ⚠️ URL 없음 → 스킵")
        continue

    print(f"  📋 URL {len(urls)}개 수집")

    # IndexNow 배치 전송 (100개씩)
    batch_size = 100
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i+batch_size]
        payload = {
            "host": domain,
            "key": INDEXNOW_KEY,
            "keyLocation": f"{site_url}/{INDEXNOW_KEY}.txt",
            "urlList": batch
        }
        for endpoint in INDEXNOW_ENDPOINTS:
            try:
                r = requests.post(endpoint, json=payload,
                                  headers={"Content-Type": "application/json"},
                                  timeout=15)
                eng = endpoint.split('/')[2]
                print(f"  IndexNow [{eng}] {len(batch)}개: HTTP {r.status_code}")
            except Exception as e:
                print(f"  ⚠️ IndexNow {endpoint}: {str(e)[:50]}")
        total_urls_submitted += len(batch)
        time.sleep(0.5)

    time.sleep(1)

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"   사이트맵 ping 성공: {total_ping_ok}회")
print(f"   사이트맵 ping 실패: {total_ping_fail}회")
print(f"   IndexNow URL 제출: {total_urls_submitted}개")
if not INDEXNOW_KEY:
    print(f"   ⚠️ IndexNow 미실행 — Secret 'INDEXNOW_KEY' 추가 필요")
print(f"{'='*60}")
