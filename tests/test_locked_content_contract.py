import json
import datetime as dt
import sys
from pathlib import Path

from control_center.quality import MIN_SCORE


ROOT = Path(__file__).resolve().parents[1]


def load_json(name):
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def test_quality_threshold_is_locked_at_70():
    assert MIN_SCORE == 70


def test_all_blog_writers_are_gpt5_mini_and_images_are_sdxl_first():
    policy = load_json("content_writing_policy.json")
    assert policy["primary_writer"]["provider"] == "openai"
    assert policy["primary_writer"]["model"] == "gpt-5-mini"
    assert policy["fallback_writer"]["provider"] == "openai"
    assert policy["image_generation"]["order"] == [
        "bytedance/sdxl-lightning-4step",
        "black-forest-labs/flux-schnell",
        "pass_without_image",
    ]
    tistory = (ROOT / "scripts" / "tistory_writer.py").read_text(encoding="utf-8")
    assert 'for provider in ("gpt",):' in tistory
    for workflow_name in ("daily-network-publish.yml", "newsrooms-daily-publisher.yml"):
        workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
        assert 'AI_TEXT_PROVIDER: "openai"' in workflow
        assert 'OPENAI_MODEL: "gpt-5-mini"' in workflow
        assert 'GEMINI_IMAGE_GENERATION_ENABLED: "false"' in workflow


def test_wordpress_and_newsroom_contract():
    sites = load_json("automation_hub_sites.json")["sites"]
    blogs = [s for s in sites if s["platform"] == "wordpress" and s.get("content_type") == "blog"]
    news = [s for s in sites if s["platform"] == "wordpress" and s.get("content_type", "").startswith("news_")]
    assert len(blogs) == 25
    assert all((s["daily_min"], s["daily_max"], s["weekly_min"], s["weekly_max"]) == (1, 1, 7, 7) for s in blogs)
    assert len(news) == 2
    assert all((s["daily_min"], s["daily_max"]) == (3, 10) for s in news)
    assert all((s["min_chars"], s["target_chars"], s["max_chars"]) == (700, 1100, 1500) for s in news)


def test_blogger_and_tistory_daily_contract():
    sites = load_json("automation_hub_sites.json")["sites"]
    blogger = [s for s in sites if s["platform"] == "blogger"]
    tistory = load_json("tistory_portfolio.json")
    assert len(blogger) == 27
    assert all((s["daily_min"], s["daily_max"], s["weekly_min"], s["weekly_max"]) == (1, 1, 7, 7) for s in blogger)
    assert tistory["daily_posts_per_site"] == 1
    assert len([s for s in tistory["sites"] if s.get("launch_enabled")]) == 5


def test_youtube_contract_and_global_worker_owner():
    channels = [c for c in load_json("youtube_channels.json")["channels"] if c.get("enabled")]
    assert len(channels) == 10
    assert all((c["interval_days_min"], c["interval_days_max"]) == (2, 3) for c in channels)
    for name in ("generate-youtube-playlist.yml", "curio-longform-daily.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "group: youtube-production-single-owner" in text
        assert "cancel-in-progress: false" in text


def test_youtube_generated_schedule_has_no_fixed_short_period_or_time_collision():
    sys.path.insert(0, str(ROOT / "scripts"))
    from roll_14day_content_calendar import KST, youtube_rows

    channels = [c for c in load_json("youtube_channels.json")["channels"] if c.get("enabled")]
    today = dt.datetime.now(KST).date()
    rows = youtube_rows(today + dt.timedelta(days=180), [], channels)
    slots = [row[1] for row in rows]
    assert len(slots) == len(set(slots))
    for channel in channels:
        dates_and_times = [
            (dt.date.fromisoformat(row[1][:10]), row[1][11:16])
            for row in rows if row[3] == channel["display_name"]
        ]
        gaps = [(b[0] - a[0]).days for a, b in zip(dates_and_times, dates_and_times[1:])]
        assert gaps and set(gaps) == {2, 3}
        assert all(a[1] != b[1] for a, b in zip(dates_and_times, dates_and_times[1:]))
        for period in range(1, min(9, len(gaps) // 2 + 1)):
            assert gaps != [gaps[i % period] for i in range(len(gaps))]


def test_policy_lock_records_newsroom_and_youtube_exceptions():
    text = (ROOT / "docs" / "CONTENT_CADENCE_POLICY_LOCK.md").read_text(encoding="utf-8")
    assert "3–10 public briefs" in text
    assert "700–1,500 visible characters" in text
    assert "every **2–3 days**" in text
