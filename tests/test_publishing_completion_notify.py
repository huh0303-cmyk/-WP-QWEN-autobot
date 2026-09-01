from scripts.publishing_completion_notify import _html_body, _plain_body


REVIEWS = [{
    "site": "example.com",
    "title": "테스트 글",
    "quality_score": 82,
    "edit_url": "https://example.com/wp-admin/post.php?post=12&action=edit",
    "post_url": "https://example.com/?p=12",
}]


def test_html_email_has_single_admin_review_button():
    body = _html_body("오늘 작성된 비공개 글입니다.", REVIEWS, "https://github.com/example/run")
    assert "관리자에서 검토 · 발행 · 예약" in body
    assert "품질점수: <b>82/100</b>" in body
    assert "승인(공개)" not in body
    assert "비승인(보류·삭제)" not in body
    assert "post=12&amp;action=edit" in body


def test_plain_email_links_to_the_post_editor_not_only_run_log():
    body = _plain_body("작성 완료", REVIEWS, "https://github.com/example/run")
    assert "검토·발행·예약" in body
    assert "품질점수: 82/100" in body
    assert REVIEWS[0]["edit_url"] in body
    assert "작업 기록" not in body


def test_mature_worker_draft_status_resolves_editor(tmp_path, monkeypatch):
    import json
    from scripts import publishing_completion_notify as mod
    monkeypatch.chdir(tmp_path)
    (tmp_path / mod.RESULT_FILE).write_text(json.dumps({"records": [{
        "status": "✅ DRAFT", "url": "https://example.com/?p=12", "title": "Review me"
    }]}), encoding="utf-8")
    monkeypatch.setattr(mod, "_site_key_map", lambda: {"https://example.com": "TEST_WP"})
    monkeypatch.setenv("TEST_WP", "test-only")
    assert mod.build_draft_reviews()[0]["edit_url"] == REVIEWS[0]["edit_url"]


def test_blogger_draft_uses_native_editor_link_without_wp_credentials(tmp_path, monkeypatch):
    import json
    from scripts import publishing_completion_notify as mod
    monkeypatch.chdir(tmp_path)
    edit_url = "https://www.blogger.com/blog/post/edit/123/44"
    (tmp_path / mod.RESULT_FILE).write_text(json.dumps({"records": [{
        "status": "draft", "platform": "blogger", "site": "demo.blogspot.com",
        "url": edit_url, "edit_url": edit_url, "title": "Blogger draft", "quality_score": 81,
    }]}), encoding="utf-8")
    review = mod.build_draft_reviews()[0]
    assert review["platform"] == "blogger"
    assert review["edit_url"] == edit_url
    assert review["quality_score"] == 81
