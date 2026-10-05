#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_khealth_duplicate_titles.py
─────────────────────────────────────────────────────────────
One-off: two pairs of posts on k-health365.com ended up with
word-for-word identical titles (near_duplicate_titles similarity
1.0 in scripts/khealth_recovery_audit.py's 2026-09-28 run), which
hurts Google indexing/ranking (duplicate-content signal).

Per instruction: change ONLY the title of the newer post in each
pair (identified by its "-2" slug suffix, meaning WordPress had to
disambiguate it from the original at creation time). Content is
left untouched. The new title is written to reflect that post's
actual lead angle so it stays accurate, not just different.

Run via GitHub Actions workflow_dispatch (reuses KHEALTH365COM secret).
"""
import os
import sys

import requests

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KHEALTH365COM", "").strip()

# post_id -> new title
RENAMES = {
    3377: "과민성대장증후군 원인과 식단 관리로 증상 완화하는 법",
    3359: "현대인 눈 건강 망치는 나쁜 습관과 개선법",
}


def main() -> int:
    if not PASSWORD:
        print("Missing KHEALTH365COM secret", file=sys.stderr)
        return 1

    auth = (USER, PASSWORD)
    ok = True
    for post_id, new_title in RENAMES.items():
        r = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}",
                          auth=auth, params={"_fields": "id,title,link"}, timeout=30)
        r.raise_for_status()
        before = r.json()
        print(f"id={post_id} 기존 제목: {before['title']['rendered']}")

        pr = requests.post(f"{SITE}/wp-json/wp/v2/posts/{post_id}",
                            auth=auth, json={"title": new_title}, timeout=30)
        if pr.status_code in (200, 201):
            data = pr.json()
            print(f"  ✅ 변경됨 -> {data['title']['rendered']}  ({data['link']})")
        else:
            ok = False
            print(f"  ❌ 실패 ({pr.status_code}): {pr.text[:300]}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
