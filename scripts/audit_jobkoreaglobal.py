import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
pw = os.getenv(site["wp_pass_env"], "")

out = []
page = 1
while True:
    r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 20, "page": page, "status": "publish",
                              "_fields": "id,title,content,excerpt,link,date,tags"}, timeout=30)
    if r.status_code != 200:
        break
    batch = r.json()
    if not batch:
        break
    for p in batch:
        title = p.get("title", {}).get("rendered", "")
        content = p.get("content", {}).get("rendered", "")
        plain = re.sub(r'<[^>]+>', ' ', content)
        plain = re.sub(r'\s+', ' ', plain).strip()
        out.append({
            "id": p["id"], "title": title, "date": p.get("date"), "link": p.get("link"),
            "text_len": len(plain), "text_preview": plain[:200],
            "img_count": len(re.findall(r'<img[\s>]', content, re.IGNORECASE)),
            "h2_count": len(re.findall(r'<h2[\s>]', content, re.IGNORECASE)),
            "table_count": len(re.findall(r'<table[\s>]', content, re.IGNORECASE)),
        })
    if len(batch) < 20:
        break
    page += 1

with open("jobkoreaglobal_full.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"총 {len(out)}개 글")
