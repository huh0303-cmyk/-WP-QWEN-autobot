#!/usr/bin/env python3
"""Safely remove the title-matching leading inline hero from one WP post.

Requires KOREAWEDDING365COM (WordPress application password). Creates a local
JSON backup before PATCH and verifies the saved content by reading it back.
"""
import json
import os
from pathlib import Path
import requests

from editorial_image_guard import strip_title_duplicate_lead_image

SITE = "https://koreawedding365.com"
SLUG = "korean-immigration-policy-updates-2026-what-international-couples-need-to-know-for-marriage-registration-and-visa-planning"
USER = "huh0303@gmail.com"


def main():
    password = os.getenv("KOREAWEDDING365COM", "").strip()
    if not password:
        raise SystemExit("Missing KOREAWEDDING365COM; no changes made")
    auth = (USER, password)
    endpoint = SITE + "/wp-json/wp/v2/posts"
    response = requests.get(endpoint, auth=auth,
                            params={"slug": SLUG, "context": "edit", "per_page": 2},
                            timeout=25)
    response.raise_for_status()
    posts = response.json()
    if len(posts) != 1:
        raise SystemExit(f"Expected exactly one post for slug; found {len(posts)}")
    post = posts[0]
    content = post.get("content", {}).get("raw")
    if content is None:
        raise SystemExit("WordPress did not return editable raw content")
    title = post.get("title", {}).get("raw") or post.get("title", {}).get("rendered", "")
    updated = strip_title_duplicate_lead_image(content, title)
    if updated == content:
        print(json.dumps({"status": "no_change", "post_id": post["id"],
                          "featured_media": post.get("featured_media"),
                          "reason": "No first-block image with ALT exactly matching title"},
                         ensure_ascii=False))
        return
    backup_dir = Path("artifacts/koreawedding-duplicate-hero")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f"post-{post['id']}-before.json"
    backup.write_text(json.dumps({"id": post["id"], "link": post.get("link"),
                                  "title": title, "content": content},
                                 ensure_ascii=False, indent=2), encoding="utf-8")
    patch = requests.post(f"{endpoint}/{post['id']}", auth=auth,
                          json={"content": updated}, timeout=30)
    patch.raise_for_status()
    verify = requests.get(f"{endpoint}/{post['id']}", auth=auth,
                          params={"context": "edit"}, timeout=25)
    verify.raise_for_status()
    saved = verify.json().get("content", {}).get("raw")
    if saved != updated:
        raise SystemExit("PATCH returned but read-back verification failed")
    if post.get("featured_media") != verify.json().get("featured_media"):
        raise SystemExit("Featured image changed unexpectedly; investigate immediately")
    print(json.dumps({"status": "fixed_verified", "post_id": post["id"],
                      "url": post.get("link"), "backup": str(backup),
                      "featured_media_preserved": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
