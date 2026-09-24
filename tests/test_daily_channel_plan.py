from datetime import date, timedelta

from scripts import plan_52_channel_daily as planner


def test_every_non_youtube_target_is_planned_daily(monkeypatch):
    monkeypatch.setattr(planner, "ROOT", planner.Path(__file__).resolve().parents[1])
    payload = planner.build(date(2026, 9, 25))
    non_youtube = [row for row in payload["slots"] if row["platform"] != "YouTube"]
    assert len(non_youtube) == 32
    assert {row["cadence"] for row in non_youtube} == {"1_per_day"}
    assert len({row["duplicate_key"] for row in payload["slots"]}) == len(payload["slots"])
    assert all(row["topic_brief"] for row in payload["slots"])


def test_each_locked_youtube_channel_is_due_two_or_three_days_per_week(monkeypatch):
    monkeypatch.setattr(planner, "ROOT", planner.Path(__file__).resolve().parents[1])
    monday = date(2026, 9, 21)
    counts = {}
    for offset in range(7):
        for row in planner.youtube_targets(monday + timedelta(days=offset)):
            counts[row["identity"]] = counts.get(row["identity"], 0) + 1
            assert row["release_policy"] == "private_review_only"
    assert len(counts) == 10
    assert set(counts.values()) <= {2, 3}


def test_daily_slots_use_randomized_non_round_minutes(monkeypatch):
    monkeypatch.setattr(planner, "ROOT", planner.Path(__file__).resolve().parents[1])
    payload = planner.build(date(2026, 9, 25))
    minutes = [int(row["scheduled_at"][14:16]) for row in payload["slots"]]
    assert all(minute % 5 for minute in minutes)
