from scripts.repair_ktrip_english_seo import DESCRIPTION, EXCERPT, SITE, SLUG


def test_ktrip_repair_uses_complete_english_search_description():
    assert SITE == "https://k-trip365.com"
    assert SLUG == "busan-weekend-smart-savings-big-memories"
    assert 100 <= len(DESCRIPTION) <= 119
    assert DESCRIPTION.endswith(".")
    assert not any("가" <= char <= "힣" for char in DESCRIPTION + EXCERPT)
