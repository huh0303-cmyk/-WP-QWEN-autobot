"""One randomized daily Tistory slot per site in Korea time."""
import hashlib
import random
from datetime import date

# One dispatch window only. Legacy manual callers using am/pm are normalized
# to this same daily slot so they cannot accidentally create two daily posts.
WINDOWS = {'daily': (8*60 + 10, 22*60 + 51)}

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
