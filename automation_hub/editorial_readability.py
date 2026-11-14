"""Shared editorial readability formatting for WordPress, Blogger, Naver and Tistory.

Only modifies presentation; character counts exclude markup and editorial add-ons.
Call validate_article_length on the article body BEFORE adding CTAs/affiliate content.
"""
import html
import re

MIN_CHARS = 2500
MAX_CHARS = 4000
PALETTES = {
    "insurance": "#2563eb", "finance": "#1d4ed8", "invest": "#1d4ed8",
    "health": "#0f766e", "medical": "#0f766e", "skin": "#0f766e",
    "trip": "#d97706", "world": "#d97706", "visa": "#7c3aed",
    "study": "#7c3aed", "job": "#7c3aed",
}
TAG_RE = re.compile(r"<[^>]*>", re.S)


def visible_length(article_html):
    text = TAG_RE.sub(" ", re.sub(r"(?is)<(script|style)\\b.*?</\\1>", "", article_html or ""))
    return len(re.sub(r"\\s+", "", html.unescape(text)))


def validate_article_length(article_html, min_chars=MIN_CHARS, max_chars=MAX_CHARS):
    count = visible_length(article_html)
    if not min_chars <= count <= max_chars:
        raise ValueError(f"ARTICLE_LENGTH_BLOCKED: {count} characters (required {min_chars}-{max_chars})")
    return count


def accent_for(site_url):
    host = re.sub(r"^https?://", "", (site_url or "").lower()).split("/")[0]
    return next((color for key, color in PALETTES.items() if key in host), "#334155")


def format_article(article_html, site_url="", *, include_faq=True):
    """Style editorial H2/H3 and add an accessible summary panel without changing prose."""
    if not article_html or 'data-london-readability="1"' in article_html:
        return article_html
    accent = accent_for(site_url)
    article = article_html
    article = re.sub(
        r"<h2(\\s[^>]*)?>",
        lambda m: '<h2 style="font-size:1.55rem;line-height:1.4;margin:2rem 0 1rem;'
        f'padding:.65rem .85rem;border-left:5px solid {accent};'
        'background:#f8fafc;border-radius:0 8px 8px 0;color:#172033;">',
        article, flags=re.I,
    )
    article = re.sub(
        r"<h3(\\s[^>]*)?>",
        lambda m: '<h3 style="font-size:1.2rem;line-height:1.5;margin:1.5rem 0 .75rem;'
        f'padding-bottom:.4rem;border-bottom:1px solid {accent};color:#1f2937;">',
        article, flags=re.I,
    )
    article = re.sub(
        r"<blockquote(\\s[^>]*)?>",
        lambda m: '<blockquote style="margin:1.5rem 0;padding:1rem 1.25rem;'
        f'border-left:4px solid {accent};background:#f8fafc;border-radius:6px;">',
        article, flags=re.I,
    )
    article = re.sub(
        r"<p(\\s[^>]*)?>",
        '<p style="margin:0 0 1.15rem;line-height:1.85;">',
        article, flags=re.I,
    )
    article = re.sub(
        r"<hr(\\s[^>]*)?/?>",
        f'<hr style="border:0;border-top:1px solid {accent};opacity:.35;margin:2rem 0;">',
        article, flags=re.I,
    )
    if include_faq:
        article = re.sub(
            r'(<div[^>]*itemtype=["\\\']https://schema.org/FAQPage["\\\'][^>]*>)',
            lambda m: m.group(1) + '<div style="background:#f8fafc;border-radius:10px;'
            'padding:1rem 1.25rem;margin:1rem 0;">',
            article, count=1, flags=re.I,
        )
        if 'itemtype="https://schema.org/FAQPage"' in article:
            article += "</div>"
    return (f'<div data-london-readability="1" style="font-family:'
            "'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif;"
            'font-size:17px;line-height:1.8;color:#1f2937;overflow-wrap:anywhere;">'
            + article + "</div>")
