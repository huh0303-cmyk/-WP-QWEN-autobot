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

# 1) fix dangling "-2026" title artifact left by an earlier year-cleanup pass
r = requests.post(f"{SITE}/wp-json/wp/v2/posts/661", auth=AUTH, timeout=20,
                   json={"title": "The Complete Rejuran Injection Seoul Price Guide (2026)"})
print("title fix:", r.status_code)

# 2) post 1730 has no featured image at all - give it one (Gyeongbokgung/travel, verified Korean)
photo_id = 7095478  # "hanok, gyeongbok palace, spring... seoul, south korea" - verified Korean landmark
pr = requests.get("https://pixabay.com/api/", params={"key": PIXABAY_KEY, "id": photo_id}, timeout=15)
pr.raise_for_status()
hits = pr.json().get("hits", [])
if hits:
    photo = hits[0]
    img = requests.get(photo["largeImageURL"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    img.raise_for_status()
    content_type = img.headers.get("content-type", "image/jpeg")
    ext = "png" if "png" in content_type else "jpg"
    upload = requests.post(f"{SITE}/wp-json/wp/v2/media", auth=AUTH, timeout=30,
                            headers={"Content-Disposition": f'attachment; filename="kmt-1730-fix-{photo_id}.{ext}"',
                                     "Content-Type": content_type},
                            data=img.content)
    upload.raise_for_status()
    media = upload.json()
    update = requests.post(f"{SITE}/wp-json/wp/v2/posts/1730", auth=AUTH, timeout=30,
                            json={"featured_media": media["id"]})
    print("post 1730 featured image set:", update.status_code, media["source_url"])
else:
    print("pixabay photo id not found for post 1730 fix")
