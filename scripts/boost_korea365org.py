import os, sys, re, json, time, random, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import (
    SITES_CONFIG, WP_USER, get_multiple_images, build_img_html,
    load_site_categories
)

site = next(s for s in SITES_CONFIG if s["url"] == "https://korea365.org")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]
theme = site["theme"]

log = {"images_added": [], "recategorized": []}

# ── 1) 이미지 없는 글에 이미지 2장 추가 (본문 맨 앞에 삽입) ──
r = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 100, "status": "publish",
                          "_fields": "id,title,content,meta"}, timeout=30)
posts = r.json() if r.status_code == 200 else []

for p in posts:
    content = p.get("content", {}).get("rendered", "")
    if len(re.findall(r'<img[\s>]', content, re.IGNORECASE)) > 0:
        continue
    pid = p["id"]
    title = p.get("title", {}).get("rendered", "")
    meta_obj = p.get("meta", {}) or {}
    keyword = (meta_obj.get("rank_math_focus_keyword", "") or title).split(",")[0].strip()

    imgs = get_multiple_images(keyword, count=2, theme=theme)
    if not imgs:
        log["images_added"].append({"id": pid, "title": title[:40], "status": "no_images_found"})
        continue
    img_html = build_img_html(imgs, keyword)
    new_content = img_html + content
    pr = requests.patch(f"{base}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                         json={"content": new_content}, timeout=25)
    log["images_added"].append({"id": pid, "title": title[:40], "img_count": len(imgs), "status": pr.status_code})
    time.sleep(random.uniform(1.5, 2.5))

# ── 2) 개선된 카테고리 매칭 (Living/Travel 수동 힌트 보강) 으로 전체 재검토 ──
LIVING_HINTS = ["apartment","rent","housing","jeonse","wolse","visa","registration","utility",
                "utilities","bank","insurance","tax","transportation","healthcare","hospital",
                "immigration","alien","business","etiquette","negotiate","workplace","hoesik",
                "salary","payslip","commute","subway","electricity","water","internet"]
TRAVEL_HINTS = ["guide","trip","itinerary","destination","tour","hiking","island","jeju",
                "festival","temple","beach","mountain","attraction","sightseeing","travel"]

cats = load_site_categories(base, pw)
cat_by_name = {n: cid for cid, n in cats}
living_id = cat_by_name.get("Living")
travel_id = cat_by_name.get("Travel")

r2 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                   params={"per_page": 100, "status": "publish",
                           "_fields": "id,title,meta,categories"}, timeout=30)
for p in r2.json():
    pid = p["id"]
    title = p.get("title", {}).get("rendered", "")
    meta_obj = p.get("meta", {}) or {}
    keyword = (meta_obj.get("rank_math_focus_keyword", "") or title).split(",")[0].strip()
    st = f"{keyword} {title}".lower()
    cur_cats = p.get("categories", [])

    target = None
    if living_id and any(h in st for h in LIVING_HINTS):
        target = living_id
    elif travel_id and any(h in st for h in TRAVEL_HINTS):
        target = travel_id

    if target and target not in cur_cats:
        pr = requests.patch(f"{base}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                             json={"categories": [target]}, timeout=20)
        log["recategorized"].append({"id": pid, "title": title[:40], "new_cat_id": target, "status": pr.status_code})
        time.sleep(0.5)

with open("korea365org_boost_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
