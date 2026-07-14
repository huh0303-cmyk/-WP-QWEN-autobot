import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]
result = {"site": base}

# 1) 필수 페이지
r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                  params={"per_page": 50, "_fields": "id,title,link,content,slug"}, timeout=25)
pages = r.json() if r.status_code == 200 else []
result["pages_found"] = [p["title"]["rendered"] for p in pages]
from collections import Counter
tc = Counter(p["title"]["rendered"].strip().lower() for p in pages)
result["duplicate_pages"] = {k: v for k, v in tc.items() if v > 1}

REQUIRED = ["about", "contact", "disclaimer", "privacy-policy"]
page_issues = []
for slug in REQUIRED:
    matches = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
               slug.replace("-", " ") in p["title"]["rendered"].strip().lower()]
    if not matches:
        page_issues.append(f"{slug}:없음")
        continue
    content = matches[0].get("content", {}).get("rendered", "")
    plain = re.sub(r'<[^>]+>', ' ', content); plain = re.sub(r'\s+', ' ', plain).strip()
    if len(plain) < 600: page_issues.append(f"{slug}:짧음({len(plain)}자)")
    if "lorem ipsum" in content.lower(): page_issues.append(f"{slug}:LOREM")
    if "huh0303@gmail.com" not in content: page_issues.append(f"{slug}:이메일없음")
result["page_issues"] = page_issues

# 2) ads.txt / robots.txt
try:
    r2 = requests.get(f"{base}/ads.txt", timeout=15)
    result["ads_txt_ok"] = (r2.status_code == 200 and "pub-" in r2.text)
except Exception:
    result["ads_txt_ok"] = False
try:
    r3 = requests.get(f"{base}/robots.txt", timeout=15)
    result["robots_ok"] = r3.status_code == 200
except Exception:
    result["robots_ok"] = False

# 3) 글 전체
posts, page_n = [], 1
while True:
    r4 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                       params={"per_page": 50, "page": page_n, "status": "publish",
                               "_fields": "id,title,content,categories,date"}, timeout=30)
    if r4.status_code != 200: break
    batch = r4.json()
    if not batch: break
    posts.extend(batch)
    if len(batch) < 50: break
    page_n += 1

lens, dup_titles, zero_img, uncategorized = [], {}, 0, 0
for p in posts:
    content = p.get("content", {}).get("rendered", "")
    plain = re.sub(r'<[^>]+>', ' ', content); plain = re.sub(r'\s+', ' ', plain).strip()
    lens.append(len(plain))
    if len(re.findall(r'<img[\s>]', content, re.IGNORECASE)) == 0: zero_img += 1
    if 1 in (p.get("categories") or []): uncategorized += 1
    t = p["title"]["rendered"].lower().strip()
    dup_titles[t] = dup_titles.get(t, 0) + 1

result["total_posts"] = len(posts)
result["avg_len"] = sum(lens)//len(lens) if lens else 0
result["min_len"] = min(lens) if lens else 0
result["thin_posts"] = sum(1 for l in lens if l < 1500)
result["zero_image_posts"] = zero_img
result["uncategorized_posts"] = uncategorized
result["duplicate_titles"] = sum(1 for v in dup_titles.values() if v > 1)

rc = requests.get(f"{base}/wp-json/wp/v2/categories", auth=(WP_USER, pw), params={"per_page": 100}, timeout=20)
result["categories"] = [{"name": c["name"], "count": c["count"]} for c in rc.json()] if rc.status_code == 200 else []

with open("kskin365_eval.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(json.dumps(result, ensure_ascii=False, indent=2))
