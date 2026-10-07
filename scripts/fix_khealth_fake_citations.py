#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_khealth_fake_citations.py
─────────────────────────────────────────────────────────────
One-off: two k-health365.com posts cite real-sounding sources
("한국 뉴스", "식품의약품안전처") with a future date (2027) that was
never published — khealth_recovery_audit.py's future_year flag
caught the date, but the real problem is a fabricated attribution,
not a typo. Changing 2027->2026 would still leave a made-up citation
attached to a real government agency, so instead we strip just the
citation parenthetical and leave the surrounding sentence/claim as
plain, unsourced prose (per repo CLAUDE.md: no fabricated sourcing).

Each entry is an EXACT substring replace, verified against the live
post content before the GET/POST happens. If the exact substring is
no longer present (content changed since this was written), that
post is skipped and reported rather than guessed at.
"""
import os
import sys

import requests

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KHEALTH365COM", "").strip()

# post_id -> list of (old_substring, new_substring)
REPLACEMENTS = {
    4817: [
        (" (한국 뉴스, 2027)", ""),
    ],
    4578: [
        (" (식품의약품안전처, 2027)", ""),
        ("<td>(식품의약품안전처, 2027)</td>", "<td>—</td>"),
    ],
}


def main() -> int:
    if not PASSWORD:
        print("Missing KHEALTH365COM secret", file=sys.stderr)
        return 1

    auth = (USER, PASSWORD)
    ok = True
    for post_id, pairs in REPLACEMENTS.items():
        r = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}",
                          auth=auth, params={"_fields": "id,title,content,link"}, timeout=30)
        r.raise_for_status()
        post = r.json()
        content = post["content"]["rendered"]
        print(f"id={post_id} {post['title']['rendered']}")

        changed = content
        applied = 0
        for old, new in pairs:
            if old in changed:
                changed = changed.replace(old, new)
                applied += 1
            else:
                print(f"  ⚠️ 문구를 못 찾음 (건너뜀): {old!r}")

        if applied == 0:
            print("  — 변경 없음")
            continue

        pr = requests.post(f"{SITE}/wp-json/wp/v2/posts/{post_id}",
                            auth=auth, json={"content": changed}, timeout=30)
        if pr.status_code in (200, 201):
            print(f"  ✅ 가짜 출처 {applied}곳 제거 ({post['link']})")
        else:
            ok = False
            print(f"  ❌ 실패 ({pr.status_code}): {pr.text[:300]}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
