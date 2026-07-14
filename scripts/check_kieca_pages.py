import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kieca-korea.org")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                  params={"per_page": 50, "_fields": "id,title,content,link,status"}, timeout=25)
pages = r.json() if r.status_code == 200 else []
out = [{"id": p["id"], "title": p["title"]["rendered"], "link": p.get("link"),
        "status": p.get("status"), "content": p.get("content", {}).get("rendered", "")} for p in pages]

with open("kieca_pages_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
