import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://k-health365.com")
pw = os.getenv(site["wp_pass_env"], "")
r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 3, "status": "publish", "_fields": "id,title,meta"}, timeout=20)
print("status:", r.status_code)
print(json.dumps(r.json(), ensure_ascii=False, indent=2)[:1500])
