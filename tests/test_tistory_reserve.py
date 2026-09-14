import pytest
from automation_hub.tistory_keywords import reserve_topic
from scripts.tistory_daily_planner import _pick_seed_topic, build_plan


def test_reserve_excludes_used_topics_without_claiming_volume():
    site = {'site_id': 'test', 'seed_topics': ['전세 계약 전 등기부 확인', '실손보험 청구 서류 준비'],
            'recent_history': ['전세 계약 전 등기부 확인']}
    title, _, evidence = reserve_topic(site, '2026-09-12')
    assert title == '실손보험 청구 서류 준비'
    assert evidence['search_volume_approx'] is None


def test_live_failure_uses_reserve(monkeypatch):
    monkeypatch.delenv('TISTORY_FORCE_TOPIC', raising=False)
    monkeypatch.setattr('automation_hub.tistory_keywords.search_volumes', lambda: {})
    monkeypatch.setattr('automation_hub.blogger_topic_router.fetch_today_headlines', lambda: [])
    monkeypatch.setattr('automation_hub.blogger_topic_router.fetch_profile_headlines', lambda p: [])
    monkeypatch.setattr('automation_hub.blogger_topic_router.rank_topics', lambda *a, **kw: [])
    assert _pick_seed_topic({'site_id': 'test', 'seed_topics': ['처음 준비하는 서류 확인']}, '2026-09-12')[2]['evergreen_reserve']


def test_exhausted_reserve_does_not_repeat():
    with pytest.raises(RuntimeError):
        reserve_topic({'site_id':'test', 'seed_topics':['이미 쓴 주제'], 'recent_history':['이미 쓴 주제']}, '2026-09-12')


def test_one_history_failure_does_not_stop_other_sites(monkeypatch):
    monkeypatch.delenv('SITE_IDS', raising=False)
    def history(site):
        if site['site_id'] == 'tistory_insurance_lab':
            raise RuntimeError('unavailable')
        return []
    monkeypatch.setattr('automation_hub.tistory_keywords.recent_history', history)
    monkeypatch.setattr('scripts.tistory_daily_planner._pick_seed_topic', lambda *a: ('새 주제',0,{}))
    plan = build_plan()
    assert len(plan['jobs']) == 4
    assert len(plan['failures']) == 1
    assert plan['enabled_sites'] == 5
