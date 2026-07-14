import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

r = requests.get(f"{base}/wp-json/wp/v2/menu-locations", auth=(WP_USER, pw), timeout=20)
locs = r.json() if r.status_code == 200 else {}

r2 = requests.get(f"{base}/wp-json/wp/v2/menus", auth=(WP_USER, pw), timeout=20)
menus = r2.json() if r2.status_code == 200 else []

out = {"locations": locs, "menus": menus}
with open("kskin365_menu_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)
print(json.dumps(out, ensure_ascii=False, indent=2, default=str)[:2000])
