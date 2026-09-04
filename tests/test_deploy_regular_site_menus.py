from pathlib import Path

from scripts.deploy_regular_site_menus import REGULAR_SITES, UTILITY, is_utility_footer_snippet


def test_scope_is_25_regular_sites_and_excludes_newsrooms():
    assert len(REGULAR_SITES) == 25
    urls = {row[0] for row in REGULAR_SITES}
    assert "https://koreanews365.com" not in urls
    assert "https://theseouljournal.com" not in urls


def test_utility_order_and_category_limit_are_locked():
    assert [row[0] for row in UTILITY] == ["about", "contact", "disclaimer", "privacy-policy"]
    source = (Path(__file__).resolve().parents[1] / "scripts" / "deploy_regular_site_menus.py").read_text(encoding="utf-8")
    assert '!= 25' in source
    assert 'categories = [c for c in categories if c.get("slug") != "uncategorized"][:4]' in source
    assert "set_theme_mod('nav_menu_locations'" in source
    assert 'network-utility-footer' in source
    assert 'flex-wrap:nowrap' in source
    assert 'header .site-logo,header .custom-logo-link' in source
    assert 'json.dumps(title, ensure_ascii=False)' in source


def test_duplicate_footer_detection_never_matches_the_visitor_counter_comment():
    counter = {
        "name": "Daily visitor counter v2",
        "code": "// render after network-utility-footer\necho '<div class=\"network-daily-visitor-counter\">';",
    }
    footer = {
        "name": "old footer",
        "code": "echo '<nav class=\"network-utility-footer\" aria-label=\"Site information\">';",
    }
    assert is_utility_footer_snippet(counter) is False
    assert is_utility_footer_snippet(footer) is True
