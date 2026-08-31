"""Blocking three-model checks-and-balances gate for every written draft."""
from __future__ import annotations

import json
import re
from typing import Callable

from claude_text import claude_available, claude_generate_text
from openai_text import openai_available, openai_generate_text


def _json(raw: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    return json.loads(text)


def three_model_consensus(*, title: str, content: str, meta: str, keyword: str,
                          gemini_generate: Callable[[str], str]) -> dict:
    """Gemini self-check + GPT independent check + Claude final audit.

    No model can approve alone. Missing credentials, invalid JSON, or any
    rejection blocks the draft from reaching the review queue.
    """
    packet = json.dumps({"keyword": keyword, "title": title, "meta_description": meta,
                         "content": content}, ensure_ascii=False)
    rule = (
        "Independently inspect factual support, search intent, grammar, natural human tone, "
        "AI-like repetition, title originality and emotional hook, cross-platform copying, "
        "metadata, headings and SEO quality. Reject unsupported firsthand/field reporting, "
        "generic stacked headline templates, and headline promises absent from the body. "
        "Do not trust another model's decision. "
        "Return only JSON: {\"ok\": bool, \"issues\": [str]}. Draft:\n" + packet
    )
    results = {}
    try:
        results["gemini"] = _json(gemini_generate("You are the first independent quality checker. " + rule))
    except Exception as exc:
        results["gemini"] = {"ok": False, "issues": [f"check_failed: {exc}"]}
    if not openai_available():
        results["gpt"] = {"ok": False, "issues": ["GPT checker unavailable"]}
    else:
        try:
            results["gpt"] = _json(openai_generate_text("You are the second independent quality checker. " + rule, temperature=0.0, max_retries=1))
        except Exception as exc:
            results["gpt"] = {"ok": False, "issues": [f"check_failed: {exc}"]}
    if not claude_available():
        results["claude"] = {"ok": False, "issues": ["Claude checker unavailable"]}
    else:
        try:
            results["claude"] = _json(claude_generate_text(rule, system="You are the third and final independent editorial auditor.", temperature=0.0, max_retries=1))
        except Exception as exc:
            results["claude"] = {"ok": False, "issues": [f"check_failed: {exc}"]}
    return {"ok": all(result.get("ok") is True for result in results.values()), "checks": results}
