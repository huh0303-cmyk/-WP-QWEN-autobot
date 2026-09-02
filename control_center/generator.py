from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from .registry import WordPressSite


OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def build_prompt(site: WordPressSite, keyword: str, feedback: list[str] | None = None) -> str:
    language = "Korean" if site.language == "ko" else "English"
    feedback_text = "; ".join(feedback or [])
    return f"""You are writing one independently edited WordPress article.
Site: {site.name} ({site.theme})
Primary keyword: {keyword}
Language: {language}
Editorial persona: {site.persona}
Tone: {site.tone}
Target body length: about {site.target_chars} non-space characters.

Create a useful, specific article for a real reader. Do not imitate an AI template, fabricate experience, statistics, quotations, prices, laws or sources. Start with a direct answer, then use a natural H2/H3 structure. Avoid filler and repeated conclusions.

SEO and review rules:
- Natural title, 20-68 characters, clearly reflecting the keyword.
- Meta description must be one complete sentence of 110-130 characters.
- 3-5 short, highly relevant tags only.
- image_queries must contain 0-2 detailed photo-realistic image briefs. Use zero when an image would not materially help.
- content_html may use only p, h2, h3, ul, ol, li, table, thead, tbody, tr, th, td, strong, em, blockquote and a tags.
- Include an internal link only when a genuinely relevant URL is known. Never invent a URL.
- Use official external sources for rules, procedures or important facts; never invent a source URL.
- Visa, insurance, medical, legal, tax and finance articles must state the reference date, that rules can change, where to verify officially, and a concise non-advisory disclaimer.
- Never include markdown fences, an AI disclosure or generic phrases such as 'comprehensive guide'.
{f'Rebuild the article and correct these prior failures: {feedback_text}' if feedback_text else ''}

Return one JSON object only with these keys:
title, meta_description, content_html, labels, image_queries.
"""


def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("ChatGPT response did not contain a JSON object")
    data = json.loads(text[start:end + 1])
    for key in ("title", "meta_description", "content_html", "labels", "image_queries"):
        if key not in data:
            raise ValueError(f"ChatGPT response is missing {key}")
    if not isinstance(data["labels"], list) or not isinstance(data["image_queries"], list):
        raise ValueError("labels and image_queries must be arrays")
    data["labels"] = [str(x).strip() for x in data["labels"] if str(x).strip()][:5]
    data["image_queries"] = [str(x).strip() for x in data["image_queries"] if str(x).strip()][:2]
    return data


def _openai_generate(model: str, prompt: str) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY가 없어 OpenAI 글 생성을 시작하지 않았습니다")
    response = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI API 오류 HTTP {response.status_code}: {response.text[:240]}")
    try:
        return response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("OpenAI API 응답 형식을 읽을 수 없습니다") from exc


def _gemini_generate(model: str, prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY가 없어 Gemini 글 생성을 시작하지 않았습니다")
    response = requests.post(
        GEMINI_URL.format(model=model), params={"key": key},
        headers={"Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json"}},
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Gemini API 오류 HTTP {response.status_code}: {response.text[:240]}")
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini API 응답 형식을 읽을 수 없습니다") from exc


def generate_article(site: WordPressSite, keyword: str, feedback: list[str] | None = None, *, text_model: str = "gemini-2.5-flash") -> dict[str, Any]:
    prompt = build_prompt(site, keyword, feedback)
    raw = _gemini_generate(text_model, prompt) if text_model.startswith("gemini-") else _openai_generate(text_model, prompt)
    return _parse_json(raw)
