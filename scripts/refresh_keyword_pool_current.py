#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current 25-blog keyword refresh entrypoint.

Keeps the legacy research implementation, but fixes two operational gaps:
1) kskin365.com was accidentally omitted from TARGETS (24/25 blogs only).
2) OpenAI web-search should not be attempted while paid OpenAI generation is disabled/
   credits are unavailable; Gemini search grounding is used directly for this scheduled job.
"""
import refresh_keyword_pool as base

# Scheduled keyword research is intentionally Gemini-first until OpenAI is explicitly re-enabled.
base.OPENAI_API_KEY = ""

KSKIN_TARGET = {
    "url": "https://kskin365.com",
    "file": "data/keywords/keywords_kskin.txt",
    "domain_desc": (
        "Evidence-led Korean skincare ingredients, routines, product categories and "
        "skin-safety guidance for international readers"
    ),
    "categories": ["Ingredients", "Routines", "Skincare"],
    "lang": "en",
}

if not any(t.get("url") == KSKIN_TARGET["url"] for t in base.TARGETS):
    # Keep it near OliveYoung/K-beauty targets for easier audit readability.
    insert_at = next(
        (i for i, t in enumerate(base.TARGETS) if t.get("url") == "https://oliveyoungkorea.com"),
        len(base.TARGETS),
    )
    base.TARGETS.insert(insert_at, KSKIN_TARGET)

if __name__ == "__main__":
    if len(base.TARGETS) != 25:
        raise SystemExit(f"Expected 25 blog targets, found {len(base.TARGETS)}")
    base.main()
