import json
from control_center.metrics_snapshot import best_snapshot


def snapshot(day):
    return {"generated_at": f"2026-09-{day:02}T08:00:00+09:00", "records": [{"url":"https://site", "today_visitors":None}]}


def test_outage_uses_last_success_instead_of_old_deployment_file(tmp_path):
    (tmp_path / "core_metrics_latest.json").write_text(json.dumps(snapshot(9)))
    assert best_snapshot(tmp_path, snapshot(11)) == snapshot(11)
    assert best_snapshot(tmp_path) == snapshot(11)
    assert best_snapshot(tmp_path, snapshot(10)) == snapshot(11)


def test_invalid_remote_cannot_replace_good_cache(tmp_path):
    best_snapshot(tmp_path, snapshot(11))
    assert best_snapshot(tmp_path, {"generated_at":"bad", "records":[]}) == snapshot(11)
    assert best_snapshot(tmp_path, []) == snapshot(11)


def test_missing_data_does_not_invent_zero(tmp_path):
    assert best_snapshot(tmp_path) == {}
    assert best_snapshot(tmp_path, snapshot(11))["records"][0]["today_visitors"] is None


def test_live_dashboard_prefers_newer_measurements_without_rewriting_daily(tmp_path):
    daily=dict(snapshot(11), report_kind="daily_0700")
    best_snapshot(tmp_path,daily)
    assert best_snapshot(tmp_path,snapshot(12)) == snapshot(12)
