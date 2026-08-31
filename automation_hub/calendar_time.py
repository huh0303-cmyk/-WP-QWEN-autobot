"""The Sheet has minute-resolution slots. Missed slots are PASS, never catch-up."""


def is_current_slot(planned, now):
    if planned.tzinfo is None or now.tzinfo is None:
        raise ValueError("Calendar time must be timezone-aware")
    return planned.replace(second=0, microsecond=0) == now.astimezone(planned.tzinfo).replace(second=0, microsecond=0)
