#!/usr/bin/env python3
"""Inventory every Blogger post that needs UI search-description review.

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
from gemini_text import gemini_generate_text
from auto_write_and_draft import _finish_meta_description

OUT = Path("blogger_draft_search_description_audit.json")


def plain_intro(content: str) -> str:
    text = re.sub(r"<[^>]+>", " ", content or "")
    return re.sub(r"\s+", " ", text).strip()[:500]


def prepare_search_descriptions(records: list[dict]) -> None:
    """Generate post-specific 100-120 character snippets in small batches."""
    for start in range(0, len(records), 8):
        batch = records[start:start + 8]
        source = [{"index": start + i, "title": row["title"], "intro": row["intro"]}
                  for i, row in enumerate(batch)]
        prompt = f"""Create one search description for each Blogger post below.
Return JSON array only: [{{"index": 0, "search_description": "..."}}].
Each description must be one grammatical sentence, 100-120 CHARACTERS including spaces, in the same language as its title. It must accurately describe that specific post, avoid hype, and must not invent facts.
POSTS: {json.dumps(source, ensure_ascii=False)}"""
        raw = gemini_generate_text(prompt, temperature=0.2)
        match = re.search(r"\[[\s\S]*\]", raw)
        generated = json.loads(match.group(0)) if match else []
        by_index = {int(item["index"]): str(item.get("search_description") or "")
                    for item in generated if "index" in item}
        for i, row in enumerate(batch):
            absolute = start + i
            candidate = by_index.get(absolute, "") or row["intro"]
            fitted = _finish_meta_description({"title": row["title"], "meta_description": candidate})["meta_description"]
            if not 100 <= len(fitted) <= 120:
                raise RuntimeError(f"search description length failed for {row['site_id']}/{row['post_id']}: {len(fitted)}")
            row["search_description"] = fitted
            row["search_description_length"] = len(fitted)


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
        seen = set()
        for status in ("draft", "scheduled", "live"):
            response = requests.get(
                f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
                headers=headers,
                params={"status": status, "fetchBodies": "true", "maxResults": 500},
                timeout=30,
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
                records.append({
                    "site_id": f"blogger_{profile['site_key']}",
                    "site": blog.get("url", ""),
                    "blog_id": blog_id,
                    "post_id": post_id,
                    "status": post.get("status") or status,
                    "title": post.get("title", ""),
                    "intro": plain_intro(post.get("content", "")),
                    "edit_url": f"https://www.blogger.com/blog/post/edit/{blog_id}/{post_id}",
                    "search_description_api_state": "not_exposed_by_blogger_v3",
                    "ui_verification_required": True,
                })
    prepare_search_descriptions(records)
    result = {"blogs_expected": len(profiles), "drafts_found": len(records), "records": records, "errors": errors}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"blogs_expected": len(profiles), "drafts_found": len(records), "errors": len(errors)}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
