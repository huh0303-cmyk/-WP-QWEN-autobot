import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, pick_best_category, load_site_categories

tests = [
    ("https://oliveyoungkorea.com", "Beauty of Joseon review", "Beauty of Joseon sunscreen review Korean"),
    ("https://theseouljournal.com", "US-Iran diplomacy hopes", "Hopes for US-Iran diplomacy through Korea"),
    ("https://koreamedicaltour.com", "botox filler price Korea", "botox filler price Korea cosmetic"),
]

log = []
for site_url, kw, title in tests:
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")
    cats = load_site_categories(site_url, pw)
    cat_id = pick_best_category(site_url, pw, kw, title)
    cat_name = next((n for cid, n in cats if cid == cat_id), f"?{cat_id}")
    log.append({"site": site_url, "keyword": kw, "picked_cat_id": cat_id, "picked_cat_name": cat_name})

with open("cat_ai_test_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
