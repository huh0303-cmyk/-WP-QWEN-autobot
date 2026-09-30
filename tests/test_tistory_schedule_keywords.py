from datetime import date,timedelta
import random
from types import SimpleNamespace
import pytest
from automation_hub.tistory_schedule import random_daily_selection
from automation_hub.tistory_keywords import choose,duplicate

def test_random_daily_selection_has_three_sites_non_round_spaced_times():
    jobs = random_daily_selection(
        ['insurance', 'finance', 'health', 'life', 'travel'],
        rng=random.Random(20261001),
    )
    assert len(jobs) == 3
    assert len({job['site_id'] for job in jobs}) == 3
    minutes = sorted(job['scheduled_minute_kst'] for job in jobs)
    assert all(8 * 60 + 10 <= minute < 22 * 60 + 51 for minute in minutes)
    assert all(minute % 5 != 0 for minute in minutes)
    assert all(b - a >= 90 for a, b in zip(minutes, minutes[1:]))

def candidate(keyword='건강검진',mentions=5,outlets=3):
    return SimpleNamespace(keyword=keyword,mention_count=mentions,outlet_count=outlets,evidence_urls=['https://a','https://b'])

def test_outlet_count_and_duplicate_are_the_real_gates():
    # 2026-09-09: a real, already multi-outlet-verified candidate (rank_topics
    # already enforces outlet_count>=2 and profile fit before choose() ever
    # sees it) must not be discarded just because it doesn't ALSO happen to
    # appear in today's unrelated general trending-search list - that
    # requirement was starving niche sites of every candidate in production
    # (tistory_ktrip365, run 34301461788). Generic trend overlap is now a
    # scoring bonus, not a gate; the real quality bars below are unchanged.
    term,_,evidence=choose([candidate()],{},[])
    assert term=='건강검진' and evidence['search_volume_approx']==0 and evidence['general_trend_match'] is False
    with pytest.raises(RuntimeError):choose([candidate(outlets=1)],{'건강검진':1000},[])
    term,_,evidence=choose([candidate()],{'건강검진':1000},[])
    assert term=='건강검진' and evidence['search_volume_approx']==1000 and evidence['general_trend_match'] is True

def test_previous_topic_and_near_identical_title_are_rejected():
    assert duplicate('건강검진 전 약과 금식 확인 방법', ['건강검진 전 약과 금식 확인방법'])
    with pytest.raises(RuntimeError):choose([candidate()],{'건강검진':1000},['건강검진'])
