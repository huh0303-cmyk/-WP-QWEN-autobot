import unittest
from unittest.mock import Mock, patch

from automation_hub.models import SiteConfig
from automation_hub.public_verifier import verify_publication
from automation_hub.registry import SiteRegistry
from automation_hub.wordpress_adapter import apply_wordpress_registry


class RegistryTests(unittest.TestCase):
    def test_initial_registry_has_correct_wordpress_topology(self):
        registry = SiteRegistry.load()
        self.assertEqual(27, len(registry.sites))
        self.assertEqual(25, len([s for s in registry.sites if s.content_type == "blog"]))
        self.assertEqual(2, len([s for s in registry.sites if s.content_type.startswith("news")]))
        self.assertEqual({}, registry.validate())

    def test_registry_has_no_fixed_site_limit(self):
        sites = [
            SiteConfig(site_id=f"site_{index}", platform="blogger", name=str(index), url=f"blog-{index}")
            for index in range(100)
        ]
        self.assertEqual(100, len(SiteRegistry(sites).sites))

    def test_sheet_rows_are_typed_and_can_disable_a_site(self):
        header = [
            "site_id", "platform", "name", "url", "content_type", "group", "enabled",
            "publish_mode", "daily_min", "daily_max", "weekly_min", "weekly_max",
            "min_gap_minutes", "content_profile", "min_chars", "target_chars", "max_chars",
            "persona", "tone", "category_mode", "default_category", "image_mode",
            "image_min", "image_max", "keyword_mode", "affiliate_profile", "secret_name",
            "language", "timezone", "allowed_categories", "rss_sources",
        ]
        row = [
            "wp_one", "wordpress", "One", "https://example.com", "blog", "A", "OFF",
            "review", "1", "2", "3", "4", "60", "option_2", "1500", "2000", "2500",
            "editor", "calm", "existing_only", "General", "mixed", "1", "2",
            "golden_keyword", "none", "EXAMPLECOM", "ko", "Asia/Seoul",
            "General,News", "registry:korean",
        ]
        registry = SiteRegistry.from_sheet_rows(header, [row])
        site = registry.by_id("wp_one")
        self.assertFalse(site.enabled)
        self.assertEqual(2, site.daily_max)
        self.assertEqual("option_2", site.content_profile)
        self.assertEqual("ko", site.language)
        self.assertEqual(["General", "News"], site.allowed_categories)
        self.assertEqual(["registry:korean"], site.rss_sources)
        self.assertEqual({}, registry.validate())

    def test_wordpress_dashboard_overlays_engine_settings(self):
        site = SiteConfig(
            site_id="wp_one", platform="wordpress", name="One", url="https://example.com",
            secret_name="EXAMPLECOM", language="ko", daily_max=3, target_chars=2100,
            max_chars=2600, persona="편집국", tone="차분한 문체",
            keyword_rules={"theme": "테스트 주제"},
        )
        legacy = [{"url": "https://example.com", "theme": "old", "wp_pass_env": "OLD"}]
        sites, personas = apply_wordpress_registry(legacy, {}, SiteRegistry([site]))
        self.assertEqual("EXAMPLECOM", sites[0]["wp_pass_env"])
        self.assertEqual(3, sites[0]["daily"])
        self.assertEqual(0, sites[0]["daily_min"])
        self.assertEqual(3, sites[0]["daily_max"])
        self.assertEqual("테스트 주제", sites[0]["theme"])
        self.assertEqual("편집국", personas["https://example.com"]["persona_ko"])
        self.assertEqual(2100, personas["https://example.com"]["min_chars"])
        self.assertTrue(sites[0]["no_image"])

    def test_wordpress_dashboard_rejects_unprofiled_destination(self):
        registry = SiteRegistry([
            SiteConfig(site_id="new", platform="wordpress", name="New", url="https://new.example")
        ])
        with self.assertRaisesRegex(ValueError, "no engine profile"):
            apply_wordpress_registry([], {}, registry)


class PublicVerifierTests(unittest.TestCase):
    @patch("automation_hub.public_verifier.requests.get")
    def test_rejects_home_redirect(self, get):
        get.return_value = Mock(status_code=200, url="https://example.com/", text="<title>Home</title>")
        result = verify_publication(
            "https://example.com/missing-post/",
            "Expected Post",
            site_url="https://example.com",
            attempts=1,
        )
        self.assertFalse(result.ok)
        self.assertEqual("redirected_to_home", result.error_code)

    @patch("automation_hub.public_verifier.requests.get")
    def test_accepts_public_article_with_expected_title(self, get):
        get.return_value = Mock(
            status_code=200,
            url="https://example.com/real-post/",
            text="<html><title>Real Post — Example</title></html>",
        )
        result = verify_publication(
            "https://example.com/real-post/",
            "Real Post",
            site_url="https://example.com",
            attempts=1,
        )
        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
