from scripts.review_sheet import HEADER, TAB_NAME


def test_review_sheet_contract_is_mobile_review_friendly():
    assert TAB_NAME == "오늘_글검수"
    assert HEADER == [
        "작성시각(KST)", "플랫폼", "채널", "제목", "글 보기",
        "상태", "승인결정", "작업기록", "비고",
    ]
