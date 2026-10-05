"""Free-only image step for Blogger posts. Order (Chairman 2026-10-05, all-free):
  1) Pexels  2) Pixabay  3) Wikimedia Commons (CC0/PD)  4) free AI (Pollinations, needs hosting)  5) no image.
Never blocks publication: every failure returns None. No paid API is ever called."""
from __future__ import annotations
import html, json, os, re
from pathlib import Path
from urllib.parse import quote, urlparse
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


def _pexels(query: str):
    key = _key("PEXELS_API_KEY")
    if not key:
        return None
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key},
                     params={"query": query, "orientation": "landscape", "per_page": 12}, timeout=15)
    r.raise_for_status()
    for p in r.json().get("photos", []):
        url = p.get("src", {}).get("large", "")
        if urlparse(url).hostname == "images.pexels.com" and p.get("width", 0) > p.get("height", 0) \
                and _relevant(query, p.get("alt", "")) and _is_image(url):
            return {"url": url, "provider": "Pexels", "id": str(p["id"]), "desc": p.get("alt", "")}
    return None


def _pixabay(query: str):
    key = _key("PIXABAY_KEY")
    if not key:
        return None
    r = requests.get("https://pixabay.com/api/", params={"key": key, "q": query, "image_type": "photo",
                     "orientation": "horizontal", "safesearch": "true", "min_width": 1000, "per_page": 12}, timeout=15)
    r.raise_for_status()
    for p in r.json().get("hits", []):
        url = p.get("largeImageURL", "")
        if urlparse(url).hostname == "pixabay.com" or str(urlparse(url).hostname).endswith(".pixabay.com"):
            if _relevant(query, p.get("tags", "")):
                return {"url": url, "provider": "Pixabay", "id": str(p["id"]), "desc": p.get("tags", ""), "needs_hosting": True}
    return None


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
                and info.get("thumbwidth", 0) >= info.get("thumbheight", 0) and _relevant(query, title) and _is_image(url):
            return {"url": url, "provider": "Wikimedia", "id": str(page.get("pageid")), "desc": title}
    return None


def _ai_free(query: str):
    """Free AI fallback (Pollinations, no key). Hotlinks are unstable, so it is only used when hosting is possible."""
    if not (os.getenv("GH_ASSET_TOKEN") and os.getenv("GITHUB_REPOSITORY")):
        return None
    url = f"https://image.pollinations.ai/prompt/{quote('editorial photo, ' + query + ', natural light, no text')}?width=1200&height=675&nologo=true"
    if _is_image(url):
        return {"url": url, "provider": "Pollinations", "id": re.sub(r"\W+", "-", query)[:40], "desc": query, "needs_hosting": True}
    return None


def pick_image(query: str):
    """Return {url, alt-ready desc, provider} or None. Order is fixed; any failure moves to the next source."""
    query = " ".join(str(query or "").split())[:100]
    if not _words(query):
        return None
    for fn in (_pexels, _pixabay, _wikimedia, _ai_free):
        try:
            found = fn(query)
        except Exception as exc:  # never log request URLs (keys)
            print(f"blogger image source unavailable: {fn.__name__} ({type(exc).__name__})")
            continue
        if not found:
            continue
        if found.get("needs_hosting"):
            try:
                from stable_image_hosting import host_permanently
                found["url"] = host_permanently(found["url"], asset_key=f"blogger-{found['provider'].lower()}-{found['id']}", folder="blogger_images")
            except Exception as exc:
                print(f"blogger image hosting unavailable: {found['provider']} ({type(exc).__name__})")
                continue
        print(f"blogger image selected: {found['provider']} {found['id']}")
        return found
    return None


def insert_image(body_html: str, found: dict, alt_text: str) -> str:
    """Place the figure after the first paragraph (or at top). ALT = article title; no visible licence copy."""
    fig = ('<div class="separator" style="clear:both;text-align:center;margin:0 0 1.2em">'
           f'<img src="{html.escape(found["url"], quote=True)}" alt="{html.escape(alt_text, quote=True)}" '
           'style="max-width:100%;height:auto" loading="lazy" width="1200" height="675"/></div>')
    m = re.search(r"</p>", body_html, re.I)
    return body_html[:m.end()] + "\n" + fig + body_html[m.end():] if m else fig + "\n" + body_html
