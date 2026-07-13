import os, sys, re, json, time, random, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import (
    SITES_CONFIG, WP_USER, get_multiple_images, build_img_html, pick_best_category
)


def get_pw(site_url):
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    return os.getenv(site["wp_pass_env"], ""), site["theme"]


def add_images(site_url, log_key, log):
    pw, theme = get_pw(site_url)
    posts, page = [], 1
    while True:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                          params={"per_page": 50, "page": page, "status": "publish",
                                  "_fields": "id,title,content,meta"}, timeout=30)
        if r.status_code != 200: break
        batch = r.json()
        if not batch: break
        posts.extend(batch)
        if len(batch) < 50: break
        page += 1

    added = failed = 0
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
            failed += 1
            continue
        img_html = build_img_html(imgs, keyword)
        new_content = img_html + content
        pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                             json={"content": new_content}, timeout=25)
        if pr.status_code in (200, 201):
            added += 1
        else:
            failed += 1
        time.sleep(random.uniform(1.2, 2.0))

    log[log_key] = {"total_checked": len(posts), "images_added": added, "failed": failed}


def fix_uncategorized(site_url, log_key, log):
    pw, _ = get_pw(site_url)
    r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 100, "categories": 1, "status": "publish",
                              "_fields": "id,title,meta"}, timeout=30)
    entries = []
    for p in (r.json() if r.status_code == 200 else []):
        pid = p["id"]
        title = p.get("title", {}).get("rendered", "")
        meta_obj = p.get("meta", {}) or {}
        keyword = (meta_obj.get("rank_math_focus_keyword", "") or title).split(",")[0].strip()
        new_cat = pick_best_category(site_url, pw, keyword, title)
        pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                             json={"categories": [new_cat]}, timeout=20)
        entries.append({"id": pid, "new_cat_id": new_cat, "status": pr.status_code})
    log[log_key] = entries


def delete_dup_privacy(site_url, log_key, log):
    pw, _ = get_pw(site_url)
    r = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"per_page": 50, "_fields": "id,title,link"}, timeout=25)
    pages = r.json() if r.status_code == 200 else []
    pp = [p for p in pages if p["title"]["rendered"].strip().lower() == "privacy policy"]
    if len(pp) <= 1:
        log[log_key] = "no_dup"
        return
    # -2 슬러그 등 canonical이 아닌 쪽을 삭제 (link에 privacy-policy/ 로 끝나는 것 유지)
    keep = next((p for p in pp if p["link"].rstrip("/").endswith("privacy-policy")), pp[0])
    to_delete = [p for p in pp if p["id"] != keep["id"]]
    results = []
    for p in to_delete:
        dr = requests.delete(f"{site_url}/wp-json/wp/v2/pages/{p['id']}", auth=(WP_USER, pw),
                              params={"force": "true"}, timeout=20)
        results.append({"deleted_id": p["id"], "status": dr.status_code})
    log[log_key] = {"kept": keep["id"], "deleted": results}


if __name__ == "__main__":
    log = {}
    delete_dup_privacy("https://koreainvest365.com", "invest_dup_page", log)
    fix_uncategorized("https://koreainvest365.com", "invest_recat", log)
    add_images("https://koreainsurance365.com", "insurance_images", log)
    add_images("https://koreainvest365.com", "invest_images", log)

    with open("insurance_invest_fix_result.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(json.dumps(log, ensure_ascii=False, indent=2))
