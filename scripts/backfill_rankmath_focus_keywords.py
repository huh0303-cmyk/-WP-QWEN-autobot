#!/usr/bin/env python3
"""Backfill and verify Rank Math focus keywords on every WordPress post.

The post status is never changed. A write only counts after a second authenticated
REST read returns the exact saved keyword.
"""
from __future__ import annotations

import html
import json
import os
import re
import time
from pathlib import Path

import requests

from site_registry import SITES

WP_USER = os.getenv("WP_USER", "huh0303@gmail.com")
STATUSES = ("publish", "future", "draft", "pending", "private")
OUT = Path(os.getenv("RANKMATH_BACKFILL_OUT", "rankmath_keyword_backfill_result.json"))


def derive_keyword(title: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", title or ""))
    text = re.sub(r"\s+", " ", text).strip(" -:|\t\r\n")
    for separator in (":", "—", "|", "?"):
        candidate = text.split(separator, 1)[0].strip()
        if 4 <= len(candidate) <= 80:
            text = candidate
            break
    return text[:80].strip()


def fetch_posts(site: str, password: str, status: str) -> list[dict]:
    found: list[dict] = []
    page = 1
    per_page = 50
    while True:
        response = requests.get(
            f"{site}/wp-json/wp/v2/posts", auth=(WP_USER, password),
            params={"status": status, "context": "edit", "per_page": per_page,
                    "page": page, "_fields": "id,status,title,meta"}, timeout=35,
        )
        if response.status_code >= 500 and per_page > 10:
            per_page = 20 if per_page == 50 else 10
            page = 1
            found = []
            time.sleep(1)
            continue
        if response.status_code == 400 and "rest_post_invalid_page_number" in response.text:
            break
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        found.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return found


def save_and_verify(site: str, password: str, post_id: int, keyword: str) -> tuple[bool, str]:
    endpoint = f"{site}/wp-json/wp/v2/posts/{post_id}"
    update = requests.post(endpoint, auth=(WP_USER, password),
                           json={"meta": {"rank_math_focus_keyword": keyword}}, timeout=30)
    if update.status_code not in (200, 201):
        return False, f"write_http_{update.status_code}"
    verify = requests.get(endpoint, auth=(WP_USER, password),
                          params={"context": "edit", "_fields": "id,meta"}, timeout=30)
    if verify.status_code != 200:
        return False, f"verify_http_{verify.status_code}"
    saved = str((verify.json().get("meta") or {}).get("rank_math_focus_keyword") or "").strip()
    return (saved == keyword, "" if saved == keyword else "meta_not_persisted")


def process_site(site: str, secret_name: str) -> dict:
    password = os.getenv(secret_name, "").strip()
    result = {"site": site, "scanned": 0, "already_set": 0, "filled": 0, "failed": 0, "errors": []}
    if not password:
        result["errors"].append("credential_missing")
        return result
    for status in STATUSES:
        try:
            posts = fetch_posts(site, password, status)
        except Exception as exc:
            result["errors"].append(f"{status}: inventory_failed: {str(exc)[:180]}")
            continue
        for post in posts:
            result["scanned"] += 1
            current = str((post.get("meta") or {}).get("rank_math_focus_keyword") or "").strip()
            if current:
                result["already_set"] += 1
                continue
            keyword = derive_keyword((post.get("title") or {}).get("rendered", ""))
            if not keyword:
                result["failed"] += 1
                result["errors"].append(f"post {post.get('id')}: empty_title")
                continue
            ok, error = save_and_verify(site, password, int(post["id"]), keyword)
            if ok:
                result["filled"] += 1
            else:
                result["failed"] += 1
                result["errors"].append(f"post {post.get('id')}: {error}")
    return result


def main() -> int:
    site_filter = os.getenv("SITE_FILTER", "").strip().rstrip("/").lower()
    selected = [row for row in SITES if not site_filter or row[0].rstrip("/").lower() == site_filter]
    if site_filter and not selected:
        raise SystemExit(f"SITE_FILTER not found: {site_filter}")
    results = [process_site(site, secret) for site, secret, _lifecycle in selected]
    payload = {"sites": results, "totals": {
        key: sum(int(row[key]) for row in results)
        for key in ("scanned", "already_set", "filled", "failed")
    }}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["totals"], ensure_ascii=False))
    return 1 if any(row["errors"] for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
