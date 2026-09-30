"""Randomized Tistory scheduling helpers in Korea time."""
import hashlib
import random

# One dispatch window only. Legacy manual callers using am/pm are normalized
# to this same daily slot so they cannot accidentally create two daily posts.
WINDOWS = {'daily': (8*60 + 10, 22*60 + 51)}
NETWORK_DAILY_POSTS = 3
MINIMUM_NETWORK_GAP_MINUTES = 90

def _slot_name(slot):
    return 'daily' if slot in {'am', 'pm', '', None} else slot

def slot_minute(site_id, day, slot='daily'):
    slot = _slot_name(slot)
    start, end = WINDOWS[slot]
    minutes = [m for m in range(start, end) if m % 5 != 0]
    seed = int(hashlib.sha256(f'{site_id}:{day}:one-daily'.encode()).hexdigest(), 16)
    return random.Random(seed).choice(minutes)

def slot_time(site_id, day, slot='daily'):
    value = slot_minute(site_id, day, slot)
    return f'{value//60:02d}:{value%60:02d}'


def random_daily_selection(site_ids, count=NETWORK_DAILY_POSTS, rng=None):
    """Pick distinct sites and well-spaced non-round minutes once per day.

    Production callers persist the returned selection before dispatching any
    work, so retries reuse the same random choice instead of creating extras.
    ``rng`` is injectable only to make the safety properties testable.
    """
    candidates = list(dict.fromkeys(site_ids))
    if count < 1 or count > len(candidates):
        raise ValueError("count must be between 1 and the number of eligible sites")
    rng = rng or random.SystemRandom()
    selected = rng.sample(candidates, count)
    start, end = WINDOWS['daily']
    minutes = [minute for minute in range(start, end) if minute % 5 != 0]
    for _ in range(500):
        chosen = sorted(rng.sample(minutes, count))
        if all(b - a >= MINIMUM_NETWORK_GAP_MINUTES for a, b in zip(chosen, chosen[1:])):
            rng.shuffle(selected)
            return [
                {
                    'site_id': site_id,
                    'scheduled_minute_kst': minute,
                    'scheduled_local_time': f'{minute // 60:02d}:{minute % 60:02d}',
                }
                for site_id, minute in zip(selected, chosen)
            ]
    raise RuntimeError("could not create three separated Tistory slots")
