#!/usr/bin/env python3
"""k-health365.com의 글쓴이 표시명을 "K-Health Editorial Desk"(영문)에서
"K-Health365 편집국"(한국어)으로 변경한다."""
import os
import requests

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PW = os.getenv("KHEALTH365COM", "").strip()
NEW_NAME = "K-Health365 편집국"


def main():
    if not PW:
        raise SystemExit("Missing KHEALTH365COM secret")

    r = requests.get(f"{SITE}/wp-json/wp/v2/users", auth=(USER, PW),
                      params={"context": "edit", "per_page": 100}, timeout=30)
    r.raise_for_status()
    users = r.json()
    print(f"사용자 {len(users)}명 발견")
    targets = [u for u in users if "editorial" in u.get("name", "").lower()
               or "editorial" in u.get("slug", "").lower()]
    if not targets:
        print("영문 편집국 계정을 못 찾음, 전체 목록:")
        for u in users:
            print(f"  id={u['id']} name={u['name']!r} slug={u['slug']!r}")
        return

    for u in targets:
        uid = u["id"]
        print(f"변경: id={uid} {u['name']!r} -> {NEW_NAME!r}")
        resp = requests.post(f"{SITE}/wp-json/wp/v2/users/{uid}", auth=(USER, PW),
                              json={"name": NEW_NAME}, timeout=30)
        print(f"  결과: {resp.status_code} {resp.text[:200]}")


if __name__ == "__main__":
    main()
