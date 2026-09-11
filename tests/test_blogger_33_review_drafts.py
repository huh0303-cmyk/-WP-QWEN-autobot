from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_blogger_33_review_mode_is_private_and_records_editor_links():
    source = (ROOT / "scripts" / "publish_blogger_33_now.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "blogger-33-review-drafts.yml").read_text(encoding="utf-8")
    assert '"true" if draft_mode else "false"' in source
    assert "www.blogger.com/blog/post/edit" in source
    assert "append_review_rows" in source
    assert "control-room review queue sync failed" in source
    assert "exact_complete" in source
    assert 'BLOGGER_REVIEW_DRAFT_MODE: "true"' in workflow
    assert 'NORMAL_COMPLETION_EMAIL_ENABLED: "false"' in workflow


def test_legacy_bulk_entry_also_creates_drafts_instead_of_public_posts():
    workflow = (ROOT / ".github" / "workflows" / "publish-blogger-33-now.yml").read_text(encoding="utf-8")
    assert 'BLOGGER_REVIEW_DRAFT_MODE: "true"' in workflow
    assert "PUBLIC_RUN_KEY" not in workflow
