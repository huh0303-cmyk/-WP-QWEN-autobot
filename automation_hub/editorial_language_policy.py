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
    # 2026-11-22 additions: stock "AI blog" headline formulas
    r"|demystif(?:y|ying|ied)|decoding\s+the|deep\s+dive|beyond\s+the\s+basics"
    r"|what\s+you\s+(?:really\s+)?need\s+to\s+know|things\s+you\s+(?:should|need\s+to)\s+know"
    r"|tips\s+(?:and|&)\s+tricks|best\s+practices\s+for|key\s+takeaways"
    r"|essential\s+(?:tips|guide)|top\s+\d+\s+(?:tips|things|ways|reasons)"
    r"|a\s+(?:comprehensive|complete|definitive)\s+(?:look|overview|breakdown)"
    r"|why\s+\w+(?:\s+\w+){0,4}\s+matters\s+(?:more\s+than\s+ever|now)"
    r"|the\s+(?:hidden|surprising)\s+truth"
    r")\b|비밀을\s*(?:풀다|밝히다)|완벽\s*가이드|궁극의\s*가이드|모든\s*것|총정리"
    r"|꿀팁|A\s*to\s*Z|A\s*부터\s*Z|한눈에\s*(?:정리|보기)|필독|알아야\s*할\s*(?:모든|핵심)|충격|대박"
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


# Removable stock lead-ins. Scrubbing them (instead of rejecting the whole article)
# keeps publication stable while still removing the AI tell.
_LEADIN = (r"(?:in\s+conclusion\s*,|without\s+further\s+ado\s*,|as\s+we\s+all\s+know\s*,"
           r"|it(?:['’]s|\s+is)\s+important\s+to\s+note\s+that)\s+")
# Phrase at the start of a paragraph/sentence: drop it and capitalise the next letter.
_LEADIN_AT_START = re.compile(r"(?i)(?P<pre>(?:^|>|[.!?]\s)\s*)" + _LEADIN + r"(?P<nx>[A-Za-z])")
# Phrase in the middle of a sentence: just drop it.
_LEADIN_MID = re.compile(r"(?i)" + _LEADIN)


def scrub_body_cliches(html_text: str) -> str:
    """Delete removable AI lead-in phrases ("In conclusion,", "It's important to note that")."""
    out = _LEADIN_AT_START.sub(lambda m: m.group("pre") + m.group("nx").upper(), html_text or "")
    return _LEADIN_MID.sub("", out)


def title_cliches(title: str) -> list[str]:
    try:
        from automation_hub.repetition_guard import title_self_issues
        _self = title_self_issues(title or "")
    except Exception:  # bs4 missing in a minimal env must not break publishing
        _self = []
    return _self + (["How-start headline"] if re.match(r'^\s*how\b', title or '', re.I) else []) + [match.group(0) for match in TITLE_CLICHE_PATTERN.finditer(title or "")]


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
