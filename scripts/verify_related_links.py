# -*- coding: utf-8 -*-
"""검증 전용(임시): backfill 결과가 실제로 반영됐는지 확인 후 verify_result.json에 기록."""
import os, json, argparse, requests

WP_USER = "huh0303@gmail.com"
MARKER = 'class="related-links"'


def check_site(site_url, wp_pass_env):
    pw = os.getenv(wp_pass_env, "")
    if not pw:
        return {"site": site_url, "error": f"no password env {wp_pass_env}"}

    total = 0
    with_block = 0
    sample = []
    page = 1
    while True:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                          params={"per_page": 50, "page": page, "status": "publish",
                                  "_fields": "id,title,link,content"}, timeout=20)
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for p in batch:
            total += 1
            content = p.get("content", {}).get("rendered", "")
            has = MARKER in content
            if has:
                with_block += 1
            if len(sample) < 3:
                title = p.get("title", {}).get("rendered", "")
                sample.append({"id": p["id"], "title": title, "link": p.get("link"), "has_related_block": has})
        if len(batch) < 50:
            break
        page += 1

    return {"site": site_url, "total_posts": total, "posts_with_related_block": with_block, "sample": sample}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--env", required=True)
    args = ap.parse_args()
    result = check_site(args.site, args.env)
    with open("verify_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
