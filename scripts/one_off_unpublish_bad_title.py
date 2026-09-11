"""One-off: revert ki-korea.com post 1765 ("Who the route fits" — an outline
heading that leaked through as the title, see autopost_mega.py fix) back to
draft so it stops being publicly visible with a broken title."""
import os
import requests

SITE = "https://ki-korea.com"
POST_ID = "1765"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.environ["KIKOREACOM"]


def main():
    response = requests.post(
        f"{SITE}/wp-json/wp/v2/posts/{POST_ID}",
        auth=(USER, PASSWORD),
        json={"status": "draft"},
        timeout=30,
    )
    response.raise_for_status()
    post = response.json()
    print(f"status now: {post.get('status')}, title: {post.get('title', {}).get('rendered')}")


if __name__ == "__main__":
    main()
