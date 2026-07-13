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
    result["pages_found"] = [{"id": p["id"], "title": p["title"]["rendered"], "link": p.get("link")} for p in pages]
    titles_lower = [p["title"]["rendered"].lower() for p in pages]
    result["has_privacy_policy"] = any("privacy" in t for t in titles_lower)
    result["has_about"] = any("about" in t for t in titles_lower)
    result["has_contact"] = any("contact" in t for t in titles_lower)
    # 중복 페이지 탐지
    from collections import Counter
    tc = Counter(titles_lower)
    result["duplicate_pages"] = {k: v for k, v in tc.items() if v > 1}

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

    lens, dup_titles, img_counts, zero_img_ids = [], {}, [], []
    for p in posts:
        content = p.get("content", {}).get("rendered", "")
        plain = re.sub(r'<[^>]+>', ' ', content)
        plain = re.sub(r'\s+', ' ', plain).strip()
        lens.append(len(plain))
        ic = len(re.findall(r'<img[\s>]', content, re.IGNORECASE))
        img_counts.append(ic)
        if ic == 0:
            zero_img_ids.append({"id": p["id"], "date": p.get("date"), "title": p["title"]["rendered"][:50]})
        t = p["title"]["rendered"].lower().strip()
        dup_titles[t] = dup_titles.get(t, 0) + 1

    result["total_posts"] = len(posts)
    result["avg_content_length"] = sum(lens)//len(lens) if lens else 0
    result["min_content_length"] = min(lens) if lens else 0
    result["posts_under_1500chars"] = sum(1 for l in lens if l < 1500)
    result["duplicate_titles"] = {k: v for k, v in dup_titles.items() if v > 1}
    result["posts_with_zero_images"] = len(zero_img_ids)
    result["zero_image_list"] = sorted(zero_img_ids, key=lambda x: x["date"])
    result["avg_images_per_post"] = round(sum(img_counts)/len(img_counts), 1) if img_counts else 0
    result["first_post_date"] = min(p["date"] for p in posts) if posts else None
    result["last_post_date"] = max(p["date"] for p in posts) if posts else None

    rc = requests.get(f"{base}/wp-json/wp/v2/categories", auth=(WP_USER, pw), params={"per_page": 100}, timeout=20)
    if rc.status_code == 200:
        result["categories"] = [{"id": c["id"], "name": c["name"], "count": c["count"]} for c in rc.json()]

    return result


if __name__ == "__main__":
    out = [evaluate(u) for u in ["https://koreainsurance365.com", "https://koreainvest365.com"]]
    with open("eval_insurance_invest.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:3000])
