import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkorea365.com")
pw = os.getenv(site["wp_pass_env"], "")

# 1) 카테고리 목록
r = requests.get(f"{site['url']}/wp-json/wp/v2/categories", auth=(WP_USER, pw),
                  params={"per_page": 100}, timeout=20)
cats = [{"id": c["id"], "name": c["name"], "count": c["count"]} for c in r.json()]

# 2) 최근 글 5개 - 제목/이미지 확인
r2 = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                   params={"per_page": 5, "orderby": "date", "order": "desc",
                           "status": "publish", "_fields": "id,title,content,date"}, timeout=25)
recent = []
for p in r2.json():
    content = p.get("content", {}).get("rendered", "")
    img_count = len(re.findall(r'<img[\s>]', content, re.IGNORECASE))
    recent.append({"id": p["id"], "date": p.get("date"), "title": p["title"]["rendered"], "img_count": img_count})

result = {"categories": cats, "recent_posts": recent}
with open("jobkorea365_check.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
