from scripts.publishing_completion_notify import _html_body, _plain_body


REVIEWS = [{
    "title": "테스트 글",
    "edit_url": "https://example.com/wp-admin/post.php?post=12&action=edit",
    "post_url": "https://example.com/?p=12",
}]


def test_html_email_has_direct_review_and_decision_buttons():
    body = _html_body("오늘 작성된 비공개 글입니다.", REVIEWS, "https://github.com/example/run")
    assert "글 먼저 보기" in body
    assert "승인(공개)" in body
    assert "비승인(보류·삭제)" in body
    assert "post=12&amp;action=edit#submitdiv" in body
    assert "post=12&amp;action=edit#delete-action" in body
    assert "모바일 검수 요청" not in body


def test_plain_email_links_to_the_post_editor_not_only_run_log():
    body = _plain_body("작성 완료", REVIEWS, "https://github.com/example/run")
    assert "글 확인·승인·비승인" in body
    assert REVIEWS[0]["edit_url"] in body
    assert "모바일 확인·업로드" not in body
