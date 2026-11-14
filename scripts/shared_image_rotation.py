"""Shared image rotation policy for all London Project publishing adapters.

Adapters must call reserve() before upload; a failed upload needs an explicit
reservation cleanup. Persist the same SQLite database across runners; a per-run temporary
file does NOT provide cross-platform duplicate protection.
"""
import hashlib
import random
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ENGINES = ('pexels', 'pixabay', 'sdxl_turbo', 'flux_schnell')
WINDOW_SECONDS = 14 * 86400


def randomized_engines(rng=None):
    order = list(ENGINES)
    (rng or random.SystemRandom()).shuffle(order)
    return order


def fingerprint(*, image_bytes=None, url=None, filename=None):
    """Use a content hash when available; otherwise canonical URL or filename."""
    if image_bytes is not None:
        return 'sha256:' + hashlib.sha256(image_bytes).hexdigest()
    if url:
        parts = urlsplit(url.strip())
        canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, '', ''))
        return 'url:' + hashlib.sha256(canonical.encode()).hexdigest()
    if filename:
        return 'file:' + hashlib.sha256(Path(filename).name.lower().encode()).hexdigest()
    raise ValueError('Image content, URL or filename is required')


class ImageRegistry:
    def __init__(self, database):
        self.database = str(database)
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE IF NOT EXISTS image_usage (fingerprint TEXT PRIMARY KEY, used_at INTEGER NOT NULL, platform TEXT NOT NULL, post_id TEXT NOT NULL, engine TEXT NOT NULL)')

    def reserve(self, key, platform, post_id, engine, now=None):
        if engine not in ENGINES:
            raise ValueError('Unknown image engine')
        now = int(time.time() if now is None else now)
        with sqlite3.connect(self.database, timeout=30, isolation_level='IMMEDIATE') as db:
            previous = db.execute('SELECT used_at FROM image_usage WHERE fingerprint=?', (key,)).fetchone()
            if previous and now - previous[0] < WINDOW_SECONDS:
                return False
            db.execute('INSERT OR REPLACE INTO image_usage VALUES (?,?,?,?,?)', (key, now, platform, post_id, engine))
            return True

