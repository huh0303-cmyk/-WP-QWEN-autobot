#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_khealth_index.py
k-health365.com 완전 색인 복구
1. blog_public = True 강제
2. rank_math_robots noindex → index 전체 글 일괄 수정
3. 퍼머링크 재저장
4. Google/Bing/Yandex/Naver 사이트맵 ping
5. IndexNow 전체 URL 즉시 제출
"""
import os, requests, time, json

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM", "")
INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "")

if not pw:
    print("❌ KHEALTH365COM 없음"); exit(1)

base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

print("=" * 55)
print("k-health365.com 색인 완전 복구 시작")
print("=" * 55)

# ── 1. blog_public 확인 및 강제 설정 ──────────────────────
print("\n[1] blog_public 설정")
try:
    r = requests.get(f"{base}/settings", auth=auth, timeout=10)
    s = r.json()
    print(f"  현재 blog_public: {s.get('blog_public','unknown')}")
    r2 = requests.post(f"{base}/settings", auth=auth,
                       json={"blog_public": True}, timeout=10)
    print(f"  blog_public → True : HTTP {r2.status_code}")
except Exception as e:
    print(f"  ⚠️ {e}")

# ── 2. 전체 글 noindex → index 수정 ───────────────────────
print("\n[2] noindex 글 전수 스캔 및 수정")
page = 1
total = 0
fixed = 0
already_ok = 0
errors = 0
all_urls = []  # IndexNow용 URL 수집

while True:
    try:
        r = requests.get(f"{base}/posts", auth=auth,
                         params={"per_page": 100, "page": page,
                                 "status": "publish",
                                 "_fields": "id,link,meta"},
                         timeout=30)
        if r.status_code != 200:
            break
        posts = r.json()
        if not posts:
            break
    except Exception as e:
        print(f"  ⚠️ 페이지 {page} 조회 실패: {e}")
        break

    for p in posts:
        total += 1
        pid   = p.get("id")
        link  = p.get("link", "")
        meta  = p.get("meta", {})

        if link:
            all_urls.append(link)

        robots_val = meta.get("rank_math_robots", []) if isinstance(meta, dict) else []
        robots_str = str(robots_val).lower()

        if "noindex" in robots_str:
            try:
                patch = requests.post(
                    f"{base}/posts/{pid}", auth=auth,
                    json={"meta": {"rank_math_robots": ["index", "follow"]}},
                    timeout=15
                )
                if patch.status_code in (200, 201):
                    fixed += 1
                    print(f"  ✅ 수정 [{pid}] {link[:60]}")
                else:
                    errors += 1
                    print(f"  ❌ 실패 [{pid}] HTTP {patch.status_code}")
            except Exception as e:
                errors += 1
                print(f"  ⚠️ [{pid}] {e}")
            time.sleep(0.2)
        else:
            already_ok += 1

    print(f"  페이지 {page}: {len(posts)}개 처리")
    if len(posts) < 100:
        break
    page += 1
    time.sleep(0.5)

print(f"\n  총 {total}개 | 수정: {fixed}개 | 이미 정상: {already_ok}개 | 오류: {errors}개")

# ── 3. 퍼머링크 재저장 ────────────────────────────────────
print("\n[3] 퍼머링크 재저장")
for i in range(3):
    try:
        r = requests.post(f"{base}/settings", auth=auth,
                          json={"permalink_structure": "/%postname%/"},
                          timeout=10)
        print(f"  재저장 {i+1}/3: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ⚠️ {e}")
    time.sleep(1)

# ── 4. 사이트맵 ping (Google/Bing/Yandex/Naver) ───────────
print("\n[4] 검색엔진 사이트맵 Ping")
SITEMAPS = [
    f"{SITE}/sitemap_index.xml",
    f"{SITE}/post-sitemap.xml",
    f"{SITE}/page-sitemap.xml",
]

PING_ENGINES = {
    "Google":  "https://www.google.com/ping?sitemap=",
    "Bing":    "https://www.bing.com/ping?sitemap=",
    "Yandex":  "https://webmaster.yandex.com/ping?sitemap=",
    "Naver":   "https://searchadvisor.naver.com/xml/submit?url=",
}

for sm in SITEMAPS:
    enc = requests.utils.quote(sm, safe="")
    for engine, ping_url in PING_ENGINES.items():
        try:
            r = requests.get(f"{ping_url}{enc}", timeout=10)
            print(f"  {engine} ← {sm.split('/')[-1]}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  ⚠️ {engine} ping 실패: {e}")
        time.sleep(0.3)

# ── 5. IndexNow 즉시 색인 요청 ────────────────────────────
print("\n[5] IndexNow 즉시 색인 요청")
if not INDEXNOW_KEY:
    print("  ⚠️ INDEXNOW_KEY 없음 → IndexNow 스킵")
    print("  💡 Secret에 INDEXNOW_KEY 추가 필요")
else:
    # URL 최대 10,000개까지 한 번에 전송 가능
    batch_size = 100
    batches = [all_urls[i:i+batch_size] for i in range(0, len(all_urls), batch_size)]
    submitted = 0

    for batch in batches:
        payload = {
            "host": "k-health365.com",
            "key": INDEXNOW_KEY,
            "keyLocation": f"{SITE}/{INDEXNOW_KEY}.txt",
            "urlList": batch
        }
        for endpoint in [
            "https://api.indexnow.org/indexnow",
            "https://www.bing.com/indexnow",
            "https://searchadvisor.naver.com/indexnow",
            "https://yandex.com/indexnow",
        ]:
            try:
                r = requests.post(endpoint, json=payload,
                                  headers={"Content-Type": "application/json"},
                                  timeout=15)
                print(f"  {endpoint.split('/')[2]}: {len(batch)}개 → HTTP {r.status_code}")
            except Exception as e:
                print(f"  ⚠️ {endpoint}: {e}")
        submitted += len(batch)
        time.sleep(1)

    print(f"  IndexNow 총 {submitted}개 URL 제출 완료")

print("\n" + "=" * 55)
print("✅ k-health365.com 색인 복구 완료")
print(f"   수정된 noindex 글: {fixed}개")
print(f"   검색엔진 ping: {len(SITEMAPS) * len(PING_ENGINES)}회")
print("=" * 55)
