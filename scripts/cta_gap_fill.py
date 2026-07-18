import os, sys, time, random, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_cta_html

MARKER = 'class="cta-box"'
TARGETS = ["https://ktech365.com", "https://k-trip365.com",
           "https://koreawedding365.com", "https://jobkoreaglobal.com"]

log = []
for site_url in TARGETS:
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")
    lang = site.get("lang", "en")
    cta_html = build_cta_html(site_url, lang)

    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                          params={"per_page": 10, "orderby": "date", "order": "desc",
                                  "status": "publish", "_fields": "id,content"}, timeout=30)
        posts = r.json() if r.status_code == 200 else []
    except Exception as e:
        log.append({"site": site_url, "error": str(e)})
        continue

    for p in posts:
        content = p.get("content", {}).get("rendered", "")
        if MARKER in content:
            continue
        try:
            pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                                 json={"content": content + cta_html}, timeout=25)
            log.append({"site": site_url, "id": p["id"], "status": pr.status_code})
        except Exception as e:
            log.append({"site": site_url, "id": p["id"], "error": str(e)})
        time.sleep(0.5)

with open("cta_gap_fill_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
