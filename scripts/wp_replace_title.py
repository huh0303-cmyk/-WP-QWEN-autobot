#!/usr/bin/env python3
"""Replace only one WordPress post title; preserve slug, body and status."""
import os
import sys
import requests


def main() -> int:
    site = os.environ["WP_SITE_URL"].rstrip("/")
    post_id = os.environ["WP_POST_ID"].strip()
    new_title = os.environ["WP_NEW_TITLE"].strip()
    user = os.environ.get("WP_USER", "huh0303@gmail.com").strip() or "huh0303@gmail.com"
    password = os.environ["WP_APP_PASSWORD"].strip()
    if not new_title or "unlock" in new_title.lower():
        raise SystemExit("replacement title is empty or still contains Unlock")
    endpoint = f"{site}/wp-json/wp/v2/posts/{post_id}"
    before = requests.get(endpoint, params={"context": "edit"}, auth=(user, password), timeout=30)
    before.raise_for_status()
    original = before.json()
    response = requests.post(endpoint, json={"title": new_title}, auth=(user, password), timeout=30)
    response.raise_for_status()
    changed = response.json()
    if "unlock" in changed.get("title", {}).get("raw", "").lower():
        raise SystemExit("title verification failed")
    print({"id": changed["id"], "status": changed["status"], "link": changed["link"],
           "old_title": original.get("title", {}).get("raw", ""), "new_title": new_title,
           "slug_preserved": changed.get("slug") == original.get("slug")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
