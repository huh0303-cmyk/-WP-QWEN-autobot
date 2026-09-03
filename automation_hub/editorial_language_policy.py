"""Deterministic network-wide ban on mass-produced AI writing clichés."""
from __future__ import annotations
import re

TITLE_CLICHE_PATTERN = re.compile(
    r"(?ix)\b(?:"
    r"unlock(?:s|ed|ing)?(?:\s+(?:the\s+)?(?:secret|secrets|power|potential|future|dreams?))?"
    r"|ultimate\s+guide|complete\s+guide|comprehensive\s+guide"
    r"|discover\s+the\s+power\s+of|unleash(?:ing)?\s+(?:the\s+)?power"
    r"|navigate\s+(?:the\s+)?(?:complexities|landscape|world)"
    r"|your\s+path\s+to|master(?:ing)?\s+the\s+art\s+of"
    r"|revolutioniz(?:e|es|ed|ing)|game[-\s]?changer"
    r"|everything\s+you\s+need\s+to\s+know"
    r"|secrets?\s+(?:revealed|unveiled)|the\s+future\s+of"
    r")\b|비밀을\s*(?:풀다|밝히다)|완벽\s*가이드|궁극의\s*가이드|모든\s*것|총정리"
)

BODY_CLICHE_PATTERN = re.compile(
    r"(?ix)\b(?:"
    r"in\s+today['’]s\s+(?:fast[-\s]?paced|dynamic|ever[-\s]?changing|digital)\s+world"
    r"|in\s+the\s+ever[-\s]?evolving\s+(?:world|landscape|realm)"
    r"|delve\s+(?:deep\s+)?into|embark\s+on\s+(?:a|an|this|your)\s+journey"
    r"|a\s+tapestry\s+of|in\s+the\s+realm\s+of|look\s+no\s+further"
    r"|whether\s+you['’]re\s+a\s+seasoned|elevate\s+your\s+(?:experience|journey|lifestyle)"
    r"|seamlessly\s+(?:navigate|integrate|blend)|it['’]s\s+important\s+to\s+note"
    r"|as\s+we\s+all\s+know|in\s+conclusion|without\s+further\s+ado"
    r")\b"
)


def title_cliches(title: str) -> list[str]:
    return [match.group(0) for match in TITLE_CLICHE_PATTERN.finditer(title or "")]


def body_cliches(text: str) -> list[str]:
    return [match.group(0) for match in BODY_CLICHE_PATTERN.finditer(text or "")]


def language_mismatch_fields(*, language: str, title: str, meta_description: str,
                             content: str, labels: list[str] | None = None) -> list[str]:
    """Return visible fields that violate the target site's language.

    English properties must not receive Korean summaries, captions, labels, or
    body fragments.  This is intentionally strict: a Korean source may inform
    an English article, but every reader-visible field must still be English.
    """
    if not (language or "").lower().startswith("en"):
        return []
    values = {
        "title": title,
        "meta_description": meta_description,
        "content": content,
        "labels": " ".join(labels or []),
    }
    return [name for name, value in values.items() if re.search(r"[가-힣]", value or "")]
