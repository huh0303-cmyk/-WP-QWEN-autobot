from __future__ import annotations


def resolve_wordpress_post_status(site: dict, *, requested_status: str, public_approved: bool) -> str:
    """Fail closed: publishing publicly always requires explicit approval.

    2026-09-06 CEO decision: this used to gate "publish" behind being a
    newsroom site specifically, so every one of the 25 regular WP sites'
    publish buttons silently landed as a private review draft even when
    dispatched with publication_approved=true - contradicting the
    daily-network-publish.yml workflow's own "no per-item review, default
    true" design and the CEO's explicit ask for the network to actually go
    public. The deterministic SEO/editorial quality gate upstream (score
    threshold plus critical-failure checks) is what protects publish
    quality now, for every site type, not a newsroom-only allowlist.
    """
    requested = (requested_status or "draft").strip().lower()
    if requested == "publish" and public_approved:
        return "publish"
    return "draft"
