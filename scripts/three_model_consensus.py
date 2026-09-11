"""Blocking two-pass GPT checks-and-balances gate for every written draft.

2026-09-03 CEO decision: drop Gemini as a reviewer network-wide (WP, Blogger,
Tistory, newsrooms) — it was blocking on real Gemini API billing outages
network-wide, and even when reachable its own factual judgment on a
newsroom rewrite kept rejecting the same article with no route to try a
different one. Two independent, cold-context GPT passes replace it
everywhere; `gemini_generate` is still accepted for backward compatibility
with older call sites but is never invoked."""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Callable

from openai_text import openai_available, openai_generate_text


def _json(raw: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _gpt_check(label: str, rule: str) -> dict:
    if not openai_available():
        return {"ok": False, "issues": ["GPT checker unavailable"]}
    try:
        return _json(openai_generate_text(f"You are the {label} independent quality checker. " + rule,
                                          temperature=0.0, max_retries=1))
    except Exception as exc:
        return {"ok": False, "issues": [f"check_failed: {exc}"]}


def three_model_consensus(*, title: str, content: str, meta: str, keyword: str,
                          gemini_generate: Callable[[str], str] | None = None,
                          is_newsroom_brief: bool = False) -> dict:
    """Two independent, cold-context GPT reviews. No model can approve alone.

    Missing credentials, invalid JSON, or either rejection blocks the draft.
    """
    del gemini_generate  # kept for call-site compatibility; never invoked
    packet = json.dumps({"keyword": keyword, "title": title, "meta_description": meta,
                         "content": content}, ensure_ascii=False)
    rule = (
        f"The verified current date is {date.today().isoformat()}; do not call that date future-dated. "
        "Independently inspect factual support, search intent, grammar, natural human tone, "
        "AI-like repetition, title originality and emotional hook, cross-platform copying, "
        "metadata, headings and SEO quality. Reject unsupported firsthand/field reporting, "
        "generic stacked headline templates, and headline promises absent from the body. "
        "Do not trust another model's decision. "
    )
    if is_newsroom_brief:
        # 2026-09-04 CEO decision: brief/wire-style coverage of a single
        # official release is an accepted, normal newsroom format for these
        # two sites — do not require a quoted excerpt, multiple corroborating
        # sources, an interview, or named individuals the source itself
        # never gave. Still block fabrication, misattributed authority/dates,
        # or a missing source link — those remain hard failures.
        rule += (
            "This is a short wire-style newsroom brief that accurately summarizes ONE official "
            "government/institutional press release in the reporter's own words. That is an "
            "ACCEPTABLE, normal news format on its own — do NOT reject solely for single-source "
            "reliance, lack of a directly quoted excerpt, lack of an interview, or missing "
            "names/figures/dates the source release itself never provided. DO still reject if the "
            "draft states specifics (names, figures, dates, who has the authority to act) that are "
            "not actually supported by the source, or if the source link is missing entirely. "
        )
    rule += "Return only JSON: {\"ok\": bool, \"issues\": [str]}. Draft:\n" + packet
    results = {"gpt_1": _gpt_check("first", rule), "gpt_2": _gpt_check("second", rule)}
    return {"ok": all(result.get("ok") is True for result in results.values()), "checks": results}
