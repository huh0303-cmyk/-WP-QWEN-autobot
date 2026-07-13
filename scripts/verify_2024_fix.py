# -*- coding: utf-8 -*-
import os, sys, json, time, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER


def check_site(site_url, wp_pass_env):
    pw = os.getenv(wp_pass_env, "")
    if not pw:
        return {"site": site_url, "error": "no_password"}
    total = 0
    remaining_2024 = 0
    page = 1
    while True:
        r = None
        for attempt in range(3):
            try:
                r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                                  params={"per_page": 20, "page": page, "status": "publish",
                                          "_fields": "id,title,content"}, timeout=40)
                break
            except Exception as e:
                if attempt == 2:
                    return {"site": site_url, "error": str(e), "total": total, "remaining_2024": remaining_2024}
                time.sleep(5)
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
        if len(batch) < 20:
            break
        page += 1
        time.sleep(0.5)
    return {"site": site_url, "total": total, "remaining_2024": remaining_2024}


if __name__ == "__main__":
    results = [check_site(s["url"], s["wp_pass_env"]) for s in SITES_CONFIG]
    with open("verify_2024_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps(results, ensure_ascii=False, indent=2))
