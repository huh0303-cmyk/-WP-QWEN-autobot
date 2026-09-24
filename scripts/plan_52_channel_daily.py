#!/usr/bin/env python3
"""Create one evenly distributed daily slot for every London Project channel.

This planner never publishes. It produces the canonical 52-slot dispatch plan;
the executor may act only when a card has verified identity and write authority.
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
PRIVATE_READY_YOUTUBE_IDS = {
    "UCbJfEtsffpgI5MsKkB7BYvQ", "UC7yEsLM-HoXudngrD-4FIqg", "UC_e-sbLkVgwJNYEeobolNog",
    "UC7jOhyMa-FIrzZuea97z1Pw", "UCKZsfAWyCmY0jckf4IWZrqw", "UCtNLZO07Oh3UnXPI2CjOgNg",
    "UCVBvZwodUF4s57KeNicxQ3w", "UCgNj-yS93A_fOHXXvG49fww", "UCLvy6kSpC8-7o3hnSrfQ47g",
    "UCwh49EokdWFJqYFE_zA6XDQ",
}


def read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def targets() -> list[dict]:
    inventory = read(ROOT / "data/london-social-account-inventory-2026-09-24.json", {})
    result = []
    for row in inventory.get("youtube", []):
        cid = str(row.get("channel_id", ""))
        result.append({"key": f"youtube:{cid}", "platform": "YouTube", "name": row.get("name", cid),
                       "identity": cid, "publish_connected": cid in PRIVATE_READY_YOUTUBE_IDS,
                       "release_policy": "private_review_only"})

    sns = read(ROOT / "config/sns_six_channel_policy.json", {})
    for row in sns.get("accounts", []):
        platform = str(row.get("platform", ""))
        result.append({"key": f"{platform.lower()}:{row.get('role')}", "platform": platform,
                       "name": row.get("display_name", row.get("role", "")),
                       "identity": row.get("handle", ""),
                       "publish_connected": bool(row.get("identity_verified") and row.get("publish_connected")),
                       "release_policy": "public_after_write_auth"})

    tistory = read(ROOT / "config/tistory_portfolio.json", {})
    for row in tistory.get("sites", []):
        result.append({"key": f"tistory:{row['site_id']}", "platform": "Tistory",
                       "name": row.get("title", row["site_id"]), "identity": row.get("url", ""),
                       "publish_connected": False, "release_policy": "public_after_local_login_test"})

    rooms = read(ROOT / "config/automation_rooms.json", {}).get("rooms", [])
    for row in rooms:
        if row.get("platform") != "naver":
            continue
        result.append({"key": f"naver:{row['room_id']}", "platform": "Naver",
                       "name": row.get("name", row["room_id"]), "identity": row.get("destination_id", ""),
                       "publish_connected": bool(row.get("enabled") and row.get("destination_id")),
                       "release_policy": "public_after_local_login_test"})
    if len(result) != 52:
        raise RuntimeError(f"expected 52 targets, found {len(result)}")
    return result


def build(day: date) -> dict:
    rows = targets()
    seed_text = f"london-52|{day.isoformat()}|{os.environ.get('SCHEDULE_RANDOM_SALT', '')}"
    rng = random.Random(int(hashlib.sha256(seed_text.encode()).hexdigest(), 16))
    rng.shuffle(rows)
    interval = 1440 / len(rows)
    phase = rng.randint(0, int(interval) - 1)
    slots = []
    for index, row in enumerate(rows):
        # A small jitter keeps the clock times changing every day while the
        # 27.7-minute base interval prevents accounts from bunching together.
        minute = (phase + round(index * interval) + rng.randint(-3, 3)) % 1440
        at = datetime.combine(day, datetime.min.time(), tzinfo=KST) + timedelta(minutes=minute)
        slots.append({**row, "scheduled_at": at.isoformat(),
                      "status": "ready" if row["publish_connected"] else "blocked_auth",
                      "duplicate_key": f"{day.isoformat()}|{row['key']}"})
    slots.sort(key=lambda row: row["scheduled_at"])
    minutes = [datetime.fromisoformat(x["scheduled_at"]).hour * 60 + datetime.fromisoformat(x["scheduled_at"]).minute for x in slots]
    gaps = [b - a for a, b in zip(minutes, minutes[1:])] + [1440 - minutes[-1] + minutes[0]]
    return {"version": 1, "date": day.isoformat(), "timezone": "Asia/Seoul", "target_count": len(slots),
            "policy": "one_slot_per_account_per_day_evenly_distributed; dispatch_only_after_write_auth",
            "generated_at": datetime.now(KST).isoformat(), "minimum_gap_minutes": min(gaps),
            "maximum_gap_minutes": max(gaps), "slots": slots}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(KST).date().isoformat())
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    day = date.fromisoformat(args.date)
    payload = build(day)
    target = Path(args.output) if args.output else ROOT / "data/daily-52-schedule" / f"{day.isoformat()}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, target)
    print(json.dumps({"output": str(target), "targets": payload["target_count"],
                      "ready": sum(s["status"] == "ready" for s in payload["slots"]),
                      "blocked_auth": sum(s["status"] == "blocked_auth" for s in payload["slots"]),
                      "min_gap": payload["minimum_gap_minutes"], "max_gap": payload["maximum_gap_minutes"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
