#!/usr/bin/env python3
"""Audit all published posts, then optionally move failed posts to private.

The audit and write phases are intentionally separate.  The generated manifest
contains enough information to restore each post because no post is deleted.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from content_quality_gate import evaluate_article
from site_registry import SITES

WP_USER = os.getenv("WP_USER", "huh0303@gmail.com")
CONFIRM_TOKEN = "PRIVATE_REBUILD_FAILED_POSTS"


def fetch_posts(site: str, password: str) -> list[dict]:
    posts: list[dict] = []
    page = 1
    while True:
        response = requests.get(
            f"{site}/wp-json/wp/v2/posts",
            auth=(WP_USER, password),
            params={
                "context": "edit", "status": "publish", "per_page": 100,
                "page": page, "_fields": "id,date,modified,link,slug,title,content,status",
            },
            timeout=30,
        )
        if response.status_code == 400 and "rest_post_invalid_page_number" in response.text:
            break
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def audit(site_filter: str, output: Path) -> None:
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy": "failed quality gate => private candidate; errors => unknown",
        "sites": {},
    }
    for site, secret, lifecycle in SITES:
        if site_filter and site_filter not in site:
            continue
        if lifecycle == "retired":
            report["sites"][site] = {"lifecycle": lifecycle, "status": "retired", "posts": []}
            continue
        password = os.getenv(secret, "")
        if not password:
            report["sites"][site] = {"lifecycle": lifecycle, "status": "unknown_missing_secret", "posts": []}
            continue
        try:
            posts = fetch_posts(site, password)
            rows = []
            for post in posts:
                result = evaluate_article(
                    post.get("title", {}).get("raw") or post.get("title", {}).get("rendered", ""),
                    post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", ""),
                    site,
                )
                rows.append({
                    "id": post["id"], "link": post.get("link"), "slug": post.get("slug"),
                    "previous_status": post.get("status", "publish"),
                    "action": "keep" if result.passed else "private_candidate",
                    "quality": result.to_dict(),
                })
            report["sites"][site] = {"lifecycle": lifecycle, "status": "audited", "posts": rows}
        except Exception as exc:
            report["sites"][site] = {"lifecycle": lifecycle, "status": "unknown_error", "error": str(exc), "posts": []}
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"감사 완료: {output}")


def apply(manifest: Path, site_filter: str, confirm: str) -> None:
    if confirm != CONFIRM_TOKEN:
        raise SystemExit(f"실행 거부: --confirm {CONFIRM_TOKEN} 필요")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    receipt = {"applied_at": datetime.now(timezone.utc).isoformat(), "changes": []}
    for site, site_data in data.get("sites", {}).items():
        if site_filter and site_filter not in site:
            continue
        if site_data.get("status") != "audited":
            continue
        registry = next((row for row in SITES if row[0] == site), None)
        if not registry or registry[2] == "retired":
            continue
        password = os.getenv(registry[1], "")
        if not password:
            continue
        for post in site_data.get("posts", []):
            if post.get("action") != "private_candidate":
                continue
            response = requests.post(
                f"{site}/wp-json/wp/v2/posts/{post['id']}",
                auth=(WP_USER, password), json={"status": "private"}, timeout=30,
            )
            receipt["changes"].append({
                "site": site, "post_id": post["id"], "link": post.get("link"),
                "from": post.get("previous_status", "publish"), "to": "private",
                "http_status": response.status_code, "ok": response.status_code in (200, 201),
            })
            Path("rebuild_private_receipt.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    print(f"비공개 처리 기록: rebuild_private_receipt.json ({len(receipt['changes'])}건)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("audit", "apply"))
    parser.add_argument("--site", default="")
    parser.add_argument("--manifest", default="rebuild_content_manifest.json")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    path = Path(args.manifest)
    if args.mode == "audit":
        audit(args.site, path)
    else:
        apply(path, args.site, args.confirm)


if __name__ == "__main__":
    main()


