import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

out = {}
for url in ["https://k-health365.com", "https://jobkorea365.com", "https://kstudy365.com",
            "https://koreamedicaltour.com", "https://k-visa365.com"]:
    site = next(s for s in SITES_CONFIG if s["url"] == url)
    pw = os.getenv(site["wp_pass_env"], "")

    rc = requests.get(f"{url}/wp-json/wp/v2/categories", auth=(WP_USER, pw),
                       params={"per_page": 100}, timeout=20)
    cat_map = {c["id"]: c["name"] for c in rc.json()} if rc.status_code == 200 else {}

    r = requests.get(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 5, "orderby": "date", "order": "desc",
                              "_fields": "id,title,categories,meta"}, timeout=25)
    posts = r.json() if r.status_code == 200 else []
    entries = []
    for p in posts:
        cats = [cat_map.get(c, f"?{c}") for c in p.get("categories", [])]
        kw = (p.get("meta") or {}).get("rank_math_focus_keyword", "")
        entries.append({"title": p["title"]["rendered"], "categories": cats, "keyword": kw})
    out[url] = {"all_categories": list(cat_map.values()), "recent_posts": entries}

with open("category_match_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
