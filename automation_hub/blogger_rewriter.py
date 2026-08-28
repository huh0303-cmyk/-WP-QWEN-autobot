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


def extract_http_links(value: str) -> list[str]:
    links = re.findall(r'''(?is)href=["'](https?://[^"'#\s]+)''', value)
    return list(dict.fromkeys(html.unescape(link) for link in links))[:30]


def similarity(source_html: str, rewritten_html: str) -> float:
    return SequenceMatcher(None, plain_text(source_html).lower(), plain_text(rewritten_html).lower()).ratio()


def parse_rewrite_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    data = json.loads(cleaned)
    if not all(str(data.get(key, "")).strip() for key in ("title", "content_html", "meta_description")):
        raise ValueError("rewrite output must include title, content_html and meta_description")
    labels = data.get("labels", [])
    if isinstance(labels, str):
        labels = [item.strip() for item in labels.split(",") if item.strip()]
    data["labels"] = [str(item).strip() for item in labels if str(item).strip()][:14]
    if len(data["labels"]) < 8:
        raise ValueError("rewrite output must include 8-14 relevant labels")
    if any(len(label) > 30 or len(label.split()) > 3 for label in data["labels"]):
        raise ValueError("labels must be short noun search terms")
    queries = data.get("image_queries", [])
    if isinstance(queries, str):
        queries = [queries] if queries.strip() else []
    data["image_queries"] = [str(query).strip() for query in queries if str(query).strip()][:2]
    return data


def _clip_words(value: str, maximum: int) -> str:
    """Clip generated prose at a word boundary without adding new text."""
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= maximum:
        return value
    clipped = value[: maximum + 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return clipped or value[:maximum].rstrip()


def normalize_rewrite_format(article: dict[str, Any], *, target_chars: int, source_url: str = "", ymyl: bool = False) -> dict[str, Any]:
    """Fit Gemini output to Blogger's hard format limits before scoring.

    This only removes Gemini-generated words/HTML blocks. It never authors or
    invents replacement copy, so Blogger prose remains Gemini-written.
    """
    normalized = dict(article)
    normalized["title"] = _clip_words(str(article.get("title", "")), 70)
    meta_words = re.sub(r"\s+", " ", str(article.get("meta_description", ""))).strip().split()
    normalized["meta_description"] = " ".join(meta_words[:120])

    content = str(article.get("content_html", ""))
    maximum = int(target_chars * 1.35)
    if len(re.sub(r"\s+", "", plain_text(content))) > maximum:
        blocks = re.findall(r"(?is)<(?:h[23]|p|ul|ol|blockquote)(?:\s[^>]*)?>.*?</(?:h[23]|p|ul|ol|blockquote)>", content)
        required: list[str] = []
        for block in blocks:
            lower = plain_text(block).lower()
            if (source_url and source_url in block) or (ymyl and re.search(r"\b(as of|subject to change|rules can change|requirements can change|disclaimer|not medical advice|not legal advice)\b", lower)):
                required.append(block)
        required = list(dict.fromkeys(required))
        required_chars = len(re.sub(r"\s+", "", plain_text("".join(required))))
        needs_attribution = bool(source_url and not any(source_url in block for block in required))
        if needs_attribution:
            required_chars += 160
        kept: list[str] = []
        for block in blocks:
            if block in required:
                continue
            candidate = "".join(kept + [block])
            if len(re.sub(r"\s+", "", plain_text(candidate))) + required_chars > maximum:
                break
            kept.append(block)
        while kept and re.match(r"(?is)^<h[23]", kept[-1]):
            kept.pop()
        final_blocks = kept + [block for block in required if block not in kept]
        if needs_attribution:
            safe_url = html.escape(source_url, quote=True)
            final_blocks.append(f'<p>Original source: <a href="{safe_url}">{safe_url}</a></p>')
        if final_blocks:
            normalized["content_html"] = "".join(final_blocks)
    return normalized


def rewrite_prompt(source_title: str, source_html: str, source_url: str, *, language: str, persona: str, tone: str, target_chars: int, prior_feedback: str = "") -> str:
    verified_links = extract_http_links(source_html)
    verified_link_text = "\n".join(f"- {link}" for link in verified_links) or "- No additional verified links supplied"
    return f"""Write a new standalone Blogspot article using only verified facts from the owned source.
Never copy or paraphrase sentence by sentence. Reusing sentences, paragraph order, headings, examples, checklist or FAQ is forbidden. Choose a different search intent and rebuild everything.
The title is the highest-priority text: make it emotionally resonant, curiosity-driving and benefit-led so a real reader wants to click, without clickbait or false promises. Never use AI-sounding stock phrases, a repeated title formula, or a title similar to another article.
The first image is equally important. image_queries must describe the title's specific human situation, emotion and practical benefit, not a generic decorative photo.
Add useful original synthesis. Do not invent personal experience, statistics, quotes or sources.
Language: {language}. Persona: {persona}. Tone: {tone}. Target length: about {target_chars} characters.
The article must feel individually edited for this site's persona, not mass-produced. Avoid AI-signaling phrases, generic filler, keyword stuffing, repetitive templates, fake freshness, exaggerated claims, and unnecessary FAQs.
Write for the reader's real task: open with a concise direct answer, then use descriptive H2/H3 sections in a natural order. Add a checklist, comparison, table, or FAQ only when it genuinely improves the answer.
Use the primary keyword naturally in the title, introduction, and relevant headings without forcing repetitions. Use descriptive, varied anchor text.
Return JSON only with keys title, meta_description, content_html, image_queries, labels.
meta_description is mandatory and must be a natural search description of 100-120 words.
labels must contain 8-14 short noun search terms directly relevant to the article. Vary the count inside that range for each article; never use sentences as labels. image_queries must contain 0-2 precise first-image prompts.
content_html must contain semantic HTML only (h2/h3/p/ul/ol/blockquote), no html/head/body, no images, no scripts.
For visa, insurance, or medical/health topics (YMYL), within the first three paragraphs include: (1) a reference-date sentence using the literal words "as of" (English) or "기준" (Korean) followed by a real month/year, e.g. "2026년 8월 기준" or "as of August 2026"; (2) a change-warning sentence using words like "can change"/"subject to change" or "변경될 수 있으니"/"확인하세요"; (3) a short non-advisory disclaimer ("consult a professional"/"전문가와 상담" or "not medical/legal advice"/"의료/법률 자문이 아닙니다"). These three must appear as real sentences, not a heading label alone, or the article fails the quality gate.
Link naturally to the owned detailed source using this exact URL in one of the first two paragraphs so it survives length editing: {source_url}
Use additional internal WordPress or authoritative primary-source links only from the verified list below. Include only links that materially support the article; never invent or guess URLs. Prefer government, regulator, university, hospital, insurer, and other primary sources for factual or time-sensitive claims.
Verified link candidates from the source article:
{verified_link_text}
Source title: {source_title}
Source article:
{plain_text(source_html)[:18000]}
{f"Previous attempt failed these checks; rebuild it and correct every item: {prior_feedback}" if prior_feedback else ""}
"""


def blogger_quality_score(article: dict[str, Any], *, source_title: str, source_url: str,
                          source_html: str, target_chars: int, maximum_similarity: float = 0.68) -> tuple[int, list[str], float]:
    """Pre-publication Blogger score. This is an internal gate, not a Google score."""
    title = str(article.get("title", "")).strip()
    meta = str(article.get("meta_description", "")).strip()
    content = str(article.get("content_html", ""))
    labels = article.get("labels", [])
    text = plain_text(content)
    score = 0
    failures: list[str] = []

    source_terms = {word.lower() for word in re.findall(r"[A-Za-z0-9가-힣]{3,}", plain_text(source_title))}
    title_terms = {word.lower() for word in re.findall(r"[A-Za-z0-9가-힣]{3,}", title)}
    if source_terms & title_terms:
        score += 10
    else:
        failures.append("title does not preserve the source topic/primary keyword")
    if 20 <= len(title) <= 70:
        score += 10
    else:
        failures.append("title length must be 20-70 characters")

    body_chars = len(re.sub(r"\s+", "", text))
    minimum = max(1200, int(target_chars * 0.78))
    maximum = int(target_chars * 1.35)
    if minimum <= body_chars <= maximum:
        score += 20
    else:
        failures.append(f"body length {body_chars} is outside {minimum}-{maximum} characters")
    if 100 <= len(meta.split()) <= 120:
        score += 10
    else:
        failures.append("meta description must be 100-120 words")
    if 8 <= len(labels) <= 14 and all(len(str(label)) <= 30 and len(str(label).split()) <= 3 for label in labels):
        score += 10
    else:
        failures.append("labels must contain 8-14 short noun search terms")

    heading_count = len(re.findall(r"(?is)<h[23](?:\s[^>]*)?>", content))
    if heading_count >= 3:
        score += 10
    else:
        failures.append("at least three useful H2/H3 headings are required")
    links = extract_http_links(content)
    if source_url in links:
        score += 5
    else:
        failures.append("verified WordPress source link is missing")
    verified = set(extract_http_links(source_html))
    if not verified or verified.intersection(links):
        score += 5
    else:
        failures.append("available verified supporting link is not used")

    copy_similarity = similarity(source_html, content)
    if copy_similarity <= maximum_similarity:
        score += 10
    else:
        failures.append(f"source similarity {copy_similarity:.3f} exceeds {maximum_similarity:.2f}")
    banned = re.findall(r"(?i)\b(as an ai|language model|in conclusion|delve into|unlock the secrets)\b", text)
    if not banned:
        score += 5
    else:
        failures.append("AI/filler phrasing detected")
    ymyl = bool(re.search(r"(?i)(visa|immigration|insurance|medical|hospital|treatment|비자|보험|의료)", source_title + " " + text))
    if not ymyl or (re.search(r"(?i)(as of|effective|기준일|[0-9]{4}년\s*[0-9]{1,2}월[^.]{0,10}기준)", text) and re.search(r"(?i)(can change|subject to change|confirm|disclaimer|consult|변경|확인|면책|상담)", text)):
        score += 5
    else:
        failures.append("YMYL as-of date/change warning/disclaimer is incomplete")
    return min(score, 100), failures, copy_similarity


@dataclass(slots=True)
class FreeImage:
    url: str
    page_url: str
    credit: str
    provider: str
    description: str = ""


def find_one_free_image(query: str, *, pexels_key: str = "", pixabay_key: str = "", session=requests) -> FreeImage | None:
    """Return exactly one free-stock image; never calls an AI image service."""
    if pexels_key:
        response = session.get("https://api.pexels.com/v1/search", headers={"Authorization": pexels_key}, params={"query": query, "per_page": 1, "orientation": "landscape"}, timeout=25)
        if response.status_code == 200 and response.json().get("photos"):
            photo = response.json()["photos"][0]
            return FreeImage(photo["src"].get("large2x") or photo["src"]["large"], photo["url"], f"Photo by {photo.get('photographer', 'Pexels contributor')} on Pexels", "Pexels", photo.get("alt", ""))
    if pixabay_key:
        response = session.get("https://pixabay.com/api/", params={"key": pixabay_key, "q": query, "image_type": "photo", "orientation": "horizontal", "per_page": 3, "safesearch": "true"}, timeout=25)
        if response.status_code == 200 and response.json().get("hits"):
            photo = response.json()["hits"][0]
            return FreeImage(photo.get("largeImageURL") or photo["webformatURL"], photo["pageURL"], f"Image by {photo.get('user', 'Pixabay contributor')} on Pixabay", "Pixabay", photo.get("tags", ""))
    return None


def image_is_relevant(image: FreeImage, *, query: str, title: str) -> bool:
    """Reject stock results whose provider description has no topic overlap."""
    topic = {x.lower() for x in re.findall(r"[A-Za-z0-9가-힣]{3,}", f"{query} {title}")}
    description = {x.lower() for x in re.findall(r"[A-Za-z0-9가-힣]{3,}", image.description)}
    return bool(description and topic.intersection(description))


def attach_single_image(content_html: str, image: FreeImage, alt: str) -> str:
    figure = (
        f'<figure><img src="{html.escape(image.url, quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy">'
        f'<figcaption><a href="{html.escape(image.page_url, quote=True)}" rel="nofollow noopener">{html.escape(image.credit)}</a></figcaption></figure>'
    )
    return figure + content_html
