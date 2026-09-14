from __future__ import annotations

from datetime import datetime, timedelta, timezone


KST = timezone(timedelta(hours=9), name="KST")


def now_kst() -> datetime:
    return datetime.now(KST)


def iso_kst(value: datetime | None = None) -> str:
    return (value or now_kst()).astimezone(KST).isoformat(timespec="seconds")


def display_kst(value: datetime) -> str:
    return value.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
