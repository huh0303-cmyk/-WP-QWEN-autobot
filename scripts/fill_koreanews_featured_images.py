"""Fill missing Koreanews365 featured images from Pexels/Pixabay with attribution."""
from __future__ import annotations
import os, re, time
from pathlib import Path
from urllib.parse import quote
import requests

SITE = "https://koreanews365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("KOREANEWS365COM", "").strip()
PEXELS = os.getenv("PEXELS_API_KEY", "").strip() or os.getenv("PEXELS_KEY", "").strip()
PIXABAY = os.getenv("PIXABAY_API_KEY", "").strip() or os.getenv("PIXABAY_KEY", "").strip()
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Koreanews365-ImageDesk/1.0"

KEYWORDS = [
    (("옥수수", "버거", "피망", "식품"), "Korean food market vegetables"),
    (("폭염", "열대야", "기온", "날씨"), "Seoul summer heat city"),
    (("근로자", "고용", "노동", "52시간"), "Korean office workers business meeting"),
    (("정치", "정부", "여권", "정청래", "김민석", "표심"), "South Korea National Assembly Seoul"),
    (("미국", "성장률", "물가", "경제"), "New York financial district economy"),
    (("반도체", "AI", "기술", "산업"), "semiconductor technology laboratory"),
    (("주식", "금융", "증시", "투자"), "stock market financial charts"),
    (("국방", "군사", "안보", "훈련"), "military training soldiers"),
    (("부동산", "아파트", "주택"), "Seoul apartment buildings skyline"),
    (("문화", "예술", "공연"), "Korean traditional culture performance"),
    (("스포츠", "야구", "축구"), "sports stadium Korea"),
]

def api(method, path, **kwargs):
    response = SESSION.request(method, f"{SITE}/wp-json/wp/v2/{path}", auth=(USER, PASSWORD), timeout=60, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}

def clean(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()

def query_for(title):
    for needles, query in KEYWORDS:
        if any(word in title for word in needles): return query
    return "Seoul Korea city news"

def find_photo(query, excluded):
    if PEXELS:
        response = SESSION.get("https://api.pexels.com/v1/search", headers={"Authorization": PEXELS},
            params={"query": query, "per_page": 30, "orientation": "landscape", "size": "large"}, timeout=30)
        if response.ok:
            for photo in response.json().get("photos", []):
                page = photo.get("url", "")
                if page and page not in excluded:
                    return {"download": photo["src"].get("large2x") or photo["src"]["large"], "page": page,
                        "credit": f"Photo by {photo.get('photographer','Pexels contributor')} / Pexels"}
    if PIXABAY:
        response = SESSION.get("https://pixabay.com/api/", params={"key": PIXABAY, "q": query,
            "image_type": "photo", "orientation": "horizontal", "safesearch": "true", "per_page": 30}, timeout=30)
        if response.ok:
            for photo in response.json().get("hits", []):
                page = photo.get("pageURL", "")
                if page and page not in excluded:
                    return {"download": photo.get("largeImageURL") or photo.get("webformatURL"), "page": page,
                        "credit": f"Image by {photo.get('user','Pixabay contributor')} / Pixabay"}
    return None

def upload(post, photo, index):
    title = clean(post["title"]["rendered"])
    content = SESSION.get(photo["download"], timeout=60).content
    if len(content) < 20_000: raise RuntimeError("Downloaded image is too small")
    filename = f"koreanews-{post['id']}-{index}.jpg"
    response = SESSION.post(f"{SITE}/wp-json/wp/v2/media", auth=(USER, PASSWORD), timeout=90,
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": "image/jpeg"}, data=content)
    response.raise_for_status()
    media_id = response.json()["id"]
    alt = f"{title} 관련 뉴스 이미지"
    caption = f"{photo['credit']} · Source: {photo['page']}"
    api("POST", f"media/{media_id}", json={"alt_text": alt, "caption": caption,
        "description": f"{alt}. {caption}"})
    api("POST", f"posts/{post['id']}", json={"featured_media": media_id})
    return media_id

def main():
    if not PASSWORD: raise SystemExit("Missing KOREANEWS365COM")
    if not (PEXELS or PIXABAY): raise SystemExit("Missing Pexels/Pixabay API key")
    posts = api("GET", "posts", params={"status": "publish", "per_page": 30, "orderby": "date", "order": "desc",
        "_fields": "id,date,slug,title,featured_media"})
    missing = [post for post in posts if not post.get("featured_media")][:20]
    excluded = set(); completed = []
    for index, post in enumerate(missing, 1):
        title = clean(post["title"]["rendered"]); query = query_for(title)
        photo = find_photo(query, excluded)
        if not photo:
            print(f"SKIP {post['id']}: no image for {query}"); continue
        try:
            media_id = upload(post, photo, index); excluded.add(photo["page"])
            completed.append((post["id"], media_id, title, photo["page"]))
            print(f"OK {post['id']} -> media {media_id}: {title}")
        except Exception as exc:
            print(f"ERROR {post['id']}: {exc}")
        time.sleep(.4)
    print(f"Filled {len(completed)} of {len(missing)} missing published posts")
    if missing and not completed: raise SystemExit(2)

if __name__ == "__main__": main()
