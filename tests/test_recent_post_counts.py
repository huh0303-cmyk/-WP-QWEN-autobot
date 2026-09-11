from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
from control_center.metric_evidence import recent_post_counts
import requests

def test_posts_count_korean_midnight_and_previous_day():
    now = datetime.now(timezone(timedelta(hours=9))).replace(hour=0, minute=1, second=0, microsecond=0)
    stamp = lambda d: d.astimezone(timezone.utc).replace(tzinfo=None).isoformat()
    response = Mock()
    response.json.return_value = [{'date_gmt': stamp(now)}, {'date_gmt': stamp(now - timedelta(minutes=2))}]
    with patch('control_center.metric_evidence.requests.get', return_value=response):
        result = recent_post_counts('https://boundary.example', 1)
    assert result == {'new_posts': 1, 'new_posts_delta': 0}

def test_posts_network_failure_is_not_zero():
    with patch('control_center.metric_evidence.requests.get', side_effect=requests.ConnectionError), patch('control_center.metric_evidence.time.sleep'):
        assert recent_post_counts('https://failed.example', 1)['new_posts'] is None
from control_center.metric_evidence import post_metrics

def test_fallback_rejects_old_inventory():
    assert post_metrics({'new_posts': None}, {'audited_at':'2000-01-01T00:00:00+00:00'})['new_posts'] is None

def test_fallback_counts_complete_inventory():
    now=datetime.now(timezone.utc).isoformat()
    entry={'audited_at':now, 'summary':{'total_published':1}, 'posts':{'1':{'published_gmt':now}}}
    assert post_metrics({'new_posts':None},entry)['new_posts']==1
    entry['summary']['total_published']=2
    assert post_metrics({'new_posts':None},entry)['new_posts'] is None
