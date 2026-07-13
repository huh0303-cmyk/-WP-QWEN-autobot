import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, pick_best_category

site = next(s for s in SITES_CONFIG if s["url"] == "https://korea365.org")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

log = {"dup_page_delete": None, "recategorized": [], "zero_image_samples": []}

# 1) 중복 Privacy Policy(id 1677, /privacy-policy-2/) 삭제
r = requests.delete(f"{base}/wp-json/wp/v2/pages/1677", auth=(WP_USER, pw),
                     params={"force": "true"}, timeout=20)
log["dup_page_delete"] = {"id": 1677, "status": r.status_code}

# 2) 미분류(category=1) 글 재분류
r2 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                   params={"per_page": 100, "categories": 1, "status": "publish",
                            "_fields": "id,title,meta"}, timeout=30)
for p in r2.json():
    pid = p["id"]
    title = p.get("title", {}).get("rendered", "")
    meta_obj = p.get("meta", {}) or {}
    keyword = meta_obj.get("rank_math_focus_keyword", "") or title
    kw = keyword.split(",")[0].strip()
    new_cat = pick_best_category(base, pw, kw, title)
    pr = requests.patch(f"{base}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                         json={"categories": [new_cat]}, timeout=20)
    log["recategorized"].append({"id": pid, "title": title[:40], "new_cat_id": new_cat, "status": pr.status_code})

# 3) 이미지 0장인 글 샘플 5개 확인 (날짜/제목만)
r3 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                   params={"per_page": 100, "status": "publish",
                            "_fields": "id,title,content,date"}, timeout=30)
zero_img = []
for p in r3.json():
    content = p.get("content", {}).get("rendered", "")
    if len(re.findall(r'<img[\s>]', content, re.IGNORECASE)) == 0:
        zero_img.append({"id": p["id"], "date": p.get("date"), "title": p["title"]["rendered"][:50]})
log["zero_image_samples"] = sorted(zero_img, key=lambda x: x["date"])[:20]

with open("korea365org_fix_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
