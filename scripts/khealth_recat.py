import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, pick_best_category

site = next(s for s in SITES_CONFIG if s["url"] == "https://k-health365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

r = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 20, "orderby": "date", "order": "desc",
                          "_fields": "id,title,categories,meta"}, timeout=30)
posts = r.json() if r.status_code == 200 else []

log = []
for p in posts:
    title = p["title"]["rendered"]
    meta_obj = p.get("meta", {}) or {}
    kw = meta_obj.get("rank_math_focus_keyword", "") or title
    new_cat = pick_best_category(base, pw, kw.split(",")[0].strip(), title)
    old_cats = p.get("categories", [])
    if new_cat in old_cats:
        continue
    pr = requests.patch(f"{base}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                         json={"categories": [new_cat]}, timeout=20)
    log.append({"id": p["id"], "title": title[:40], "new_cat_id": new_cat, "status": pr.status_code})

with open("khealth_recat_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
