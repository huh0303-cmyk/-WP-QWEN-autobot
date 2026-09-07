from datetime import date,timedelta
from types import SimpleNamespace
import pytest
from automation_hub.tistory_schedule import slot_minute
from automation_hub.tistory_keywords import choose,duplicate

def test_each_day_has_distinct_morning_and_afternoon_times():
    for site in ['insurance','finance','health','life','travel']:
        previous={}
        for offset in range(365):
            day=(date(2026,9,7)+timedelta(days=offset)).isoformat()
            for slot,start,end in [('am',420,660),('pm',780,1020)]:
                value=slot_minute(site,day,slot)
                assert start<=value<end
                assert previous.get(slot)!=value
                assert slot_minute(site,day,slot)==value
                previous[slot]=value

def candidate(keyword='건강검진',mentions=5,outlets=3):
    return SimpleNamespace(keyword=keyword,mention_count=mentions,outlet_count=outlets,evidence_urls=['https://a','https://b'])

def test_both_search_volume_and_mentions_required():
    with pytest.raises(RuntimeError):choose([candidate()],{},[])
    with pytest.raises(RuntimeError):choose([candidate(outlets=1)],{'건강검진':1000},[])
    term,_,evidence=choose([candidate()],{'건강검진':1000},[])
    assert term=='건강검진' and evidence['search_volume_approx']==1000

def test_previous_topic_and_near_identical_title_are_rejected():
    assert duplicate('건강검진 전 약과 금식 확인 방법', ['건강검진 전 약과 금식 확인방법'])
    with pytest.raises(RuntimeError):choose([candidate()],{'건강검진':1000},['건강검진'])
