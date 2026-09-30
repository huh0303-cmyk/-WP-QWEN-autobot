#!/usr/bin/env python3
"""Create a randomized, research-gated daily plan for the three Naver blogs."""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "naver_homefeed_automation.json"
CALENDAR_PATH = ROOT / "config" / "naver_monthly_keyword_calendar.json"
KST = ZoneInfo("Asia/Seoul")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _spaced_minutes(count: int, minimum_gap: int, rng: random.Random) -> list[int]:
    start, end = 6 * 60 + 37, 23 * 60 + 18
    slack = (end - 1 - start) - minimum_gap * (count - 1)
    if slack < count - 1:
        raise RuntimeError(f"cannot fit {count} slots with {minimum_gap}-minute gaps")
    for _ in range(2000):
        offsets = sorted(rng.sample(range(slack + 1), count))
        chosen = [start + index * minimum_gap + offsets[index] for index in range(count)]
        if all(minute % 5 for minute in chosen):
            return chosen
    raise RuntimeError(f"cannot create {count} slots with {minimum_gap}-minute gaps")


def _topic_pool(calendar: dict, month: int, site_id: str, year: int) -> list[dict]:
    links = calendar["research_links"]
    candidates = []
    seen = set()
    for cluster in calendar["months"][str(month)]:
        if site_id not in cluster["site_ids"]:
            continue
        official_urls = [links[key] for key in cluster["official_sources"]]
        for query in cluster["queries"]:
            variants = [
                f"{year}년 {month}월 {query}",
                f"{query} 신청방법과 확인할 것",
                f"{query} 대상·기간·공식 링크",
            ]
            for title_seed in variants:
                normalized = "".join(title_seed.split()).lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                encoded = quote_plus(query)
                candidates.append({
                    "cluster": cluster["cluster"],
                    "title_seed": title_seed,
                    "base_query": query,
                    "research": {
                        "naver_search": links["naver_web_search_template"].format(query=encoded),
                        "naver_news": links["naver_news_search_template"].format(query=encoded),
                        "naver_datalab": links["naver_datalab"],
                        "official_sources": official_urls,
                    },
                    "status": "RESEARCH_REQUIRED",
                    "measured_search_volume": None,
                })
    if site_id == "naver_n1":
        for query in calendar["evergreen_expansions"]["finance_queries"]:
            encoded = quote_plus(query)
            candidates.append({
                "cluster": "상시 생활금융",
                "title_seed": f"{year}년 {query}, 신청·계약 전에 확인할 것",
                "base_query": query,
                "research": {
                    "naver_search": links["naver_web_search_template"].format(query=encoded),
                    "naver_news": links["naver_news_search_template"].format(query=encoded),
                    "naver_datalab": links["naver_datalab"],
                    "official_sources": [links["government24"]],
                },
                "status": "RESEARCH_REQUIRED",
                "measured_search_volume": None,
            })
    if site_id == "naver_n3":
        for station in calendar["evergreen_expansions"]["rail_origins"]:
            query = f"{station} KTX 시간표"
            encoded = quote_plus(query)
            candidates.append({
                "cluster": "역별 기차시간·예매",
                "title_seed": f"{year}년 {station} KTX 시간표·예매 전 확인할 것",
                "base_query": query,
                "research": {
                    "naver_search": links["naver_web_search_template"].format(query=encoded),
                    "naver_news": links["naver_news_search_template"].format(query=encoded),
                    "naver_datalab": links["naver_datalab"],
                    "official_sources": [links["korail"]],
                },
                "status": "RESEARCH_REQUIRED",
                "measured_search_volume": None,
            })
        for area in calendar["evergreen_expansions"]["airport_bus_areas"]:
            query = f"{area} 인천공항버스 시간표"
            encoded = quote_plus(query)
            candidates.append({
                "cluster": "지역별 공항버스",
                "title_seed": f"{year}년 {area} 인천공항버스 시간표·요금·타는 곳",
                "base_query": query,
                "research": {
                    "naver_search": links["naver_web_search_template"].format(query=encoded),
                    "naver_news": links["naver_news_search_template"].format(query=encoded),
                    "naver_datalab": links["naver_datalab"],
                    "official_sources": [links["airport_transport"]],
                },
                "status": "RESEARCH_REQUIRED",
                "measured_search_volume": None,
            })
    return candidates


def build_plan(now: datetime | None = None, rng: random.Random | None = None) -> dict:
    now = now or datetime.now(KST)
    rng = rng or random.SystemRandom()
    policy = load_json(POLICY_PATH)
    calendar = load_json(CALENDAR_PATH)
    day = now.date().isoformat()
    jobs = []
    for site_id in policy["active_site_ids"]:
        cadence = policy["per_site_cadence"][site_id]
        count = rng.randint(int(cadence["daily_min"]), int(cadence["daily_max"]))
        topics = _topic_pool(calendar, now.month, site_id, now.year)
        by_query = {}
        for topic in topics:
            by_query.setdefault(topic["base_query"], []).append(topic)
        if len(by_query) < count:
            raise RuntimeError(f"not enough monthly candidates for {site_id}")
        selected_queries = rng.sample(list(by_query), count)
        selected = [rng.choice(by_query[query]) for query in selected_queries]
        minutes = _spaced_minutes(count, int(cadence["minimum_interval_minutes"]), rng)
        for index, (topic, minute) in enumerate(zip(selected, minutes), start=1):
            jobs.append({
                "job_id": f"{site_id}:{day}:{index}",
                "site_id": site_id,
                "display_name": cadence["display_name"],
                "blog_id": cadence["blog_id"],
                "scheduled_local_time": f"{minute // 60:02d}:{minute % 60:02d}",
                **topic,
                "gates": [
                    "compare_relative_interest_in_naver_datalab",
                    "confirm_current_news_or_evergreen_intent",
                    "open_primary_official_source",
                    "check_recent_titles_and_body_similarity",
                    "write_original_answer_first_article",
                    "verify_exact_destination_blog_id",
                    "verify_public_url_after_publish",
                ],
            })
    return {
        "generated_at": now.isoformat(),
        "date": day,
        "timezone": "Asia/Seoul",
        "month": now.month,
        "network_daily_min": policy["cadence"]["network_daily_min"],
        "network_daily_max": policy["cadence"]["network_daily_max"],
        "selected_job_count": len(jobs),
        "search_volume_numbers_invented": False,
        "google_indexing_api_for_general_posts": False,
        "jobs": sorted(jobs, key=lambda item: item["scheduled_local_time"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/naver-daily-plan.json")
    args = parser.parse_args()
    plan = build_plan()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"date": plan["date"], "jobs": len(plan["jobs"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
