from __future__ import annotations

from copy import deepcopy

from .registry import SiteRegistry


def apply_wordpress_registry(
    legacy_sites: list[dict],
    legacy_personas: dict[str, dict],
    registry: SiteRegistry,
) -> tuple[list[dict], dict[str, dict]]:
    """Overlay dashboard settings onto the mature WordPress publisher config."""
    by_url = {site["url"].rstrip("/").lower(): site for site in legacy_sites}
    configured: list[dict] = []
    personas = deepcopy(legacy_personas)

    for site in registry.enabled("wordpress"):
        url_key = site.url.rstrip("/").lower()
        if url_key not in by_url:
            raise ValueError(f"WordPress destination has no engine profile yet: {site.url}")
        current = deepcopy(by_url[url_key])
        current.update(
            url=site.url.rstrip("/"),
            lang=site.language,
            theme=str(site.keyword_rules.get("theme") or current.get("theme") or site.name),
            wp_pass_env=site.secret_name,
            daily=site.daily_max,
            daily_min=site.daily_min,
            daily_max=site.daily_max,
            weekly_min=site.weekly_min,
            weekly_max=site.weekly_max,
            automation_site_id=site.site_id,
            content_profile=site.content_profile,
            publish_mode=site.publish_mode,
            min_chars=site.min_chars,
            target_chars=site.target_chars,
            max_chars=site.max_chars,
            default_category=site.default_category,
            image_mode=site.image_mode,
            image_min=site.image_min,
            image_max=site.image_max,
        )
        configured.append(current)

        persona = deepcopy(personas.get(current["url"], {}))
        persona["persona_ko" if site.language == "ko" else "persona_en"] = site.persona
        persona["tone"] = site.tone
        persona["min_chars"] = site.target_chars
        persona["max_chars"] = site.max_chars
        personas[current["url"]] = persona

    return configured, personas
