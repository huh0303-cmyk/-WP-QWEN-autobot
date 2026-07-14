import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://theseouljournal.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                  params={"slug": "disclaimer"}, timeout=25)
pages = r.json()
if not pages:
    print("페이지 못찾음")
else:
    p = pages[0]
    out = {
        "id": p["id"],
        "title": p["title"]["rendered"],
        "template": p.get("template"),
        "meta_keys": list((p.get("meta") or {}).keys()),
        "content_preview": p.get("content", {}).get("rendered", "")[:300],
        "all_top_level_keys": list(p.keys()),
    }
    with open("disclaimer_meta_check.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
