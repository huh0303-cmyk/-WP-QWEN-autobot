"""Bounded polling window for minute-resolution Sheet calendar slots."""

import datetime as dt


def is_current_slot(planned, now, window_minutes=30):
    if planned.tzinfo is None or now.tzinfo is None:
        raise ValueError("Calendar time must be timezone-aware")
    if not 1 <= window_minutes <= 60:
        raise ValueError("window_minutes must be between 1 and 60")
    planned_minute = planned.replace(second=0, microsecond=0)
    now_minute = now.astimezone(planned.tzinfo).replace(second=0, microsecond=0)
    delta = now_minute - planned_minute
    return dt.timedelta(0) <= delta < dt.timedelta(minutes=window_minutes)
