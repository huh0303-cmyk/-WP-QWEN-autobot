import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

TARGETS = {
    "https://koreamedicaltour.com": "text-4",
    "https://koreainvest365.com": "text-4",
    "https://koreataxnlaw.com": "block-7",
    "https://koreacrypto365.com": "text-2",
    "https://ktech365.com": "text-3",
    "https://k-visa365.com": "text-4",
    "https://studyinkorea365.com": "text-2",
    "https://kieca-korea.org": "text-1",
    "https://jobkorea365.com": "text-2",
    "https://jobinkorea365.com": "text-1",
    "https://jobkoreaglobal.com": "text-1",
    "https://korea365.org": "text-2",
}

log = []
for site_url, widget_id in TARGETS.items():
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")
    try:
        r = requests.delete(f"{site_url}/wp-json/wp/v2/widgets/{widget_id}", auth=(WP_USER, pw),
                             params={"force": "true"}, timeout=25)
        log.append({"site": site_url, "widget": widget_id, "status": r.status_code})
    except Exception as e:
        log.append({"site": site_url, "widget": widget_id, "exception": str(e)})

with open("widget_demo_cleanup.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
