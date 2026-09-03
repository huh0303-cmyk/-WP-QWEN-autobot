from pathlib import Path

from scripts.deploy_regular_site_menus import REGULAR_SITES, UTILITY


def test_scope_is_25_regular_sites_and_excludes_newsrooms():
    assert len(REGULAR_SITES) == 25
    urls = {row[0] for row in REGULAR_SITES}
    assert "https://koreanews365.com" not in urls
    assert "https://theseouljournal.com" not in urls


def test_utility_order_and_category_limit_are_locked():
    assert [row[0] for row in UTILITY] == ["privacy-policy", "disclaimer", "contact", "about"]
    source = (Path(__file__).resolve().parents[1] / "scripts" / "deploy_regular_site_menus.py").read_text(encoding="utf-8")
    assert '!= 25' in source
    assert 'categories = [c for c in categories if c.get("slug") != "uncategorized"][:4]' in source
    assert 'assignment[primary] = category_menu' in source
    assert 'network-utility-footer' in source
    assert 'flex-wrap:nowrap' in source
