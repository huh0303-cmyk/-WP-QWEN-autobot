#!/usr/bin/env python3
"""Synchronize all 27 Blogger destinations into the main site registry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "automation_hub_sites.json"
PROFILES_PATH = ROOT / "config" / "content_engine_profiles.json"


def main() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))["profiles"]
    wordpress = [site for site in registry["sites"] if site.get("platform") == "wordpress"]
    others = [site for site in registry["sites"] if site.get("platform") not in {"wordpress", "blogger"}]
    wp_by_url = {site["url"].rstrip("/"): site for site in wordpress}
    bloggers = []

    for profile in profiles:
        blog = profile["blogspot"]
        if not blog.get("ready_for_automation") or not blog.get("destination_id"):
            raise SystemExit(f"Blogger destination is incomplete: {profile['site_key']}")
        source = wp_by_url.get(profile["wordpress"]["url"].rstrip("/"))
        if not source:
            raise SystemExit(f"WordPress source is missing: {profile['site_key']}")
        bloggers.append({
            "site_id": f"blogger_{profile['site_key']}",
            "platform": "blogger",
            "name": blog["url"].removeprefix("https://").removesuffix(".blogspot.com"),
            "url": blog["url"],
            "destination_id": str(blog["destination_id"]),
            "enabled": True,
            "content_type": "blog",
            "group": "BLOGGER",
            "language": profile["language"],
            "publish_mode": "review",
            "publish_policy": "draft",
            "daily_min": 1,
            "daily_max": 1,
            "weekly_min": 7,
            "weekly_max": 7,
            "content_profile": source.get("content_profile", "option_1"),
            "min_chars": blog["min_chars"],
            "target_chars": blog["target_chars"],
            "max_chars": blog["max_chars"],
            "persona": blog["persona"],
            "tone": blog["tone"],
            "image_mode": "replicate_ai_generated",
            "image_min": 0,
            "image_max": 1,
            "keyword_mode": "golden_keyword_queue",
            "keyword_rules": {
                "source_site_id": source["site_id"],
                "text_provider": "gpt-5-mini",
                "review_provider": "gemini-2.5-flash",
                "meta_description_chars_min": 100,
                "meta_description_chars_max": 120,
                "labels_min": 3,
                "labels_max": 8,
            },
        })

    if len(bloggers) != 27:
        raise SystemExit(f"Expected 27 Blogger destinations, got {len(bloggers)}")
    if len({b["site_id"] for b in bloggers}) != 27:
        raise SystemExit("Duplicate Blogger site_id")
    if len({b["destination_id"] for b in bloggers}) != 27:
        raise SystemExit("Duplicate Blogger destination_id")
    if len({b["url"] for b in bloggers}) != 27:
        raise SystemExit("Duplicate Blogger URL")

    registry["sites"] = wordpress + bloggers + others
    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "ok": True,
        "wordpress": len(wordpress),
        "blogger": len(bloggers),
        "enabled": sum(1 for row in bloggers if row["enabled"]),
        "unique_destination_ids": len({b["destination_id"] for b in bloggers}),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
