import os, html, requests

WP_USER = "huh0303@gmail.com"
_LOG = []
def log(m):
    print(m); _LOG.append(str(m))

SITE_RENAMES = {
    "https://k-trip365.com": ("KTRIP365COM", {
        "Hotels & Stays": "Hotels", "AirBnB & 민박": "AirBnB",
    }),
    "https://kworld365.com": ("KWORLD365COM", {
        "K-Pop & Artists": "K-Pop", "K-Culture & Learn Korean": "Learn Korean", "Korean Life & Travel": "Travel",
    }),
    "https://korea365.org": ("KOREA365ORG", {
        "Travel & Food": "Travel",
    }),
}

for site_url, (secret, rename_map) in SITE_RENAMES.items():
    pw = os.environ.get(secret)
    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)
    log(f"\n{site_url}")
    r = requests.get(f"{site_url}/wp-json/wp/v2/categories", auth=auth, params={"per_page": 100}, timeout=20)
    cats = {html.unescape(c["name"]): c for c in r.json()}
    for old_name, new_name in rename_map.items():
        if old_name in cats:
            cid = cats[old_name]["id"]
            rr = requests.post(f"{site_url}/wp-json/wp/v2/categories/{cid}", auth=auth,
                                json={"name": new_name}, timeout=20)
            log(f"  '{old_name}'(id={cid}) -> '{new_name}': status={rr.status_code} {rr.text[:150]}")
        else:
            log(f"  ⚠️ '{old_name}' 여전히 못찾음. 실제목록: {list(cats.keys())}")

with open("rename_fix2_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
