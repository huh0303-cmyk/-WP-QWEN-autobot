import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

out = {}
for url in ["https://k-health365.com", "https://jobkorea365.com", "https://kstudy365.com",
            "https://koreamedicaltour.com", "https://k-visa365.com"]:
    site = next(s for s in SITES_CONFIG if s["url"] == url)
    pw = os.getenv(site["wp_pass_env"], "")
    r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 3, "orderby": "date", "order": "desc",
                              "_fields": "id,title,date"}, timeout=25)
    out[url] = r.json() if r.status_code == 200 else r.text[:200]

with open("publish_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
