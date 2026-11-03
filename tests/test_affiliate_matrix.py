import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "affiliate_matrix.py"
spec = importlib.util.spec_from_file_location("affiliate_matrix", SCRIPT)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

class AffiliateMatrixTests(unittest.TestCase):
    def sample_catalog(self):
        return {p: [{"id":f"{p}-{i}","title":f"{p} item {i}",
            "tracking_url":f"https://track.example/{p}/{i}",
            "image_url":f"https://img.example/{p}/{i}.jpg",
            "affiliate_link_verified":True,"image_rights_verified":True} for i in range(10)]
            for p in engine.PROVIDERS}

    def test_builds_exactly_40_cards_and_four_provider_sections(self):
        block = engine.make_cards(self.sample_catalog())
        self.assertEqual(block.count('class="affiliate-card"'), 40)
        self.assertEqual(block.count("<h3>"), 4)
        self.assertIn('rel="sponsored nofollow noopener"', block)
        self.assertIn("affiliate-disclosure", block)

    def test_insert_is_idempotent(self):
        block = engine.make_cards(self.sample_catalog())
        once = engine.insert_block("<p>Article</p>", block)
        twice = engine.insert_block(once, block)
        self.assertEqual(once, twice)
        self.assertEqual(twice.count(engine.START), 1)

    def test_incomplete_marker_is_blocked(self):
        with self.assertRaises(ValueError):
            engine.insert_block("<p>x</p>"+engine.START, "block")

    def test_site_key_is_site_specific(self):
        self.assertEqual(engine.site_key("wp_ktrip365"), "ktrip365")
        self.assertEqual(engine.site_key("blogger_kstudy365"), "kstudy365")
        self.assertIn("wp_khealth365", engine.EXCLUDED_WORDPRESS_SITE_IDS)

    def test_catalog_requires_https_and_verified_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = engine.CATALOG_DIR
            try:
                engine.CATALOG_DIR = Path(tmp)
                products = []
                for provider in engine.PROVIDERS:
                    for i in range(10):
                        products.append({"provider":provider,"id":f"{provider}-{i}","title":"Item",
                            "tracking_url":f"https://track.example/{provider}/{i}",
                            "image_url":f"https://img.example/{provider}/{i}.jpg",
                            "affiliate_link_verified":True,"image_rights_verified":True})
                p = Path(tmp)/"wp_ktrip365-affiliate-matrix.json"
                p.write_text(json.dumps({"site_id":"wp_ktrip365","status":"verified","products":products}),encoding="utf-8")
                self.assertEqual(sum(map(len,engine.load_catalog("wp_ktrip365").values())),40)
                products[0]["image_url"]="http://insecure.example/a.jpg"
                p.write_text(json.dumps({"site_id":"wp_ktrip365","status":"verified","products":products}),encoding="utf-8")
                with self.assertRaises(ValueError): engine.load_catalog("wp_ktrip365")
            finally:
                engine.CATALOG_DIR = old

if __name__ == "__main__":
    unittest.main()
