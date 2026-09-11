import os, requests, time

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com",       "KHEALTH365COM",        519),
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM",   95),
    ("https://koreainvest365.com",     "KOREAINVEST365COM",     53),
    ("https://ki-korea.com",           "KIKOREACOM",            27),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM",  80),
    ("https://kfinance365.com",        "KFINANCE365COM",        78),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM",       89),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM",     47),
    ("https://krealestate365.com",     "KREALESTATE365COM",     24),
    ("https://ktech365.com",           "KTECH365COM",           51),
    ("https://kskin365.com",           "KSKIN365COM",           72),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM",    40),
    ("https://kworld365.com",          "KWORLD365COM",           4),
    ("https://k-trip365.com",          "KTRIP365COM",          444),
    ("https://k-visa365.com",          "KVISA365COM",           62),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM",    40),
    ("https://kstudy365.com",          "KSTUDY365COM",          51),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM",    44),
    ("https://kieca-korea.org",        "KIECAKOREAORG",         24),
    ("https://ksa-korea.org",          "KSAKOREAORG",           25),
    ("https://sis-korea.com",          "SISKOREACOM",           29),
    ("https://jobkorea365.com",        "JOBKOREA365COM",        57),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM",      64),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM",     54),
    ("https://korea365.org",           "KOREA365ORG",          111),
    ("https://koreanews365.com",       "KOREANEWS365COM",      127),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM",   131),
]

print(f"{'#':>2} {'도메인':<28} {'삭제전':>6} {'현재':>6} {'삭제됨':>7}")
print("=" * 55)

tb = tn = td = 0
for i, (url, env, before) in enumerate(SITES, 1):
    pw  = os.getenv(env, "")
    dom = url.replace("https://","")
    if not pw:
        print(f"{i:>2} {dom:<28} {before:>6} {'?':>6} {'?':>7}")
        continue
    try:
        r = requests.get(url + "/wp-json/wp/v2/posts",
                        auth=(WP_USER, pw),
                        params={"per_page":1,"status":"publish"},
                        timeout=10)
        if r.status_code == 200:
            now     = int(r.headers.get("X-WP-Total", 0))
            deleted = before - now
            tb += before; tn += now; td += deleted
            flag = " <<< 긴급" if now < 20 else ""
            print(f"{i:>2} {dom:<28} {before:>6} {now:>6} {deleted:>7}{flag}")
        else:
            print(f"{i:>2} {dom:<28} {before:>6} {'ERR':>6} {r.status_code:>7}")
    except:
        print(f"{i:>2} {dom:<28} {before:>6} {'ERR':>6} {'?':>7}")
    time.sleep(0.3)

print("=" * 55)
print(f"{'합계':<30} {tb:>6} {tn:>6} {td:>7}")
