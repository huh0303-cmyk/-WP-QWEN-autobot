"""Immutable 07:00 Asia/Seoul baselines; never manufacture missing comparisons."""
from datetime import datetime, timedelta, timezone
KST = timezone(timedelta(hours=9))
VERSION = "kst0700-v1"


def classify(stamp, baseline_date=""):
    actual = datetime.fromisoformat(stamp)
    if not baseline_date:
        return {"report_kind":"manual", "policy_version":VERSION}
    target = datetime.fromisoformat(baseline_date + "T07:00:00+09:00")
    lag = (actual - target).total_seconds()
    return {"report_kind":"daily_0700" if 0 <= lag <= 600 else "late_manual",
            "policy_version":VERSION, "scheduled_for":target.isoformat(), "start_delay_seconds":lag}


def prior_rows(history, stamp):
    day = (datetime.fromisoformat(stamp).date() - timedelta(days=1)).isoformat()
    previous = history.get("days", {}).get(day, {})
    if previous.get("report_kind") != "daily_0700" or previous.get("policy_version") != VERSION:
        return {}
    return {r["url"]: r for r in previous.get("records", [])}


def apply_comparisons(report, history):
    previous = prior_rows(history, report["generated_at"])
    official = report.get("report_kind") == "daily_0700"
    for row in report["records"]:
        old = previous.get(row["url"], {}) if official else {}
        def diff(key):
            a, b = row.get(key), old.get(key)
            return a - b if a is not None and b is not None else None
        increase = diff("total_visitors")
        if increase is not None and increase < 0:
            row.setdefault("errors", []).append("누적 조회수 감소·초기화 확인 필요 · 24시간 방문 수 계산 제외")
            increase = None
        row["today_visitors"] = increase
        row["total_delta"] = increase
        row["today_delta"] = increase - old["today_visitors"] if increase is not None and old.get("today_visitors") is not None else None
        row["posts_delta"] = diff("total_posts")
        row["indexed_delta"] = None if row.get("index_partial") or old.get("index_partial") else diff("indexed")
        row["comparison_at"] = old.get("snapshot_at")
        row["snapshot_at"] = report.get("scheduled_for") if official else None
        if not old:
            row.setdefault("errors", []).append("전날 07:00 고정 기준값 없음 · 증감 계산 대기")
    return report


def freeze(history, report):
    if report.get("report_kind") != "daily_0700":
        return False
    day = report["generated_at"][:10]
    days = history.setdefault("days", {})
    if day in days:
        return False
    days[day] = report
    return True
