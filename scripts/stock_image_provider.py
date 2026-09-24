"""Strict stock-photo selection before paid generation. No paid matching calls."""
from __future__ import annotations
import hashlib
import html
import json
import os
from pathlib import Path
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
            params={"query": query, "orientation": "landscape", "per_page": 12}, timeout=12)
        response.raise_for_status()
        items = [{"id": str(p["id"]), "description": p.get("alt", ""),
                  "url": p.get("src", {}).get("large2x", ""), "source": p.get("url", ""),
                  "author": p.get("photographer", ""), "width": p.get("width", 0),
                  "height": p.get("height", 0)} for p in response.json().get("photos", [])]
    else:
        response = requests.get("https://pixabay.com/api/", params={"key": key, "q": query,
            "image_type": "photo", "orientation": "horizontal", "safesearch": "true",
            "min_width": 1000, "per_page": 12}, timeout=12)
        response.raise_for_status()
        items = [{"id": str(p["id"]), "description": p.get("tags", ""),
                  "url": p.get("largeImageURL", ""), "source": p.get("pageURL", ""),
                  "author": p.get("user", ""), "width": p.get("imageWidth", 0),
                  "height": p.get("imageHeight", 0)} for p in response.json().get("hits", [])]
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"at": time.time(), "items": items}), encoding="utf-8")
    return items


def find_stock_image(subject, theme=""):
    if os.getenv("STOCK_IMAGES_ENABLED", "false").lower() != "true":
        return None
    # Stock cannot document a particular breaking event or identify a patient.
    if "NEWS ILLUSTRATION ONLY" in theme or SENSITIVE.search(subject + " " + theme):
        return None
    from editorial_topic_scope import stock_query
    query = " ".join(stock_query(subject, theme).split())
    if not query or len(query) > 100 or not terms(query):
        return None
    for provider, key, domain, license_url in [
        ("Pexels", os.getenv("PEXELS_API_KEY", ""), "images.pexels.com", "https://www.pexels.com/license/"),
        ("Pixabay", os.getenv("PIXABAY_KEY", ""), "pixabay.com", "https://pixabay.com/service/license-summary/")]:
        if not key:
            print(f"stock search unavailable: {provider} key missing")
            continue
        try:
            for item in _search(provider, query, key):
                host = urlparse(item["url"]).hostname or ""
                source_host = urlparse(item["source"]).hostname or ""
                source_domain = "pexels.com" if provider == "Pexels" else "pixabay.com"
                if not (host == domain or host.endswith("." + domain)):
                    continue
                if not (source_host == source_domain or source_host.endswith("." + source_domain)):
                    continue
                if not item["url"].startswith("https://") or not item["source"].startswith("https://"):
                    continue
                if item["width"] < 1000 or item["width"] <= item["height"] or not matches(query, item["description"]):
                    continue
                from stable_image_hosting import host_permanently
                stable = host_permanently(item["url"], asset_key=f"stock-{provider.lower()}-{item['id']}")
                metadata = {**item, "provider": provider, "license": license_url,
                            "query": query, "estimated_image_cost_usd": 0, "hosted_url": stable}
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
    r"illustrative\\s+stock\\s+photo|photo\\s+license|"
    r"not\\s+a\\s+photograph\\s+of\\s+a\\s+specific\\s+event|"
    r"stock\\s+photo\\s*/\\s*자료사진|class=[\"']?photo-credit",
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
