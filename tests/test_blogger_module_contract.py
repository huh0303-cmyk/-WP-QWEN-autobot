import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BloggerModuleContractTests(unittest.TestCase):
    def test_all_33_destinations_have_locked_draft_policy(self):
        sites = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))["sites"]
        bloggers = [site for site in sites if site.get("platform") == "blogger"]
        self.assertEqual(33, len(bloggers))
        self.assertEqual(33, len({site["site_id"] for site in bloggers}))
        self.assertEqual(33, len({site["destination_id"] for site in bloggers}))
        self.assertEqual(33, len({site["url"] for site in bloggers}))
        for site in bloggers:
            rules = site["keyword_rules"]
            self.assertTrue(site["enabled"])
            self.assertEqual("review", site["publish_mode"])
            self.assertEqual("draft", site["publish_policy"])
            self.assertEqual(20, site["min_gap_minutes"])
            self.assertEqual("gpt-5-mini", rules["text_provider"])
            self.assertEqual("gpt-5-mini-second-pass", rules["review_provider"])
            self.assertEqual(100, rules["meta_description_chars_min"])
            self.assertEqual(120, rules["meta_description_chars_max_exclusive"])
            self.assertEqual(8, rules["labels_min"])
            self.assertEqual(14, rules["labels_max"])
            self.assertEqual(
                ["sdxl-lightning", "flux-schnell", "pass_no_image"],
                rules["image_provider_order"],
            )


if __name__ == "__main__":
    unittest.main()
