import os
import socket
import requests

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

SITE = "https://koreamedicaltour.com"
AUTH = ("huh0303@gmail.com", os.environ["KOREAMEDICALTOURCOM"])
PIXABAY_KEY = os.environ["PIXABAY_KEY"]
POST_ID = 1729
# the wrong Japanese-Nebuta-festival image installed a moment ago; replace again
OLD_IMAGE_URL = "https://koreamedicaltour.com/wp-content/uploads/2026/09/kmt-festival-fix-3317010.jpg"
PIXABAY_PHOTO_ID = 3315324  # verified: "palace, travel, republic of korea, korea, seoul, gyeongbok palace, traditional, tourism, people"

r = requests.get("https://pixabay.com/api/", params={"key": PIXABAY_KEY, "id": PIXABAY_PHOTO_ID}, timeout=15)
r.raise_for_status()
hits = r.json().get("hits", [])
if not hits:
    raise SystemExit("photo id not found")
photo = hits[0]
print("using:", photo["tags"], photo["pageURL"])

img = requests.get(photo["largeImageURL"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
img.raise_for_status()
content_type = img.headers.get("content-type", "image/jpeg")
ext = "png" if "png" in content_type else "jpg"
fname = f"kmt-festival-fix-v2-{photo['id']}.{ext}"

upload = requests.post(f"{SITE}/wp-json/wp/v2/media", auth=AUTH, timeout=30,
                        headers={"Content-Disposition": f'attachment; filename="{fname}"',
                                 "Content-Type": content_type},
                        data=img.content)
upload.raise_for_status()
media = upload.json()
new_url = media["source_url"]
new_id = media["id"]
print("uploaded media id", new_id, new_url)

get_post = requests.get(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", auth=AUTH,
                         params={"_fields": "content"}, timeout=20)
get_post.raise_for_status()
content = get_post.json()["content"]["rendered"]
if OLD_IMAGE_URL not in content:
    print("WARNING: old image url not found in content, skipping content replace")
    new_content = content
else:
    new_content = content.replace(OLD_IMAGE_URL, new_url)

update = requests.post(f"{SITE}/wp-json/wp/v2/posts/{POST_ID}", auth=AUTH, timeout=30,
                        json={"featured_media": new_id, "content": new_content})
update.raise_for_status()
print("post updated:", update.status_code)
