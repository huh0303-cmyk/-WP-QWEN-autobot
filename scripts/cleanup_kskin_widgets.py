import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

TO_DELETE = ["block-7", "block-8", "block-9", "block-10", "block-11", "block-12", "block-13"]

log = []
for wid in TO_DELETE:
    r = requests.delete(f"{base}/wp-json/wp/v2/widgets/{wid}", auth=(WP_USER, pw),
                         params={"force": "true"}, timeout=25)
    log.append({"id": wid, "status": r.status_code})

with open("kskin365_widgets_cleanup.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
