"""2026-09-12: a burst of RSS items for one newsroom used to dispatch every
one of them back-to-back, which pushed koreanews365.com's Hostinger host
past its rate limiter (403 on the WP REST reads process_one() needs) and,
with no fresh WP article to pair with, left the Blogger companion rewriting
one stale pre-outage post into repeated near-duplicate articles. These
tests cover the fix: at most one dispatch per newsroom per cooldown window."""
import json
import time
from unittest.mock import patch

from control_center.operations import Store
from control_center.rss_watch import MIN_DISPATCH_GAP_SECONDS, RSSWatcher


def _make_watcher(tmp_path):
    store = Store(tmp_path / "ops.sqlite3")
    config_path = tmp_path / "rss_watch.json"
    config_path.write_text(json.dumps({
        "poll_seconds": 60,
        "sources": [{"key": "koreanews365", "name": "Test Feed", "language": "ko", "feed": "https://example.com/rss"}],
    }), encoding="utf-8")
    target = {"site_id": "koreanews365", "site_group": "wp_koreanews365", "site_url": "https://koreanews365.com",
              "label": "koreanews365.com", "platform": "news", "workflow": "newsrooms-daily-publisher.yml", "inputs": {}}
    return store, RSSWatcher(store, config_path, lambda: [target])


def _insert_waiting_item(store, item_id, title="Story"):
    now = time.time()
    with store.connect() as db:
        db.execute("INSERT INTO rss_items VALUES (?,?,?,?,?,?,?,?)",
                   (item_id, "koreanews365", "koreanews365", f"https://a.example/{item_id}", title, now, now, "waiting"))
        db.execute("INSERT INTO rss_item_evidence VALUES (?,?)",
                   (item_id, json.dumps({"title": title, "url": f"https://a.example/{item_id}"})))


def _item_state(store, item_id):
    with store.connect() as db:
        return db.execute("SELECT state FROM rss_items WHERE id=?", (item_id,)).fetchone()[0]


def test_dispatch_within_cooldown_is_deferred_not_dropped(tmp_path):
    store, watcher = _make_watcher(tmp_path)
    _insert_waiting_item(store, "item-1")
    with store.connect() as db:
        db.execute("INSERT INTO settings VALUES ('rss_last_dispatch_koreanews365', ?)", (str(time.time()),))

    with patch("control_center.rss_watch.requests.get", side_effect=Exception("no network in test")):
        watcher.scan()

    assert _item_state(store, "item-1") == "waiting"


def test_dispatch_proceeds_once_cooldown_has_elapsed(tmp_path):
    store, watcher = _make_watcher(tmp_path)
    _insert_waiting_item(store, "item-1")
    with store.connect() as db:
        db.execute("INSERT INTO settings VALUES ('rss_last_dispatch_koreanews365', ?)",
                   (str(time.time() - MIN_DISPATCH_GAP_SECONDS - 1),))

    with patch("control_center.rss_watch.requests.get", side_effect=Exception("no network in test")):
        watcher.scan()

    assert _item_state(store, "item-1") == "accepted"


def test_a_burst_of_items_for_one_newsroom_dispatches_only_the_first(tmp_path):
    store, watcher = _make_watcher(tmp_path)
    _insert_waiting_item(store, "item-1", "Breaking story one")
    _insert_waiting_item(store, "item-2", "Breaking story two")

    with patch("control_center.rss_watch.requests.get", side_effect=Exception("no network in test")):
        watcher.scan()

    states = {_item_state(store, "item-1"), _item_state(store, "item-2")}
    assert states == {"accepted", "waiting"}
