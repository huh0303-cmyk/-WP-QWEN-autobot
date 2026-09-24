import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def test_london_schedule_contract():
    policy = load("london_content_schedule.json")
    assert policy["timezone"] == "Asia/Seoul"
    assert policy["schedule_policy"]["planned_jitter_minutes"] == 60
    assert policy["schedule_policy"]["forbid_exact_hour"] is True
    assert policy["cadence"]["wordpress_general"]["target"] == "1_per_day"
    news = policy["cadence"]["newsrooms"]
    assert news["daily_max"] == 1
    assert news["target"] == "1_per_day_per_newsroom"
    assert news["never_invent_to_fill_minimum"] is True
    assert policy["cadence"]["blogspot"]["target"] == "1_public_post_per_enabled_destination_per_day"
    assert policy["cadence"]["tistory"]["target"] == "1_public_post_per_enabled_site_per_day"
    for key in ("instagram", "threads", "tiktok", "facebook", "naver"):
        assert policy["cadence"][key]["weekly_target"] == 7


def test_locked_youtube_cadence_is_two_to_three_times_weekly_and_private_first():
    policy = load("london_content_schedule.json")
    for key in ("youtube_playlist", "youtube_knowledge"):
        cfg = policy["cadence"][key]
        assert (cfg["weekly_min"], cfg["weekly_max"]) == (2, 3)
        assert cfg["upload_default"] == "private"
    survival = policy["cadence"]["survival_10_language"]
    assert survival["enabled"] is False
    assert len(survival["languages"]) == 10
    assert survival["lessons_per_language"] == 50
    assert survival["total_lessons"] == 500
    assert survival["completed_through_lesson"] == 2
    assert survival["next_lesson"] == 3
    assert survival["require_chairman_approval_before_public"] is True


def test_london_image_policy_prefers_copyright_safe_sources():
    policy = load("london_content_schedule.json")
    assert policy["image_policy"]["copyright_safe_first"] is True
    assert policy["image_policy"]["order"] == [
        "pexels",
        "pixabay",
        "bytedance/sdxl-lightning-4step",
        "black-forest-labs/flux-schnell",
        "pass_without_image",
    ]
    assert policy["image_policy"]["never_copy_unlicensed_news_photo"] is True


def test_london_failover_has_safe_hold_and_activity_ledger():
    policy = load("london_project_blueprint.json")
    assert policy["failover"]["pm_chain"] == ["openai", "anthropic", "gemini", "safe_hold"]
    assert policy["activity_ledger"]["every_task_must_be_recorded"] is True
    assert policy["governance"]["verified_complete_authority"] == "deterministic_audit_engine"
