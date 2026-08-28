from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.tistory_daily_planner import build_plan, load_config


def test_tistory_portfolio_is_five_distinct_sites():
    cfg = load_config()
    assert len(cfg["sites"]) == 5
    assert len({s["site_id"] for s in cfg["sites"]}) == 5
    assert len({s["title"] for s in cfg["sites"]}) == 5


def test_daily_plan_is_one_per_site_and_never_public():
    plan = build_plan(datetime(2026, 8, 28, 9, 0, tzinfo=ZoneInfo("Asia/Seoul")))
    assert len(plan["jobs"]) == 5
    assert plan["daily_posts_per_site"] == 1
    assert plan["public_allowed"] is False
    assert all(j["publish_policy"] == "awaiting_approval" for j in plan["jobs"])
    assert all(j["duplicate_guard"] is True for j in plan["jobs"])
    assert all(j["public_allowed"] is False for j in plan["jobs"])


def test_life365_requires_official_source():
    cfg = load_config()
    site = next(s for s in cfg["sites"] if s["site_id"] == "tistory_life365")
    assert site["trend_mode"] is True
    assert site["official_source_required"] is True
    assert "정부지원금" in site["categories"]
    assert "교통·시간표" in site["categories"]


def test_ktrip_is_english_for_foreign_visitors():
    cfg = load_config()
    site = next(s for s in cfg["sites"] if s["site_id"] == "tistory_ktrip365")
    assert site["language"] == "en"
    assert "Foreign" in site["audience"]
