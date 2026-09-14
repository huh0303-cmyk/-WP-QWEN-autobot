"""Deterministic ranking for evidence-backed golden-keyword mentions."""

from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urlparse


SOURCE_SURFACES = ("newspaper", "naver", "google", "media")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_noun(noun: str) -> str:
    """Collapse spacing/punctuation/case variants of the same named noun."""
    return re.sub(r"[^0-9a-z가-힣]+", "", _clean(noun).casefold())


def parse_mention_rows(
    text: str, valid_categories: list[str], *, observed_on: str | None = None
) -> list[dict[str, str]]:
    """Parse strictly sourced mention rows; malformed or invented-looking rows are dropped."""
    rows: list[dict[str, str]] = []
    category_set = set(valid_categories)
    for raw in text.splitlines():
        parts = [_clean(part) for part in raw.strip().split("\t")]
        if len(parts) != 7:
            continue
        keyword, category, noun, surface, outlet, published_on, url = parts
        surface = surface.casefold()
        parsed = urlparse(url)
        if (
            not keyword
            or not noun
            or category not in category_set
            or surface not in SOURCE_SURFACES
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published_on)
            or (observed_on is not None and published_on != observed_on)
        ):
            continue
        noun_key = normalize_noun(noun)
        if len(noun_key) < 2:
            continue
        rows.append(
            {
                "keyword": keyword,
                "category": category,
                "noun": noun,
                "noun_key": noun_key,
                "surface": surface,
                "outlet": outlet or parsed.netloc.casefold(),
                "published_on": published_on,
                "url": url,
            }
        )
    return rows


def rank_mentioned_keywords(
    rows: list[dict[str, str]], *, minimum_surfaces: int = 2
) -> list[tuple[str, str, dict[str, int]]]:
    """Rank nouns by unique-URL mentions, then outlet and surface diversity.

    Repeated copies from the same URL count once. A noun seen on only one discovery
    surface is rejected even if that single surface repeats it many times.
    """
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_mentions: set[tuple[str, str]] = set()
    for row in rows:
        dedupe_key = (row["noun_key"], row["url"])
        if dedupe_key in seen_mentions:
            continue
        seen_mentions.add(dedupe_key)
        grouped[row["noun_key"]].append(row)

    ranked: list[tuple[str, str, dict[str, int], str]] = []
    for noun_key, mentions in grouped.items():
        surfaces = {row["surface"] for row in mentions}
        if len(surfaces) < minimum_surfaces:
            continue
        outlets = {row["outlet"].casefold() for row in mentions}
        # Prefer the wording attached to the most broadly evidenced noun cluster.
        representative = mentions[0]
        metrics = {
            "surface_count": len(surfaces),
            "outlet_count": len(outlets),
            "mention_count": len(mentions),
        }
        ranked.append((representative["keyword"], representative["category"], metrics, noun_key))

    ranked.sort(
        key=lambda item: (
            -item[2]["mention_count"],
            -item[2]["outlet_count"],
            -item[2]["surface_count"],
            item[3],
        )
    )
    return [(keyword, category, metrics) for keyword, category, metrics, _ in ranked]
