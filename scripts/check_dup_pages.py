import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

out = []
for site_url in ["https://jobinkorea365.com", "https://jobkoreaglobal.com", "https://jobkorea365.com"]:
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")
    r = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"per_page": 50, "_fields": "id,title,link,status,content,modified"}, timeout=25)
    pages = r.json() if r.status_code == 200 else []
    for p in pages:
        content = p.get("content", {}).get("rendered", "")
        out.append({
            "site": site_url, "id": p["id"], "title": p["title"]["rendered"],
            "status": p.get("status"), "link": p.get("link"), "modified": p.get("modified"),
            "content_len": len(content)
        })

with open("dup_pages_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
