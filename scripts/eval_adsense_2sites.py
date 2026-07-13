import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER


def evaluate(site_url):
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")
    base = site_url
    result = {"site": site_url}

    r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"per_page": 50, "_fields": "id,title,link,status"}, timeout=25)
    pages = r.json() if r.status_code == 200 else []
    page_titles = [p["title"]["rendered"].lower() for p in pages]
    result["pages_found"] = [p["title"]["rendered"] for p in pages]
    result["has_privacy_policy"] = any("privacy" in t for t in page_titles)
    result["has_about"] = any("about" in t for t in page_titles)
    result["has_contact"] = any("contact" in t for t in page_titles)

    try:
        r2 = requests.get(f"{base}/ads.txt", timeout=15)
        result["ads_txt_status"] = r2.status_code
        result["ads_txt_content"] = r2.text[:200] if r2.status_code == 200 else None
    except Exception as e:
        result["ads_txt_error"] = str(e)

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

    lens, dup_titles = [], {}
    for p in posts:
        plain = re.sub(r'<[^>]+>', ' ', p.get("content", {}).get("rendered", ""))
        plain = re.sub(r'\s+', ' ', plain).strip()
        lens.append(len(plain))
        t = p["title"]["rendered"].lower().strip()
        dup_titles[t] = dup_titles.get(t, 0) + 1

    result["total_posts"] = len(posts)
    result["avg_content_length"] = sum(lens)//len(lens) if lens else 0
    result["min_content_length"] = min(lens) if lens else 0
    result["max_content_length"] = max(lens) if lens else 0
    result["posts_under_1500chars"] = sum(1 for l in lens if l < 1500)
    result["duplicate_titles"] = {k: v for k, v in dup_titles.items() if v > 1}
    result["first_post_date"] = min(p["date"] for p in posts) if posts else None
    result["last_post_date"] = max(p["date"] for p in posts) if posts else None

    try:
        r4 = requests.get(f"{base}/robots.txt", timeout=15)
        result["robots_status"] = r4.status_code
    except Exception as e:
        result["robots_error"] = str(e)

    # 카테고리별 분포 (미분류 비중 확인)
    rc = requests.get(f"{base}/wp-json/wp/v2/categories", auth=(WP_USER, pw),
                       params={"per_page": 100}, timeout=20)
    if rc.status_code == 200:
        result["categories"] = [{"id": c["id"], "name": c["name"], "count": c["count"]} for c in rc.json()]

    return result


if __name__ == "__main__":
    out = [evaluate(u) for u in ["https://jobinkorea365.com", "https://jobkoreaglobal.com"]]
    with open("adsense_eval_2sites.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
