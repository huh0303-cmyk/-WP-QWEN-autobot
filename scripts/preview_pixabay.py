import os
import socket
import requests

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

PIXABAY_KEY = os.environ["PIXABAY_KEY"]
for query in ["Seoul Korea city skyline", "Korea hanbok Seoul palace", "Gyeongbokgung palace Korea"]:
    r = requests.get("https://pixabay.com/api/", params={
        "key": PIXABAY_KEY, "q": query, "image_type": "photo",
        "orientation": "horizontal", "safesearch": "true", "min_width": 1200, "per_page": 6,
    }, timeout=15)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    print(f"=== {query} ({len(hits)} hits) ===")
    for h in hits[:6]:
        print(" ", h["id"], h["tags"], h["pageURL"])
