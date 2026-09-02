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
        "categories": ["속보", "정치", "경제", "사회", "국제", "군사", "스포츠"],
        "daily_total_min": 3,
        "daily_total_max": 10,
        "daily_original_min": 2,
        "weekly_original_ratio_min": 0.30,
        "theme_candidate": "Twenty Twenty-Five News Blog",
    },
    "https://theseouljournal.com": {
        "publication": "The Seoul Journal",
        "language": "en",
        "categories": ["Top Stories", "World", "Business", "Technology", "Asia & Korea", "Military", "Sports"],
        "daily_total_min": 3,
        "daily_total_max": 10,
        "daily_original_min": 2,
        "weekly_original_ratio_min": 0.30,
        "theme_candidate": "Twenty Twenty-Five News Blog",
    },
}

# use=headline_fact_lead means the feed title/link can trigger independent
# reporting. It never authorizes copying article paragraphs or media.
NEWS_SOURCES = [
    {
        "key": "uk_government_politics_ko_desk",
        "name": "UK Government Politics",
        "language": "ko",
        "category": "정치",
        "feed": "https://www.gov.uk/search/news-and-communications.atom?keywords=politics",
        "license": "uk_open_government_licence_primary",
        "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "use": "primary_fact_lead_translate",
    },
    {
        "key": "uk_government_culture_ko_desk",
        "name": "UK Government Culture",
        "language": "ko",
        "category": "문화",
        "feed": "https://www.gov.uk/search/news-and-communications.atom?keywords=culture",
        "license": "uk_open_government_licence_primary",
        "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "use": "primary_fact_lead_translate",
    },
    {
        "key": "uk_government_sport_ko_desk",
        "name": "UK Government Sport",
        "language": "ko",
        "category": "스포츠",
        "feed": "https://www.gov.uk/search/news-and-communications.atom?keywords=sport",
        "license": "uk_open_government_licence_primary",
        "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "use": "primary_fact_lead_translate",
    },
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
        "key": "us_defense_news_ko_desk",
        "name": "U.S. Department of Defense News",
        "language": "ko",
        "category": "국방",
        "feed": "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead_translate",
    },
    {
        "key": "us_defense_releases_ko_desk",
        "name": "U.S. Department of Defense Releases",
        "language": "ko",
        "category": "국방",
        "feed": "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=9&Site=945&max=10",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead_translate",
    },
    {
        "key": "globalvoices_stories_ko_desk",
        "name": "Global Voices (CC BY 3.0)",
        "language": "ko",
        "category": "글로벌",
        "feed": "https://globalvoices.org/feed/?cat=-28",
        "license": "cc_by_3",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "use": "headline_fact_lead_translate",
    },
    {
        "key": "globalvoices_east_asia_ko_desk",
        "name": "Global Voices East Asia (CC BY 3.0)",
        "language": "ko",
        "category": "글로벌",
        "feed": "https://globalvoices.org/-/world/east-asia/feed/",
        "license": "cc_by_3",
        "license_url": "https://creativecommons.org/licenses/by/3.0/",
        "use": "headline_fact_lead_translate",
    },
    {
        "key": "voa_usa_ko_desk",
        "name": "Voice of America",
        "language": "ko",
        "category": "글로벌",
        "feed": "https://www.voanews.com/api/zqboml-vomx-tpeivmy",
        "license": "voa_public_domain_item_check",
        "license_url": "https://www.voanews.com/p/5338.html",
        "use": "headline_fact_lead_translate",
    },
    {
        "key": "voa_east_asia_ko_desk",
        "name": "Voice of America East Asia",
        "language": "ko",
        "category": "글로벌",
        "feed": "https://www.voanews.com/api/zobo_l-vomx-tpepvmv",
        "license": "voa_public_domain_item_check",
        "license_url": "https://www.voanews.com/p/5338.html",
        "use": "headline_fact_lead_translate",
    },
    {
        "key": "nasa_ko_desk",
        "name": "NASA",
        "language": "ko",
        "category": "경제",
        "feed": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
        "use": "primary_fact_lead_translate",
    },
    {
        "key": "federal_reserve_ko_desk",
        "name": "Federal Reserve",
        "language": "ko",
        "category": "금융",
        "feed": "https://www.federalreserve.gov/feeds/press_all.xml",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead_translate",
    },
    {
        "key": "sec_ko_desk",
        "name": "U.S. Securities and Exchange Commission",
        "language": "ko",
        "category": "금융",
        "feed": "https://www.sec.gov/news/pressreleases.rss",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead_translate",
    },
    {
        "key": "us_defense_news",
        "name": "U.S. Department of Defense News",
        "language": "en",
        "category": "Military",
        "feed": "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=10",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead",
    },
    {
        "key": "uk_government_politics",
        "name": "UK Government Politics",
        "language": "en",
        "category": "Politics",
        "feed": "https://www.gov.uk/search/news-and-communications.atom?keywords=politics",
        "license": "uk_open_government_licence_primary",
        "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "use": "primary_fact_lead",
    },
    {
        "key": "uk_government_culture",
        "name": "UK Government Culture",
        "language": "en",
        "category": "Culture",
        "feed": "https://www.gov.uk/search/news-and-communications.atom?keywords=culture",
        "license": "uk_open_government_licence_primary",
        "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "use": "primary_fact_lead",
    },
    {
        "key": "uk_government_sport",
        "name": "UK Government Sport",
        "language": "en",
        "category": "Sports",
        "feed": "https://www.gov.uk/search/news-and-communications.atom?keywords=sport",
        "license": "uk_open_government_licence_primary",
        "license_url": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "use": "primary_fact_lead",
    },
    {
        "key": "us_defense_releases",
        "name": "U.S. Department of Defense Releases",
        "language": "en",
        "category": "Military",
        "feed": "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=9&Site=945&max=10",
        "license": "us_federal_primary_item_check",
        "license_url": "https://www.usa.gov/government-copyright",
        "use": "primary_fact_lead",
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

# Images are eligible only when the individual asset carries one of these
# licenses. A site-wide public-sector label is never treated as permission for
# an unmarked photo, and any third-party credit blocks automatic reuse.
IMAGE_LICENSE_ALLOWLIST = {"kogl_0", "kogl_1", "cc0", "public_domain", "cc_by"}
IMAGE_BLOCKED_CREDITS = (
    "연합뉴스", "뉴시스", "뉴스1", "reuters", "associated press", "ap photo",
    "getty", "게티이미지", "공동취재", "자료사진", "제공",
)

IMAGE_SOURCES = [
    {
        "key": "kogl_portal",
        "name": "공공누리",
        "domains": ["kogl.or.kr"],
        "categories": ["정치", "경제", "사회", "국제", "군사", "스포츠"],
        "allowed_licenses": ["kogl_0", "kogl_1"],
        "policy_url": "https://www.kogl.or.kr/info/license.do",
        "use": "download_original_with_attribution",
    },
    {
        "key": "ktv",
        "name": "KTV 국민방송",
        "domains": ["ktv.go.kr"],
        "categories": ["정치", "경제", "사회", "군사"],
        "allowed_licenses": ["kogl_0", "kogl_1"],
        "policy_url": "https://www.ktv.go.kr/",
        "use": "item_level_license_only",
    },
    {
        "key": "national_assembly",
        "name": "대한민국 국회",
        "domains": ["assembly.go.kr"],
        "categories": ["정치", "사회"],
        "allowed_licenses": ["kogl_0", "kogl_1"],
        "policy_url": "https://www.assembly.go.kr/",
        "use": "item_level_license_only",
    },
    {
        "key": "mnd",
        "name": "대한민국 국방부",
        "domains": ["mnd.go.kr", "opendata.mnd.go.kr"],
        "categories": ["군사", "정치"],
        "allowed_licenses": ["kogl_0", "kogl_1"],
        "policy_url": "https://opendata.mnd.go.kr/",
        "use": "item_level_license_only",
    },
    {
        "key": "arirang",
        "name": "Arirang TV",
        "domains": ["arirang.com"],
        "categories": ["국제", "정치", "경제", "사회"],
        "allowed_licenses": ["kogl_0", "kogl_1"],
        "policy_url": "https://company.arirang.com/policy/copyright/?lang=en",
        "use": "item_level_license_only",
    },
    {
        "key": "nanet",
        "name": "대한민국 국회도서관",
        "domains": ["nanet.go.kr"],
        "categories": ["정치", "사회"],
        "allowed_licenses": ["kogl_0", "kogl_1", "cc0", "public_domain", "cc_by"],
        "policy_url": "https://www.nanet.go.kr/libintroduce/etc/libCoypRightView.do",
        "use": "item_level_license_only",
    },
    {
        "key": "natv",
        "name": "국회방송",
        "domains": ["natv.go.kr"],
        "categories": ["정치"],
        "allowed_licenses": ["kogl_0", "kogl_1"],
        "policy_url": "https://www.natv.go.kr/",
        "use": "embed_only_unless_item_level_license",
    },
]


def image_source_audit(license_code: str, credit: str = "", *, media_marked: bool = True) -> dict:
    """Return a conservative reuse decision for a single image asset."""
    normalized_license = license_code.strip().lower()
    normalized_credit = credit.strip().lower()
    blocked_credit = next(
        (token for token in IMAGE_BLOCKED_CREDITS if token.lower() in normalized_credit),
        None,
    )
    allowed = media_marked and normalized_license in IMAGE_LICENSE_ALLOWLIST and not blocked_credit
    return {
        "allowed": allowed,
        "reason": (
            "eligible_with_attribution" if allowed else
            "third_party_credit" if blocked_credit else
            "missing_or_ineligible_item_level_license"
        ),
        "blocked_credit": blocked_credit,
    }


def get_enabled_rss_sources(language: str) -> list[tuple[str, str]]:
    """All returned feeds have a no-contact reuse basis recorded above."""
    return [
        (source["name"], source["feed"])
        for source in NEWS_SOURCES
        if source["language"] == language and source.get("feed")
    ]


def get_enabled_rss_source_records(language: str) -> list[dict]:
    """Return complete, rights-audited source records for category-aware routing.

    Callers that only need a feed can keep using ``get_enabled_rss_sources``.
    Newsroom publishers should use this form so the recorded licence basis and
    editorial category are not discarded before publication.
    """
    return [
        dict(source)
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
