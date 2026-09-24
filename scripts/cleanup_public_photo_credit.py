#!/usr/bin/env python3
"""Remove reader-visible internal stock-photo/licence notices from published WordPress posts.

Safe remediation:
- scans the canonical WordPress registry;
- changes only posts/excerpts containing tightly matched operational photo-credit text;
- leaves image assets, captions that describe the image, article prose and licensing receipts intact;
- writes an audit receipt to artifacts/photo-credit-cleanup.json.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from site_registry import SITES

WP_USER = os.getenv("WP_USER", "huh0303@gmail.com")
APPLY = os.getenv("PHOTO_CREDIT_CLEANUP_APPLY", "false").strip().lower() in {"1", "true", "yes", "on"}
REPORT = ROOT / "artifacts" / "photo-credit-cleanup.json"

ILLUSTRATIVE_PREFIX = re.compile(
    r"^\s*Illustrative\s+stock\s+photo\s*:\s*.*?"
    r"(?:Not\s+a\s+photograph\s+of\s+a\s+specific\s+event\s*,\s*client\s+or\s+reviewed\s+product\.?|"
    r"Stock\s+photo\s*/\s*자료사진\.?)\s*",
    re.I | re.S,
)
PLAIN_CREDIT = re.compile(
    r"^\s*Photo\s*:\s*.*?(?:Pexels|Pixabay).*?(?:Stock\s+photo\s*/\s*자료사진|License)\s*",
    re.I | re.S,
)
LEAK_MARKERS = (
    "illustrative stock photo",
    "photo license",
    "not a photograph of a specific event",
    "stock photo / 자료사진",
)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def _strip_visible_prefix(text: str) -> tuple[str, bool]:
    before = text or ""
    after = ILLUSTRATIVE_PREFIX.sub("", before, count=1)
    if after == before:
        after = PLAIN_CREDIT.sub("", before, count=1)
    return after.strip(), after != before


def sanitize_html(raw: str) -> tuple[str, bool]:
    if not raw:
        return raw, False
    soup = BeautifulSoup(raw, "html.parser")
    changed = False

    for node in list(soup.select(".photo-credit")):
        node.decompose()
        changed = True

    for node in list(soup.find_all(["p", "div", "figcaption"])):
        visible = _norm(node.get_text(" ", strip=True))
        low = visible.lower()
        if not any(marker in low for marker in LEAK_MARKERS):
            continue
        cleaned, matched = _strip_visible_prefix(visible)
        if not matched and (
            low.startswith("illustrative stock photo")
            or (low.startswith("photo:") and ("pexels" in low or "pixabay" in low))
        ):
            cleaned = ""
            matched = True
        if matched:
            if cleaned:
                node.clear()
                node.append(cleaned)
            else:
                node.decompose()
            changed = True

    rendered = str(soup)
    return rendered, changed


def sanitize_excerpt(raw: str) -> tuple[str, bool]:
    if not raw:
        return raw, False
    cleaned_html, changed = sanitize_html(raw)
    if changed:
        return cleaned_html, True
    visible = _norm(BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))
    cleaned, matched = _strip_visible_prefix(visible)
    return (cleaned if matched else raw), matched


def scan_site(site_url: str, secret_name: str) -> dict:
    password = os.getenv(secret_name, "")
    result = {"site": site_url, "secret_name": secret_name, "scanned": 0, "changed": [], "status": "ok"}
    if not password:
        result["status"] = "skipped_missing_secret"
        return result

    auth = (WP_USER, password)
    page = 1
    while True:
        response = requests.get(
            site_url.rstrip("/") + "/wp-json/wp/v2/posts",
            auth=auth,
            params={
                "status": "publish",
                "context": "edit",
                "per_page": 100,
                "page": page,
                "orderby": "id",
                "order": "desc",
                "_fields": "id,link,title,content,excerpt,status",
            },
            timeout=30,
        )
        if response.status_code == 400 and page > 1:
            break
        response.raise_for_status()
        posts = response.json()
        if not posts:
            break

        for post in posts:
            result["scanned"] += 1
            content_raw = (post.get("content") or {}).get("raw") or (post.get("content") or {}).get("rendered") or ""
            excerpt_raw = (post.get("excerpt") or {}).get("raw") or ""
            new_content, content_changed = sanitize_html(content_raw)
            new_excerpt, excerpt_changed = sanitize_excerpt(excerpt_raw)
            if not (content_changed or excerpt_changed):
                continue

            item = {
                "post_id": post.get("id"),
                "url": post.get("link"),
                "title": BeautifulSoup((post.get("title") or {}).get("rendered", ""), "html.parser").get_text(" ", strip=True),
                "content_changed": content_changed,
                "excerpt_changed": excerpt_changed,
                "applied": False,
            }
            if APPLY:
                payload = {}
                if content_changed:
                    payload["content"] = new_content
                if excerpt_changed:
                    payload["excerpt"] = new_excerpt
                update = requests.post(
                    site_url.rstrip("/") + f"/wp-json/wp/v2/posts/{post['id']}",
                    auth=auth,
                    json=payload,
                    timeout=30,
                )
                update.raise_for_status()
                item["applied"] = True
            result["changed"].append(item)

        if len(posts) < 100:
            break
        page += 1
    return result


def main() -> int:
    results = []
    failures = []
    for site_url, secret_name, _tier in SITES:
        try:
            outcome = scan_site(site_url, secret_name)
        except Exception as exc:
            outcome = {"site": site_url, "secret_name": secret_name, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
            failures.append(outcome)
        results.append(outcome)
        print(json.dumps(outcome, ensure_ascii=False))

    summary = {
        "apply": APPLY,
        "sites": len(results),
        "scanned_posts": sum(int(r.get("scanned", 0)) for r in results),
        "changed_posts": sum(len(r.get("changed", [])) for r in results),
        "failures": len(failures),
        "results": results,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("apply", "sites", "scanned_posts", "changed_posts", "failures")}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
