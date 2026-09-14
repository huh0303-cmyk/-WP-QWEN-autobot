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


def test_newsrooms_accept_new_story_events_without_fixed_publication_slots():
    workflow = (ROOT / ".github" / "workflows" / "newsrooms-daily-publisher.yml").read_text(encoding="utf-8")
    cron_lines = [line.strip() for line in workflow.splitlines() if line.strip().startswith('- cron:')]
    assert not cron_lines
    assert "options: [koreanews365, theseouljournal]" in workflow
    assert "NEWSROOM_SOURCE_URL: ${{ inputs.source_url }}" in workflow
    assert "KO_CATS=" not in workflow
    assert "EN_CATS=" not in workflow


def test_exact_story_event_takes_priority_over_optional_editorial_desk():
    source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
    assert 'suggested = os.getenv("NEWSROOM_SUGGESTED_CATEGORY"' in source
    assert "pool = candidates if exact_source_url else preferred_candidates or candidates" in source
    assert "if forced_preferred and not preferred_candidates:" in source
    assert "no eligible story published within 72 hours" in source
