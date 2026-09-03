from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_seoul_journal_can_force_empty_editorial_desk():
    source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "newsrooms-daily-publisher.yml").read_text(encoding="utf-8")
    assert 'os.getenv("NEWSROOM_PREFERRED_CATEGORY"' in source
    assert "NEWSROOM_PREFERRED_CATEGORY: ${{ inputs.preferred_category }}" in workflow
    assert "World, Sports, Military, Art" in workflow


def test_rights_cleared_art_feed_is_registered():
    registry = (ROOT / "scripts" / "news_source_registry.py").read_text(encoding="utf-8")
    assert '"key": "uk_government_art"' in registry
    assert '"category": "Art"' in registry
    assert "open-government-licence/version/3" in registry
