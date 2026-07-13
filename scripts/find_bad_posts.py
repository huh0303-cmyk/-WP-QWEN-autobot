import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobinkorea365.com")
pw = os.getenv(site["wp_pass_env"], "")
r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 100, "status": "publish", "_fields": "id,title,content,link"}, timeout=30)
out = []
for p in r.json():
    title = p.get("title", {}).get("rendered", "")
    if title.lower().startswith(("certainly!", "sure,", "here is", "here's")):
        content = p.get("content", {}).get("rendered", "")
        out.append({"id": p["id"], "title": title, "link": p.get("link"), "content_preview": content[:500]})
with open("bad_posts.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
