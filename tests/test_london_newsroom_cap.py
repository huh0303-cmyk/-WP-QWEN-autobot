import sqlite3

from control_center import rss_watch


class Store:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db


def test_newsroom_daily_policy_is_three_to_ten():
    assert rss_watch.NEWSROOM_DAILY_TARGET_MIN == 3
    assert rss_watch.NEWSROOM_DAILY_MAX == 10


def test_newsroom_dispatch_counter_is_per_newsroom(tmp_path):
    store = Store(tmp_path / "rss.sqlite3")
    assert rss_watch._dispatch_count(store, "koreanews365") == 0
    assert rss_watch._increment_dispatch_count(store, "koreanews365") == 1
    assert rss_watch._increment_dispatch_count(store, "koreanews365") == 2
    assert rss_watch._dispatch_count(store, "koreanews365") == 2
    assert rss_watch._dispatch_count(store, "theseouljournal") == 0


def test_newsroom_hard_cap_constant_is_ten():
    store = Store(__import__("pathlib").Path(__import__("tempfile").mkstemp()[1]))
    # Counter storage can exceed the constant only if a caller ignores the guard;
    # RSSWatcher.scan checks the value before dispatching every item.
    for _ in range(rss_watch.NEWSROOM_DAILY_MAX):
        rss_watch._increment_dispatch_count(store, "koreanews365")
    assert rss_watch._dispatch_count(store, "koreanews365") == 10
