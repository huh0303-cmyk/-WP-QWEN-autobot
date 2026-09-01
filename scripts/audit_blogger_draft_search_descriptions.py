#!/usr/bin/env python3
"""Inventory every Blogger draft that needs UI search-description review.

Blogger API v3 deliberately has no Post.searchDescription field. This audit
therefore creates a complete, non-secret editor-link inventory for the local
authenticated browser pass instead of falsely reporting the field as saved.
"""
from __future__ import annotations

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

OUT = Path("blogger_draft_search_description_audit.json")


def plain_intro(content: str) -> str:
    text = re.sub(r"<[^>]+>", " ", content or "")
    return re.sub(r"\s+", " ", text).strip()[:500]


def main() -> int:
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    token = _access_token("")
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    errors = []
    for profile in profiles:
        blog = profile.get("blogspot") or {}
        blog_id = str(blog.get("destination_id") or "")
        if not blog_id:
            errors.append({"site_id": f"blogger_{profile['site_key']}", "error": "destination_id missing"})
            continue
        response = requests.get(
            f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
            headers=headers,
            params={"status": "draft", "fetchBodies": "true", "maxResults": 500},
            timeout=30,
        )
        if response.status_code != 200:
            errors.append({"site_id": f"blogger_{profile['site_key']}", "error": f"HTTP {response.status_code}"})
            continue
        for post in response.json().get("items", []):
            post_id = str(post.get("id") or "")
            records.append({
                "site_id": f"blogger_{profile['site_key']}",
                "site": blog.get("url", ""),
                "blog_id": blog_id,
                "post_id": post_id,
                "title": post.get("title", ""),
                "intro": plain_intro(post.get("content", "")),
                "edit_url": f"https://www.blogger.com/blog/post/edit/{blog_id}/{post_id}",
                "search_description_api_state": "not_exposed_by_blogger_v3",
                "ui_verification_required": True,
            })
    result = {"blogs_expected": len(profiles), "drafts_found": len(records), "records": records, "errors": errors}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"blogs_expected": len(profiles), "drafts_found": len(records), "errors": len(errors)}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

