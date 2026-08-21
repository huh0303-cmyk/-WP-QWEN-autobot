"""Copyright-aware source and cadence policy for the two newsrooms.

A feed being technically reachable is not permission to republish it. Third-party
publisher feeds stay disabled until the operator records written commercial-use
permission in a GitHub secret.
"""
from __future__ import annotations

import os

NEWSROOMS = {
    "https://koreanews365.com": {
        "publication": "Koreanews365 한국신문",
        "language": "ko",
        "categories": ["속보", "정치", "경제", "사회", "국제"],
        "daily_total_min": 3,
        "daily_total_max": 5,
        "daily_original_min": 2,
        "weekly_original_ratio_min": 0.30,
        "theme_candidate": "Twenty Twenty-Five News Blog",
    },
    "https://theseouljournal.com": {
        "publication": "The Seoul Journal",
        "language": "en",
        "categories": ["Top Stories", "World", "Business", "Technology", "Asia & Korea"],
        "daily_total_min": 3,
        "daily_total_max": 5,
        "daily_original_min": 2,
        "weekly_original_ratio_min": 0.30,
        "theme_candidate": "Twenty Twenty-Five News Blog",
    },
}

# license:
# - primary_public: primary government/public information; facts still require verification.
# - kogl_item_check: reuse depends on the individual item's KOGL type.
# - written_permission_required: never ingest until commercial syndication permission is recorded.
NEWS_SOURCES = [
    {
        "key": "chosun",
        "name": "조선일보",
        "language": "ko",
        "category": "종합",
        "feed": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
        "license": "written_permission_required",
        "permission_env": "NEWS_RIGHTS_CHOSUN",
        "use": "headline_monitor_only",
    },
    {
        "key": "yonhapnewstv",
        "name": "연합뉴스TV",
        "language": "ko",
        "category": "속보",
        "feed": "https://www.yonhapnewstv.co.kr/category/news/headline/feed/",
        "license": "written_permission_required",
        "permission_env": "NEWS_RIGHTS_YONHAPNEWSTV",
        "use": "headline_monitor_only",
    },
    {
        "key": "korea_policy",
        "name": "대한민국 정책브리핑",
        "language": "ko",
        "category": "정책",
        "feed": "",
        "license": "kogl_item_check",
        "permission_env": "",
        "use": "primary_source_manual_item_check",
        "note": "RSS service discontinued; check each item's copyright/KOGL label.",
    },
    {
        "key": "cnn",
        "name": "CNN",
        "language": "en",
        "category": "Top Stories",
        "feed": "http://rss.cnn.com/rss/edition.rss",
        "license": "written_permission_required",
        "permission_env": "NEWS_RIGHTS_CNN",
        "use": "headline_monitor_only",
    },
    {
        "key": "nyt",
        "name": "The New York Times",
        "language": "en",
        "category": "Top Stories",
        "feed": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "license": "written_permission_required",
        "permission_env": "NEWS_RIGHTS_NYT",
        "use": "headline_monitor_only",
    },
    {
        "key": "nasa",
        "name": "NASA",
        "language": "en",
        "category": "Science & Technology",
        "feed": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "license": "primary_public",
        "permission_env": "",
        "use": "primary_fact_lead",
    },
    {
        "key": "federal_reserve",
        "name": "Federal Reserve",
        "language": "en",
        "category": "Business",
        "feed": "https://www.federalreserve.gov/feeds/press_all.xml",
        "license": "primary_public",
        "permission_env": "",
        "use": "primary_fact_lead",
    },
    {
        "key": "sec",
        "name": "U.S. Securities and Exchange Commission",
        "language": "en",
        "category": "Business",
        "feed": "https://www.sec.gov/news/pressreleases.rss",
        "license": "primary_public",
        "permission_env": "",
        "use": "primary_fact_lead",
    },
]


def _confirmed(source: dict) -> bool:
    if source["license"] == "primary_public":
        return True
    env = source.get("permission_env", "")
    return bool(env) and os.getenv(env, "").strip().lower() == "true"


def get_enabled_rss_sources(language: str) -> list[tuple[str, str]]:
    """Return only sources whose reuse gate is satisfied."""
    return [
        (source["name"], source["feed"])
        for source in NEWS_SOURCES
        if source["language"] == language
        and source.get("feed")
        and _confirmed(source)
    ]


def source_audit() -> list[dict]:
    return [
        {
            "key": source["key"],
            "name": source["name"],
            "language": source["language"],
            "license": source["license"],
            "use": source["use"],
            "enabled": bool(source.get("feed")) and _confirmed(source),
        }
        for source in NEWS_SOURCES
    ]
