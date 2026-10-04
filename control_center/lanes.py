"""Independent publication lanes.

Until 2026-10-04 every platform (WordPress, news, Blogspot, Tistory) shared ONE
SQLite job table and ONE polling worker.  A stuck job, a slow GitHub call or a
lock on that single file froze every platform at once.  Each lane below owns its
own database file, its own worker thread and its own health record, so one lane
failing cannot block another.

Lanes:
    wordpress  - the 25 regular WordPress sites and the 2 newsrooms
    blogspot   - the 33 Blogspot blogs
    youtube    - YouTube channels
    sns        - Instagram / Facebook / other social accounts
    tistory    - kept separate from the two blog lanes so it can never couple them
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from .operations import Store, Worker

LANES = ("wordpress", "blogspot", "youtube", "sns", "tistory")

# Lane worker pool size. WordPress and Blogspot carry the volume; the rest are
# low-traffic, so they poll with fewer threads.
POOL_SIZE = {"wordpress": 4, "blogspot": 4, "youtube": 2, "sns": 2, "tistory": 2}

PLATFORM_LANE = {
    "wordpress": "wordpress", "news": "wordpress",
    "blogger": "blogspot", "blogspot": "blogspot",
    "youtube": "youtube",
    "sns": "sns", "instagram": "sns", "facebook": "sns", "threads": "sns",
    "tistory": "tistory",
}

MIGRATION_KEY = "lanes_migrated_v1"


def lane_for_group(group: str) -> str:
    """Map a control-room request group to the lane that owns it."""
    group = str(group or "")
    if group in {"wp25", "news2"} or group.startswith("wp_"):
        return "wordpress"
    if group == "blogspot33" or group.startswith("blogspot_"):
        return "blogspot"
    if group.startswith("youtube"):
        return "youtube"
    if group.startswith("sns"):
        return "sns"
    return "tistory"


def lane_for_platform(platform: str, group: str = "") -> str:
    return PLATFORM_LANE.get(str(platform or "").lower()) or lane_for_group(group)


def lane_db_path(core_path: str | os.PathLike, lane: str) -> Path:
    """control-operations.sqlite3 -> control-operations-<lane>.sqlite3 (same folder)."""
    core = Path(core_path)
    return core.with_name(f"{core.stem}-{lane}{core.suffix}")


class Lane:
    def __init__(self, name: str, store: Store, worker: Worker):
        self.name, self.store, self.worker = name, store, worker

    def health(self) -> dict:
        data = self.store.summary()
        data["worker"] = self.worker.health()
        data["lane"] = self.name
        return data


def build_lanes(core_path: str | os.PathLike, gateway) -> dict[str, Lane]:
    lanes = {}
    for name in LANES:
        store = Store(lane_db_path(core_path, name))
        worker = Worker(store, gateway, name=f"receipts-{name}", pool_size=POOL_SIZE[name])
        lanes[name] = Lane(name, store, worker)
    return lanes


def migrate_legacy(core_store: Store, lanes: dict[str, Lane]) -> dict[str, int]:
    """Copy jobs from the old shared database into their lane databases, once.

    The legacy file is never modified except for a marker row, so a rollback to
    the previous release still finds every job exactly where it was.  After the
    marker is set the legacy table is no longer polled.
    """
    counts = {name: 0 for name in lanes}
    with core_store.connect() as core:
        done = core.execute("SELECT 1 FROM settings WHERE key=?", (MIGRATION_KEY,)).fetchone()
        if done:
            return counts
        jobs = core.execute("SELECT * FROM jobs ORDER BY created").fetchall()
        requests_rows = core.execute("SELECT id, group_id FROM requests").fetchall()
        events = {}
        for row in core.execute("SELECT id, job_id, at, phase, detail FROM events ORDER BY id"):
            events.setdefault(row["job_id"], []).append(row)
    for row in requests_rows:
        lane = lanes.get(lane_for_group(row["group_id"]))
        if lane:
            with lane.store.connect() as db:
                db.execute("INSERT OR IGNORE INTO requests VALUES (?, ?)", (row["id"], row["group_id"]))
    for row in jobs:
        try:
            platform = json.loads(row["payload"]).get("platform", "")
        except ValueError:
            platform = ""
        lane = lanes.get(lane_for_platform(platform, row["group_id"]))
        if not lane:
            continue
        with lane.store.connect() as db:
            # Several gunicorn workers start together and each runs this copy.
            # INSERT OR IGNORE + rowcount keeps it race-safe: only the process
            # that actually inserts the job also writes its events.
            inserted = db.execute(
                "INSERT OR IGNORE INTO jobs (id, request_id, site_id, group_id, phase, payload, created, updated, lease, next_poll) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (row["id"], row["request_id"], row["site_id"], row["group_id"], row["phase"], row["payload"],
                 row["created"], row["updated"], 0, row["next_poll"])).rowcount
            if not inserted:
                continue
            for event in events.get(row["id"], []):
                db.execute("INSERT INTO events(job_id,at,phase,detail) VALUES (?,?,?,?)",
                           (event["job_id"], event["at"], event["phase"], event["detail"]))
        counts[lane.name] += 1
    with core_store.connect() as core:
        core.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (MIGRATION_KEY, str(time.time())))
    return counts
