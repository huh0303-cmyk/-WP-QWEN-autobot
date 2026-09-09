import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("core_metrics", Path(__file__).resolve().parents[1] / "scripts/core_metrics_report.py")
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def test_old_snapshot_is_not_yesterday():
    history = {"days": {"2026-09-02": {"records": [{"url": "https://example.com", "total_posts": 10}]}}}
    assert metrics.previous_day(history, "2026-09-09") == {}


def test_zero_is_evidence_but_missing_is_not_zero():
    assert metrics.delta(0, 5) == -5
    assert metrics.delta(0, None) is None
    assert metrics.format_metric({"count": 0, "change": 0}, "count", "change") == "0 (+0)"
    assert metrics.format_metric({}, "count", "change") == "미확인"


def test_exact_previous_day_is_used():
    row = {"url": "https://example.com", "total_posts": 10}
    assert metrics.previous_day({"days": {"2026-09-08": {"records": [row]}}}, "2026-09-09") == {row["url"]: row}
