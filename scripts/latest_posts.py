import os, requests

WP_USER = "huh0303@gmail.com"
_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
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

for site_url, secret in SITES:
    pw = os.environ.get(secret)
    if not pw:
        log(f"{site_url} | ⚠️ 시크릿없음")
        continue
    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=auth,
                          params={"per_page": 1, "orderby": "date", "order": "desc",
                                  "_fields": "id,date,link,title,meta"}, timeout=20)
        if r.status_code == 200 and r.json():
            p = r.json()[0]
            title = p.get("title", {}).get("rendered", "")
            score = p.get("meta", {}).get("rank_math_seo_score", "N/A")
            log(f"{site_url}")
            log(f"  제목: {title[:50]}")
            log(f"  링크: {p.get('link')}")
            log(f"  발행일: {p.get('date')}")
            log(f"  SEO점수: {score}")
            log("")
        else:
            log(f"{site_url} | ⚠️ 조회실패 status={r.status_code}\n")
    except Exception as e:
        log(f"{site_url} | ⚠️ 오류: {e}\n")

with open("latest_posts_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
