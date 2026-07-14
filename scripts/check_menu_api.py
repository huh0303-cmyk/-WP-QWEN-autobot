import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://koreamedicaltour.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

out = {}
r = requests.get(f"{base}/wp-json/wp/v2/menus", auth=(WP_USER, pw), timeout=20)
out["menus_status"] = r.status_code
out["menus"] = r.json() if r.status_code == 200 else r.text[:300]

r2 = requests.get(f"{base}/wp-json/wp/v2/menu-items", auth=(WP_USER, pw), timeout=20)
out["menu_items_status"] = r2.status_code
out["menu_items"] = r2.json() if r2.status_code == 200 else r2.text[:300]

r3 = requests.get(f"{base}/wp-json/wp/v2/menu-locations", auth=(WP_USER, pw), timeout=20)
out["menu_locations_status"] = r3.status_code
out["menu_locations"] = r3.json() if r3.status_code == 200 else r3.text[:300]

with open("menu_api_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)
print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:3000])
