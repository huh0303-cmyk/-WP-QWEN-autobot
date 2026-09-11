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
from openai_text import openai_generate_text

OUT = Path("blogger_draft_search_description_audit.json")


def plain_intro(content: str) -> str:
    text = re.sub(r"<[^>]+>", " ", content or "")
    return re.sub(r"\s+", " ", text).strip()[:500]


def prepare_search_descriptions(records: list[dict]) -> None:
    """Generate post-specific 100-120 character snippets in small batches."""
    for start in range(0, len(records), 8):
        batch = records[start:start + 8]
        pending = {start + i: row for i, row in enumerate(batch)}
        accepted: dict[int, str] = {}
        for attempt in range(1, 4):
            if not pending:
                break
            source = [{"index": index, "title": row["title"], "intro": row["intro"]}
                      for index, row in pending.items()]
            prompt = f"""Create one search description for each Blogger post below.
Return JSON array only: [{{"index": 0, "search_description": "..."}}].
Each description must be ONE complete grammatical sentence, 100-115 CHARACTERS including spaces, in the same language as its title. Count characters before answering. Never truncate a phrase. It must accurately describe that specific post, avoid hype, and invent no facts.
POSTS: {json.dumps(source, ensure_ascii=False)}"""
            raw = openai_generate_text(prompt, temperature=0.1, max_retries=3)
            match = re.search(r"\[[\s\S]*\]", raw)
            generated = json.loads(match.group(0)) if match else []
            for item in generated:
                index = int(item.get("index", -1))
                candidate = str(item.get("search_description") or "").strip()
                bad_ending = bool(re.search(
                    r"(?i)\b(and|or|of|in|for|to|with|including|emphasizing|focusing|various|practical|precise|own|work|healthy)\.$",
                    candidate,
                ))
                if index in pending and 100 <= len(candidate) <= 119 and candidate.endswith((".", "!", "?")) and not bad_ending:
                    accepted[index] = candidate
                    pending.pop(index)
        if pending:
            failed = [f"{row['site_id']}/{row['post_id']}" for row in pending.values()]
            raise RuntimeError(f"complete 100-120 character search descriptions not generated: {failed}")
        for i, row in enumerate(batch):
            fitted = accepted[start + i]
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
