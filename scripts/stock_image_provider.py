"""Strict stock-photo selection before paid generation. No paid matching calls."""
from __future__ import annotations
import hashlib
import html
import json
import os
from pathlib import Path
import random
import re
import time
from urllib.parse import urlparse
import requests

CACHE = Path(os.getenv("STOCK_IMAGE_CACHE_DIR", "data/stock_image_cache"))
METADATA = {}
STOP = set("a an the of in on at for and with photo photograph image scene editorial realistic beautiful natural lighting composition close up view illustration about related".split())
SENSITIVE = re.compile(r"\b(war|strike|attack|casualty|cancer|disease|patient|diagnosis|crime|arrest)\b|전쟁|공습|환자|질병|범죄", re.I)


def terms(text):
    return {w.rstrip("s") for w in re.findall(r"[a-zA-Z0-9가-힣]+", text.lower()) if len(w) > 2 and w not in STOP}


def matches(subject, description):
    required = terms(subject)
    # Never substitute a broad generic image for an unknown named subject.
    return bool(required) and required <= terms(description)


def query_variants(query):
    """Full query, then progressively shorter ones (3 words, 2 words, first word)."""
    words = re.findall(r"[a-zA-Z0-9가-힣]+", query)
    out = [query]
    for n in (3, 2, 1):
        if len(words) > n:
            out.append(" ".join(words[:n]))
    return list(dict.fromkeys(out))


def _search(provider, query, key):
    cache_key = hashlib.sha256(f"{provider}:{query}".encode()).hexdigest()
    path = CACHE / (cache_key + ".json")
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - cached["at"] < 86400:
            return cached["items"]
    except (OSError, ValueError, KeyError):
        pass
    if provider == "Pexels":
        response = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": key},
            params={"query": query, "per_page": 30}, timeout=12)
        response.raise_for_status()
        items = [{"id": str(p["id"]), "description": p.get("alt", ""),
                  "url": p.get("src", {}).get("large2x", ""), "source": p.get("url", ""),
                  "author": p.get("photographer", ""), "width": p.get("width", 0),
                  "height": p.get("height", 0)} for p in response.json().get("photos", [])]
    elif provider == "Pixabay":
        response = requests.get("https://pixabay.com/api/", params={"key": key, "q": query,
            "image_type": "photo", "safesearch": "true",
            "min_width": 800, "min_height": 800, "per_page": 40}, timeout=12)
        response.raise_for_status()
        items = [{"id": str(p["id"]), "description": p.get("tags", ""),
                  "url": p.get("largeImageURL", ""), "source": p.get("pageURL", ""),
                  "author": p.get("user", ""), "width": p.get("imageWidth", 0),
                  "height": p.get("imageHeight", 0)} for p in response.json().get("hits", [])]
    else:
        response = requests.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "format": "json", "generator": "search",
            "gsrnamespace": 6, "gsrsearch": f"filetype:bitmap {query}", "gsrlimit": 20,
            "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600,
        }, headers={"User-Agent": "Korea365-Control/1.0"}, timeout=15)
        response.raise_for_status()
        items = []
        for page in (response.json().get("query", {}).get("pages", {}) or {}).values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = str((meta.get("LicenseShortName") or {}).get("value") or "").lower()
            if license_name not in {"cc0", "public domain", "pdm"}:
                continue
            items.append({
                "id": str(page.get("pageid") or ""),
                "description": " ".join(filter(None, [str(page.get("title") or "").removeprefix("File:"), str((meta.get("ImageDescription") or {}).get("value") or "")])),
                "url": info.get("thumburl") or info.get("url") or "",
                "source": info.get("descriptionurl") or "",
                "author": str((meta.get("Artist") or {}).get("value") or ""),
                "width": info.get("thumbwidth") or info.get("width") or 0,
                "height": info.get("thumbheight") or info.get("height") or 0,
                "license": str((meta.get("LicenseUrl") or {}).get("value") or "https://creativecommons.org/publicdomain/mark/1.0/"),
            })
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"at": time.time(), "items": items}), encoding="utf-8")
    return items


def find_stock_image(subject, theme="", *, force=False, selected_provider="auto"):
    if not force and os.getenv("STOCK_IMAGES_ENABLED", "false").lower() != "true":
        return None
    # Stock cannot document a particular breaking event or identify a patient.
    if "NEWS ILLUSTRATION ONLY" in theme or SENSITIVE.search(subject + " " + theme):
        return None
    from editorial_topic_scope import stock_query
    query = " ".join(stock_query(subject, theme).split())
    if not query or len(query) > 100 or not terms(query):
        return None
    # 2026-10-09: Pexels/Pixabay 둘 중 하나를 매번 고정으로 먼저 호출하지 않도록 둘의
    # 순서만 무작위로 섞는다(Chairman 지시, blogger_free_image.py와 동일 로직) — Wikimedia는
    # 그 뒤 순서 고정 유지.
    pexels_pixabay_providers = [
        ("Pexels", os.getenv("PEXELS_API_KEY", ""), "images.pexels.com", "https://www.pexels.com/license/"),
        ("Pixabay", os.getenv("PIXABAY_KEY", ""), "pixabay.com", "https://pixabay.com/service/license-summary/"),
    ]
    random.shuffle(pexels_pixabay_providers)
    for provider, key, domain, license_url in [
        *pexels_pixabay_providers,
        ("Wikimedia", "public-api", "upload.wikimedia.org", "https://creativecommons.org/publicdomain/mark/1.0/")]:
        if selected_provider != "auto" and provider.lower() != selected_provider:
            continue
        if not key:
            print(f"stock search unavailable: {provider} key missing")
            continue
        try:
            if True:  # full query first, then shorter variants; each variant must still match strictly (no off-subject photos)
                for q in query_variants(query):
                    for item in _search(provider, q, key):
                        host = urlparse(item["url"]).hostname or ""
                        source_host = urlparse(item["source"]).hostname or ""
                        source_domain = {"Pexels": "pexels.com", "Pixabay": "pixabay.com", "Wikimedia": "commons.wikimedia.org"}[provider]
                        if not (host == domain or host.endswith("." + domain)):
                            continue
                        if not (source_host == source_domain or source_host.endswith("." + source_domain)):
                            continue
                        if not item["url"].startswith("https://") or not item["source"].startswith("https://"):
                            continue
                        # 1:1 crop makes orientation irrelevant; only require a usable short side.
                        if min(item["width"], item["height"]) < 800:
                            continue
                        if not matches(q, item["description"]):
                            continue
                        from stable_image_hosting import host_permanently  # also centre-crops to 1:1
                        stable = host_permanently(item["url"], asset_key=f"stock-{provider.lower()}-{item['id']}")
                        metadata = {**item, "provider": provider, "license": item.get("license") or license_url,
                                    "query": q, "estimated_image_cost_usd": 0, "hosted_url": stable}
                        METADATA[stable] = metadata
                        receipt = Path("artifacts/stock-image-receipts.jsonl")
                        receipt.parent.mkdir(parents=True, exist_ok=True)
                        with receipt.open("a", encoding="utf-8") as handle:
                            handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
                        print(f"stock photo selected: {provider} {item['id']}; image API estimate $0")
                        return stable
        except Exception as exc:
            # Never log the request URL: Pixabay's query includes its secret key.
            print(f"stock search/hosting unavailable: {provider} ({type(exc).__name__})")
    return None


PUBLIC_PHOTO_NOTICE = re.compile(
    r"illustrative\s+stock\s+photo|photo\s+license|"
    r"not\s+a\s+photograph\s+of\s+a\s+specific\s+event|"
    r"stock\s+photo\s*/\s*자료사진|class=[\"']?photo-credit",
    re.I,
)


def contains_public_photo_credit(content):
    """True when internal stock/licensing provenance leaked into reader-visible copy."""
    return bool(PUBLIC_PHOTO_NOTICE.search(html.unescape(str(content or ""))))


def credit_html(url):
    """Never expose stock-provider/licence operations in reader-visible article HTML.

    Rights/source provenance is already persisted by find_stock_image() in
    artifacts/stock-image-receipts.jsonl and must remain internal.  Keeping
    this function as a no-op makes every legacy caller safe without requiring
    each publishing path to remember the rule independently.
    """
    return ""
