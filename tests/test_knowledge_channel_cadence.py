import datetime as dt
import unittest
from scripts.knowledge_channel_cadence import slots, due_channels, KST

class TestCadence(unittest.TestCase):
    def test_weekly(self):
        day = dt.date(2026, 11, 9)
        for channel in ('nasa', 'invention', 'silent_era', 'retro_reels'):
            values = slots(channel, day)
            self.assertEqual(len(values), 3)
            self.assertEqual(len({x.date() for x in values}), 3)
            self.assertEqual(values, slots(channel, day + dt.timedelta(days=3)))
    def test_history_daily(self):
        self.assertEqual(len(slots('history', dt.date(2026, 11, 9))), 7)
    def test_due(self):
        slot = slots('history', dt.date(2026, 11, 9))[0]
        self.assertIn('history', due_channels(slot))
        self.assertNotIn('history', due_channels(slot + dt.timedelta(hours=1)))

if __name__ == '__main__': unittest.main()
