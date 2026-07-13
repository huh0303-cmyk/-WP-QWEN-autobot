import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, pick_best_category

log = []

for site_url in ["https://jobinkorea365.com", "https://jobkoreaglobal.com"]:
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")

    r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 100, "categories": 1, "status": "publish",
                              "_fields": "id,title,meta"}, timeout=30)
    uncategorized = r.json() if r.status_code == 200 else []

    for p in uncategorized:
        pid = p["id"]
        title = p.get("title", {}).get("rendered", "")
        meta_obj = p.get("meta", {}) or {}
        keyword = meta_obj.get("rank_math_focus_keyword", "") or title
        kw = keyword.split(",")[0].strip()

        new_cat = pick_best_category(site_url, pw, kw, title)
        pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                             json={"categories": [new_cat]}, timeout=20)
        log.append({"site": site_url, "id": pid, "title": title[:40],
                     "new_cat_id": new_cat, "status": pr.status_code})

with open("recat_uncategorized_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
print(f"\n총 {len(log)}개 재분류")
