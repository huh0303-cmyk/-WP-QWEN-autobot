#!/usr/bin/env python3
"""One-off: replace dead inline images (expired Replicate URLs) on koreainvest365.com
posts 3245 and 3241 with free Pexels photos, and rehost them to WP permanently."""
import hashlib
import os
import re
import requests
from requests.auth import HTTPBasicAuth

WP_USER = "huh0303@gmail.com"
PW = os.environ["KOREAINVEST365COM"]
PEXELS_KEY = os.environ["PEXELS_API_KEY"]
BASE = "https://koreainvest365.com/wp-json/wp/v2"
AUTH = HTTPBasicAuth(WP_USER, PW)

TARGETS = {
    3245: "esports gaming studio",
    3241: "sustainable finance investment",
}


def pexels_search(query):
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": query, "per_page": 1, "orientation": "landscape"},
        timeout=20,
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError(f"no pexels result for {query!r}")
    return photos[0]["src"]["large2x"]


def rehost(image_url):
    image = requests.get(image_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    image.raise_for_status()
    mime = image.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
    ext = ".png" if "png" in mime else ".webp" if "webp" in mime else ".jpg"
    filename = "pexels-" + hashlib.md5(image_url.encode()).hexdigest()[:12] + ext
    r = requests.post(
        f"{BASE}/media", auth=AUTH,
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime},
        data=image.content, timeout=35,
    )
    r.raise_for_status()
    return r.json()["source_url"]


for post_id, query in TARGETS.items():
    r = requests.get(f"{BASE}/posts/{post_id}", params={"_fields": "content"}, timeout=20)
    html = r.json()["content"]["rendered"]
    old_urls = re.findall(r'<img[^>]+src="([^"]+)"', html)
    if not old_urls:
        print(post_id, "no inline image found, skipping")
        continue
    old_url = old_urls[0]
    pexels_url = pexels_search(query)
    new_url = rehost(pexels_url)
    new_html = html.replace(old_url, new_url, 1)
    upd = requests.post(f"{BASE}/posts/{post_id}", auth=AUTH, json={"content": new_html}, timeout=30)
    print(post_id, "update status:", upd.status_code, "new image:", new_url)
