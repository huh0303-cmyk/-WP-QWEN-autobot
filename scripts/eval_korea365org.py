import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://korea365.org")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]
result = {"site": base}

# 1) 페이지 (중복 여부 포함 전체 나열)
r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                  params={"per_page": 50, "_fields": "id,title,link,status"}, timeout=25)
pages = r.json() if r.status_code == 200 else []
result["pages_found"] = [{"id": p["id"], "title": p["title"]["rendered"], "link": p.get("link")} for p in pages]
titles_lower = [p["title"]["rendered"].lower() for p in pages]
result["has_privacy_policy"] = any("privacy" in t for t in titles_lower)
result["has_about"] = any("about" in t for t in titles_lower)
result["has_contact"] = any("contact" in t for t in titles_lower)

# 2) ads.txt / robots.txt
try:
    r2 = requests.get(f"{base}/ads.txt", timeout=15)
    result["ads_txt_status"] = r2.status_code
    result["ads_txt_content"] = r2.text[:200] if r2.status_code == 200 else None
except Exception as e:
    result["ads_txt_error"] = str(e)
try:
    r5 = requests.get(f"{base}/robots.txt", timeout=15)
    result["robots_status"] = r5.status_code
except Exception as e:
    result["robots_error"] = str(e)

# 3) 전체 발행글
posts, page_n = [], 1
while True:
    r3 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                       params={"per_page": 50, "page": page_n, "status": "publish",
                               "_fields": "id,title,content,date,categories"}, timeout=30)
    if r3.status_code != 200: break
    batch = r3.json()
    if not batch: break
    posts.extend(batch)
    if len(batch) < 50: break
    page_n += 1

lens, dup_titles, img_counts = [], {}, []
for p in posts:
    content = p.get("content", {}).get("rendered", "")
    plain = re.sub(r'<[^>]+>', ' ', content)
    plain = re.sub(r'\s+', ' ', plain).strip()
    lens.append(len(plain))
    img_counts.append(len(re.findall(r'<img[\s>]', content, re.IGNORECASE)))
    t = p["title"]["rendered"].lower().strip()
    dup_titles[t] = dup_titles.get(t, 0) + 1

result["total_posts"] = len(posts)
result["avg_content_length"] = sum(lens)//len(lens) if lens else 0
result["min_content_length"] = min(lens) if lens else 0
result["posts_under_1500chars"] = sum(1 for l in lens if l < 1500)
result["duplicate_titles"] = {k: v for k, v in dup_titles.items() if v > 1}
result["posts_with_zero_images"] = sum(1 for c in img_counts if c == 0)
result["avg_images_per_post"] = round(sum(img_counts)/len(img_counts), 1) if img_counts else 0
result["first_post_date"] = min(p["date"] for p in posts) if posts else None
result["last_post_date"] = max(p["date"] for p in posts) if posts else None

# 4) 카테고리 분포
rc = requests.get(f"{base}/wp-json/wp/v2/categories", auth=(WP_USER, pw), params={"per_page": 100}, timeout=20)
if rc.status_code == 200:
    result["categories"] = [{"id": c["id"], "name": c["name"], "count": c["count"]} for c in rc.json()]

with open("eval_korea365org.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
