import datetime as dt
import unittest
from scripts.nasa_weekly_schedule import KST, weekly_slots, is_slot

class TestNasaWeekly(unittest.TestCase):
    def test_three_distinct_days_and_stable(self):
        day = dt.date(2026, 11, 9)
        slots = weekly_slots(day)
        self.assertEqual(len(slots), 3)
        self.assertEqual(len({s.date() for s in slots}), 3)
        self.assertEqual(slots, weekly_slots(day + dt.timedelta(days=4)))
        self.assertTrue(all(s.tzinfo == KST for s in slots))
    def test_one_slot_per_day(self):
        for slot in weekly_slots(dt.date(2026, 11, 9)):
            self.assertTrue(is_slot(slot))
            self.assertFalse(is_slot(slot + dt.timedelta(hours=1)))

if __name__ == '__main__': unittest.main()
