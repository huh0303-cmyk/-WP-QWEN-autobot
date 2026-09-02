import pytest

from control_center.tistory import TistoryDraft


def _draft(**changes):
    values = {
        "site_id": "tistory_finance_housing",
        "site_url": "https://k-vietnam.tistory.com/",
        "title": "주택담보대출 금리 비교 전 확인할 항목",
        "content_html": '<p><img src="hero.png" alt="주택담보대출 조건을 계산기로 비교하는 사람"></p><p>본문</p>',
        "category": "주택대출·생활금융",
        "search_description": "주택담보대출 금리와 월 상환액, 중도상환수수료, 부대비용을 같은 조건에서 비교하기 전에 확인할 핵심 항목을 실제 계약 순서에 맞춰 정리합니다.",
    }
    values.update(changes)
    return TistoryDraft(**values)


def test_valid_private_draft_and_review_url():
    draft = _draft()
    assert draft.validate() == []
    assert draft.editor_url(24) == "https://k-vietnam.tistory.com/manage/newpost/24?type=post"


@pytest.mark.parametrize("content", [
    '<img src="hero.png">',
    '<img src="hero.png" alt="">',
    '<img src="hero.png" alt="hero.png">',
])
def test_missing_or_invalid_alt_blocks_registration(content):
    assert any("ALT" in error for error in _draft(content_html=content).validate())


def test_public_visibility_is_never_accepted():
    assert any("비공개" in error for error in _draft(visibility="public").validate())
