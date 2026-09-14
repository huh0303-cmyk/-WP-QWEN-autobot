"""Two distinct daily slots per site, in Korea time (no repeated adjacent day)."""
import hashlib
import random
from datetime import date

WINDOWS = {'am': (7*60, 11*60), 'pm': (13*60, 17*60)}

def slot_minute(site_id, day, slot):
    start, end = WINDOWS[slot]
    minutes = list(range(start, end))
    seed = int(hashlib.sha256(f'{site_id}:{slot}'.encode()).hexdigest(), 16)
    random.Random(seed).shuffle(minutes)
    return minutes[date.fromisoformat(day).toordinal() % len(minutes)]

def slot_time(site_id, day, slot):
    value = slot_minute(site_id, day, slot)
    return f'{value//60:02d}:{value%60:02d}'
