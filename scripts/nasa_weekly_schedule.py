"""Deterministic, idempotent NASA three-times-weekly random KST slots."""
from __future__ import annotations
import datetime as dt
import hashlib
import random

KST = dt.timezone(dt.timedelta(hours=9))

def weekly_slots(day: dt.date) -> list[dt.datetime]:
    monday = day - dt.timedelta(days=day.weekday())
    seed = int.from_bytes(hashlib.sha256(f"NASA_XFILES:{monday.isoformat()}".encode()).digest()[:8], "big")
    rng = random.Random(seed)
    days = sorted(rng.sample(range(7), 3))
    return [dt.datetime.combine(monday + dt.timedelta(days=d), dt.time(rng.randrange(10, 23), rng.randrange(0, 60)), KST) for d in days]

def is_slot(now: dt.datetime) -> bool:
    local = now.astimezone(KST)
    return any(s.date() == local.date() and s.hour == local.hour for s in weekly_slots(local.date()))

if __name__ == "__main__":
    for slot in weekly_slots(dt.datetime.now(KST).date()):
        print(slot.isoformat())
