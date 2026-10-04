import json
import time
from unittest.mock import Mock

import pytest

from control_center.lanes import (LANES, MIGRATION_KEY, build_lanes, lane_db_path, lane_for_group,
                                  lane_for_platform, migrate_legacy)
from control_center.operations import Conflict, Store, Worker


def target(site="site_one", platform="wordpress"):
    return dict(site_id=site, site_group="g_" + site, label=site, platform=platform,
                site_url="https://example.com", workflow="writer.yml", inputs={})


@pytest.fixture
def core(tmp_path):
    return Store(tmp_path / "control-operations.sqlite3")


@pytest.fixture
def lanes(core, tmp_path):
    return build_lanes(tmp_path / "control-operations.sqlite3", Mock())


@pytest.mark.parametrize("group,lane", [
    ("wp25", "wordpress"), ("news2", "wordpress"), ("wp_koreataxnlaw", "wordpress"),
    ("blogspot33", "blogspot"), ("blogspot_k_health", "blogspot"),
    ("youtube_kpop", "youtube"), ("sns_instagram", "sns"),
    ("tistory5", "tistory"), ("tistory_one", "tistory"),
])
def test_group_maps_to_its_own_lane(group, lane):
    assert lane_for_group(group) == lane


def test_platform_mapping_matches_the_four_requested_lanes():
    assert lane_for_platform("wordpress") == "wordpress"
    assert lane_for_platform("news") == "wordpress"
    assert lane_for_platform("blogger") == "blogspot"
    assert lane_for_platform("youtube") == "youtube"
    assert lane_for_platform("instagram") == "sns"
    assert lane_for_platform("", "blogspot33") == "blogspot"


def test_every_lane_has_its_own_database_and_worker(lanes, tmp_path):
    assert set(lanes) == set(LANES)
    paths = {lane.store.path for lane in lanes.values()}
    assert len(paths) == len(LANES)
    assert all(lane_db_path(tmp_path / "control-operations.sqlite3", n).exists() for n in LANES)
    assert len({id(lane.worker) for lane in lanes.values()}) == len(LANES)
    assert len({lane.worker.name for lane in lanes.values()}) == len(LANES)


def test_job_in_one_lane_never_blocks_or_appears_in_another(lanes):
    lanes["wordpress"].store.submit("wp25", [target("shared_id")], "request-wordpress-0001")
    # Same site id in another lane is a different pipeline - it must not conflict.
    lanes["blogspot"].store.submit("blogspot33", [target("shared_id", "blogger")], "request-blogspot-00001")
    assert len(lanes["wordpress"].store.snapshot()) == 1
    assert len(lanes["blogspot"].store.snapshot()) == 1
    assert lanes["youtube"].store.snapshot() == [] and lanes["sns"].store.snapshot() == []
    with pytest.raises(Conflict):  # ...but inside one lane the guard still works
        lanes["wordpress"].store.submit("wp_shared_id", [target("shared_id")], "request-wordpress-0002")


def test_a_stuck_lane_does_not_stop_the_others(lanes):
    lanes["wordpress"].store.submit("wp25", [target("a")], "request-wordpress-0001")
    lanes["blogspot"].store.submit("blogspot33", [target("b", "blogger")], "request-blogspot-00001")
    stuck = lanes["wordpress"].store.claim()
    assert stuck and stuck["site_id"] == "a"
    # WordPress lane is mid-dispatch/leased; Blogspot lane still hands out its own work.
    assert lanes["wordpress"].store.claim() is None
    assert lanes["blogspot"].store.claim()["site_id"] == "b"


def test_a_failing_gateway_in_one_lane_is_recorded_not_propagated(core, tmp_path):
    bad = Mock()
    bad.dispatch.side_effect = RuntimeError("boom")
    good = Mock()
    lanes = build_lanes(tmp_path / "control-operations.sqlite3", good)
    lanes["youtube"].worker.gateway = bad
    lanes["youtube"].store.submit("youtube_kpop", [target("kpop", "youtube")], "request-youtube-00001")
    lanes["sns"].store.submit("sns_instagram", [target("ig", "sns")], "request-sns-0000000001")
    lanes["youtube"].worker.tick()
    lanes["sns"].worker.tick()
    good.dispatch.assert_called_once()
    assert lanes["youtube"].store.snapshot()[0]["connection_warning"]  # failure recorded on its own job
    assert "connection_warning" not in lanes["sns"].store.snapshot()[0]  # SNS lane unaffected


def test_worker_health_reports_errors_by_type_only(core):
    worker = Worker(core, Mock(), name="receipts-test", pool_size=1)
    worker.record_error(ValueError("secret-token-123"))  # the message must never be stored
    health = worker.health()
    assert health["last_error"] == "ValueError" and health["error_count"] == 1 and "secret" not in json.dumps(health)


def test_summary_counts_active_attention_and_last_publish(lanes):
    store = lanes["blogspot"].store
    store.submit("blogspot33", [target("x", "blogger"), target("y", "blogger")], "request-blogspot-00001")
    summary = store.summary()
    assert summary["active"] == 2 and summary["attention"] == 0 and summary["last_published_at"] is None


def legacy_job(core, job_id, group, platform, phase="published", event=True):
    now = time.time()
    payload = dict(target(job_id, platform), id=job_id, request_id="r-" + job_id, group=group, phase=phase, detail="x")
    with core.connect() as db:
        db.execute("INSERT OR IGNORE INTO requests VALUES (?, ?)", ("r-" + job_id, group))
        db.execute("INSERT INTO jobs (id, request_id, site_id, group_id, phase, payload, created, updated) VALUES (?,?,?,?,?,?,?,?)",
                   (job_id, "r-" + job_id, job_id, group, phase, json.dumps(payload), now, now))
        if event:
            db.execute("INSERT INTO events(job_id,at,phase,detail) VALUES (?,?,?,?)", (job_id, now, phase, "legacy event"))


def test_legacy_jobs_move_to_the_right_lane_once_and_legacy_is_untouched(core, lanes):
    legacy_job(core, "wp1", "wp25", "wordpress")
    legacy_job(core, "news1", "news2", "news", phase="queued")
    legacy_job(core, "bl1", "blogspot33", "blogger", phase="attention")
    legacy_job(core, "yt1", "youtube_kpop", "youtube")
    legacy_job(core, "ti1", "tistory5", "tistory")
    counts = migrate_legacy(core, lanes)
    assert counts == {"wordpress": 2, "blogspot": 1, "youtube": 1, "sns": 0, "tistory": 1}
    assert {j["id"] for j in lanes["wordpress"].store.snapshot()} == {"wp1", "news1"}
    moved = lanes["blogspot"].store.snapshot()[0]
    assert moved["phase"] == "attention" and moved["history"][0]["detail"] == "legacy event"
    with core.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 5  # rollback-safe
        assert db.execute("SELECT 1 FROM settings WHERE key=?", (MIGRATION_KEY,)).fetchone()
    assert migrate_legacy(core, lanes) == {name: 0 for name in LANES}  # idempotent
    assert len(lanes["wordpress"].store.snapshot()) == 2


def test_migration_keeps_request_ids_so_double_click_protection_survives(core, lanes):
    legacy_job(core, "wp1", "wp25", "wordpress")
    migrate_legacy(core, lanes)
    request_id, skipped = lanes["wordpress"].store.submit("wp25", [target("wp1")], "r-wp1")
    assert request_id == "r-wp1" and skipped == []
    assert len(lanes["wordpress"].store.snapshot()) == 1
