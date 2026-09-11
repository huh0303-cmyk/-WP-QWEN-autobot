#!/usr/bin/env python3
"""Audit image ALT coverage across all live, scheduled, and draft Blogger posts."""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from process_platform_queue import _access_token


def image_audit(content: str) -> tuple[int, list[dict]]:
    images = re.findall(r"(?is)<img\b[^>]*>", content or "")
    missing = []
    for index, tag in enumerate(images):
        match = re.search(r'''(?is)\balt\s*=\s*(["'])(.*?)\1''', tag)
        alt = html.unescape(match.group(2)).strip() if match else ""
        if not alt:
            src = re.search(r'''(?is)\bsrc\s*=\s*(["'])(.*?)\1''', tag)
            missing.append({"image_index": index, "src": (src.group(2) if src else "")[:240]})
    return len(images), missing


def main() -> int:
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    headers = {"Authorization": f"Bearer {_access_token('')}"}
    records, errors = [], []
    for profile in profiles:
        blog = profile.get("blogspot") or {}
        blog_id = str(blog.get("destination_id") or "")
        if not blog_id:
            continue
        seen = set()
        for status in ("draft", "scheduled", "live"):
            response = requests.get(
                f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
                headers=headers, params={"status": status, "fetchBodies": "true", "maxResults": 500}, timeout=30,
            )
            if response.status_code != 200:
                errors.append({"site_id": f"blogger_{profile['site_key']}", "status": status,
                               "error": f"HTTP {response.status_code}"})
                continue
            for post in response.json().get("items", []):
                post_id = str(post.get("id") or "")
                if not post_id or post_id in seen:
                    continue
                seen.add(post_id)
                count, missing = image_audit(post.get("content", ""))
                records.append({
                    "site_id": f"blogger_{profile['site_key']}", "blog_id": blog_id, "post_id": post_id,
                    "status": post.get("status") or status, "title": post.get("title", ""),
                    "edit_url": f"https://www.blogger.com/blog/post/edit/{blog_id}/{post_id}",
                    "image_count": count, "missing_alt_count": len(missing), "missing_images": missing,
                })
    result = {
        "posts_checked": len(records), "images_checked": sum(r["image_count"] for r in records),
        "images_missing_alt": sum(r["missing_alt_count"] for r in records),
        "records": records, "errors": errors,
    }
    Path("blogger_image_alt_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("posts_checked", "images_checked", "images_missing_alt")}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

