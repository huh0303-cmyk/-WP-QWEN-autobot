"""Calendar-day publishing totals and honest cost coverage at the report cutoff."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
KST = timezone(timedelta(hours=9))


def publication_counts(posts, stamp, date_key):
    end = datetime.fromisoformat(stamp).astimezone(KST)
    start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    previous_start, previous_end = start-timedelta(days=1), end-timedelta(days=1)
    current = previous = 0
    seen = set()
    try:
        for post in posts:
            identity = post.get("url") or post.get("link")
            if not identity or identity in seen:
                raise ValueError("Missing or duplicate publication identity")
            seen.add(identity)
            raw = post[date_key]
            if date_key == "date_gmt" and not raw.endswith("Z"):
                raw += "+00:00"
            at = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(KST)
            current += start <= at <= end
            previous += previous_start <= at <= previous_end
    except (KeyError, TypeError, ValueError, AttributeError):
        return {"published_today":None, "published_previous_same_time":None}
    return {"published_today":current, "published_previous_same_time":previous}


def header_summary(records, stamp, budget):
    valid = [r for r in records if r.get("published_today") is not None and r.get("published_previous_same_time") is not None]
    complete = bool(records) and len(valid) == len(records)
    count = sum(r["published_today"] for r in valid)
    previous = sum(r["published_previous_same_time"] for r in valid)
    end = datetime.fromisoformat(stamp).astimezone(KST)
    start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    estimate = Decimal(0)
    entries = 0
    for call in budget.get("calls", []):
        try:
            at = datetime.fromisoformat(call["at"]).astimezone(KST)
            amount = Decimal(str(call["amount_usd"]))
            if start <= at <= end and amount.is_finite() and amount >= 0:
                estimate += amount
                entries += 1
        except (KeyError, ValueError, TypeError, InvalidOperation):
            continue
    return {"published_today":count if complete else None,
            "published_delta":count-previous if complete else None,
            "confirmed_published_today":count, "covered_sites":len(valid), "expected_sites":len(records),
            "scope":"WP 25 · Blogspot 33 · 뉴스룸 2 · 현재 공개 글의 발행일 기준",
            "period":"KST 당일 00:00부터 표시된 기준 시각까지 · 전날 같은 시간대와 비교",
            "api_cost_total":None, "api_cost_delta":None, "api_cost_currency":"USD",
            "recorded_estimate_usd":float(estimate) if entries else None,
            "api_cost_note":"실제 청구 총액 미연동 · 원장에는 일부 경로의 사전 추정 예약금액만 기록됨"}
