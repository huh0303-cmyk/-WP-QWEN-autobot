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

for url, env in SITES:
    pw = os.getenv(env, "")
    dom = url.replace("https://", "")
    if not pw:
        print(f"SKIP {dom}")
        continue

    base = f"{url}/wp-json/wp/v2"
    auth = (WP_USER, pw)

    # 퍼머링크 3회 재저장
    for i in range(3):
        requests.post(f"{base}/settings", auth=auth,
                     json={"permalink_structure": "/%postname%/"}, timeout=10)
        time.sleep(1)

    requests.post(f"{base}/settings", auth=auth,
                 json={"blog_public": True}, timeout=8)

    time.sleep(3)

    # sitemap 확인
    found = False
    for path in ["/sitemap_index.xml", "/sitemap.xml"]:
        try:
            r = requests.get(f"{url}{path}", timeout=10,
                           headers={"User-Agent": "Googlebot/2.1"},
                           allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 50:
                print(f"OK {dom}{path}")
                sm = requests.utils.quote(f"{url}{path}")
                requests.get(f"https://www.google.com/ping?sitemap={sm}", timeout=5)
                found = True
                break
        except:
            pass

    if not found:
        print(f"FAIL {dom}")

    time.sleep(0.5)

print("DONE")
