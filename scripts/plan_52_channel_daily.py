#!/usr/bin/env python3
"""Build the London Project daily publication plan.

Owner cadence (2026-09-25): the locked ten YouTube channels receive two or
three randomly selected private-production days per week. Every non-YouTube
account receives one slot every day. Planning never bypasses identity or write
authorization gates and never makes a YouTube video public.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(os.environ.get("KOREA365_ROOT", "/opt/korea365"))
KST = timezone(timedelta(hours=9))
WINDOW_START_MINUTE = 8 * 60 + 10
WINDOW_END_MINUTE = 22 * 60 + 50


def read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _weekly_youtube_days(channel_id: str, week_start: date) -> set[int]:
    salt = os.environ.get("SCHEDULE_RANDOM_SALT", "")
    seed = f"london-youtube-week|{week_start.isoformat()}|{channel_id}|{salt}"
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    weekly_count = rng.choice((2, 3))
    return set(rng.sample(range(7), weekly_count))


def youtube_targets(day: date) -> list[dict]:
    lock = read(ROOT / "config/youtube-ten-channel-lock.json", {})
    rows = lock.get("groups", {}).get("playlist", []) + lock.get("groups", {}).get("knowledge", [])
    if len(rows) != 10:
        raise RuntimeError(f"expected 10 locked YouTube channels, found {len(rows)}")
    week_start = day - timedelta(days=day.weekday())
    due = []
    for row in rows:
        channel_id = str(row.get("channel_id", ""))
        if day.weekday() not in _weekly_youtube_days(channel_id, week_start):
            continue
        group = "playlist" if int(row.get("order", 0)) <= 5 else "knowledge"
        due.append({
            "key": f"youtube:{channel_id}", "platform": "YouTube",
            "name": row.get("label", channel_id), "identity": channel_id,
            "publish_connected": True, "release_policy": "private_review_only",
            "cadence": "2_to_3_per_week_random_days",
            "topic_source": f"youtube_{group}_topic_pipeline",
            "topic_brief": "Select a fresh, non-duplicate topic from the channel-specific topic bank.",
        })
    return due


def daily_non_youtube_targets() -> list[dict]:
    result = []
    sns = read(ROOT / "config/sns_six_channel_policy.json", {})
    roles = {row.get("key"): row for row in sns.get("roles", [])}
    for row in sns.get("accounts", []):
        platform = str(row.get("platform", ""))
        role = roles.get(row.get("role"), {})
        result.append({
            "key": f"{platform.lower()}:{row.get('role')}", "platform": platform,
            "name": row.get("display_name", row.get("role", "")), "identity": row.get("handle", ""),
            "publish_connected": bool(row.get("identity_verified") and row.get("publish_connected")),
            "release_policy": "public_after_write_auth", "cadence": "1_per_day",
            "topic_source": "config/sns_six_channel_policy.json",
            "topic_brief": role.get("topic", "Platform-native original content"),
        })

    tistory = read(ROOT / "config/tistory_portfolio.json", {})
    for row in tistory.get("sites", []):
        seeds = row.get("seed_topics", [])
        result.append({
            "key": f"tistory:{row['site_id']}", "platform": "Tistory",
            "name": row.get("title", row["site_id"]), "identity": row.get("url", ""),
            "publish_connected": False, "release_policy": "public_after_local_login_test",
            "cadence": "1_per_day", "topic_source": "config/tistory_portfolio.json",
            "topic_brief": seeds[0] if seeds else row.get("description", "Site-specific original search content"),
        })

    rooms = read(ROOT / "config/automation_rooms.json", {}).get("rooms", [])
    for row in rooms:
        if row.get("platform") != "naver":
            continue
        destination = str(row.get("destination_id", ""))
        result.append({
            "key": f"naver:{row['room_id']}", "platform": "Naver",
            "name": row.get("name", row["room_id"]), "identity": destination,
            "publish_connected": bool(row.get("enabled") and destination),
            "release_policy": "public_after_local_login_test", "cadence": "1_per_day",
            "topic_source": "account_specific_keyword_bank",
            "topic_brief": "Select one original account-specific search topic with duplicate protection.",
        })
    if len(result) != 32:
        raise RuntimeError(f"expected 32 daily non-YouTube targets, found {len(result)}")
    return result


def targets(day: date) -> list[dict]:
    return daily_non_youtube_targets() + youtube_targets(day)


def _safe_minute(value: int) -> int:
    value = max(WINDOW_START_MINUTE, min(WINDOW_END_MINUTE, value))
    if value % 5 == 0:
        value += 1 if value < WINDOW_END_MINUTE else -1
    return value


def build(day: date) -> dict:
    rows = targets(day)
    seed_text = f"london-daily|{day.isoformat()}|{os.environ.get('SCHEDULE_RANDOM_SALT', '')}"
    rng = random.Random(int(hashlib.sha256(seed_text.encode()).hexdigest(), 16))
    rng.shuffle(rows)
    span = WINDOW_END_MINUTE - WINDOW_START_MINUTE
    interval = span / max(1, len(rows) - 1)
    slots = []
    for index, row in enumerate(rows):
        minute = _safe_minute(round(WINDOW_START_MINUTE + index * interval + rng.randint(-3, 3)))
        at = datetime.combine(day, datetime.min.time(), tzinfo=KST) + timedelta(minutes=minute)
        slots.append({**row, "scheduled_at": at.isoformat(),
                      "status": "ready" if row["publish_connected"] else "blocked_auth",
                      "duplicate_key": f"{day.isoformat()}|{row['key']}"})
    slots.sort(key=lambda row: row["scheduled_at"])
    minutes = [datetime.fromisoformat(x["scheduled_at"]).hour * 60 + datetime.fromisoformat(x["scheduled_at"]).minute for x in slots]
    gaps = [b - a for a, b in zip(minutes, minutes[1:])]
    youtube_due = sum(row["platform"] == "YouTube" for row in slots)
    return {
        "version": 2, "task_id": f"london-{day.isoformat()}-owner-cadence",
        "date": day.isoformat(), "timezone": "Asia/Seoul",
        "target_count": len(slots), "daily_non_youtube_count": 32,
        "youtube_due_count": youtube_due,
        "policy": "non_youtube_one_daily; locked_youtube10_two_or_three_weekly_private_only; dispatch_after_write_auth",
        "generated_at": datetime.now(KST).isoformat(),
        "minimum_gap_minutes": min(gaps) if gaps else 0,
        "maximum_gap_minutes": max(gaps) if gaps else 0, "slots": slots,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(KST).date().isoformat())
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    day = date.fromisoformat(args.date)
    payload = build(day)
    target = Path(args.output) if args.output else ROOT / "data/daily-channel-schedule" / f"{day.isoformat()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, target)
    print(json.dumps({
        "output": str(target), "targets": payload["target_count"],
        "daily_non_youtube": payload["daily_non_youtube_count"],
        "youtube_due": payload["youtube_due_count"],
        "ready": sum(s["status"] == "ready" for s in payload["slots"]),
        "blocked_auth": sum(s["status"] == "blocked_auth" for s in payload["slots"]),
        "min_gap": payload["minimum_gap_minutes"], "max_gap": payload["maximum_gap_minutes"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
