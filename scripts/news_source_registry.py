"""No-contact, copyright-aware source policy for the two newsrooms.

Only sources with an explicit public-domain, CC BY, or primary-government basis
are eligible. A feed is used as a story lead; source text and media are not
copied. Item-level third-party credits still override the source-level policy.
"""
from __future__ import annotations

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

# use=headline_fact_lead means the feed title/link can trigger independent
# reporting. It never authorizes copying article paragraphs or media.
NEWS_SOURCES = [
    {
        "key": "globalvoices_ko",
        "name": "Global Voices 한국어 (CC BY 3.0)",
        "language": "ko",
        "category": "국제",
        "feed": "https://ko.globalvoices.org/feed/",
        "license": "cc_by_3",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "use": "headline_fact_lead",
    },
    {
        "key": "globalvoices_korea",
        "name": "Global Voices South Korea (CC BY 3.0)",
        "language": "ko",
        "category": "국제",
        "feed": "https://globalvoices.org/-/world/east-asia/south-korea/feed/",
        "license": "cc_by_3",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "use": "headline_fact_lead_translate",
    },
    {
        "key": "voa_east_asia_ko",
        "name": "Voice of America East Asia",
        "language": "ko",
        "category": "국제",
        "feed": "https://www.voanews.com/api/zobo_l-vomx-tpepvmv",
        "license": "voa_public_domain_item_check",
        "license_url": "https://www.voanews.com/p/5338.html",
        "use": "headline_fact_lead_translate",
    },
    {
        "key": "globalvoices_stories",
        "name": "Global Voices (CC BY 3.0)",
        "language": "en",
        "category": "World",
        "feed": "https://globalvoices.org/feed/?cat=-28",
        "license": "cc_by_3",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "use": "headline_fact_lead",
    },
    {
        "key": "globalvoices_east_asia",
        "name": "Global Voices East Asia (CC BY 3.0)",
        "language": "en",
        "category": "Asia & Korea",
        "feed": "https://globalvoices.org/-/world/east-asia/feed/",
        "license": "cc_by_3",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "use": "headline_fact_lead",
    },
    {
        "key": "voa_usa",
        "name": "Voice of America",
        "language": "en",
        "category": "Top Stories",
        "feed": "https://www.voanews.com/api/zqboml-vomx-tpeivmy",
        "license": "voa_public_domain_item_check",
        "license_url": "https://www.voanews.com/p/5338.html",
        "use": "headline_fact_lead",
    },
    {
        "key": "voa_east_asia",
        "name": "Voice of America East Asia",
        "language": "en",
        "category": "Asia & Korea",
        "feed": "https://www.voanews.com/api/zobo_l-vomx-tpepvmv",
        "license": "voa_public_domain_item_check",
        "license_url": "https://www.voanews.com/p/5338.html",
        "use": "headline_fact_lead",
    },
    {
        "key": "nasa",
        "name": "NASA",
        "language": "en",
        "category": "Technology",
        "feed": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
        "use": "primary_fact_lead",
    },
    {
        "key": "federal_reserve",
        "name": "Federal Reserve",
        "language": "en",
        "category": "Business",
        "feed": "https://www.federalreserve.gov/feeds/press_all.xml",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead",
    },
    {
        "key": "sec",
        "name": "U.S. Securities and Exchange Commission",
        "language": "en",
        "category": "Business",
        "feed": "https://www.sec.gov/news/pressreleases.rss",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead",
    },
]

BLOCKED_SOURCES = [
    "조선일보",
    "연합뉴스TV",
    "CNN",
    "The New York Times",
    "BBC",
    "Reuters",
    "AP",
]


def get_enabled_rss_sources(language: str) -> list[tuple[str, str]]:
    """All returned feeds have a no-contact reuse basis recorded above."""
    return [
        (source["name"], source["feed"])
        for source in NEWS_SOURCES
        if source["language"] == language and source.get("feed")
    ]


def source_audit() -> list[dict]:
    return [
        {
            "key": source["key"],
            "name": source["name"],
            "language": source["language"],
            "license": source["license"],
            "license_url": source["license_url"],
            "use": source["use"],
            "enabled": True,
        }
        for source in NEWS_SOURCES
    ]
