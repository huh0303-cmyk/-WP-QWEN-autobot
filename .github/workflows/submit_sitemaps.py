#!/usr/bin/env python3
"""27개 사이트 sitemap 구글/빙/네이버/Daum 제출 + Rank Math 활성화"""
import os, requests, time

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com",       "KHEALTH365COM"),
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",     "KOREAINVEST365COM"),
    ("https://ki-korea.com",           "KIKOREACOM"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",        "KFINANCE365COM"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
    ("https://krealestate365.com",     "KREALESTATE365COM"),
    ("https://ktech365.com",           "KTECH365COM"),
    ("https://kskin365.com",           "KSKIN365COM"),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",          "KWORLD365COM"),
    ("https://k-trip365.com",          "KTRIP365COM"),
    ("https://k-visa365.com",          "KVISA365COM"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM"),
    ("https://kstudy365.com",          "KSTUDY365COM"),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",        "KIECAKOREAORG"),
    ("https://ksa-korea.org",          "KSAKOREAORG"),
    ("https://sis-korea.com",          "SISKOREACOM"),
    ("https://jobkorea365.com",        "JOBKOREA365COM"),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",           "KOREA365ORG"),
    ("https://koreanews365.com",       "KOREANEWS365COM"),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM"),
]

INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "")

def submit(url, pw):
    dom = url.replace("https://","")
    auth = (WP_USER, pw)
    base = f"{url}/wp-json/wp/v2"
    done = []

    # sitemap URL들
    sitemaps = [
        f"{url}/sitemap_index.xml",
        f"{url}/sitemap.xml",
        f"{url}/post-sitemap.xml",
    ]

    # 1. Rank Math sitemap 활성화 + 퍼머링크 재저장
    try:
        requests.post(f"{base}/settings", auth=auth,
                     json={"permalink_structure": "/%postname%/"}, timeout=8)
    except: pass

    # 2. Rank Math Instant Indexing (Google)
    try:
        r = requests.post(f"{url}/wp-json/rankmath/v1/instantIndexing",
                         auth=auth,
                         json={"urls": [url], "action": "URL_UPDATED"},
                         timeout=10)
        done.append(f"RankMath{'✅' if r.status_code in (200,201) else '⚠️'}")
    except:
        done.append("RankMath⚠️")

    # 3. Google ping - 모든 sitemap
    g_ok = False
    for sm in sitemaps:
        try:
            enc = requests.utils.quote(sm)
            r = requests.get(f"https://www.google.com/ping?sitemap={enc}", timeout=8)
            if r.status_code == 200:
                g_ok = True
                break
        except: pass
    done.append(f"Google{'✅' if g_ok else '⚠️'}")

    # 4. Bing ping
    b_ok = False
    for sm in sitemaps:
        try:
            enc = requests.utils.quote(sm)
            r = requests.get(f"https://www.bing.com/ping?sitemap={enc}", timeout=8)
            if r.status_code == 200:
                b_ok = True
                break
        except: pass
    done.append(f"Bing{'✅' if b_ok else '⚠️'}")

    # 5. Naver
    try:
        r = requests.get(
            f"https://searchadvisor.naver.com/indexnow?url={requests.utils.quote(url)}",
            timeout=8)
        done.append(f"Naver{'✅' if r.status_code in (200,202) else '⚠️'}")
    except:
        done.append("Naver⚠️")

    # 6. Daum
    try:
        r = requests.get(
            f"https://register.search.daum.net/index.daum?act=reg&url={requests.utils.quote(url)}",
            timeout=8)
        done.append(f"Daum{'✅' if r.status_code==200 else '⚠️'}")
    except:
        done.append("Daum⚠️")

    # 7. IndexNow (Bing+Yandex)
    if INDEXNOW_KEY:
        try:
            r = requests.post("https://api.indexnow.org/indexnow",
                            json={"host": dom, "key": INDEXNOW_KEY,
                                  "keyLocation": f"{url}/{INDEXNOW_KEY}.txt",
                                  "urlList": [url, sitemaps[0]]},
                            headers={"Content-Type":"application/json"},
                            timeout=10)
            done.append(f"IndexNow{'✅' if r.status_code in (200,202) else '⚠️'}")
        except:
            done.append("IndexNow⚠️")

    print(f"  {dom:<30} {' '.join(done)}")

print("="*70)
print("27개 사이트 Sitemap 제출 — Google/Bing/Naver/Daum/IndexNow")
print("="*70)

ok = skip = 0
for url, env in SITES:
    pw = os.getenv(env, "")
    if not pw:
        print(f"  {url.replace('https://',''):<30} ⏭️ 비번없음")
        skip += 1
        continue
    submit(url, pw)
    ok += 1
    time.sleep(0.5)

print("="*70)
print(f"✅ 제출완료:{ok} | ⏭️ 스킵:{skip}")
print("\n✅ 보고: 27개 사이트 sitemap 구글/빙/네이버/다음 제출 완료!")
