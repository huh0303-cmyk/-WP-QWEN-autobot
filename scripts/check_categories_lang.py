import os, requests

SITES = [
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM"),
    ("https://ki-korea.com",           "KIKOREACOM"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",        "KFINANCE365COM"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
    ("https://krealestate365.com",     "KREALESTATE365COM"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM"),
    ("https://ksa-korea.org",          "KSAKOREAORG"),
]
WP_USER = "huh0303@gmail.com"

_LOG = []
def log(m):
    print(m)
    _LOG.append(str(m))

for site_url, secret in SITES:
    pw = os.environ.get(secret)
    log(f"\n🌐 {site_url}")
    if not pw:
        log("  ⚠️ secret 없음")
        continue
    r = requests.get(f"{site_url}/wp-json/wp/v2/categories",
                      auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                      params={"per_page": 50}, timeout=20)
    if r.status_code != 200:
        log(f"  ⚠️ API 오류 status={r.status_code}")
        continue
    for c in r.json():
        log(f"  id={c['id']:>5} name='{c['name']}' slug={c['slug']} count={c['count']}")

with open("check_categories_lang_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
