#!/usr/bin/env python3
import os, requests

WP_USER = "huh0303@gmail.com"
SITES = [
    ("https://kworld365.com",  "KWORLD365COM"),
    ("https://kieca-korea.org","KIECAKOREAORG"),
]

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw:
        print(f"❌ {site_url} — Secret없음"); continue

    base = f"{site_url}/wp-json/wp/v2"
    auth = (WP_USER, pw)
    print(f"\n🌐 {site_url}")

    # 1. WP REST 접근
    r = requests.get(f"{base}/posts?per_page=3&_fields=id,title,date",
                     auth=auth, timeout=15)
    print(f"  REST 접근: HTTP {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        print(f"  글 수 확인: {len(posts)}개")
        for p in posts:
            t = p.get("title",{}).get("rendered","")
            print(f"    [{p['id']}] {t[:50]} | {p['date'][:10]}")
    else:
        print(f"  오류: {r.text[:200]}")

    # 2. 사이트 도달 가능
    try:
        r2 = requests.head(f"{site_url}/wp-json/", auth=auth, timeout=8)
        print(f"  wp-json: HTTP {r2.status_code}")
        deny = r2.headers.get("x-deny-reason","없음")
        print(f"  WAF deny: {deny}")
    except Exception as e:
        print(f"  연결오류: {e}")

    # 3. 테스트 글 발행
    test = {"title":"[TEST] kworld 발행 테스트","content":"테스트","status":"draft"}
    r3 = requests.post(f"{base}/posts", auth=auth, json=test, timeout=15)
    print(f"  테스트 발행: HTTP {r3.status_code}")
    if r3.status_code in (200,201):
        pid = r3.json().get("id")
        print(f"  ✅ 발행 성공 (draft id={pid})")
        # 즉시 삭제
        requests.delete(f"{base}/posts/{pid}", auth=auth,
                       params={"force":"true"}, timeout=10)
        print(f"  🗑️  테스트 글 삭제")
    else:
        print(f"  ❌ 발행 실패: {r3.text[:200]}")
