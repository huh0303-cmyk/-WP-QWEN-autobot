"""Evidence-backed topic and WordPress-source routing for Blogger.

This module deliberately does not call a text-generation model.  The two GPT
calls available to a Blogger job remain reserved for writing and one repair.
Topic discovery uses today's public media/RSS evidence, while source routing
uses only public posts from the WordPress property paired in
``content_engine_profiles.json``.
"""

from __future__ import annotations

import html
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import quote_plus, urlparse
from xml.etree import ElementTree

import requests


KST = timezone(timedelta(hours=9))

# Direct feeds keep the named priority publications visible even when a search
# aggregator is unavailable. Google News adds a broad, independent repetition
# surface and returns the original outlet name in the RSS source element.
MEDIA_FEEDS = (
    ("Chosun Ilbo", "newspaper", "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("Hankyoreh", "newspaper", "https://www.hani.co.kr/rss/"),
    ("CNN", "newspaper", "https://rss.cnn.com/rss/edition.rss"),
    ("The New York Times", "newspaper", "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
    ("The Washington Post", "newspaper", "https://news.google.com/rss/search?q=when:1d+source:Washington_Post&hl=en-US&gl=US&ceid=US:en"),
    ("Los Angeles Times", "newspaper", "https://news.google.com/rss/search?q=when:1d+source:Los_Angeles_Times&hl=en-US&gl=US&ceid=US:en"),
    ("Google News Korea", "google", "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"),
    ("Google News US", "google", "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"),
)
TREND_FEEDS = (
    "https://trends.google.com/trending/rss?geo=KR",
    "https://trends.google.com/trending/rss?geo=US",
)
PRIORITY_OUTLETS = {"chosun ilbo", "hankyoreh", "cnn", "the new york times", "the washington post", "los angeles times"}
GENERAL_PROFILE_KEYS = {"korea365", "koreanews", "seouljournal", "tistory_life365"}

_EN_STOP = {
    "about", "after", "again", "amid", "and", "are", "as", "at", "but", "by", "for", "from", "has", "have",
    "first", "how", "into", "its", "new", "not", "over", "people", "says", "that", "the", "their", "this",
    "in", "into", "of", "on", "through", "to", "today", "was", "were", "will", "with", "world", "korea", "south",
    "latest", "live", "news", "update", "updates",
    "price", "prices", "cost", "costs", "guide", "tips", "best",
    "jan", "january", "feb", "february", "mar", "march", "apr", "april",
    "may", "jun", "june", "jul", "july", "aug", "august", "sep", "sept",
    "september", "oct", "october", "nov", "november", "dec", "december",
    "change", "changed", "changes", "changing", "could", "would", "should", "plan", "plans",
}
_KO_STOP = {
    "관련", "대한", "위한", "오늘", "뉴스", "속보", "논란", "발표", "정부", "한국",
    "했다", "한다", "된다", "있는", "없는", "통해", "대해", "가운데", "그리고", "차세대", "제정",
}
_CONCEPTS = {
    "travel": ("travel", "tour", "tourism", "flight", "hotel", "trip", "festival", "여행", "관광", "항공", "축제"),
    "kpop": ("k-pop", "kpop", "idol", "album", "concert", "billboard", "아이돌", "컴백", "가수", "공연"),
    "employment": ("job", "jobs", "employment", "worker", "salary", "career", "hiring", "취업", "고용", "근로", "채용", "임금"),
    "study": ("study", "student", "university", "school", "admission", "scholarship", "education", "유학", "학생", "대학", "입학", "장학", "교육"),
    "insurance": ("insurance", "coverage", "claim", "premium", "보험", "보장", "보험료"),
    "finance": ("finance", "bank", "banking", "credit", "card", "loan", "remittance", "금융", "은행", "대출", "송금"),
    "medical": ("medical", "hospital", "clinic", "patient", "treatment", "surgery", "의료", "병원", "환자", "치료", "수술"),
    "visa": ("visa", "immigration", "residence", "foreigner", "비자", "이민", "체류", "외국인"),
    "investment": ("investment", "investor", "stock", "market", "kospi", "fund", "투자", "주식", "증시", "펀드"),
    "beauty": ("beauty", "skincare", "cosmetic", "makeup", "ingredient", "뷰티", "화장품", "피부", "성분"),
    "crypto": ("crypto", "bitcoin", "ethereum", "token", "exchange", "blockchain", "가상자산", "비트코인", "코인", "거래소"),
    "wedding": ("wedding", "marriage", "couple", "bride", "groom", "결혼", "웨딩", "부부", "혼인"),
    "technology": ("technology", "tech", "ai", "semiconductor", "startup", "chip", "인공지능", "기술", "반도체", "스타트업"),
    "taxlaw": ("tax", "law", "legal", "regulation", "compliance", "세금", "세법", "법률", "규제"),
    "realestate": ("real estate", "housing", "apartment", "rent", "mortgage", "property", "부동산", "주택", "아파트", "전세", "월세"),
    "health": ("health", "disease", "nutrition", "wellness", "medicine", "건강", "질병", "영양", "의학"),
    "support": ("support", "benefit", "subsidy", "welfare", "grant", "지원금", "보조금", "혜택", "복지"),
}


class NoEligibleTopic(RuntimeError):
    """Raised when today's evidence contains no topic appropriate to a site."""


class NoRelatedWordPressSource(RuntimeError):
    """Raised when the winning topic has no sufficiently related public WP post."""


@dataclass(frozen=True)
class TopicCandidate:
    keyword: str
    score: float
    mention_count: int
    outlet_count: int
    surface_count: int
    viral_score: float
    evidence_urls: tuple[str, ...]
    evidence_text: str
    evidence_items: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class RoutedSource:
    topic: TopicCandidate
    post: dict | None
    source_score: float | None
    result_code: str


def _plain(value: object) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+-]{1,}|[가-힣]{2,}", _plain(text).casefold())
    return {
        word.rstrip("은는이가을를의에로와과도만") if re.search(r"[가-힣]", word) else word.rstrip("s")
        for word in words
        if word not in _EN_STOP and word not in _KO_STOP and len(word) >= 2
    }


def _concepts(text: str) -> set[str]:
    folded = _plain(text).casefold()
    return {
        concept
        for concept, aliases in _CONCEPTS.items()
        if any(re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", folded) if alias.isascii() else alias in folded for alias in aliases)
    }


def _published_date(item: ElementTree.Element) -> date | None:
    raw = ""
    for name in ("pubDate", "published", "updated", "{http://purl.org/dc/elements/1.1/}date"):
        node = item.find(name)
        if node is not None and node.text:
            raw = node.text.strip()
            break
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(KST).date()


def _rss_items(xml_text: str | bytes, *, fallback_outlet: str, surface: str, today: date) -> list[dict[str, str]]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []
    rows: list[dict[str, str]] = []
    for item in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title_node = item.find("title")
        if title_node is None:
            title_node = item.find("{http://www.w3.org/2005/Atom}title")
        link_node = item.find("link")
        if link_node is None:
            link_node = item.find("{http://www.w3.org/2005/Atom}link")
        if title_node is None or not (title_node.text or "").strip() or link_node is None:
            continue
        published = _published_date(item)
        if published is not None and published != today:
            continue
        url = (link_node.text or link_node.attrib.get("href") or "").strip()
        if urlparse(url).scheme not in {"http", "https"}:
            continue
        source_node = item.find("source")
        outlet = (source_node.text or "").strip() if source_node is not None else fallback_outlet
        rows.append({
            "title": _plain(title_node.text).strip(), "url": url, "outlet": outlet or fallback_outlet,
            "surface": surface, "published_on": today.isoformat(),
        })
    return rows


def fetch_today_headlines(*, session=requests, today: date | None = None, timeout: int = 12) -> list[dict[str, str]]:
    observed_on = today or datetime.now(KST).date()
    rows: list[dict[str, str]] = []
    for outlet, surface, url in MEDIA_FEEDS:
        try:
            response = session.get(url, timeout=timeout, headers={"User-Agent": "Korea365TopicRouter/1.0"})
            response.raise_for_status()
            rows.extend(_rss_items(response.content, fallback_outlet=outlet, surface=surface, today=observed_on))
        except (requests.RequestException, ValueError):
            continue
    # One URL cannot become multiple independent mentions through aggregation.
    return list({row["url"]: row for row in rows}.values())


def fetch_profile_headlines(profile: dict, *, session=requests, today: date | None = None, timeout: int = 12) -> list[dict[str, str]]:
    """Fetch a same-day topical Google News surface for a specialist site."""
    if is_general_profile(profile):
        return []
    observed_on = today or datetime.now(KST).date()
    theme = str((profile.get("wordpress") or {}).get("theme", "")).strip()
    persona = str((profile.get("wordpress") or {}).get("persona", "")).strip()
    categories = (profile.get("wordpress") or {}).get("categories") or []
    category_hint = " OR ".join(str(item).strip() for item in categories[:3] if str(item).strip())
    # The persona usually carries the missing geographic or audience qualifier
    # (for example "Korea travel"), so use it to keep a broad theme such as
    # Travel from drifting into unrelated US-only seasonal stories.
    profile_scope = f"{theme} {persona}".casefold()
    # Keep the query compact. Long persona prose weakens Google News matching;
    # only retain the geographic qualifier that materially narrows the niche.
    scope_hint = f'"{theme}" Korea' if "korea" in profile_scope and "korea" not in theme.casefold() else theme
    query = f"({scope_hint})" + (f" ({category_hint})" if category_hint else "") + " when:1d"
    language = str(profile.get("language", "en")).casefold()
    locale = "hl=ko&gl=KR&ceid=KR:ko" if language.startswith("ko") else "hl=en-US&gl=US&ceid=US:en"
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&{locale}"
    try:
        response = session.get(url, timeout=timeout, headers={"User-Agent": "Korea365TopicRouter/1.0"})
        response.raise_for_status()
        return _rss_items(response.content, fallback_outlet="Google News", surface="google", today=observed_on)
    except (requests.RequestException, ValueError):
        return []


def fetch_trending_terms(*, session=requests, timeout: int = 12) -> list[str]:
    terms: list[str] = []
    for url in TREND_FEEDS:
        try:
            response = session.get(url, timeout=timeout, headers={"User-Agent": "Korea365TopicRouter/1.0"})
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
            terms.extend(_plain(node.text).strip() for node in root.findall(".//item/title") if (node.text or "").strip())
        except (requests.RequestException, ElementTree.ParseError, ValueError):
            continue
    return list(dict.fromkeys(terms))


def _headline_phrases(title: str) -> set[str]:
    # Outlet suffixes add noise and tend to dominate aggregated feeds.
    title = re.split(r"\s[-|]\s(?=[^-|]+$)", _plain(title).strip())[0]
    raw = re.findall(r"[A-Za-z][A-Za-z0-9+-]{1,}|[가-힣]{2,}", title)
    # Stop words are boundaries, not merely removable filler. This prevents
    # artificial phrases made by joining words that were not adjacent in the
    # original headline (for example, "September changed travel").
    segments: list[list[str]] = [[]]
    for word in raw:
        if word.casefold() in _EN_STOP or word in _KO_STOP:
            if segments[-1]:
                segments.append([])
            continue
        segments[-1].append(word)
    phrases: set[str] = set()
    for kept in segments:
        for width in (1, 2, 3):
            for index in range(len(kept) - width + 1):
                chunk = kept[index:index + width]
                if any(re.search(r"[가-힣]", word) for word in chunk) and any(re.search(r"[A-Za-z]", word) for word in chunk):
                    continue
                phrase = " ".join(chunk).strip()
                if len("".join(chunk)) >= 3:
                    phrases.add(phrase)
    return phrases


def _profile_text(profile: dict) -> str:
    wp = profile.get("wordpress") or {}
    blog = profile.get("blogspot") or {}
    categories: list[str] = []
    for value in (profile.get("categories"), wp.get("categories"), blog.get("categories")):
        if isinstance(value, list):
            categories.extend(str(item) for item in value)
    return " ".join((str(wp.get("theme", "")), str(wp.get("persona", "")), str(blog.get("persona", "")), *categories))


def is_general_profile(profile: dict) -> bool:
    key = str(profile.get("site_key", ""))
    # General routing is an explicit editorial classification.  Never infer it
    # from a long or comma-separated theme: a specialist such as weddings can
    # legitimately cover several subtopics and must still stay in its lane.
    return key in GENERAL_PROFILE_KEYS


def _fits_profile(candidate_text: str, profile: dict) -> bool:
    if is_general_profile(profile):
        return True
    scope = _profile_text(profile)
    scope_tokens = _tokens(scope)
    candidate_tokens = _tokens(candidate_text)
    return bool(scope_tokens & candidate_tokens or _concepts(scope) & _concepts(candidate_text))


def rank_topics(headlines: Iterable[dict[str, str]], *, profile: dict, trend_terms: Iterable[str] = ()) -> list[TopicCandidate]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    display: dict[str, str] = {}
    for row in headlines:
        for phrase in _headline_phrases(row.get("title", "")):
            key = re.sub(r"[^0-9a-z가-힣]+", "", phrase.casefold())
            if len(key) < 3:
                continue
            grouped[key].append(row)
            display.setdefault(key, phrase)

    trend_sets = [(_tokens(term), term.casefold()) for term in trend_terms]
    candidates: list[TopicCandidate] = []
    for key, mentions in grouped.items():
        unique = {row.get("url", ""): row for row in mentions if row.get("url")}
        if len(unique) < 2:
            continue
        rows = list(unique.values())
        outlets = {row.get("outlet", "").casefold() for row in rows if row.get("outlet")}
        if len(outlets) < 2:
            continue
        evidence_text = " ".join(row.get("title", "") for row in rows)
        phrase = display[key]
        phrase_tokens = _tokens(phrase)
        if not phrase_tokens:
            continue
        # A lone generic English noun from a topical search (for example
        # "Prices" or "Labor") is not a useful specialist keyword. Require
        # either a multi-word phrase or a direct match to the site's scope.
        if not is_general_profile(profile) and len(phrase_tokens) == 1 and re.fullmatch(r"[A-Za-z0-9+-]+", phrase):
            scope = _profile_text(profile)
            if not (phrase_tokens & _tokens(scope) or _concepts(phrase) & _concepts(scope)):
                continue
        if not _fits_profile(f"{phrase} {evidence_text}", profile):
            continue
        surfaces = {row.get("surface", "") for row in rows if row.get("surface")}
        # A search query naturally repeats the site's broad theme in most
        # results. It is a scope filter, not a newsworthy topic by itself.
        if not is_general_profile(profile) and phrase_tokens <= _tokens(_profile_text(profile)):
            continue
        trend_matches = sum(1 for tokens, raw in trend_sets if phrase.casefold() in raw or (phrase_tokens and phrase_tokens <= tokens))
        priority_count = len(PRIORITY_OUTLETS & outlets)
        viral_score = min(20.0, trend_matches * 10.0 + max(0, len(rows) - 2) * 2.0 + max(0, len(outlets) - 2) * 2.0)
        score = (
            min(48.0, len(rows) * 12.0)
            + min(20.0, len(outlets) * 6.0)
            + min(8.0, len(surfaces) * 4.0)
            + min(8.0, priority_count * 2.0)
            + viral_score
            + min(4.0, len(phrase_tokens))
        )
        candidates.append(TopicCandidate(
            keyword=phrase, score=round(min(100.0, score), 2), mention_count=len(rows),
            outlet_count=len(outlets), surface_count=len(surfaces), viral_score=viral_score,
            evidence_urls=tuple(unique), evidence_text=evidence_text,
            evidence_items=tuple((row.get("outlet", "Media"), row.get("title", ""), row.get("url", "")) for row in rows),
        ))
    candidates.sort(key=lambda item: (-item.score, -len(item.keyword), item.keyword.casefold()))
    return candidates


def fetch_public_wp_posts(site_url: str, *, session=requests, timeout: int = 20) -> list[dict]:
    response = session.get(
        f"{site_url.rstrip('/')}/wp-json/wp/v2/posts",
        params={
            "status": "publish", "per_page": 100, "orderby": "date", "order": "desc",
            "_fields": "id,link,status,title,excerpt,content,date",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("WordPress posts endpoint did not return a list")
    return [post for post in payload if post.get("status") == "publish" and post.get("link")]


def source_similarity(topic: TopicCandidate | str, post: dict, *, profile: dict) -> float:
    keyword = topic.keyword if isinstance(topic, TopicCandidate) else str(topic)
    title = _plain((post.get("title") or {}).get("rendered", ""))
    excerpt = _plain((post.get("excerpt") or {}).get("rendered", ""))
    body = _plain((post.get("content") or {}).get("rendered", ""))[:4000]
    topic_tokens = _tokens(keyword)
    if not topic_tokens:
        return 0.0
    title_tokens, body_tokens = _tokens(title), _tokens(f"{excerpt} {body}")
    direct_title = len(topic_tokens & title_tokens) / len(topic_tokens)
    direct_body = len(topic_tokens & body_tokens) / len(topic_tokens)
    topic_concepts = _concepts(f"{keyword} {getattr(topic, 'evidence_text', '')}")
    post_concepts = _concepts(f"{title} {excerpt} {body}")
    concept_overlap = len(topic_concepts & post_concepts) / max(1, len(topic_concepts))
    exact = 1.0 if re.sub(r"\W+", "", keyword.casefold()) in re.sub(r"\W+", "", title.casefold()) else 0.0
    # A shared broad site concept alone (for example, both are 'health') is not
    # enough. At least one topic term must occur in the public article.
    if not (topic_tokens & (title_tokens | body_tokens)):
        return 0.0
    return round(0.55 * direct_title + 0.20 * direct_body + 0.15 * concept_overlap + 0.10 * exact, 4)


def select_wp_source(
    topic: TopicCandidate,
    posts: Iterable[dict],
    *,
    profile: dict,
    excluded_urls: Iterable[str] = (),
    minimum_score: float = 0.32,
) -> tuple[dict, float] | None:
    excluded = {url.rstrip("/") for url in excluded_urls}
    ranked = [
        (source_similarity(topic, post, profile=profile), post)
        for post in posts
        if str(post.get("link", "")).rstrip("/") not in excluded
    ]
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    if not ranked or ranked[0][0] < minimum_score:
        return None
    return ranked[0][1], ranked[0][0]


def resolve_automatic_source(
    profile: dict,
    *,
    session=requests,
    today: date | None = None,
    excluded_urls: Iterable[str] = (),
) -> RoutedSource:
    headlines = fetch_today_headlines(session=session, today=today)
    headlines.extend(fetch_profile_headlines(profile, session=session, today=today))
    headlines = list({row["url"]: row for row in headlines}.values())
    trends = fetch_trending_terms(session=session)
    topics = rank_topics(headlines, profile=profile, trend_terms=trends)
    if not topics:
        raise NoEligibleTopic("오늘자 복수 매체 근거와 사이트 주제를 함께 만족하는 주제어가 없습니다.")
    # The user asked for the highest-virality topic first. We do not silently
    # downgrade to an unrelated lower-ranked topic merely because it has a WP post.
    winner = topics[0]
    wp_url = str((profile.get("wordpress") or {}).get("url", "")).rstrip("/")
    if not wp_url:
        raise NoRelatedWordPressSource("프로필에 연결된 WordPress 주소가 없습니다.")
    try:
        posts = fetch_public_wp_posts(wp_url, session=session)
    except (requests.RequestException, ValueError):
        posts = []
    selected = select_wp_source(winner, posts, profile=profile, excluded_urls=excluded_urls)
    if selected is None:
        return RoutedSource(
            topic=winner, post=None, source_score=None,
            result_code="INDEPENDENT_TREND_ARTICLE",
        )
    post, score = selected
    return RoutedSource(topic=winner, post=post, source_score=score, result_code="WP_RELATED_SOURCE")
