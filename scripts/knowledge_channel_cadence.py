"""Stable random weekly cadence for archival YouTube channels (KST)."""
import datetime as dt
import hashlib
import random

KST = dt.timezone(dt.timedelta(hours=9))
WEEKLY = ('nasa', 'invention', 'silent_era', 'retro_reels')
DAILY = ('history',)

def slots(channel, day):
    if channel not in WEEKLY + DAILY:
        raise ValueError('Unknown channel')
    monday = day - dt.timedelta(days=day.weekday())
    seed = int.from_bytes(hashlib.sha256(f'{channel}:{monday.isoformat()}'.encode()).digest()[:8], 'big')
    rng = random.Random(seed)
    days = range(7) if channel in DAILY else sorted(rng.sample(range(7), 3))
    return [dt.datetime.combine(monday + dt.timedelta(days=d), dt.time(rng.randrange(10, 22), rng.randrange(60)), KST) for d in days]

def due_channels(now):
    local = now.astimezone(KST)
    return [c for c in DAILY + WEEKLY if any(s.date() == local.date() and s.hour == local.hour for s in slots(c, local.date()))]

if __name__ == '__main__':
    import json
    now = dt.datetime.now(KST)
    print(json.dumps({'now_kst': now.isoformat(), 'due': due_channels(now), 'slots': {c: [s.isoformat() for s in slots(c, now.date())] for c in DAILY + WEEKLY}}))
