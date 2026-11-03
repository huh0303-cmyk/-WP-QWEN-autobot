import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("queue_builder", ROOT / "scripts" / "build_social_affiliate_queue.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class SocialAffiliateQueueTests(unittest.TestCase):
    def test_provider_mix_is_exact(self):
        self.assertEqual(MODULE.EXPECTED, {
            "coupang_partners": 4, "olive_young_global": 2,
            "trip_com": 2, "agoda": 2
        })
        self.assertEqual(sum(MODULE.EXPECTED.values()), 10)

    def test_youtube_registry_includes_23_rows(self):
        self.assertEqual(len(MODULE.youtube_destinations()), 23)

    def test_all_social_inventory_rows_are_included(self):
        self.assertEqual(len(MODULE.social_destinations()), len(MODULE.SNS.get("accounts", [])))
        self.assertEqual({x["platform"] for x in MODULE.social_destinations()},
                         {"tiktok", "instagram", "facebook", "threads"})

    def test_missing_catalog_blocks_instead_of_publishing(self):
        destination = {
            "platform": "youtube", "destination_key": "test", "channel_id": "UC-test",
            "identity_verified": True, "publish_connected": True,
            "catalog_key": "catalog_that_does_not_exist"
        }
        job = MODULE.build_job(destination, {"content_id": "test"})
        self.assertEqual(job["status"], "blocked")
        self.assertFalse(job["publish_attempted"])
        self.assertIn("catalog_missing:catalog_that_does_not_exist", job["blockers"])

if __name__ == "__main__":
    unittest.main()
