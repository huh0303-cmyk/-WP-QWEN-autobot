#!/usr/bin/env python3
"""Truth-preserving measurement rules for the executive control Sheet.

Missing billing/analytics connections are represented as ``연결 필요``. They are
never coerced to zero, because that would make net profit look better than it is.
"""

CONNECTED = "연결됨"
NEEDS_CONNECTION = "연결 필요"


def source_row(name, values=None, error=""):
    values = values or {}
    complete = all(values.get(period) is not None for period in ("today", "seven_days", "month"))
    return {
        "name": name,
        "today": values.get("today"),
        "seven_days": values.get("seven_days"),
        "month": values.get("month"),
        "status": CONNECTED if complete else NEEDS_CONNECTION,
        "error": error or ("" if complete else "공식 API/청구 export 연결 필요"),
    }


def guarded_sum(rows, period):
    """Return a sum only when every required source has a real value."""
    if not rows or any(row.get("status") != CONNECTED or row.get(period) is None for row in rows):
        return None
    return sum(row[period] for row in rows)


def net_profit(revenue_rows, cost_rows, period):
    revenue = guarded_sum(revenue_rows, period)
    cost = guarded_sum(cost_rows, period)
    return None if revenue is None or cost is None else revenue - cost
