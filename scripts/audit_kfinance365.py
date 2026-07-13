import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kfinance365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]
result = {"site": base}

# 페이지
r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                  params={"per_page": 50, "_fields": "id,title,link"}, timeout=25)
pages = r.json() if r.status_code == 200 else []
result["pages_found"] = [{"id": p["id"], "title": p["title"]["rendered"], "link": p.get("link")} for p in pages]
from collections import Counter
tc = Counter(p["title"]["rendered"].strip().lower() for p in pages)
result["duplicate_pages"] = {k: v for k, v in tc.items() if v > 1}

# ads.txt/robots
try:
    r2 = requests.get(f"{base}/ads.txt", timeout=15)
    result["ads_txt_status"] = r2.status_code
    result["ads_txt_content"] = r2.text[:200] if r2.status_code == 200 else None
except Exception as e:
    result["ads_txt_error"] = str(e)

# 전체 글 - 제목 전부 출력 + 이상신호 탐지
posts, page_n = [], 1
while True:
    r3 = requests.get(f"{base}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                       params={"per_page": 50, "page": page_n, "status": "publish",
                               "_fields": "id,title,content,date,meta,categories"}, timeout=30)
    if r3.status_code != 200: break
    batch = r3.json()
    if not batch: break
    posts.extend(batch)
    if len(batch) < 50: break
    page_n += 1

all_titles = []
weird_titles = []
zero_img = []
short_content = []
NAME_ONLY_RE = re.compile(r'^[A-Z][a-z]+\s[A-Z][a-z]+$')  # "Firstname Lastname" 패턴만 있는 제목

for p in posts:
    title = p["title"]["rendered"]
    content = p.get("content", {}).get("rendered", "")
    plain = re.sub(r'<[^>]+>', ' ', content)
    plain = re.sub(r'\s+', ' ', plain).strip()
    all_titles.append({"id": p["id"], "date": p.get("date"), "title": title, "text_len": len(plain)})

    if NAME_ONLY_RE.match(title.strip()) or len(title.strip()) < 15:
        weird_titles.append({"id": p["id"], "title": title, "text_len": len(plain)})
    if len(re.findall(r'<img[\s>]', content, re.IGNORECASE)) == 0:
        zero_img.append({"id": p["id"], "title": title[:50]})
    if len(plain) < 1500:
        short_content.append({"id": p["id"], "title": title[:50], "len": len(plain)})

result["total_posts"] = len(posts)
result["all_titles"] = all_titles
result["weird_titles"] = weird_titles
result["zero_image_count"] = len(zero_img)
result["zero_image_list"] = zero_img
result["short_content_count"] = len(short_content)
result["short_content_list"] = short_content

rc = requests.get(f"{base}/wp-json/wp/v2/categories", auth=(WP_USER, pw), params={"per_page": 100}, timeout=20)
if rc.status_code == 200:
    result["categories"] = [{"id": c["id"], "name": c["name"], "count": c["count"]} for c in rc.json()]

with open("kfinance365_audit.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"총 {len(posts)}개 글, 이상제목 {len(weird_titles)}개, 이미지없음 {len(zero_img)}개, 짧은글 {len(short_content)}개")
