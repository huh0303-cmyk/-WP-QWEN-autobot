#!/usr/bin/env python3
"""User-approved: publish two original articles (5 digital-product side-income
ideas each) to kfinance365.com, the closest-fitting existing WP site for this
topic. Original writing, not a reproduction of any specific creator's video."""
import hashlib
import os
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parent

WP_USER = "huh0303@gmail.com"
PW = os.environ["KFINANCE365COM"]
BASE = "https://kfinance365.com/wp-json/wp/v2"
AUTH = HTTPBasicAuth(WP_USER, PW)
PEXELS_KEY = os.environ["PEXELS_API_KEY"]

ARTICLES = [
    {
        "title": "5 Digital Products You Can Build Once and Sell Again and Again",
        "file": "digital_products_article1.html",
        "meta_description": "Five build-once digital product ideas for extra income in Korea: checklists, calculators, Notion templates, workbooks, and slide decks.",
        "tags": ["side income", "digital products", "passive income", "personal finance Korea", "extra income"],
        "image_query": "laptop workspace planning notebook",
    },
    {
        "title": "5 More Digital Product Ideas for Extra Income While Living in Korea",
        "file": "digital_products_article2.html",
        "meta_description": "More build-once digital product ideas: job-transition packages, seller toolkits, mini-courses, photo packs, and B2B document templates.",
        "tags": ["side income", "digital products", "freelance Korea", "extra income", "small business templates"],
        "image_query": "freelancer working laptop desk",
    },
]


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
        return None
    return photos[0]["src"]["large2x"]


def rehost(image_url, tag):
    image = requests.get(image_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    image.raise_for_status()
    mime = image.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
    ext = ".png" if "png" in mime else ".webp" if "webp" in mime else ".jpg"
    filename = "digitalprod-" + tag + "-" + hashlib.md5(image_url.encode()).hexdigest()[:8] + ext
    r = requests.post(
        f"{BASE}/media", auth=AUTH,
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime},
        data=image.content, timeout=35,
    )
    r.raise_for_status()
    return r.json()["id"]


def resolve_category():
    r = requests.get(f"{BASE}/categories", params={"per_page": 100}, timeout=20)
    r.raise_for_status()
    cats = r.json()
    keywords = ("income", "finance", "money", "saving", "budget")
    for c in cats:
        name = c["name"].lower()
        if any(k in name for k in keywords):
            return c["id"]
    return None


def resolve_tag_ids(names):
    ids = []
    for name in names:
        r = requests.get(f"{BASE}/tags", params={"search": name}, timeout=20)
        r.raise_for_status()
        existing = next((t for t in r.json() if t["name"].lower() == name.lower()), None)
        if existing:
            ids.append(existing["id"])
            continue
        created = requests.post(f"{BASE}/tags", auth=AUTH, json={"name": name}, timeout=20)
        if created.status_code in (200, 201):
            ids.append(created.json()["id"])
    return ids


category_id = resolve_category()
print("category_id:", category_id)

for article in ARTICLES:
    with open(ROOT / article["file"], "r", encoding="utf-8") as f:
        content_html = f.read()
    image_url = pexels_search(article["image_query"])
    media_id = rehost(image_url, article["file"].split(".")[0]) if image_url else None
    tag_ids = resolve_tag_ids(article["tags"])
    data = {
        "title": article["title"],
        "content": content_html,
        "status": "publish",
        "comment_status": "closed",
        "ping_status": "closed",
        "tags": tag_ids,
        "meta": {
            "rank_math_focus_keyword": "digital products side income",
            "rank_math_description": article["meta_description"],
        },
    }
    if category_id:
        data["categories"] = [category_id]
    if media_id:
        data["featured_media"] = media_id
    r = requests.post(f"{BASE}/posts", auth=AUTH, json=data, timeout=30)
    r.raise_for_status()
    payload = r.json()
    print("PUBLISHED:", payload.get("id"), payload.get("link"))
