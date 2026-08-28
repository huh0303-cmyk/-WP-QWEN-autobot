from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit


ACTIVE_CONTENT_STATUSES = {"ready", "processing", "drafted", "published", "review_ready"}


def canonical_source_id(value: str) -> str:
    """Normalize a source URL without changing its semantic path."""
    raw = (value or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return raw.casefold()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def stable_content_id(platform: str, site_id: str, source_id: str, *, version: str = "v1") -> str:
    payload = "\n".join((platform.strip().lower(), site_id.strip().lower(), canonical_source_id(source_id), version))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def is_same_content(row: dict[str, str], *, site_id: str, source_id: str) -> bool:
    return (
        row.get("site_id", "").strip().lower() == site_id.strip().lower()
        and canonical_source_id(row.get("source_keyword", "")) == canonical_source_id(source_id)
    )


def active_duplicate(rows: list[dict[str, str]], *, site_id: str, source_id: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("status", "").strip().lower() in ACTIVE_CONTENT_STATUSES and is_same_content(
            row, site_id=site_id, source_id=source_id
        ):
            return row
    return None


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip().casefold()


def is_similar_content(row: dict[str, str], *, site_id: str, title: str, content_html: str, threshold: float = 0.92) -> bool:
    """Catch same-destination title/body copies even when source URLs differ."""
    if row.get("site_id", "").strip().lower() != site_id.strip().lower():
        return False
    old_title, new_title = _plain(row.get("title", "")), _plain(title)
    old_body, new_body = _plain(row.get("content_html", "")), _plain(content_html)
    title_match = bool(old_title and new_title and SequenceMatcher(None, old_title, new_title).ratio() >= threshold)
    body_match = bool(old_body and new_body and SequenceMatcher(None, old_body[:5000], new_body[:5000]).ratio() >= threshold)
    return title_match or body_match
