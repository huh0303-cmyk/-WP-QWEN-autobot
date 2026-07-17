import os, sys, json, time, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, pick_best_category

TARGETS = [
    "https://oliveyoungkorea.com", "https://theseouljournal.com",
    "https://krealestate365.com", "https://koreamedicaltour.com",
    "https://koreacrypto365.com", "https://korea365.org",
]

log = []
for site_url in TARGETS:
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")

    r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 25, "orderby": "date", "order": "desc",
                              "_fields": "id,title,categories,meta"}, timeout=35)
    posts = r.json() if r.status_code == 200 else []

    site_log = {"site": site_url, "changed": 0, "total": len(posts), "entries": []}
    for p in posts:
        title = p["title"]["rendered"]
        meta_obj = p.get("meta", {}) or {}
        kw = meta_obj.get("rank_math_focus_keyword", "") or title
        new_cat = pick_best_category(site_url, pw, kw.split(",")[0].strip(), title)
        old_cats = p.get("categories", [])
        if new_cat in old_cats:
            continue
        pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                             json={"categories": [new_cat]}, timeout=20)
        if pr.status_code in (200, 201):
            site_log["changed"] += 1
        site_log["entries"].append({"id": p["id"], "title": title[:40],
                                      "new_cat_id": new_cat, "status": pr.status_code})
        time.sleep(0.5)

    log.append(site_log)
    print(f"{site_url}: {site_log['changed']}/{site_log['total']} 변경")
    with open("recat_worst_result.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
