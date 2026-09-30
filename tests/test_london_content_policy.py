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
    assert policy["cadence"]["tistory"]["network_daily_total"] == 3
    for key in ("instagram", "threads", "tiktok", "facebook"):
        assert policy["cadence"][key]["weekly_target"] == 7
    assert policy["cadence"]["naver"]["network_daily_min"] >= 3


def test_locked_youtube_cadence_uses_owner_approved_immediate_public_for_core_ten():
    policy = load("london_content_schedule.json")
    for key in ("youtube_playlist", "youtube_knowledge"):
        cfg = policy["cadence"][key]
        assert (cfg["weekly_min"], cfg["weekly_max"]) == (7, 7)
        assert cfg["upload_default"] == "public"
        assert cfg["human_review_before_public"] is False
    for key in ("survival_10_language", "youtube_daily_additional"):
        cfg = policy["cadence"][key]
        assert (cfg["weekly_min"], cfg["weekly_max"]) == (7, 7)
        assert cfg["upload_default"] == "public_after_exact_channel_auth"
    survival = policy["cadence"]["survival_10_language"]
    assert survival["enabled"] is False
    assert len(survival["languages"]) == 10
    assert survival["lessons_per_language"] == 50
    assert survival["total_lessons"] == 500
    assert survival["completed_through_lesson"] == 2
    assert survival["next_lesson"] == 3
    assert survival["require_chairman_approval_before_public"] is False
    assert survival["missing_channel_ids"] == []
    assert policy["schedule_policy"]["cost_lock"] == "free_only_no_paid_fallback"


def test_london_image_policy_prefers_copyright_safe_sources():
    policy = load("london_content_schedule.json")
    assert policy["image_policy"]["copyright_safe_first"] is True
    assert policy["image_policy"]["order"] == [
        "pexels",
        "pixabay",
        "wikimedia_commons_cc0_public_domain",
        "pass_without_image",
    ]
    assert policy["image_policy"]["never_copy_unlicensed_news_photo"] is True


def test_london_failover_has_safe_hold_and_activity_ledger():
    policy = load("london_project_blueprint.json")
    assert policy["failover"]["pm_chain"] == ["openai", "anthropic", "gemini", "safe_hold"]
    assert policy["activity_ledger"]["every_task_must_be_recorded"] is True
    assert policy["governance"]["verified_complete_authority"] == "deterministic_audit_engine"
