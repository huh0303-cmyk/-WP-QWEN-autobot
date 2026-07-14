import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://k-health365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

out = {}

r = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"slug": "post"}, timeout=20)
out["post_slug_check"] = r.json()

suspects = ["post-58-2", "post-118-2", "post-62-2", "post-94-2-2", "post-37-2", "post-87-2"]
out["numbered_slug_posts"] = []
for slug in suspects:
    r2 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                       params={"slug": slug, "_fields": "id,title,slug,link,meta"}, timeout=20)
    m = r2.json()
    if m:
        p = m[0]
        out["numbered_slug_posts"].append({
            "id": p["id"], "slug": p["slug"], "title": p["title"]["rendered"], "link": p["link"],
            "focus_keyword": (p.get("meta") or {}).get("rank_math_focus_keyword", "")
        })
    else:
        out["numbered_slug_posts"].append({"slug": slug, "found": False})

with open("khealth_slug_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
