#!/usr/bin/env python3
"""Build config/content_engine_profiles.json, the single source of truth
for the sheet-triggered auto-write pipeline.

Merges config/automation_hub_sites.json (WP persona/tone/secret_name —
the copy actually wired to real WP Application Passwords) with
config/blogger_portfolio.json (Blogspot address/destination_id/status —
the locked 1:1 master map). Run this again any time either source file
changes; it always overwrites content_engine_profiles.json from the
current state of both inputs, so it never itself becomes a third
disagreeing source.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    wp_sites = {
        s["url"].rstrip("/"): s
        for s in json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8")).get("sites", [])
        if s.get("platform") == "wordpress"
    }
    portfolio = json.loads((ROOT / "config" / "blogger_portfolio.json").read_text(encoding="utf-8"))["channels"]

    profiles = []
    for channel in portfolio:
        wp_url = channel["wp"].rstrip("/")
        wp_site = wp_sites.get(wp_url)
        if not wp_site:
            raise SystemExit(f"blogger_portfolio.json order {channel['order']} ({wp_url}) has no match in automation_hub_sites.json")
        blogspot_ready = channel["status"] in {"EXISTING", "CREATED"} and bool(channel.get("destination_id"))
        profiles.append({
            "order": channel["order"],
            "site_key": channel.get("site_key") or wp_site["site_id"].removeprefix("wp_"),
            "source_site_id": wp_site["site_id"],
            "language": wp_site["language"],
            "wordpress": {
                "url": wp_site["url"],
                "secret_name": wp_site["secret_name"],
                "persona": wp_site["persona"],
                "tone": wp_site["tone"],
                "theme": wp_site.get("keyword_rules", {}).get("theme", channel["topic"]),
                "min_chars": wp_site.get("min_chars", 1800),
                "target_chars": wp_site.get("target_chars", 2400),
                "max_chars": wp_site.get("max_chars", 3200),
                "content_type": wp_site.get("content_type", "blog"),
                "editorial_funnel": wp_site.get("editorial_funnel", {}),
            },
            "blogspot": {
                "url": channel["blogspot"],
                "status": channel["status"],
                "destination_id": channel.get("destination_id", ""),
                "ready_for_automation": blogspot_ready,
                "description": channel.get("description", ""),
                "search_description": channel.get("search_description", ""),
                "notes": channel.get("notes", ""),
                "editorial_funnel": channel.get("funnel") or wp_site.get("editorial_funnel", {}),
                # Same persona/tone as WordPress (same site, same voice) but a
                # shorter, distinctly-keyworded piece per the locked v2 policy:
                # WordPress carries the deep-dive, Blogspot a related-but-different
                # angle. Derived as a ratio of the WordPress length so every site
                # gets a sane range without a second hand-maintained table.
                "persona": wp_site["persona"],
                "tone": wp_site["tone"],
                "min_chars": max(1000, round(wp_site.get("min_chars", 1800) * 0.7)),
                "target_chars": max(1300, round(wp_site.get("target_chars", 2400) * 0.7)),
                "max_chars": max(1600, round(wp_site.get("max_chars", 3200) * 0.72)),
                "text_model": channel.get("text_model", ""),
                "image_models": channel.get("image_models", []),
            },
        })

    output = {
        "generated_from": ["config/automation_hub_sites.json", "config/blogger_portfolio.json"],
        "count": len(profiles),
        "wordpress_ready_count": len(wp_sites),
        "blogspot_ready_count": sum(1 for p in profiles if p["blogspot"]["ready_for_automation"]),
        "profiles": profiles,
    }
    out_path = ROOT / "config" / "content_engine_profiles.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path} — {output['wordpress_ready_count']} WP ready, {output['blogspot_ready_count']}/{output['count']} Blogspot ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
