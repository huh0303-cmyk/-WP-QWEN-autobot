import os, requests

WP_USER = "huh0303@gmail.com"
SITES = [
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://korea365.org", "KOREA365ORG"),
]
_LOG = []
def log(m):
    print(m); _LOG.append(str(m))

for site_url, secret in SITES:
    pw = os.environ.get(secret)
    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)
    log(f"\n{site_url}")
    r = requests.get(f"{site_url}/wp-json/wp/v2/categories", auth=auth, params={"per_page": 100}, timeout=20)
    log(f"status={r.status_code}")
    if r.status_code == 200:
        for c in r.json():
            log(f"  id={c['id']} name='{c['name']}' count={c['count']}")

with open("real_cats_debug.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
