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

print(f"{'#':>2} {'도메인':<30} {'현재글수':>8}")
print("=" * 45)

total = 0
for i, (url, env) in enumerate(SITES, 1):
    pw = os.getenv(env, "")
    dom = url.replace("https://","")
    if not pw:
        print(f"{i:>2} {dom:<30} {'비번없음':>8}")
        continue
    try:
        r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                        params={"per_page":1,"status":"publish"}, timeout=10)
        if r.status_code == 200:
            count = int(r.headers.get("X-WP-Total", 0))
            total += count
            print(f"{i:>2} {dom:<30} {count:>8}")
        else:
            print(f"{i:>2} {dom:<30} {'오류':>8} ({r.status_code})")
    except:
        print(f"{i:>2} {dom:<30} {'접속불가':>8}")
    time.sleep(0.3)

print("=" * 45)
print(f"{'합계':<32} {total:>8}")
