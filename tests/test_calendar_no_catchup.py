import datetime as dt
import pytest
from automation_hub.calendar_time import is_current_slot
from automation_hub.youtube_calendar import select_due, READY


@pytest.mark.parametrize("offset,eligible", [(-1440, False), (-60, False), (-1, False), (0, True), (1, False)])
def test_missed_or_future_slots_never_dispatch(offset, eligible):
    now = dt.datetime(2026, 8, 31, 17, 17, 30, tzinfo=dt.timezone(dt.timedelta(hours=9)))
    planned = now.replace(second=0) + dt.timedelta(minutes=offset)
    assert is_current_slot(planned, now) is eligible
    row = {"id": "CAL-test", "when": planned, "key": "mbb", "status": READY,
           "url": "", "topic": "Unchanged topic", "notes": ""}
    assert bool(select_due([row], now, {"mbb"})[0]) is eligible
