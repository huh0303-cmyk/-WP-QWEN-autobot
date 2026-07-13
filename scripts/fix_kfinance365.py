import os, sys, re, time, random, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import (
    SITES_CONFIG, WP_USER, build_diverse_title, pick_best_category,
    get_multiple_images, build_img_html
)

site = next(s for s in SITES_CONFIG if s["url"] == "https://kfinance365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]
lang = site.get("lang", "en")
theme = site["theme"]

posts, page = [], 1
while True:
    r = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 20, "page": page, "status": "publish",
                              "_fields": "id,title,content,meta"}, timeout=30)
    if r.status_code != 200: break
    batch = r.json()
    if not batch: break
    posts.extend(batch)
    if len(batch) < 20: break
    page += 1

log = []
for p in posts:
    pid = p["id"]
    old_title = p.get("title", {}).get("rendered", "")
    content = p.get("content", {}).get("rendered", "")
    meta_obj = p.get("meta", {}) or {}
    keyword = meta_obj.get("rank_math_focus_keyword", "") or old_title
    kw = keyword.split(",")[0].strip()
    # "◇ By 이름" 같은 깨진 제목이면 키워드가 사실상 없는 것이므로 본문 앞부분에서 대체 키워드 시도
    if re.match(r'^[◇\s]*By\s', kw, re.IGNORECASE) or len(kw) < 4:
        plain = re.sub(r'<[^>]+>', ' ', content)
        kw = re.sub(r'\s+', ' ', plain).strip()[:40] or "Korea finance guide"

    new_title = build_diverse_title(kw, lang, site_url=base)
    new_cat = pick_best_category(base, pw, kw, old_title)

    payload = {"title": new_title, "categories": [new_cat]}

    if len(re.findall(r'<img[\s>]', content, re.IGNORECASE)) == 0:
        imgs = get_multiple_images(kw, count=2, theme=theme)
        if imgs:
            payload["content"] = build_img_html(imgs, kw) + content

    r2 = requests.patch(f"{base}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw), json=payload, timeout=25)
    log.append({"id": pid, "old_title": old_title[:45], "new_title": new_title[:45],
                 "cat_id": new_cat, "img_added": "content" in payload, "status": r2.status_code})
    time.sleep(random.uniform(1.2, 2.0))

    if len(log) % 15 == 0:
        with open("kfinance365_fix_result.json", "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

with open("kfinance365_fix_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(f"총 {len(log)}개 처리")
