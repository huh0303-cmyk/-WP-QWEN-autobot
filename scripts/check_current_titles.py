import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
pw = os.getenv(site["wp_pass_env"], "")

r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 100, "status": "publish", "_fields": "id,title,date,modified"}, timeout=30)
posts = r.json()

out = [{"id": p["id"], "title": p["title"]["rendered"], "date": p["date"], "modified": p["modified"]}
       for p in posts]
out.sort(key=lambda x: x["date"], reverse=True)

with open("current_state.json", "w", encoding="utf-8") as f:
    json.dump({"total": len(out), "posts": out}, f, ensure_ascii=False, indent=2)
print(f"총 {len(out)}개")
for p in out[:15]:
    print(p["date"][:10], "| modified:", p["modified"][:16], "|", p["title"][:55])
