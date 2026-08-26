import unittest
from unittest.mock import Mock, patch

from automation_hub.models import SiteConfig
from automation_hub.public_verifier import verify_publication
from automation_hub.registry import SiteRegistry


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
