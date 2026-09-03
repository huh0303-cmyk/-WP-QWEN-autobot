"""One-click manual publish: flip a single already-reviewed WordPress post
from draft/private to public. Triggered from the CEO control room's
"지금 발행" button — never runs automatically, always one specific post_id
picked by a human."""
import os

import requests


def main():
    site = os.environ["SITE"].rstrip("/")
    post_id = os.environ["POST_ID"]
    user = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
    password = os.environ["WP_PASSWORD"]

    response = requests.post(
        f"{site}/wp-json/wp/v2/posts/{post_id}",
        auth=(user, password),
        json={"status": "publish"},
        timeout=30,
    )
    response.raise_for_status()
    post = response.json()
    if post.get("status") != "publish":
        raise SystemExit(f"post {post_id} did not report status=publish after update: {post.get('status')}")
    print(f"OK published {site}/?p={post_id} -> {post.get('link')}")


if __name__ == "__main__":
    main()
