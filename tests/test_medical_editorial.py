import pytest
from automation_hub.medical_editorial import medical_profile, require_medical_topic, medical_instructions


def test_medical_language_and_scope_do_not_change_paired_wordpress():
    original = {"site_key": "kmedical_job_center", "language": "en", "wordpress": {"theme": "Health"}, "blogspot": {}}
    profile = medical_profile(original)
    assert profile["language"] == "ko"
    assert original["wordpress"]["theme"] == "Health"
    assert "자격" in profile["wordpress"]["theme"]
    require_medical_topic(profile, "요양보호사 응시자격 확인")
    with pytest.raises(ValueError):
        require_medical_topic(profile, "비타민과 피부 관리")
    assert "등록은 국가공인" in medical_instructions(profile)


def test_other_blogs_unchanged():
    profile = {"site_key": "khealth365", "language": "en"}
    assert medical_profile(profile) is profile
    require_medical_topic(profile, "General health")
