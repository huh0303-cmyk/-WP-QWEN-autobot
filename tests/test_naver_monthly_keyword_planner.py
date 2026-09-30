import random
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.naver_monthly_keyword_planner import build_plan, load_json, CALENDAR_PATH, CATALOG_PATH


def test_calendar_covers_all_months_and_three_sites():
    calendar = load_json(CALENDAR_PATH)
    assert set(calendar["months"]) == {str(month) for month in range(1, 13)}
    covered = {
        site_id
        for clusters in calendar["months"].values()
        for cluster in clusters
        for site_id in cluster["site_ids"]
    }
    assert covered == {"naver_n1", "naver_n2", "naver_n3"}


def test_monthly_keyword_catalog_has_exactly_100_unique_candidates_per_month():
    catalog = load_json(CATALOG_PATH)
    assert set(catalog["months"]) == {str(month) for month in range(1, 13)}
    for keywords in catalog["months"].values():
        assert len(keywords) == 100
        assert len({item["query"] for item in keywords}) == 100
        assert all(item["official_sources"] for item in keywords)


def test_october_plan_respects_randomized_daily_ranges_and_gaps():
    plan = build_plan(
        datetime(2026, 10, 1, 1, 0, tzinfo=ZoneInfo("Asia/Seoul")),
        rng=random.Random(101),
    )
    by_site = {}
    for job in plan["jobs"]:
        by_site.setdefault(job["site_id"], []).append(job)
        assert job["status"] == "RESEARCH_REQUIRED"
        assert job["measured_search_volume"] is None
        assert job["research"]["official_sources"]
        assert "naver_news" in job["research"]
    assert 3 <= len(by_site["naver_n1"]) <= 4
    assert 3 <= len(by_site["naver_n2"]) <= 4
    assert 8 <= len(by_site["naver_n3"]) <= 10
    assert 14 <= len(plan["jobs"]) <= 18
    minimums = {"naver_n1": 180, "naver_n2": 180, "naver_n3": 75}
    for site_id, jobs in by_site.items():
        assert len({job["base_query"] for job in jobs}) == len(jobs)
        minutes = sorted(int(j["scheduled_local_time"][:2]) * 60 + int(j["scheduled_local_time"][3:]) for j in jobs)
        assert all(b - a >= minimums[site_id] for a, b in zip(minutes, minutes[1:]))
        assert all(minute % 5 for minute in minutes)
        assert all(minute >= 8 * 60 + 17 for minute in minutes)


def test_general_naver_posts_never_use_google_indexing_api():
    plan = build_plan(
        datetime(2026, 12, 1, 1, 0, tzinfo=ZoneInfo("Asia/Seoul")),
        rng=random.Random(12),
    )
    assert plan["google_indexing_api_for_general_posts"] is False
    assert plan["search_volume_numbers_invented"] is False
