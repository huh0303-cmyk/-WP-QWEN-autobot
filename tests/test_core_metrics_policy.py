import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from core_metrics_policy import classify, apply_comparisons, freeze, VERSION


def report(day, total, visits=None, **extras):
    return {"generated_at":f"2026-09-{day:02}T07:00:30+09:00", **classify(f"2026-09-{day:02}T07:00:30+09:00", f"2026-09-{day:02}"),
            "records":[{"url":"https://site", "total_visitors":total, "today_visitors":visits, "total_posts":12, "indexed":4, **extras}]}


def test_only_fixed_window_is_a_daily_baseline():
    assert classify("2026-09-12T07:00:01+09:00", "2026-09-12")["report_kind"] == "daily_0700"
    assert classify("2026-09-12T08:00:00+09:00", "2026-09-12")["report_kind"] == "late_manual"
    assert classify("2026-09-12T06:59:00+09:00", "2026-09-12")["report_kind"] == "late_manual"
    assert classify("2026-09-12T07:00:00+09:00")["report_kind"] == "manual"


def test_24_hour_counts_and_changes_share_the_same_baseline():
    history={"days":{"2026-09-12":report(12,100,20)}}
    row=apply_comparisons(report(13,135),history)["records"][0]
    assert row["today_visitors"] == 35 and row["total_delta"] == 35
    assert row["today_delta"] == 15 and row["posts_delta"] == 0 and row["indexed_delta"] == 0


def test_manual_missing_or_wrong_policy_data_never_becomes_comparison():
    old=report(12,100,20); old["report_kind"]="manual"
    row=apply_comparisons(report(13,135),{"days":{"2026-09-12":old}})["records"][0]
    assert all(row[k] is None for k in ["today_visitors","today_delta","total_delta","posts_delta","indexed_delta"])
    current=report(13,135); current["report_kind"]="manual"
    assert not freeze({},current)


def test_counter_reset_and_partial_index_do_not_invent_counts():
    row=apply_comparisons(report(13,90,index_partial=True,indexed=None),{"days":{"2026-09-12":report(12,100,20)}})["records"][0]
    assert row["today_visitors"] is None and row["today_delta"] is None and row["indexed_delta"] is None


def test_daily_baseline_cannot_be_overwritten():
    history={}
    assert freeze(history,report(12,100))
    assert not freeze(history,report(12,999))
    assert history["days"]["2026-09-12"]["records"][0]["total_visitors"] == 100
