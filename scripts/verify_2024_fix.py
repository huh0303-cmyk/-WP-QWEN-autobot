# -*- coding: utf-8 -*-
"""검증 전용(임시): 27개 사이트 전체에서 남아있는 '2024' 잔여 개수 집계."""
import os, sys, json, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER


def check_site(site_url, wp_pass_env):
    pw = os.getenv(wp_pass_env, "")
    if not pw:
        return {"site": site_url, "error": "no_password"}
    total = 0
    remaining_2024 = 0
    remaining_titles = []
    page = 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,title,content,link"}, timeout=25)
        except Exception as e:
            return {"site": site_url, "error": str(e), "total": total, "remaining_2024": remaining_2024}
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            total += 1
            title = p.get("title", {}).get("rendered", "")
            content = p.get("content", {}).get("rendered", "")
            if "2024" in title or "2024" in content:
                remaining_2024 += 1
                if len(remaining_titles) < 5:
                    remaining_titles.append({"id": p["id"], "title": title, "link": p.get("link")})
        if len(batch) < 50:
            break
        page += 1
    return {"site": site_url, "total": total, "remaining_2024": remaining_2024, "sample_remaining": remaining_titles}


if __name__ == "__main__":
    results = []
    for site in SITES_CONFIG:
        res = check_site(site["url"], site["wp_pass_env"])
        results.append(res)
        print(json.dumps(res, ensure_ascii=False))
    with open("verify_2024_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
