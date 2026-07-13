import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

targets = ["https://koreamedicaltour.com", "https://k-visa365.com"]
out = []
for site in SITES_CONFIG:
    if site["url"] not in targets:
        continue
    pw = os.getenv(site["wp_pass_env"], "")
    page = 1
    while True:
        r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                          params={"per_page": 20, "page": page, "status": "publish",
                                  "_fields": "id,title,content,link,date"}, timeout=30)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            content = p.get("content", {}).get("rendered", "")
            title = p.get("title", {}).get("rendered", "")
            if "2024" in title or "2024" in content:
                idx = content.find("2024")
                ctx = content[max(0,idx-60):idx+60]
                out.append({"site": site["url"], "id": p["id"], "title": title,
                             "date": p.get("date"), "context": ctx})
        if len(batch) < 20:
            break
        page += 1

with open("ctx_2024.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
