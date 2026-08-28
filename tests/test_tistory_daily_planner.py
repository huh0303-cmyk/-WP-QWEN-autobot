from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.tistory_daily_planner import build_plan, load_config


def test_tistory_portfolio_is_five_distinct_sites():
    cfg = load_config()
    assert len(cfg["sites"]) == 5
    assert len({s["site_id"] for s in cfg["sites"]}) == 5
    assert len({s["title"] for s in cfg["sites"]}) == 5


def test_daily_plan_stays_empty_until_sites_are_explicitly_launched():
    plan = build_plan(datetime(2026, 8, 28, 9, 0, tzinfo=ZoneInfo("Asia/Seoul")))
    assert plan["portfolio_sites"] == 5
    assert plan["enabled_sites"] == 0
    assert len(plan["jobs"]) == 0
    assert plan["daily_posts_per_site"] == 1
    assert plan["public_allowed"] is False
    assert all(j["publish_policy"] == "awaiting_approval" for j in plan["jobs"])
    assert all(j["duplicate_guard"] is True for j in plan["jobs"])
    assert all(j["public_allowed"] is False for j in plan["jobs"])


def test_petcare_preserves_existing_identity_and_requires_sources():
    cfg = load_config()
    site = next(s for s in cfg["sites"] if s["site_id"] == "tistory_petcare")
    assert site["title"] == "K-Petcare"
    assert site["url"] == "https://huh0303.tistory.com/"
    assert site["official_source_required"] is True
    assert "강아지건강" in site["categories"]
    assert "펫보험" in site["categories"]


def test_healthcare_site_is_not_repurposed_as_finance():
    cfg = load_config()
    site = next(s for s in cfg["sites"] if s["site_id"] == "tistory_healthcare_careers")
    assert site["title"] == "K-보건의료자격증"
    assert "국가자격" in site["categories"]
    assert "대출" not in site["categories"]


def test_all_sites_are_guarded_for_staged_relaunch():
    cfg = load_config()
    assert [s["launch_order"] for s in sorted(cfg["sites"], key=lambda x: x["launch_order"])] == [1, 2, 3, 4, 5]
    assert all(s["launch_enabled"] is False for s in cfg["sites"])
    assert all(s["preserve_identity"] is True for s in cfg["sites"])


def test_ktrip_is_english_for_foreign_visitors():
    cfg = load_config()
    site = next(s for s in cfg["sites"] if s["site_id"] == "tistory_ktrip365")
    assert site["language"] == "en"
    assert "Foreign" in site["audience"]
