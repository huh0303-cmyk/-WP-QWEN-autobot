from scripts.promote_calendar_to_golden_keywords import (
    _blogger_angle,
    _blogger_channel_to_site_key,
    _blogspot_to_site_key,
    _domain_to_site_key,
)


def test_all_27_wp_and_33_blogger_destinations_have_queue_mappings():
    assert len(_domain_to_site_key()) == 27
    assert len(_blogspot_to_site_key()) == 33
    assert len(_blogger_channel_to_site_key()) >= 33
    assert _blogger_channel_to_site_key()["korea365"] == "korea365"
    assert _blogger_channel_to_site_key()["koreanews365"] == "koreanews"


def test_blogger_gets_a_distinct_angle_from_wordpress():
    source = "Korea travel: seasonal update"
    assert _blogger_angle(source, "en") != source
    assert "reader questions" in _blogger_angle(source, "en")
    assert "독자 질문" in _blogger_angle("한국 여행", "ko")
