import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

REQUIRED = {"about": "About Us", "contact": "Contact Us", "disclaimer": "Disclaimer", "privacy-policy": "Privacy Policy"}

rp = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                   params={"per_page": 50, "_fields": "id,title,slug,link"}, timeout=25)
pages = rp.json() if rp.status_code == 200 else []

log = []
for menu_id in [412, 12]:
    for slug, label in REQUIRED.items():
        match = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
                 slug.replace("-", " ") in p["title"]["rendered"].strip().lower()]
        if not match:
            log.append({"menu": menu_id, "slug": slug, "status": "page_not_found"})
            continue
        mi = requests.post(f"{base}/wp-json/wp/v2/menu-items", auth=(WP_USER, pw),
                            json={"title": label, "url": match[0]["link"], "menus": menu_id,
                                  "status": "publish"}, timeout=25)
        log.append({"menu": menu_id, "slug": slug, "status": mi.status_code})

with open("kskin365_menu_fix_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
