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

BEFORE = {
    "k-health365.com": 519,
    "koreamedicaltour.com": 95,
    "koreainvest365.com": 53,
    "ki-korea.com": 27,
    "koreainsurance365.com": 80,
    "kfinance365.com": 78,
    "koreataxnlaw.com": 89,
    "koreacrypto365.com": 47,
    "krealestate365.com": 24,
    "ktech365.com": 51,
    "kskin365.com": 72,
    "oliveyoungkorea.com": 40,
    "kworld365.com": 4,
    "k-trip365.com": 444,
    "k-visa365.com": 62,
    "koreawedding365.com": 40,
    "kstudy365.com": 51,
    "studyinkorea365.com": 44,
    "kieca-korea.org": 24,
    "ksa-korea.org": 25,
    "sis-korea.com": 29,
    "jobkorea365.com": 57,
    "jobinkorea365.com": 64,
    "jobkoreaglobal.com": 54,
    "korea365.org": 111,
    "koreanews365.com": 127,
    "theseouljournal.com": 131,
}

print(f"{'#':>2} {'도메인':<28} {'삭제전':>6} {'현재':>6} {'삭제됨':>7}")
print("=" * 55)

total_before = total_now = total_del = 0
for i, (url, env) in enumerate(SITES, 1):
    pw  = os.getenv(env, "")
    dom = url.replace("https://","")
    before = BEFORE.get(dom, 0)

    if not pw:
        print(f"{i:>2} {dom:<28} {before:>6} {'?':>6} {'?':>7}")
        continue

    try:
        r = requests.get(url + "/wp-json/wp/v2/posts",
                        auth=(WP_USER, pw),
                        params={"per_page":1,"status":"publish"},
                        timeout=10)
        if r.status_code == 200:
            now = int(r.headers.get("X-WP-Total", 0))
            deleted = before - now
            total_before += before
            total_now    += now
            total_del    += deleted
            print(f"{i:>2} {dom:<28} {before:>6} {now:>6} {deleted:>7}")
        else:
            print(f"{i:>2} {dom:<28} {before:>6} {'ERR':>6} {r.status_code:>7}")
    except:
        print(f"{i:>2} {dom:<28} {before:>6} {'ERR':>6} {'?':>7}")
    time.sleep(0.3)

print("=" * 55)
print(f"{'합계':<30} {total_before:>6} {total_now:>6} {total_del:>7}")
