from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class KeywordSuggestion:
    keyword: str
    category: str
    verification: str = "weekly_research_pool"


KEYWORD_FILES = {
    "k-health365.com": "keywords_khealth.txt",
    "koreamedicaltour.com": "keywords_medicaltour.txt",
    "koreainvest365.com": "keywords_kinvest.txt",
    "ki-korea.com": "keywords_kikorea.txt",
    "koreainsurance365.com": "keywords_kinsurance.txt",
    "kfinance365.com": "keywords_kfinance.txt",
    "koreataxnlaw.com": "keywords_ktax.txt",
    "koreacrypto365.com": "keywords_kcrypto.txt",
    "krealestate365.com": "keywords_krealestate.txt",
    "ktech365.com": "keywords_ktech.txt",
    "oliveyoungkorea.com": "keywords_oliveyoung.txt",
    "kworld365.com": "keywords_kworld.txt",
    "k-trip365.com": "keywords_ktrip.txt",
    "k-visa365.com": "keywords_kvisa.txt",
    "kvisa365.com": "keywords_kvisa.txt",
    "koreawedding365.com": "keywords_kwedding.txt",
    "kstudy365.com": "keywords_kstudy365.txt",
    "studyinkorea365.com": "keywords_studyinkorea365.txt",
    "kieca-korea.org": "keywords_kieca.txt",
    "ksa-korea.org": "keywords_ksaKorea.txt",
    "sis-korea.com": "keywords_sisKorea.txt",
    "siskorea.com": "keywords_sisKorea.txt",
    "jobkorea365.com": "keywords_jobkorea365.txt",
    "jobinkorea365.com": "keywords_jobinkorea365.txt",
    "jobkoreaglobal.com": "keywords_jobkoreaglobal.txt",
    "korea365.org": "keywords_korea365.txt",
}


def _read_pool(domain: str) -> list[KeywordSuggestion]:
    filename = KEYWORD_FILES.get(domain.lower())
    if not filename:
        return []
    path = ROOT / "data" / "keywords" / filename
    if not path.exists():
        return []
    suggestions: list[KeywordSuggestion] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row or not row[0].strip():
                continue
            suggestions.append(KeywordSuggestion(
                keyword=row[0].strip(),
                category=row[1].strip() if len(row) > 1 else "General",
            ))
    return suggestions


def weekly_suggestions(domain: str, *, limit: int = 5, today: date | None = None) -> list[KeywordSuggestion]:
    """Choose stable weekly candidates; never invent unavailable score data."""
    pool = _read_pool(domain)
    if not pool:
        return []
    current = today or date.today()
    iso = current.isocalendar()
    seed = f"{domain.lower()}:{iso.year}:{iso.week}".encode("utf-8")
    start = int(hashlib.sha256(seed).hexdigest()[:12], 16) % len(pool)
    ordered = pool[start:] + pool[:start]
    return ordered[: max(1, min(limit, 5))]


def top_keywords_by_category(domain: str, *, per_category: int = 3) -> list[dict[str, object]]:
    """Top N keywords per category, ranked by today's search-volume+virality.

    2026-09-04 CEO: the "지금 발행" button needs a visible pick, not a silent
    auto-choice — 3 keyword chips per category, click one then publish.
    scripts/refresh_keyword_pool.py already re-researches and re-ranks this
    file every day (mention/outlet/surface count, highest first) and writes
    each category's entries in that same rank order, so simply grouping by
    category and keeping the first `per_category` per group already IS
    "today's top search-volume/virality keywords, per category" — no extra
    rotation or scoring needed here.
    """
    pool = _read_pool(domain)
    grouped: dict[str, list[str]] = {}
    for item in pool:
        bucket = grouped.setdefault(item.category, [])
        if len(bucket) < per_category:
            bucket.append(item.keyword)
    return [{"category": category, "keywords": keywords} for category, keywords in grouped.items()]


def tistory_seed_topics(site_id: str) -> list[dict[str, object]]:
    """This site's own configured seed topics as chips (Tistory has no daily
    virality-ranked pool file like WordPress, just a fixed candidate list per
    site in tistory_portfolio.json — still lets the CEO see a topic before
    creating the review draft, same UX as the WP/Blogspot chips)."""
    import json

    path = ROOT / "config" / "tistory_portfolio.json"
    if not path.exists():
        return []
    try:
        sites = json.loads(path.read_text(encoding="utf-8")).get("sites", [])
    except (OSError, ValueError):
        return []
    site = next((item for item in sites if item.get("site_id") == site_id), None)
    if not site:
        return []
    topics = [str(topic).strip() for topic in site.get("seed_topics") or [] if str(topic).strip()]
    if not topics:
        return []
    return [{"category": "추천 주제", "keywords": topics[:6]}]
