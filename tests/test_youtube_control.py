import datetime as dt
import unittest

from automation_hub.youtube_registry import load_channels
from scripts.youtube_control_scheduler import KST, is_due, next_run
from automation_hub.youtube_identity import verify_authenticated_channel
from unittest.mock import Mock


class YouTubeRegistryTests(unittest.TestCase):
    def test_registry_has_five_playlist_and_five_knowledge_channels(self):
        channels = load_channels()
        self.assertEqual(10, len(channels))
        self.assertEqual(5, len([c for c in channels if c.channel_type == "playlist"]))
        self.assertEqual(5, len([c for c in channels if c.channel_type == "knowledge"]))
        self.assertEqual(10, len({c.channel_id for c in channels}))
        self.assertEqual(10, len({c.secret_profile for c in channels}))

    def test_disabled_channel_is_never_due(self):
        row = {"enabled": "OFF", "next_run_at": ""}
        self.assertFalse(is_due(row, dt.datetime.now(KST)))

    def test_due_time_and_next_slot_are_timezone_aware(self):
        now = dt.datetime(2026, 8, 27, 2, 30, tzinfo=KST)
        row = {
            "channel_key": "nasa", "enabled": "ON", "next_run_at": "2026-08-27T02:00:00+09:00",
            "interval_days_min": "2", "interval_days_max": "3",
            "allowed_hour_start": "6", "allowed_hour_end": "22",
        }
        self.assertTrue(is_due(row, now))
        planned = next_run(row, now)
        self.assertIn((planned.date() - now.date()).days, {2, 3})
        self.assertGreaterEqual(planned.hour, 6)
        self.assertLessEqual(planned.hour, 22)
        self.assertEqual(KST, planned.tzinfo)

    def test_oauth_channel_mismatch_blocks_upload(self):
        service = Mock()
        service.channels.return_value.list.return_value.execute.return_value = {"items": [{"id": "UC0000000000000000000000"}]}
        with self.assertRaisesRegex(RuntimeError, "OAuth channel mismatch"):
            verify_authenticated_channel(service, "nasa")


if __name__ == "__main__":
    unittest.main()
