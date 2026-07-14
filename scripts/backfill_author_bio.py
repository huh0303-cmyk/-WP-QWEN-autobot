# -*- coding: utf-8 -*-
"""기존 발행글에 저자소개(EEAT) 박스를 소급 삽입. 이미 있으면 스킵."""
import os, sys, time, random, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_author_bio_html

MARKER = 'class="author-bio"'


def fix_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}
    lang = site.get("lang", "ko")

    posts, page = [], 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,content,meta,author"}, timeout=35)
        except Exception as e:
            return {"site": site_url, "error": str(e)}
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    updated = skipped = failed = 0
    default_reporter = {"name": ("김하나" if lang == "ko" else "Grace Jung")}
    for p in posts:
        content = p.get("content", {}).get("rendered", "")
        if MARKER in content:
            skipped += 1
            continue
        meta_obj = p.get("meta", {}) or {}
        keyword = meta_obj.get("rank_math_focus_keyword", "")
        bio_html = build_author_bio_html(site_url, lang, default_reporter, keyword)
        if not bio_html:
            skipped += 1
            continue
        try:
            pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                                 json={"content": content + bio_html}, timeout=25)
            if pr.status_code in (200, 201):
                updated += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        time.sleep(random.uniform(0.5, 1.0))

    return {"site": site_url, "updated": updated, "skipped": skipped, "failed": failed}


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = fix_site(site)
        results.append(res)
        print(f"{res['site']}: 추가{res.get('updated',0)} / 스킵{res.get('skipped',0)} / 실패{res.get('failed',0)} / 오류{res.get('error','')}")
        with open("backfill_author_bio_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
