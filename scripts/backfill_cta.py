# -*- coding: utf-8 -*-
"""기존 발행글에 CTA 박스를 소급 삽입. 이미 있으면 스킵."""
import os, sys, time, random, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_cta_html

MARKER = 'class="cta-box"'


def fix_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}
    lang = site.get("lang", "ko")

    cta_html = build_cta_html(site_url, lang)
    if not cta_html:
        return {"site": site_url, "skipped_all": "no_cta_defined"}

    posts, page = [], 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,content"}, timeout=35)
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
    for p in posts:
        content = p.get("content", {}).get("rendered", "")
        if MARKER in content:
            skipped += 1
            continue
        try:
            pr = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                                 json={"content": content + cta_html}, timeout=25)
            if pr.status_code in (200, 201):
                updated += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        time.sleep(random.uniform(0.4, 0.8))

    return {"site": site_url, "updated": updated, "skipped": skipped, "failed": failed}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="")
    args = ap.parse_args()

    targets = [s for s in SITES_CONFIG if (not args.site or s["url"] == args.site)]
    results = []
    for site in targets:
        res = fix_site(site)
        results.append(res)
        print(f"{res['site']}: 추가{res.get('updated',0)} / 스킵{res.get('skipped',0)} / 실패{res.get('failed',0)} / 오류{res.get('error','')}")
        with open("backfill_cta_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
