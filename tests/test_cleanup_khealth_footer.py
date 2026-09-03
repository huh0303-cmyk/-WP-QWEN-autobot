from pathlib import Path


def test_cleanup_preserves_real_counter_and_removes_legacy_shortcode():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "cleanup_khealth_footer.py").read_text(encoding="utf-8")
    assert 'if "[hits]" in html' in source
    assert 'if "network-daily-visitor-counter" not in html' in source
    assert "generate_copyright" in source
