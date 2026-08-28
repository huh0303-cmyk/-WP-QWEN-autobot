#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""긴급 복구: k-health365.com에서 private/draft/pending으로 묶여있는 글을
다시 공개(publish)로 되돌린다.

배경: 2026-08-28 감사(scripts/khealth_recovery_audit.py) 결과 전체 307개 글 중
공개(publish)는 0개, private 263개·pending 43개·draft 1개로 사실상 사이트
전체가 비공개 상태였다. 기존 버전은 private/draft만 봐서 pending 43개를
놓쳤고, 안전장치 없이 실행 즉시 전부 바꿨다 — 이번에 두 문제 모두 고친다.

기본값은 항상 DRY RUN(무엇을 바꿀지만 출력)이다. APPLY_CHANGES=true를 명시한
실행에서만 실제로 status를 publish로 바꾼다. 삭제는 절대 하지 않는다 —
상태값만 되돌린다.

사용법:
    python scripts/restore_khealth_public.py            # dry-run만
    APPLY_CHANGES=true python scripts/restore_khealth_public.py   # 실제 적용
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

SITE = "https://k-health365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KHEALTH365COM", "").strip()
HIDDEN_STATUSES = ("private", "pending", "draft")
APPLY_CHANGES = os.getenv("APPLY_CHANGES", "false").strip().lower() == "true"


def fetch_hidden_posts(status: str) -> list[dict]:
    auth = (USER, PASSWORD)
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{SITE}/wp-json/wp/v2/posts", auth=auth,
            params={"status": status, "per_page": 100, "page": page, "_fields": "id,link,status,title"},
            timeout=30,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def restore_post(post_id: int) -> tuple[bool, int]:
    resp = requests.post(
        f"{SITE}/wp-json/wp/v2/posts/{post_id}", auth=(USER, PASSWORD),
        json={"status": "publish"}, timeout=30,
    )
    return resp.status_code in (200, 201), resp.status_code


def run(apply_changes: bool = APPLY_CHANGES) -> dict:
    if not PASSWORD:
        raise SystemExit("Missing KHEALTH365COM secret")

    plan = []
    for status in HIDDEN_STATUSES:
        for post in fetch_hidden_posts(status):
            plan.append({"id": post["id"], "status": post["status"], "link": post.get("link", "")})

    # Python 3.11 CI 러너는 f-string 안에서 같은 종류 따옴표를 중첩하면
    # SyntaxError를 낸다(3.12+에서만 허용) — 카운트를 미리 문자열로 만들어둔다.
    per_status_counts = {status: sum(1 for p in plan if p["status"] == status) for status in HIDDEN_STATUSES}
    counts_str = ", ".join(f"{status}:{count}" for status, count in per_status_counts.items())
    prefix = "[DRY RUN] " if not apply_changes else ""
    print(f"{prefix}복구 대상 {len(plan)}개 ({counts_str})")

    results = []
    for item in plan:
        if not apply_changes:
            results.append({**item, "action": "WOULD_PUBLISH"})
            continue
        ok, code = restore_post(item["id"])
        results.append({**item, "action": "PUBLISHED" if ok else "FAILED", "http_status": code})
        print(f"  {'OK' if ok else 'FAIL'} ({code}) id={item['id']} {item['link']}")

    return {
        "site": SITE,
        "apply_changes": apply_changes,
        "hidden_statuses_checked": list(HIDDEN_STATUSES),
        "total_found": len(plan),
        "results": results,
    }


def main() -> int:
    import json
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/khealth-restore-report.json")
    args = parser.parse_args()

    report = run()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"REPORT_WRITTEN={out}")
    if not report["apply_changes"] and report["total_found"] > 0:
        print("이건 DRY RUN입니다 — 실제로 되돌리려면 APPLY_CHANGES=true로 다시 실행하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
