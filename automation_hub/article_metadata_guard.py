"""Final editorial metadata guard shared by WordPress publishing paths."""
from __future__ import annotations

import re


_STOP = {
    "그리고", "또는", "대한", "위한", "관련", "방법", "정보", "안내", "정리",
    "최고", "완벽", "총정리", "알아보기", "guide", "best", "complete", "tips",
}


def _compact(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").casefold())


def sanitize_article_labels(labels, *, title: str, keyword: str, limit: int = 5) -> list[str]:
    """Keep only unique labels demonstrably tied to the assigned topic/title.

    Do not fill missing slots with generic site-wide labels. Fewer relevant
    labels are preferable to a polluted tag cloud.
    """
    title = str(title or "").strip()
    keyword = str(keyword or "").strip()
    context = _compact(title + " " + keyword)
    context_tokens = [
        token.casefold() for token in re.findall(r"[가-힣A-Za-z0-9]+", title + " " + keyword)
        if len(token) >= 2 and token.casefold() not in _STOP
    ]
    candidates = []
    seen = set()
    for raw in labels if isinstance(labels, (list, tuple)) else []:
        label = re.sub(r"\s+", " ", str(raw or "")).strip(" ,;|:-")
        key = _compact(label)
        if not label or len(label) > 32 or len(label.split()) > 4 or key in seen:
            continue
        # Require an actual phrase overlap with the headline/assigned keyword.
        # This rejects tags imported from unrelated posts even if the model
        # emits a large mixed-topic label list.
        relevant = bool(key and (key in context or any(token in key for token in context_tokens)))
        if not relevant:
            label_tokens = [t.casefold() for t in re.findall(r"[가-힣A-Za-z0-9]+", label)
                            if len(t) >= 2 and t.casefold() not in _STOP]
            relevant = any(token in context for token in label_tokens)
        if relevant:
            seen.add(key)
            candidates.append(label)
        if len(candidates) >= limit:
            break

    # Add the assigned keyword only when it is a meaningful, topic-specific phrase.
    if len(candidates) < 3 and keyword:
        key = _compact(keyword)
        if key and key in context and key not in seen and len(keyword) <= 32:
            candidates.insert(0, keyword)
            seen.add(key)

    # If the model supplied no useful labels, use at most a few exact title
    # phrases; never invent generic cross-topic tags to meet a quota.
    if len(candidates) < 3:
        for phrase in re.split(r"[:：,，|·—–/]", title):
            phrase = re.sub(r"\s+", " ", phrase).strip()
            key = _compact(phrase)
            if 2 <= len(key) <= 32 and key not in seen and phrase.casefold() not in _STOP:
                candidates.append(phrase)
                seen.add(key)
            if len(candidates) >= 3:
                break
    return candidates[:limit]


def wp_repetition_issues(*, site_url: str, secret_name: str, article: dict, wp_user: str) -> list[str]:
    """Check a candidate against published, scheduled and review-state WP posts."""
    import os
    import requests
    from automation_hub.repetition_guard import fetch_wp_history, repetition_issues

    password = os.environ.get(secret_name, "").strip()
    if not site_url or not password:
        raise RuntimeError(f"WordPress history guard cannot authenticate: {secret_name or site_url}")
    history = fetch_wp_history(requests.Session(), site_url, (wp_user, password))
    return repetition_issues(
        str(article.get("title") or ""),
        str(article.get("content_html") or ""),
        history,
    )


def repetition_feedback(issues: list[str]) -> str:
    """Make the retry actionable without leaking a whole archive into the prompt."""
    return (
        "EDITORIAL DUPLICATE BLOCK: Rewrite the title and opening from a genuinely different "
        "reader question and practical angle. Do not merely swap words or reorder the same "
        "phrase. Correct these detected issues: " + "; ".join(issues[:5])
    )
