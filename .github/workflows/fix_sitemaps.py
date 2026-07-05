#!/usr/bin/env python3
import os, requests, time

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-trip365.com",       "KTRIP365COM"),
    ("https://ki-korea.com",        "KIKOREACOM"),
    ("https://kfinance365.com",     "KFINANCE365COM"),
    ("https://kskin365.com",        "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kstudy365.com",       "KSTUDY365COM"),
    ("https://kieca-korea.org",     "KIECAKOREAORG"),
    ("https://ksa-korea.org",       "KSAKOREAORG"),
    ("https://ktech365.com",        "KTECH365COM"),
    ("https://kworld365.com",       "KWORLD365COM"),
    ("https://koreanews365.com",    "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
    ("https://kstudy365.com",       "KSTUDY365COM"),
    ("https://jobkoreaglobal.com",  "JOBKOREAGLOBALCOM"),
    ("https://jobinkorea365.com",   "JOBINKOREA365COM"),
    ("https://koreainsurance365.com","KOREAINSURANCE365COM"),
    ("https://sis-korea.com",       "SISKOREACOM"),
]

# 중복 제거
seen = set()
SITES = [(u,e) for u,e in SITES if u not in seen and not seen.add(u)]

def fix(url, pw):
    dom  = url.replace("https://","")
    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)

    # 1. 퍼머링크 2번 재저장 (가장 중요)
    for i in range(2):
        r = requests.post(f"{base}/settings", auth=auth,
                         json={"permalink_structure": "/%postname%/"},
                         timeout=10)
        time.sleep(1)

    # 2. blog_public 확인
    requests.post(f"{base}/settings", auth=auth,
                 json={"blog_public": True}, timeout=8)

    # 3. sitemap 확인
    time.sleep(2)
    ok = False
    for path in ["/sitemap_index.xml", "/sitemap.xml"]:
        try:
            r2 = requests.get(f"{url}{path}", timeout=8,
                            headers={"User-Agent":"Googlebot/2.1"})
            if r2.status_code == 200:
                print(f"  ✅ {dom}{path} ({r2.status_code})")
                ok = True
                # Google ping
                sm = requests.utils.quote(f"{url}{path}")
                requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=5)
                break
        except: pass
    if not ok:
        print(f"  ❌ {dom} sitemap 없음")

print("="*55)
print("sitemap 복구 — 퍼머링크 재저장")
print("="*55)
for url, env in SITES:
    pw = os.getenv(env,"")
    if not pw:
        print(f"  ⏭️  {url.replace('https://','')}")
        continue
    fix(url, pw)
    time.sleep(0.5)
print("\n✅ 완료!")
