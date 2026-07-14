import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

out = {}

for mid in [412, 12]:
    r = requests.get(f"{base}/wp-json/wp/v2/menu-items", auth=(WP_USER, pw),
                      params={"menus": mid, "per_page": 100}, timeout=25)
    items = r.json() if r.status_code == 200 else []
    out[f"menu_{mid}_items"] = [{"title": it.get("title", {}).get("rendered"), "url": it.get("url")} for it in items]

with open("kskin365_menu_items.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
