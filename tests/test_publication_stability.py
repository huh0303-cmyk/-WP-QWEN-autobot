import sys
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import Mock

import pytest
from automation_hub import result_collector as collector
from automation_hub.rooms import AutomationRoom, RoomRegistry

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import editorial_title_gate as gate
import three_model_consensus as consensus


def test_missing_workflow_does_not_hide_other_room_results(monkeypatch):
    rooms = [AutomationRoom(room_id=name, platform='wordpress', name=name,
                            workflow=name + '.yml', enabled=True)
             for name in ('missing', 'working')]
    monkeypatch.setattr(collector.RoomRegistry, 'load', lambda: RoomRegistry(rooms))
    def request(url, token):
        if 'missing.yml' in url:
            raise HTTPError(url, 404, 'Not Found', {}, None)
        return {'workflow_runs': [{'id': 123, 'status': 'completed', 'conclusion': 'success'}]}
    monkeypatch.setattr(collector, '_request', request)
    result = collector.collect('owner/repo', 'not-a-real-token')
    rows = {row['room_id']: row for row in result['rows']}
    assert result['summary']['total'] == 2
    assert result['summary']['collection_errors'] == {'missing.yml': 'HTTP 404'}
    assert rows['missing']['failure_reason'].startswith('RESULT_COLLECTION_FAILED')
    assert rows['working']['run_id'] == '123'


def test_news_evidence_reaches_both_independent_checks(monkeypatch):
    monkeypatch.setenv('CHATGPT_SINGLE_MODEL_PIPELINE', 'true')
    check = Mock(return_value={'ok': True, 'issues': []})
    monkeypatch.setattr(consensus, '_gpt_check', check)
    evidence = {'publisher': 'Example News', 'url': 'https://example.org/story',
                'headline': 'Council opens library', 'excerpt': 'The library opened Monday.'}
    gate.require_editorial_approval(title='Council opens library', content='Example News reports a library opening.',
        meta='Library opening', keyword='library', gemini_generate=None,
        is_newsroom_brief=True, source_evidence=evidence)
    assert check.call_count == 2
    for call in check.call_args_list:
        assert 'The library opened Monday.' in call.args[1]
        assert 'https://example.org/story' in call.args[1]


def test_missing_news_evidence_cannot_bypass_review(monkeypatch):
    monkeypatch.setenv('CHATGPT_SINGLE_MODEL_PIPELINE', 'true')
    with pytest.raises(ValueError, match='NEWS_SOURCE_EVIDENCE_MISSING'):
        gate.require_editorial_approval(title='Council opens library', content='body',
            meta='meta', keyword='library', gemini_generate=None, is_newsroom_brief=True)
