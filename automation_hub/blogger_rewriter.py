from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import requests


def plain_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", value)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", value))).strip()


def similarity(source_html: str, rewritten_html: str) -> float:
    return SequenceMatcher(None, plain_text(source_html).lower(), plain_text(rewritten_html).lower()).ratio()


def parse_rewrite_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    data = json.loads(cleaned)
    if not all(str(data.get(key, "")).strip() for key in ("title", "content_html", "image_query")):
        raise ValueError("rewrite output must include title, content_html and image_query")
    return data


def rewrite_prompt(source_title: str, source_html: str, source_url: str, *, language: str, persona: str, tone: str, target_chars: int) -> str:
    return f"""You are adapting an owned WordPress article for a different Blogspot audience.
Do not paraphrase sentence by sentence. Choose a different search intent and rebuild the outline, examples, checklist and FAQ.
Add useful original synthesis. Do not invent personal experience, statistics, quotes or sources.
Language: {language}. Persona: {persona}. Tone: {tone}. Target length: about {target_chars} characters.
Return JSON only with keys title, content_html, image_query, labels.
content_html must contain semantic HTML only (h2/h3/p/ul/ol/blockquote), no html/head/body, no images, no scripts.
End with a short paragraph linking to the owned detailed source using this exact URL: {source_url}
Source title: {source_title}
Source article:
{plain_text(source_html)[:18000]}
"""


@dataclass(slots=True)
class FreeImage:
    url: str
    page_url: str
    credit: str
    provider: str


def find_one_free_image(query: str, *, pexels_key: str = "", pixabay_key: str = "", session=requests) -> FreeImage | None:
    """Return exactly one free-stock image; never calls an AI image service."""
    if pexels_key:
        response = session.get("https://api.pexels.com/v1/search", headers={"Authorization": pexels_key}, params={"query": query, "per_page": 1, "orientation": "landscape"}, timeout=25)
        if response.status_code == 200 and response.json().get("photos"):
            photo = response.json()["photos"][0]
            return FreeImage(photo["src"].get("large2x") or photo["src"]["large"], photo["url"], f"Photo by {photo.get('photographer', 'Pexels contributor')} on Pexels", "Pexels")
    if pixabay_key:
        response = session.get("https://pixabay.com/api/", params={"key": pixabay_key, "q": query, "image_type": "photo", "orientation": "horizontal", "per_page": 3, "safesearch": "true"}, timeout=25)
        if response.status_code == 200 and response.json().get("hits"):
            photo = response.json()["hits"][0]
            return FreeImage(photo.get("largeImageURL") or photo["webformatURL"], photo["pageURL"], f"Image by {photo.get('user', 'Pixabay contributor')} on Pixabay", "Pixabay")
    return None


def attach_single_image(content_html: str, image: FreeImage, alt: str) -> str:
    figure = (
        f'<figure><img src="{html.escape(image.url, quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy">'
        f'<figcaption><a href="{html.escape(image.page_url, quote=True)}" rel="nofollow noopener">{html.escape(image.credit)}</a></figcaption></figure>'
    )
    return figure + content_html
