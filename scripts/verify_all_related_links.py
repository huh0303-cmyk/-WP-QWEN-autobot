# -*- coding: utf-8 -*-
"""검증 전용(임시): 27개 사이트 전체의 관련글 블록 적용 현황을 한번에 집계."""
import os, sys, json, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

MARKER = 'class="related-links"'


def check_site(site_url, wp_pass_env):
    pw = os.getenv(wp_pass_env, "")
    if not pw:
        return {"site": site_url, "error": "no_password"}
    total = 0
    with_block = 0
    page = 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,content"}, timeout=20)
        except Exception as e:
            return {"site": site_url, "error": str(e)}
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            total += 1
            content = p.get("content", {}).get("rendered", "")
            if MARKER in content:
                with_block += 1
        if len(batch) < 50:
            break
        page += 1
    return {"site": site_url, "total": total, "with_block": with_block}


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = check_site(site["url"], site["wp_pass_env"])
        results.append(res)
    with open("verify_all_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))
