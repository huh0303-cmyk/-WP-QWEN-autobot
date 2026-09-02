import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_registry_has_25_review_blogs_and_two_newsrooms():
    records = json.loads(
        (ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8")
    )["sites"]
    wordpress = [r for r in records if r.get("platform") == "wordpress" and r.get("enabled", True)]
    blogs = [r for r in wordpress if r.get("content_type", "blog") == "blog"]
    newsrooms = [r for r in wordpress if r.get("content_type") in {"news_ko", "news_en"}]
    assert len(blogs) == 25
    assert {r["url"] for r in newsrooms} == {
        "https://koreanews365.com",
        "https://theseouljournal.com",
    }


def test_wp_and_newsroom_workflows_are_fail_closed_by_role():
    wp = (ROOT / ".github/workflows/daily-network-publish.yml").read_text(encoding="utf-8")
    newsroom = (ROOT / ".github/workflows/newsrooms-daily-publisher.yml").read_text(encoding="utf-8")
    assert "inputs.publication_approved && 'publish' || 'draft'" in wp
    assert "inputs.publication_approved && 'true' || 'false'" in wp
    assert 'WP_POST_STATUS: "publish"' in newsroom
    assert 'WP_PUBLICATION_APPROVED: "true"' in newsroom
    assert "newsroom-publisher-single-owner" in newsroom
    assert "for attempt in 1 2 3" in newsroom
    assert 'EDITORIAL_GEMINI_OUTAGE_FALLBACK: "true"' in newsroom


def test_both_workflows_use_sheet_registry_and_locked_models():
    for name in ("daily-network-publish.yml", "newsrooms-daily-publisher.yml"):
        text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert 'AUTOMATION_HUB_SOURCE: "sheets"' in text
        assert 'AI_TEXT_PROVIDER: "openai"' in text
        assert 'OPENAI_MODEL: "gpt-5-mini"' in text
        assert 'GEMINI_REVIEW_MODEL: "gemini-2.5-flash"' in text
        assert "REPLICATE_API_TOKEN" in text
