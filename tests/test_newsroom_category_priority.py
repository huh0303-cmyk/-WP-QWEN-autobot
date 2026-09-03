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


def test_each_newsroom_has_ten_scheduled_round_robin_slots():
    workflow = (ROOT / ".github" / "workflows" / "newsrooms-daily-publisher.yml").read_text(encoding="utf-8")
    cron_lines = [line.strip() for line in workflow.splitlines() if line.strip().startswith('- cron:')]
    assert len(cron_lines) == 20
    assert 'KO_CATS=("정치" "경제" "국방" "글로벌" "문화" "스포츠")' in workflow
    assert 'EN_CATS=("Politics" "Business" "Military" "World" "Culture" "Art" "Sports")' in workflow
    assert workflow.count('KEY="koreanews365"') >= 1
    assert workflow.count('KEY="theseouljournal"') >= 1


def test_scheduled_desk_is_soft_and_falls_back_to_fresh_full_pool():
    source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
    assert 'suggested = os.getenv("NEWSROOM_SUGGESTED_CATEGORY"' in source
    assert "pool = preferred_candidates or candidates" in source
    assert "if forced_preferred and not preferred_candidates:" in source
    assert "no eligible story published within 72 hours" in source
