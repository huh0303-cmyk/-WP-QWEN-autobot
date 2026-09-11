from review_status_sync import approval_state, parse_review_url


def test_approval_state_mapping():
    assert approval_state("publish") == ("공개", "승인완료")
    assert approval_state("future") == ("예약공개", "승인완료")
    assert approval_state("draft") == ("비공개 초안", "검토대기")
    assert approval_state("trash") == ("휴지통", "반려")


def test_parse_review_url():
    assert parse_review_url("https://example.com/wp-admin/post.php?post=123&action=edit") == ("https://example.com", 123)
    assert parse_review_url("https://example.com/no-post") is None
