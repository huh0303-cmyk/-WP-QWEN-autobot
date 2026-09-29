"""Verified destination catalog for the London GPT web app."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def content_sites() -> list[dict]:
    categories = {
        "https://" + str(row["domain"]).strip().lower(): list(row.get("categories", []))
        for row in _json("WP24_CATEGORY_MASTER.json").get("sites", []) if row.get("domain")
    }
    categories.update({
        "https://k-health365.com": ["건강정보"],
        "https://koreanews365.com": ["GLOBAL"],
        "https://theseouljournal.com": ["GLOBAL"],
    })
    sites: list[dict] = []
    wordpress_seen: set[str] = set()
    for profile in _json("content_engine_profiles.json").get("profiles", []):
        if profile.get("site_key") == "kmedical_job_center":
            from automation_hub.medical_editorial import medical_profile
            profile = medical_profile(profile)
        key = profile["site_key"]
        wp, blog = profile.get("wordpress") or {}, profile.get("blogspot") or {}
        wp_url = str(wp.get("url") or "").rstrip("/")
        wp_id = str(profile.get("source_site_id") or f"wp_{key}").strip()
        if wp_url and wp_id and wp_id not in wordpress_seen:
            sites.append({"site_id": wp_id, "platform": "wordpress", "url": wp_url,
                          "editor_url": wp_url + "/wp-admin/post-new.php",
                          "label": wp_url.removeprefix("https://"), "enabled": True, "auto_publish": True,
                          "language": profile.get("language", "en"), "persona": wp.get("persona", ""),
                          "tone": wp.get("tone", ""), "theme": wp.get("theme", ""),
                          "categories": categories.get(wp_url, ["General"])})
            wordpress_seen.add(wp_id)
        blog_url = str(blog.get("url") or "").rstrip("/")
        sites.append({"site_id": f"blogger_{key}", "platform": "blogger", "url": blog_url,
                      "editor_url": "https://www.blogger.com/blog/posts/" + str(blog.get("destination_id") or ""),
                      "label": blog_url.removeprefix("https://"),
                      "enabled": bool(blog_url and blog.get("destination_id") and blog.get("ready_for_automation")),
                      "auto_publish": True, "language": profile.get("language", "en"),
                      "persona": blog.get("persona") or wp.get("persona", ""),
                      "tone": blog.get("tone") or wp.get("tone", ""), "theme": wp.get("theme", ""),
                      "categories": []})
    for item in _json("tistory_portfolio.json").get("sites", []):
        url = str(item.get("url") or "").rstrip("/")
        sites.append({"site_id": item["site_id"], "platform": "tistory", "url": url,
                      "editor_url": url + "/manage/newpost",
                      "label": item.get("title") or url, "enabled": bool(item.get("launch_enabled")),
                      "auto_publish": False, "language": item.get("language", "ko"),
                      "persona": item.get("audience") or "한국어 독자를 위한 생활정보 편집자",
                      "tone": "정확하고 실용적인 한국어 안내", "theme": item.get("description") or item.get("title", ""),
                      "categories": list(item.get("categories") or [])})
    for room in _json("automation_rooms.json").get("rooms", []):
        if room.get("platform") != "naver":
            continue
        blog_id = str(room.get("destination_id") or "").strip()
        sites.append({"site_id": room["room_id"], "platform": "naver",
                      "url": f"https://blog.naver.com/{blog_id}" if blog_id else "",
                      "editor_url": room.get("editor_url") or (f"https://blog.naver.com/{blog_id}?Redirect=Write" if blog_id else ""),
                      "label": room.get("name") or room["room_id"],
                      "enabled": bool(blog_id), "auto_publish": False,
                      "unavailable_reason": "블로그 ID 연결 필요" if not blog_id else "",
                      "language": room.get("language", "ko"),
                      "persona": "한국어 생활정보 블로그 편집자", "tone": "명확하고 실용적인 한국어 안내",
                      "theme": "한국 생활정보", "categories": []})
    return sites


def manual_profile(site_id: str) -> tuple[str, dict]:
    site = next((item for item in content_sites() if item["site_id"] == site_id and item["enabled"]), None)
    if not site or site["platform"] not in {"naver", "tistory"}:
        raise ValueError("manual publishing site is unavailable")
    settings = {"url": site["url"], "theme": site["theme"], "persona": site["persona"],
                "tone": site["tone"], "min_chars": 1400, "target_chars": 2000,
                "max_chars": 3000, "editorial_funnel": {}}
    return site["platform"], {"language": site["language"], "wordpress": settings,
                              "manual_destination": site["url"]}
