import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import blogger_daily_auto_publish as m


def test_legacy_dispatch_is_never_counted_as_publication(tmp_path):
    path = tmp_path/'state.json'
    path.write_text(json.dumps({'date': '2000-01-01', 'posted': ['one']}))
    with patch.object(m, 'STATE_FILE', path):
        state = m.load_state()
    assert state['posted'] == []
    assert state['pending']['one']['status'] == 'legacy_unverified'


def test_corrupt_state_does_not_trigger_duplicate_dispatches(tmp_path):
    path = tmp_path/'state.json'
    path.write_text('broken')
    with patch.object(m, 'STATE_FILE', path), pytest.raises(RuntimeError):
        m.load_state()


def test_only_todays_public_post_clears_pending():
    state = {'date': '2026-09-12', 'posted': [], 'pending': {'one': {}, 'two': {}}}
    sites = [{'site_id': 'one', 'url': 'https://one.blogspot.com'}, {'site_id': 'two', 'url': 'https://two.blogspot.com'}]
    def check(row):
        return {'status': 'public_post_found', 'latest_published':
            '2026-09-11T16:00:00Z' if 'one.' in row['url'] else '2026-09-11T12:00:00Z'}
    with patch('publication_health_audit.check', side_effect=check):
        assert m.reconcile(state, sites) == {'one', 'two'}
    assert state['posted'] == ['one']
    assert 'two' in state['pending']
