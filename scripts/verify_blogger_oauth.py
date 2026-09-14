#!/usr/bin/env python3
"""Isolated Blogger OAuth check - no LLM calls, no writes.

Confirms BLOGGER_GOOGLE_CLIENT_ID/_SECRET/_REFRESH_TOKEN can mint an access
token with Blogger write scope and read one blog's metadata. Exists to
separate "is the OAuth wired up" from "did the content pass the quality
gate" while validating the new Blogger secrets end-to-end.
"""
import os

import requests

BLOG_ID = os.environ.get("VERIFY_BLOG_ID", "").strip()


def main() -> int:
    client_id = os.environ.get("BLOGGER_GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("BLOGGER_GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("BLOGGER_GOOGLE_REFRESH_TOKEN", "").strip()
    missing = [name for name, value in (
        ("BLOGGER_GOOGLE_CLIENT_ID", client_id),
        ("BLOGGER_GOOGLE_CLIENT_SECRET", client_secret),
        ("BLOGGER_GOOGLE_REFRESH_TOKEN", refresh_token),
    ) if not value]
    if missing:
        raise SystemExit(f"missing secrets: {', '.join(missing)}")
    if not BLOG_ID:
        raise SystemExit("VERIFY_BLOG_ID is required")

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    if token_resp.status_code >= 400:
        raise SystemExit(f"token refresh failed: {token_resp.status_code} {token_resp.text[:500]}")
    access_token = token_resp.json()["access_token"]
    print("token refresh: OK")

    blog_resp = requests.get(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    if blog_resp.status_code >= 400:
        raise SystemExit(f"blog read failed: {blog_resp.status_code} {blog_resp.text[:500]}")
    blog = blog_resp.json()
    print(f"blog read: OK name={blog.get('name')!r} url={blog.get('url')!r}")

    perms_resp = requests.get(
        f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"maxResults": 1, "fetchBodies": "false"},
        timeout=20,
    )
    if perms_resp.status_code >= 400:
        raise SystemExit(f"posts list failed: {perms_resp.status_code} {perms_resp.text[:500]}")
    print("posts list: OK (write scope confirmed reachable)")
    print("VERIFY_BLOGGER_OAUTH: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
