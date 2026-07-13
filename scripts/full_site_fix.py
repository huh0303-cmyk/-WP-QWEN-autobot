# -*- coding: utf-8 -*-
"""
지정한 사이트 하나를 전체 정비한다:
  1. 중복 Privacy Policy 페이지 정리 (canonical만 남김)
  2. 전체 발행글 제목 재생성(22템플릿) + 카테고리 재분류(사이트 실제 카테고리 내에서만)
  3. 이미지 없는 글에 이미지 2장 보강

사용법: python scripts/full_site_fix.py --site https://xxx.com
"""
import os, sys, re, time, random, json, argparse, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import (
    SITES_CONFIG, WP_USER, build_diverse_title, pick_best_category,
    get_multiple_images, build_img_html
)


def _get_with_retry(url, auth, params, tries=4, timeout=45):
    last_exc = None
    for i in range(tries):
        try:
            return requests.get(url, auth=auth, params=params, timeout=timeout)
        except Exception as e:
            last_exc = e
            time.sleep(6)
    raise last_exc


def fix_dup_privacy(site_url, pw, log):
    r = _get_with_retry(f"{site_url}/wp-json/wp/v2/pages", (WP_USER, pw),
                         {"per_page": 50, "_fields": "id,title,link"})
    pages = r.json() if r.status_code == 200 else []
    pp = [p for p in pages if p["title"]["rendered"].strip().lower() == "privacy policy"]
    if len(pp) <= 1:
        log["dup_pages"] = "none"
        return
    keep = next((p for p in pp if p["link"].rstrip("/").endswith("privacy-policy")), pp[0])
    deleted = []
    for p in pp:
        if p["id"] == keep["id"]:
            continue
        dr = requests.delete(f"{site_url}/wp-json/wp/v2/pages/{p['id']}", auth=(WP_USER, pw),
                              params={"force": "true"}, timeout=20)
        deleted.append({"id": p["id"], "status": dr.status_code})
    log["dup_pages"] = {"kept": keep["id"], "deleted": deleted}


def fix_titles_categories_images(site_url, pw, lang, theme, log):
    posts, page = [], 1
    while True:
        r = _get_with_retry(f"{site_url}/wp-json/wp/v2/posts", (WP_USER, pw),
                             {"per_page": 20, "page": page, "status": "publish",
                              "_fields": "id,title,content,meta"})
        if r.status_code != 200: break
        batch = r.json()
        if not batch: break
        posts.extend(batch)
        if len(batch) < 20: break
        page += 1

    entries = []
    img_added_count = 0
    for p in posts:
        pid = p["id"]
        old_title = p.get("title", {}).get("rendered", "")
        try:
            content = p.get("content", {}).get("rendered", "")
            meta_obj = p.get("meta", {}) or {}
            keyword = meta_obj.get("rank_math_focus_keyword", "") or old_title
            kw = keyword.split(",")[0].strip()
            if re.match(r'^[◇\s]*By\s', kw, re.IGNORECASE) or len(kw) < 4:
                plain = re.sub(r'<[^>]+>', ' ', content)
                kw = re.sub(r'\s+', ' ', plain).strip()[:40] or f"{theme} Korea guide"

            new_title = build_diverse_title(kw, lang, site_url=site_url)
            new_cat = pick_best_category(site_url, pw, kw, old_title)

            payload = {"title": new_title, "categories": [new_cat]}
            img_added = False
            if len(re.findall(r'<img[\s>]', content, re.IGNORECASE)) == 0:
                imgs = get_multiple_images(kw, count=2, theme=theme)
                if imgs:
                    payload["content"] = build_img_html(imgs, kw) + content
                    img_added = True

            r2 = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                                 json=payload, timeout=25)
            if img_added and r2.status_code in (200, 201):
                img_added_count += 1
            entries.append({"id": pid, "old_title": old_title[:40], "new_title": new_title[:40],
                              "cat_id": new_cat, "img_added": img_added, "status": r2.status_code})
        except Exception as e:
            entries.append({"id": pid, "old_title": old_title[:40], "error": str(e)})

        time.sleep(random.uniform(1.0, 1.8))

        if len(entries) % 15 == 0:
            log["posts"] = entries
            log["total_posts"] = len(posts)
            log["images_added"] = img_added_count
            with open("full_site_fix_result.json", "w", encoding="utf-8") as f:
                json.dump(log, f, ensure_ascii=False, indent=2)

    log["posts"] = entries
    log["total_posts"] = len(posts)
    log["images_added"] = img_added_count
    log["failed"] = sum(1 for e in entries if e["status"] not in (200, 201))


if __name__ == "__main__":
    import traceback
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    args = ap.parse_args()

    log = {"site": args.site}
    try:
        site = next(s for s in SITES_CONFIG if s["url"] == args.site)
        pw = os.getenv(site["wp_pass_env"], "")
        lang = site.get("lang", "en")
        theme = site["theme"]

        if not pw:
            log["error"] = f"no_password: {site['wp_pass_env']}"
        else:
            fix_dup_privacy(args.site, pw, log)
            fix_titles_categories_images(args.site, pw, lang, theme, log)
    except Exception as e:
        log["fatal_error"] = str(e)
        log["traceback"] = traceback.format_exc()

    with open("full_site_fix_result.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"=== {args.site} 완료: 총{log.get('total_posts','?')} / 이미지추가{log.get('images_added','?')} / 실패{log.get('failed','?')} / 오류{log.get('fatal_error','')} ===")
