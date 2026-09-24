#!/usr/bin/env python3
"""Create 33 randomized, one-site Blogger publication timers for a KST day."""

from __future__ import annotations

import json
import random
import subprocess
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path("/opt/korea365")
KST = ZoneInfo("Asia/Seoul")


def site_keys() -> list[str]:
    data = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
    keys = [p["site_key"] for p in data["profiles"] if p["blogspot"].get("ready_for_automation")]
    if len(keys) != 33 or len(set(keys)) != 33:
        raise RuntimeError("scope guard: exactly 33 unique Blogger sites are required")
    return keys


def build_slots(now: datetime, count: int) -> list[datetime]:
    day = now.date()
    normal_start = datetime.combine(day, time(6, 10), KST)
    normal_end = datetime.combine(day, time(23, 20), KST)
    if now < normal_start:
        start, end = normal_start, normal_end
    else:
        start = now + timedelta(minutes=2)
        end = datetime.combine(day, time(23, 59), KST)
        if start >= end:
            start = now + timedelta(minutes=1)
            end = start + timedelta(minutes=max(count, 60))

    span = (end - start).total_seconds()
    rng = random.Random(f"korea365-blogger33:{day.isoformat()}")
    slots: list[datetime] = []
    for index in range(count):
        center = span * (index + 0.5) / count
        jitter = rng.uniform(-0.32, 0.32) * (span / count)
        slots.append(start + timedelta(seconds=max(0, min(span, center + jitter))))
    return sorted(slots)


def main() -> int:
    now = datetime.now(KST)
    run_date = now.date().isoformat()
    keys = site_keys()
    rng = random.Random(f"korea365-blogger33-order:{run_date}")
    rng.shuffle(keys)
    slots = build_slots(now, len(keys))
    plan = []

    for index, (key, slot) in enumerate(zip(keys, slots), start=1):
        unit = f"korea365-blogger33-{run_date.replace('-', '')}-{index:02d}"
        utc_slot = slot.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        command = [
            "systemd-run", "--quiet", "--collect", f"--unit={unit}",
            f"--on-calendar={utc_slot}", "--timer-property=AccuracySec=1s",
            f"--setenv=BLOGGER_SITE_KEY={key}", f"--setenv=BLOGGER_RUN_DATE={run_date}",
            "/opt/korea365/.venv/bin/python", "/opt/korea365/scripts/run_blogger33_daily_vps.py",
        ]
        completed = subprocess.run(command, check=False, text=True, capture_output=True)
        status = "scheduled" if completed.returncode == 0 else "existing_or_failed"
        plan.append({"site": key, "kst": slot.isoformat(), "unit": unit, "status": status,
                     "detail": (completed.stderr or completed.stdout).strip()[:300]})

    out_dir = ROOT / "data" / "blogger33-schedules"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_date}.json").write_text(
        json.dumps({"run_date": run_date, "created_at": now.isoformat(), "items": plan},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    scheduled = sum(item["status"] == "scheduled" for item in plan)
    print(json.dumps({"run_date": run_date, "scheduled": scheduled, "total": len(plan)}, ensure_ascii=False))
    return 0 if scheduled == 33 else 1


if __name__ == "__main__":
    raise SystemExit(main())
