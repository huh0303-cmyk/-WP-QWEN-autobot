from pathlib import Path

from scripts.site_registry import ACTIVE_SITES


ROOT = Path(__file__).resolve().parents[1]


def test_header_rule_is_locked_to_all_27_sites_and_keeps_text_title():
    assert len(ACTIVE_SITES) == 27
    php = (ROOT / "scripts" / "header_text_title_only.php").read_text(encoding="utf-8")
    deployer = (ROOT / "scripts" / "deploy_header_text_title_only.py").read_text(encoding="utf-8")
    assert "get_custom_logo" in php
    assert "network-text-site-title" in php
    assert "custom-logo" in php
    assert "expected 27 active WordPress sites" in deployer
