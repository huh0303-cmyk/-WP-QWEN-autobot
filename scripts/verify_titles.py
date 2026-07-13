import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
pw = os.getenv(site["wp_pass_env"], "")
r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 47, "status": "publish", "_fields": "title"}, timeout=30)
titles = [p["title"]["rendered"] for p in r.json()]
with open("verify_titles.json", "w", encoding="utf-8") as f:
    json.dump(titles, f, ensure_ascii=False, indent=2)
for t in titles:
    print(t)
