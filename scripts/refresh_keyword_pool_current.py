#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current 25-blog keyword refresh entrypoint."""
import refresh_keyword_pool as base

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
