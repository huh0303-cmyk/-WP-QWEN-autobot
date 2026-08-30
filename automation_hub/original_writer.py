"""Prompt + quality gate for an original article written from a keyword,
not rewritten from a source post. Sibling to blogger_rewriter.py, which
handles the WordPress->Blogger rewrite case; this handles the sheet-driven
"write something new for this keyword" case used for both platforms.
"""
from __future__ import annotations

import re
from typing import Any

from automation_hub.blogger_rewriter import plain_text


def original_prompt(*, keyword: str, site_theme: str, language: str, persona: str,
                    tone: str, target_chars: int, prior_feedback: str = "") -> str:
    return f"""Write a new standalone article for the keyword below. This is original work, not a rewrite of any existing article.
Site theme: {site_theme}. Primary keyword/topic: {keyword}.
The title is the highest-priority text: make it emotionally resonant, curiosity-driving and benefit-led so a real reader wants to click, without clickbait or false promises. Never use AI-sounding stock phrases, a repeated title formula, or a title similar to another article. The title must be a complete, grammatical phrase or sentence that is 68 characters or fewer including spaces - count the characters and shorten it until it fits before finalizing; never write a longer title expecting it to be trimmed, since a trimmed title reads as broken.
The first image is equally important. image_queries must describe the title's specific human situation, emotion and practical benefit, not a generic decorative photo.
Language: {language}. Persona: {persona}. Tone: {tone}. Target length: about {target_chars} characters.
The article must feel individually edited for this site's persona, not mass-produced. Avoid AI-signaling phrases, generic filler, keyword stuffing, repetitive templates, fake freshness, exaggerated claims, and unnecessary FAQs.
Write for the reader's real task: open with a concise direct answer, then use descriptive H2/H3 sections in a natural order. Add a checklist, comparison, table, or FAQ only when it genuinely improves the answer.
Use the primary keyword naturally in the title, introduction, and relevant headings without forcing repetitions. Use descriptive, varied anchor text.
Add useful original synthesis grounded in generally known, verifiable facts. Do not invent personal experience, specific statistics, quotes, prices, or sources you cannot be confident are correct. When a fact would need a citation to be trustworthy (a specific number, date, rule, or claim), phrase it as general guidance instead of a false-precision fact.
Return JSON only with keys title, meta_description, content_html, image_queries, labels.
meta_description is mandatory. Write it as exactly 2-3 short sentences, then count the words and revise until the total is between 100 and 120 words - not visually "about right," an actual word count in that exact range. This is checked mechanically and anything outside 100-120 fails.
labels must contain 8-14 short noun search terms directly relevant to the article. Vary the count inside that range for each article; never use sentences as labels. image_queries must contain 0-2 precise first-image prompts.
content_html must contain semantic HTML only (h2/h3/p/ul/ol/blockquote), no html/head/body, no images, no scripts, and must not link to any URL (no external or invented links).
For visa, insurance, or medical/health topics (YMYL), within the first three paragraphs include: (1) a reference-date sentence using the literal words "as of" (English) or "기준" (Korean) followed by a real month/year, e.g. "2026년 8월 기준" or "as of August 2026"; (2) a change-warning sentence using words like "can change"/"subject to change" or "변경될 수 있으니"/"확인하세요"; (3) a short non-advisory disclaimer ("consult a professional"/"전문가와 상담" or "not medical/legal advice"/"의료/법률 자문이 아닙니다"). These three must appear as real sentences, not a heading label alone, or the article fails the quality gate.
{f"Previous attempt failed these checks; rebuild it and correct every item: {prior_feedback}" if prior_feedback else ""}
"""


def original_quality_score(article: dict[str, Any], *, keyword: str, target_chars: int) -> tuple[int, list[str]]:
    """Pre-publication score for an original (non-rewrite) article. No
    source-similarity check applies since there is no source to compare to."""
    title = str(article.get("title", "")).strip()
    meta = str(article.get("meta_description", "")).strip()
    content = str(article.get("content_html", ""))
    labels = article.get("labels", [])
    text = plain_text(content)
    score = 0
    failures: list[str] = []

    keyword_terms = {word.lower() for word in re.findall(r"[A-Za-z0-9가-힣]{3,}", keyword)}
    title_terms = {word.lower() for word in re.findall(r"[A-Za-z0-9가-힣]{3,}", title)}
    if keyword_terms & title_terms:
        score += 15
    else:
        failures.append("title does not reflect the assigned keyword")
    if 20 <= len(title) <= 70:
        score += 10
    else:
        failures.append("title length must be 20-70 characters")

    body_chars = len(re.sub(r"\s+", "", text))
    minimum = max(1000, int(target_chars * 0.78))
    maximum = int(target_chars * 1.35)
    if minimum <= body_chars <= maximum:
        score += 20
    else:
        failures.append(f"body length {body_chars} is outside {minimum}-{maximum} characters")
    if 100 <= len(meta.split()) <= 120:
        score += 15
    else:
        failures.append("meta description must be 100-120 words")
    if 8 <= len(labels) <= 14 and all(len(str(label)) <= 30 and len(str(label).split()) <= 3 for label in labels):
        score += 15
    else:
        failures.append("labels must contain 8-14 short noun search terms")

    heading_count = len(re.findall(r"(?is)<h[23](?:\s[^>]*)?>", content))
    if heading_count >= 3:
        score += 10
    else:
        failures.append("at least three useful H2/H3 headings are required")
    banned = re.findall(r"(?i)\b(as an ai|language model|in conclusion|delve into|unlock the secrets)\b", text)
    if not banned:
        score += 10
    else:
        failures.append("AI/filler phrasing detected")
    ymyl = bool(re.search(r"(?i)(visa|immigration|insurance|medical|hospital|treatment|비자|보험|의료)", keyword + " " + text))
    if not ymyl or (re.search(r"(?i)(as of|effective|기준일|[0-9]{4}년\s*[0-9]{1,2}월[^.]{0,10}기준)", text) and re.search(r"(?i)(can change|subject to change|confirm|disclaimer|consult|변경|확인|면책|상담)", text)):
        score += 5
    else:
        failures.append("YMYL as-of date/change warning/disclaimer is incomplete")
    return min(score, 100), failures
