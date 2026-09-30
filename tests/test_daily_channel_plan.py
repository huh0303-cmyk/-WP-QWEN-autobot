from datetime import date

from scripts import plan_52_channel_daily as planner


def test_every_non_youtube_target_is_planned_daily(monkeypatch):
    monkeypatch.setattr(planner, "ROOT", planner.Path(__file__).resolve().parents[1])
    payload = planner.build(date(2026, 9, 25))
    non_youtube = [row for row in payload["slots"] if row["platform"] != "YouTube"]
    assert len(non_youtube) == 24
    for platform in ("Instagram", "Threads", "Facebook", "TikTok"):
        assert len([row for row in non_youtube if row["platform"] == platform]) == 4
    assert {row["cadence"] for row in non_youtube} == {"1_per_day"}
    assert len({row["duplicate_key"] for row in payload["slots"]}) == len(payload["slots"])
    assert all(row["topic_brief"] for row in payload["slots"])


def test_all_locked_youtube_channels_have_one_daily_slot_without_claiming_publish_auth(monkeypatch):
    monkeypatch.setattr(planner, "ROOT", planner.Path(__file__).resolve().parents[1])
    rows = planner.youtube_targets(date(2026, 10, 1))
    assert len(rows) == len({row["identity"] for row in rows}) == 23
    assert {row["group"] for row in rows} == {"playlist", "knowledge", "language", "health", "shopping"}
    assert all(row["cadence"] == "1_per_day" and not row["publish_connected"] for row in rows)
    assert all(row["release_policy"] == "public_after_exact_channel_auth_and_receipt" for row in rows)


def test_daily_slots_use_randomized_non_round_minutes(monkeypatch):
    monkeypatch.setattr(planner, "ROOT", planner.Path(__file__).resolve().parents[1])
    payload = planner.build(date(2026, 9, 25))
    minutes = [int(row["scheduled_at"][14:16]) for row in payload["slots"]]
    assert all(minute % 5 for minute in minutes)
    assert payload["target_count"] == 47
    assert payload["daily_non_youtube_count"] == 24
    assert payload["minimum_gap_minutes"] >= 15
