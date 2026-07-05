#!/usr/bin/env python3
"""sitemap 404 긴급 수정 — 퍼머링크 3회 재저장"""
import os, requests, time

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://ki-korea.com",        "KIKOREACOM"),
    ("https://kfinance365.com",     "KFINANCE365COM"),
    ("https://kskin365.com",        "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://k-trip365.com",       "KTRIP365COM"),
    ("https://kstudy365.com",       "KSTUDY365COM"),
    ("https://kieca-korea.org",     "KIECAKOREAORG"),
    ("https://ksa-korea.org",       "KSAKOREAORG"),
]

def fix(url, pw):
    dom  = url.replace("https://","")
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)

    # 퍼머링크 3회 재저장 (WordPress sitemap 캐시 재생성)
    for i in range(3):
        r = requests.post(f"{base}/settings", auth=auth,
                         json={"permalink_structure": "/%postname%/"},
                         timeout=10)
        time.sleep(1)

    # 색인 허용 확인
    requests.post(f"{base}/settings", auth=auth,
                 json={"blog_public": True}, timeout=8)

    # Rank Math sitemap 강제 갱신
    try:
        requests.post(f"{url}/wp-json/rankmath/v1/sitemap/regenerate",
                     auth=auth, timeout=10)
    except: pass

    # 결과 확인
    time.sleep(3)
    sm_ok = False
    for path in ["/sitemap_index.xml", "/sitemap.xml"]:
        try:
            r2 = requests.get(f"{url}{path}", timeout=10,
                            headers={"User-Agent": "Googlebot/2.1"},
                            allow_redirects=True)
            if r2.status_code == 200 and len(r2.text) > 50:
                print(f"  ✅ {dom}{path} — 성공!")
                # Google ping
                sm = requests.utils.quote(f"{url}{path}")
                requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=5)
                requests.get(f"https://www.bing.com/ping?sitemap={sm}", timeout=5)
                sm_ok = True
                break
        except: pass

    if not sm_ok:
        print(f"  ❌ {dom} — sitemap 여전히 없음 (wp-admin에서 퍼머링크 수동 저장 필요)")

print("="*55)
print("sitemap 긴급 수정 — 퍼머링크 재저장")
print("="*55)
ok = skip = 0
for url, env in SITES:
    pw = os.getenv(env, "")
    if not pw:
        print(f"  ⏭️  {url.replace('https://','')}")
        skip += 1
        continue
    fix(url, pw)
    ok += 1
    time.sleep(0.5)

print(f"\n처리:{ok} | 스킵:{skip}")
