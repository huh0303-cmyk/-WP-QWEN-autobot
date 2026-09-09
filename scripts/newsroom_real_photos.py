"""Reviewed photo assets supplement AI illustrations; never invent scene metadata."""
import html
import json
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

CATALOG = Path(__file__).resolve().parents[1] / "config/newsroom_real_photos.json"
DISCLAIMER = "The appearance of U.S. Department of War (DoW) visual information does not imply or constitute DoW endorsement."


def select_photo(topic, *, get=requests.get, catalog=None):
    assets = catalog if catalog is not None else json.loads(CATALOG.read_text(encoding="utf-8"))["assets"]
    for asset in assets:
        groups = asset.get("topic_groups", [])
        if not groups or not all(any(term.casefold() in topic.casefold() for term in group) for group in groups):
            continue
        # Only individually reviewed DVIDS assets are enabled at present. More
        # providers require their own item-level verification, not a domain guess.
        if (asset.get("license") != "public_domain" or asset.get("context") != "archive"
                or not all(asset.get(k) for k in ("taken", "credit", "caption_en", "caption_ko", "verified_on"))
                or urlparse(asset["source_page"]).hostname != "www.dvidshub.net"
                or urlparse(asset["image_url"]).hostname != "d1ldvf68ux039x.cloudfront.net"
                or not asset["image_url"].startswith("https://")):
            continue
        try:
            response = get(asset["source_page"], timeout=8)
            response.raise_for_status()
            text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
            if "PUBLIC DOMAIN" not in text or "NAVCENT Public Affairs" not in text:
                continue
        except requests.RequestException:
            continue
        return dict(asset)
    return None


def figure(asset, language="en"):
    caption = asset["caption_ko" if language == "ko" else "caption_en"]
    esc = html.escape
    return (f'<figure class="newsroom-real-photo"><img src="{esc(asset["image_url"], quote=True)}" '
            f'alt="{esc(caption, quote=True)}" style="width:100%;height:auto" loading="lazy">'
            f'<figcaption>{esc(caption)} '
            f'<a href="{esc(asset["source_page"], quote=True)}" rel="noopener">{esc(asset["credit"])}</a> · '
            f'<a href="{esc(asset["license_url"], quote=True)}" rel="license noopener">Public domain — usage conditions</a>. '
            f'{DISCLAIMER}</figcaption></figure>')
