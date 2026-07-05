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

def fix(url, pw):
    dom = url.replace("https://","")
    base = url + "/wp-json/wp/v2"
    auth = (WP_USER, pw)

    # 퍼머링크 3회 재저장
    for _ in range(3):
        requests.post(base + "/settings", auth=auth,
                     json={"permalink_structure": "/%postname%/"}, timeout=10)
        time.sleep(1)

    requests.post(base + "/settings", auth=auth,
                 json={"blog_public": True}, timeout=8)

    time.sleep(3)

    # sitemap 확인
    sm_ok = False
    for path in ["/sitemap_index.xml", "/sitemap.xml"]:
        try:
            r = requests.get(url + path, timeout=10,
                           headers={"User-Agent": "Googlebot/2.1"})
            if r.status_code == 200 and len(r.text) > 100:
                sm_ok = True
                enc = requests.utils.quote(url + path)
                requests.get("https://www.google.com/ping?sitemap=" + enc, timeout=5)
                requests.get("https://www.bing.com/ping?sitemap=" + enc, timeout=5)
                print("OK " + dom + path)
                break
        except:
            pass

    if not sm_ok:
        print("FAIL " + dom)

print("=" * 55)
print("sitemap fix 27 sites")
print("=" * 55)
ok = skip = 0
for url, env in SITES:
    pw = os.getenv(env, "")
    if not pw:
        print("SKIP " + url.replace("https://",""))
        skip += 1
        continue
    fix(url, pw)
    ok += 1
    time.sleep(0.3)

print("Done: " + str(ok) + " / skip: " + str(skip))
