import json, sys
sys.path.insert(0, "tests")
from test_write_article_expand import article
from automation_hub.original_writer import original_quality_score
from scripts.london_site_catalog import manual_profile, content_sites

KW = "생활금융 주거 부동산 안내"


def body_failures(chars, platform_cfg):
    a = article(chars)
    _, f = original_quality_score(a, keyword=KW, target_chars=platform_cfg["target_chars"], language="ko",
                                  min_chars=platform_cfg["min_chars"], max_chars=platform_cfg["max_chars"])
    return [x for x in f if x.startswith("body length")]


def policy():
    return json.load(open("config/platform_length_policy.json", encoding="utf-8"))["platforms"]


def test_same_body_passes_naver_but_fails_tistory():
    p = policy()
    assert body_failures(1300, p["naver"]) == []
    assert body_failures(1300, p["tistory"]) != []


def test_naver_and_tistory_profiles_differ():
    naver = next(s["site_id"] for s in content_sites() if s["platform"] == "naver" and s["enabled"])
    tis = next(s["site_id"] for s in content_sites() if s["platform"] == "tistory" and s["enabled"])
    n = manual_profile(naver)[1]["wordpress"]
    t = manual_profile(tis)[1]["wordpress"]
    assert (n["min_chars"], n["target_chars"], n["max_chars"]) == (1200, 1800, 2600)
    assert (t["min_chars"], t["target_chars"], t["max_chars"]) == (1800, 2400, 3400)


def test_default_behaviour_unchanged_without_min_max():
    a = article(1900)
    _, f = original_quality_score(a, keyword=KW, target_chars=2000, language="ko")
    assert not [x for x in f if x.startswith("body length")]
