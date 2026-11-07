import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from meta_daily_schedule import plan

class ScheduleTests(unittest.TestCase):
    def test_thirty_unique_slots_and_three_per_connection(self):
        slots = plan("2026-11-08")
        self.assertEqual(len(slots), 30)
        self.assertEqual(len({s["slot_id"] for s in slots}), 30)
        from collections import Counter
        self.assertEqual(set(Counter((s["platform"], s["account_key"]) for s in slots).values()), {3})

    def test_restarts_keep_plan_and_dates_change_times(self):
        self.assertEqual(plan("2026-11-08"), plan("2026-11-08"))
        self.assertNotEqual([s["time_kst"] for s in plan("2026-11-08")],
                            [s["time_kst"] for s in plan("2026-11-09")])

    def test_slots_stay_in_separate_windows(self):
        for s in plan("2026-11-08"):
            hour, minute = map(int, s["time_kst"].split(":"))
            low, high = {1: (490,749), 2:(750,1039), 3:(1040,1370)}[s["slot"]]
            self.assertTrue(low <= hour*60+minute <= high)
