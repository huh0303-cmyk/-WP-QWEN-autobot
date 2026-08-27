from __future__ import annotations


NEWSROOM_TYPES = {"news_ko", "news_en"}
NEWSROOM_MODES = {"news", "news_en"}


def resolve_wordpress_post_status(site: dict, *, requested_status: str, public_approved: bool) -> str:
    """Fail closed: only an explicitly approved newsroom may publish publicly."""
    requested = (requested_status or "draft").strip().lower()
    is_newsroom = site.get("content_type") in NEWSROOM_TYPES or site.get("mode") in NEWSROOM_MODES
    if requested == "publish" and is_newsroom and public_approved:
        return "publish"
    return "draft"
