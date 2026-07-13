import os, sys, time, random, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title, pick_best_category

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkorea365.com")
pw = os.getenv(site["wp_pass_env"], "")
lang = site.get("lang", "ko")

posts, page = [], 1
while True:
    r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 20, "page": page, "status": "publish",
                              "_fields": "id,title,meta,categories"}, timeout=30)
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
    meta_obj = p.get("meta", {}) or {}
    keyword = meta_obj.get("rank_math_focus_keyword", "") or old_title
    kw = keyword.split(",")[0].strip()

    new_title = build_diverse_title(kw, lang, site_url=site["url"])
    new_cat = pick_best_category(site["url"], pw, kw, old_title)

    payload = {"title": new_title, "categories": [new_cat]}
    try:
        r = requests.patch(f"{site['url']}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                            json=payload, timeout=20)
        log.append({"id": pid, "old_title": old_title[:40], "new_title": new_title[:40],
                     "cat_id": new_cat, "status": r.status_code})
    except Exception as e:
        log.append({"id": pid, "error": str(e)})

    time.sleep(random.uniform(0.8, 1.5))
    if len(log) % 10 == 0:
        with open("jobkorea365_retitle_result.json", "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

with open("jobkorea365_retitle_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(f"총 {len(log)}개 처리")
