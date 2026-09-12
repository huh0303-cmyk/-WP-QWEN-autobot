#!/usr/bin/env python3
"""One-off: replace the koreawedding365.com post-888 featured image."""
import os
import re
import socket
import sys

if os.getenv("FORCE_SOURCE_IPV4", "false").strip().lower() == "true":
    _orig = socket.getaddrinfo
    socket.getaddrinfo = lambda host, port, family=0, *a, **kw: _orig(host, port, socket.AF_INET, *a, **kw)

sys.path.insert(0, "scripts")
import requests

SITE = "https://koreawedding365.com"
POST_ID = 888
WP_USER = os.environ["WP_USER"]
WP_PASS = os.environ["KOREAWEDDING365COM"]
AUTH = (WP_USER, WP_PASS)


def main():
    post = requests.get(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", auth=AUTH,
                         params={"_fields": "id,title,content,featured_media"}, timeout=20).json()
    title = post["title"]["rendered"]
    body = post["content"]["rendered"]
    old_media_id = post.get("featured_media", 0)
    print("post:", title)

    old_img_urls = set(re.findall(r'<img[^>]+src="([^"]+)"', body))

    import replicate_image_provider
    subject = "Seoul city hall public wedding ceremony hall, empty formal wedding registration room, no people, wide angle"
    new_url = replicate_image_provider.generate_image_url(subject, theme="Wedding Planning")
    if not new_url:
        print("no replacement image available"); return 1
    print("new image:", new_url)

    media_resp = requests.get(new_url, timeout=30)
    media_resp.raise_for_status()
    ext = "jpg" if "jpg" in new_url or "jpeg" in new_url else "webp" if "webp" in new_url else "png"
    upload = requests.post(f"{SITE}/wp-json/wp/v2/media", auth=AUTH, timeout=30,
                            headers={"Content-Disposition": f'attachment; filename="koreawedding-888-{POST_ID}.{ext}"'},
                            data=media_resp.content)
    upload.raise_for_status()
    media = upload.json()
    new_media_id = media["id"]
    new_source_url = media["source_url"]
    print("uploaded media id:", new_media_id, new_source_url)

    new_body = body
    for old_url in old_img_urls:
        new_body = new_body.replace(old_url, new_source_url)

    update = requests.post(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", auth=AUTH, timeout=30,
                            json={"featured_media": new_media_id, "content": new_body})
    update.raise_for_status()
    print("post updated, new featured_media:", new_media_id)

    if old_media_id and old_media_id != new_media_id:
        delete = requests.delete(f"{SITE}/wp-json/wp/v2/media/{old_media_id}", auth=AUTH,
                                  params={"force": "true"}, timeout=20)
        print("old media delete status:", delete.status_code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
