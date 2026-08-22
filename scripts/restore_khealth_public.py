#!/usr/bin/env python3
"""긴급 복구: k-health365.com 전체 글을 다시 공개로 되돌린다.
방금 돌린 prune 작업이 색인신청 진행 중이던 글까지 비공개 처리해버려서,
신청이 무효화되는 걸 막기 위한 즉시 복구."""
import os
import requests

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PW = os.getenv("KHEALTH365COM", "").strip()


def main():
    if not PW:
        raise SystemExit("Missing KHEALTH365COM secret")
    for status in ("private", "draft"):
        r = requests.get(f"{SITE}/wp-json/wp/v2/posts", auth=(USER, PW),
                          params={"status": status, "per_page": 100, "_fields": "id,link,status"},
                          timeout=30)
        posts = r.json() if r.status_code == 200 else []
        print(f"{status} 상태 글 {len(posts)}개")
        for p in posts:
            resp = requests.post(f"{SITE}/wp-json/wp/v2/posts/{p['id']}",
                                  auth=(USER, PW), json={"status": "publish"}, timeout=30)
            print(f"  {'OK' if resp.status_code in (200,201) else 'FAIL'} ({resp.status_code}) id={p['id']} {p['link']}")


if __name__ == "__main__":
    main()
