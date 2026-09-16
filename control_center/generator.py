from __future__ import annotations

import json
import re
from typing import Any

from .orchestrator import generate_text
from .registry import WordPressSite


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
        raise ValueError("LLM response did not contain a JSON object")
    data = json.loads(text[start:end + 1])
    for key in ("title", "meta_description", "content_html", "labels", "image_queries"):
        if key not in data:
            raise ValueError(f"LLM response is missing {key}")
    if not isinstance(data["labels"], list) or not isinstance(data["image_queries"], list):
        raise ValueError("labels and image_queries must be arrays")
    data["labels"] = [str(x).strip() for x in data["labels"] if str(x).strip()][:5]
    data["image_queries"] = [str(x).strip() for x in data["image_queries"] if str(x).strip()][:2]
    return data


def generate_article(
    site: WordPressSite,
    keyword: str,
    feedback: list[str] | None = None,
    *,
    text_model: str = "gpt-5.6-luna",
    task_type: str | None = None,
) -> dict[str, Any]:
    """Generate through Project A provider failover.

    `text_model` remains for compatibility with existing callers. A Gemini
    hint selects the Blogger/Gemini-first chain; WordPress uses
    OpenAI -> Claude -> Gemini. Actual model ids are environment-configurable.
    """
    prompt = build_prompt(site, keyword, feedback)
    resolved_task_type = task_type or ("blogger" if text_model.startswith("gemini-") else "wordpress")
    raw, meta = generate_text(prompt, task_type=resolved_task_type)
    result = _parse_json(raw)
    result["orchestrator"] = meta
    return result
