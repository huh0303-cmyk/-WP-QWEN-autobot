import os
import socket
import requests

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

SITE = "https://ksa-korea.org"
AUTH = ("huh0303@gmail.com", os.environ["KSAKOREAORG"])
PIXABAY_KEY = os.environ["PIXABAY_KEY"]

# (post_id, old_image_url, pixabay_photo_id, description)
FIXES = [
    (865, "https://ksa-korea.org/wp-content/uploads/2026/09/news-b5fca86fd7b0.png", None,
     "Seoul National University 2027 foreign admissions guide - was an eerie lone figure in an endless dark archive hall"),
    (863, "https://ksa-korea.org/wp-content/uploads/2026/09/news-995155b9ad05.png", None,
     "STEM scholarship application guide - was an incoherent AI scene (masked people in a restaurant-like room)"),
]

QUERIES = ["university campus students graduation", "korean university students studying library"]


BLOCKED_TAGS = ("japan", "china", "chinese", "japanese", "taiwan", "thailand", "vietnam")


def search(query):
    r = requests.get("https://pixabay.com/api/", params={
        "key": PIXABAY_KEY, "q": query, "image_type": "photo",
        "orientation": "horizontal", "safesearch": "true", "min_width": 1200, "per_page": 8,
    }, timeout=15)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    return [h for h in hits if not any(b in h["tags"].lower() for b in BLOCKED_TAGS)]


for i, (post_id, old_url, _, desc) in enumerate(FIXES):
    hits = search(QUERIES[i % len(QUERIES)])
    if not hits:
        print(f"post {post_id}: no pixabay results, skipped")
        continue
    photo = hits[0]
    print(f"post {post_id} ({desc}): using {photo['tags']} {photo['pageURL']}")

    img = requests.get(photo["largeImageURL"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    img.raise_for_status()
    content_type = img.headers.get("content-type", "image/jpeg")
    ext = "png" if "png" in content_type else "jpg"
    upload = requests.post(f"{SITE}/wp-json/wp/v2/media", auth=AUTH, timeout=30,
                            headers={"Content-Disposition": f'attachment; filename="ksa-{post_id}-fix-{photo["id"]}.{ext}"',
                                     "Content-Type": content_type},
                            data=img.content)
    upload.raise_for_status()
    media = upload.json()
    new_url = media["source_url"]
    new_id = media["id"]

    get_post = requests.get(f"{SITE}/wp-json/wp/v2/posts/{post_id}", auth=AUTH,
                             params={"_fields": "content"}, timeout=20)
    get_post.raise_for_status()
    content = get_post.json()["content"]["rendered"]
    new_content = content.replace(old_url, new_url) if old_url in content else content

    update = requests.post(f"{SITE}/wp-json/wp/v2/posts/{post_id}", auth=AUTH, timeout=30,
                            json={"featured_media": new_id, "content": new_content})
    update.raise_for_status()
    print(f"  updated: {update.status_code}, new image: {new_url}")
