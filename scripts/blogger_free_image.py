"""Free-only image step for Blogger posts. Order (all-free):
  1) Pexels  2) Pixabay  3) Wikimedia Commons (CC0/PD)  4) no image (caller falls back to a topic card).
2026-10-10 Chairman: Pollinations/AI images are removed for good (watermarked, uncanny); every photo is 1:1.
Never blocks publication: every failure returns None. No paid API is ever called."""
from __future__ import annotations
import html, json, os, random, re
from pathlib import Path
from urllib.parse import urlparse
import requests

RUNTIME = Path("/etc/korea365/article-runtime.json")
UA = {"User-Agent": "Korea365-Control/1.0"}
STOP = set("a an the of in on at for and with to your you guide complete best how what why korea korean".split())


def _key(name: str) -> str:
    v = os.getenv(name, "").strip()
    if v:
        return v
    try:
        return str(json.loads(RUNTIME.read_text(encoding="utf-8")).get(name, "")).strip()
    except (OSError, ValueError):
        return ""


def _words(text: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP}


def _relevant(query: str, description: str) -> bool:
    """Relaxed: at least one meaningful query word appears in the photo description."""
    q = _words(query)
    return bool(q) and bool(q & _words(description))


def _is_image(url: str) -> bool:
    try:
        r = requests.get(url, headers=UA, timeout=25, stream=True)
        ok = r.status_code == 200 and r.headers.get("content-type", "").lower().startswith("image/")
        r.close()
        return ok
    except requests.RequestException:
        return False



_USED_CACHE: dict = {}


def photo_id_from_url(url: str) -> str:
    m = re.search(r"pexels-photo-(\d+)|/photos/(\d+)/", url or "")
    return (m.group(1) or m.group(2)) if m else ""


def used_photo_ids() -> set[str]:
    """Photo ids already used on any of our Blogger blogs (live scan, cached per process, fail-open).
    Prevents the 'first search hit' picker from putting the same photo on many posts/sites."""
    if "ids" in _USED_CACHE:
        return _USED_CACHE["ids"]
    ids: set[str] = set()
    try:
        cid, sec, ref = (os.environ.get(k) for k in ("BLOGGER_GOOGLE_CLIENT_ID", "BLOGGER_GOOGLE_CLIENT_SECRET", "BLOGGER_GOOGLE_REFRESH_TOKEN"))
        if cid and sec and ref:
            tok = requests.post("https://oauth2.googleapis.com/token", data={"client_id": cid, "client_secret": sec,
                                "refresh_token": ref, "grant_type": "refresh_token"}, timeout=20).json()["access_token"]
            root = Path(__file__).resolve().parents[1]
            prof = json.loads((root / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
            for row in prof["profiles"]:
                bid = (row.get("blogspot") or {}).get("destination_id")
                if not bid:
                    continue
                r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{bid}/posts", headers={"Authorization": f"Bearer {tok}"},
                                 params={"maxResults": 500, "fetchBodies": "false", "fetchImages": "true", "status": "LIVE"}, timeout=30)
                if r.ok:
                    for post in r.json().get("items", []):
                        ids.update(filter(None, (photo_id_from_url(i.get("url", "")) for i in post.get("images", []))))
    except Exception as exc:  # never block publishing on the dedup scan
        print(f"used-photo scan unavailable ({type(exc).__name__})")
    _USED_CACHE["ids"] = ids
    return ids


def _pexels_square(p: dict) -> str:
    """Pexels serves imgix-resized files: ask for a centred 1:1 crop directly (no hosting needed)."""
    base = (p.get("src", {}).get("original") or p.get("src", {}).get("large") or "").split("?")[0]
    return f"{base}?auto=compress&cs=tinysrgb&fit=crop&w=1080&h=1080" if base else ""


def _pexels(query: str, exclude=frozenset()):
    key = _key("PEXELS_API_KEY")
    if not key:
        return None
    ordered = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2 and w not in STOP]
    variants = [query, " ".join(ordered[:3]), " ".join(ordered[:2]), (ordered[0] if ordered else "")]
    for q in dict.fromkeys(v for v in variants if v):  # full query first, then progressively looser retries
        r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key},
                         params={"query": q, "per_page": 30}, timeout=15)  # any orientation: the 1:1 crop handles it
        r.raise_for_status()
        for p in r.json().get("photos", []):
            if str(p.get("id")) in exclude or min(p.get("width", 0), p.get("height", 0)) < 800:
                continue
            url = _pexels_square(p)
            if urlparse(url).hostname == "images.pexels.com" and _relevant(q, p.get("alt", "")) and _is_image(url):
                return {"url": url, "provider": "Pexels", "id": str(p["id"]), "desc": p.get("alt", "")}
    return None


def _pixabay(query: str, exclude=frozenset()):
    key = _key("PIXABAY_KEY")
    if not key:
        return None
    ordered = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2 and w not in STOP]
    variants = [query, " ".join(ordered[:3]), " ".join(ordered[:2]), (ordered[0] if ordered else "")]
    for q in dict.fromkeys(v for v in variants if v):
        r = requests.get("https://pixabay.com/api/", params={"key": key, "q": q[:100], "image_type": "photo",
                         "safesearch": "true", "min_width": 800, "min_height": 800, "per_page": 40}, timeout=15)
        r.raise_for_status()
        for p in r.json().get("hits", []):
            if str(p.get("id")) in exclude:
                continue
            url = p.get("largeImageURL", "")
            if urlparse(url).hostname == "pixabay.com" or str(urlparse(url).hostname).endswith(".pixabay.com"):
                if _relevant(q, p.get("tags", "")):  # hosting step centre-crops to 1:1
                    return {"url": url, "provider": "Pixabay", "id": str(p["id"]), "desc": p.get("tags", ""), "needs_hosting": True}
    return None


_pexels.accepts_exclude = True
_pixabay.accepts_exclude = True


def _wikimedia(query: str):
    r = requests.get("https://commons.wikimedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"filetype:bitmap {query}", "gsrlimit": 20, "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1200}, headers=UA, timeout=20)
    r.raise_for_status()
    for page in (r.json().get("query", {}).get("pages", {}) or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = str((meta.get("LicenseShortName") or {}).get("value") or "").lower()
        url = info.get("thumburl") or info.get("url") or ""
        title = str(page.get("title") or "").removeprefix("File:")
        if lic in {"cc0", "public domain", "pdm"} and urlparse(url).hostname == "upload.wikimedia.org" \
                and _relevant(query, title) and _is_image(url):
            return {"url": url, "provider": "Wikimedia", "id": str(page.get("pageid")), "desc": title}
    return None


def pick_image(query: str, alternates=()):
    """Return {url, alt-ready desc, provider} or None.
    Source order: Pexels/Pixabay (random order), then Wikimedia; within each source the specific query is tried
    first, then looser alternates (e.g. the site's topic) so a relevant-enough photo is found almost always."""
    queries = []
    for q in [query, *alternates]:
        q = " ".join(str(q or "").split())[:100]
        if _words(q) and q not in queries:
            queries.append(q)
    if not queries:
        return None
    exclude = used_photo_ids()
    # 2026-10-09: Pexels/Pixabay 둘 중 하나를 매번 고정으로 먼저 호출하지 않도록 둘의
    # 순서만 무작위로 섞는다(Chairman 지시) — Wikimedia/AI는 그 뒤 순서 고정 유지.
    pexels_pixabay = [_pexels, _pixabay]
    random.shuffle(pexels_pixabay)
    for fn in (*pexels_pixabay, _wikimedia):
        found = None
        for q in queries:
            try:
                found = fn(q, exclude) if getattr(fn, "accepts_exclude", False) else fn(q)
            except Exception as exc:  # never log request URLs (keys)
                print(f"image source unavailable: {fn.__name__} ({type(exc).__name__})")
                break
            if found:
                break
        if not found:
            continue
        if found.get("needs_hosting") or found["provider"] == "Wikimedia":  # hosting also centre-crops to 1:1
            try:
                from stable_image_hosting import host_permanently
                found["url"] = host_permanently(found["url"], asset_key=f"blogger-{found['provider'].lower()}-{found['id']}", folder="blogger_images")
            except Exception as exc:
                print(f"image hosting unavailable: {found['provider']} ({type(exc).__name__})")
                if found.get("needs_hosting"):
                    continue
        print(f"image selected: {found['provider']} {found['id']}")
        return found
    return None


def insert_image(body_html: str, found: dict, alt_text: str) -> str:
    """Place the figure after the first paragraph (or at top). ALT = article title; no visible licence copy."""
    fig = ('<div class="separator" style="clear:both;text-align:center;margin:0 0 1.2em">'
           f'<img src="{html.escape(found["url"], quote=True)}" alt="{html.escape(alt_text, quote=True)}" '
           'style="max-width:100%;height:auto;aspect-ratio:1/1" loading="lazy" width="1080" height="1080"/></div>')
    m = re.search(r"</p>", body_html, re.I)
    return body_html[:m.end()] + "\n" + fig + body_html[m.end():] if m else fig + "\n" + body_html
