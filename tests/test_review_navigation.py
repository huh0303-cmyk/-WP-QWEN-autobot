from importlib import import_module
from unittest.mock import patch

import pytest

module = import_module('control_center.app')


@pytest.mark.parametrize('status', ['idle', 'polling'])
def test_tistory_flash_targets_requested_site_and_does_not_duplicate(status):
    client = module.app.test_client()
    with patch.object(module, 'get_tistory_data', return_value=[{'site_id': 'tistory_ktrip365', 'name': '한국여행정보'}]), patch.object(module, '_bulk_read', return_value={'status': status}), patch.object(module, '_bulk_write') as write, patch.object(module.threading, 'Thread') as worker:
        response = client.post('/trigger/tistory-single', data={'csrf_token': module.app.config['CONTROL_CENTER_CSRF'], 'site_id': 'tistory_ktrip365'})
    assert response.status_code == 302
    assert response.location == '/'
    with client.session_transaction() as session:
        message = session['_flashes'][0][1]
    assert message['target'] == 'bulk-status-tistory_tistory_ktrip365'
    assert '한국여행정보' in message['text']
    assert worker.call_count == (1 if status == 'idle' else 0)
    if status == 'idle':
        assert write.call_args.args[1]['status'] == 'dispatching'
        assert write.call_args.args[1]['review_job_id'] == 'tistory_ktrip365:' + worker.call_args.kwargs['args'][2]


def test_invalid_request_cannot_start_generation():
    with patch.object(module.threading, 'Thread') as worker:
        assert module.app.test_client().post('/trigger/tistory-single', data={'site_id': 'tistory_ktrip365'}).status_code == 302
    worker.assert_not_called()


@pytest.mark.parametrize('conclusion', ['success', 'failure'])
def test_completed_link_uses_exact_request_job(conclusion):
    state = {'status': 'done', 'review_job_id': 'tistory_ktrip365:manual-tistory_ktrip365-aabb', 'items': [{'status': 'done', 'conclusion': conclusion, 'label': '한국여행정보'}]}
    with patch.object(module, '_bulk_read', return_value=state):
        result = module.app.test_client().get('/api/publish-group-status/tistory_tistory_ktrip365').json
    if conclusion == 'success':
        assert result['review_url'] == '/review/tistory/tistory_ktrip365:manual-tistory_ktrip365-aabb'
    else:
        assert 'review_url' not in result


def test_worker_preserves_request_id_through_dispatch_and_polling(monkeypatch):
    monkeypatch.setenv('CONTROL_CENTER_GITHUB_TOKEN', 'test-only')
    stored = {}
    def write(group, state):
        stored.update(state)
    with patch.object(module, '_bulk_write', side_effect=write), patch.object(module, '_bulk_read', side_effect=lambda group: stored.copy()), patch.object(module, '_dispatch_and_track', return_value={'status': 'done', 'conclusion': 'success'}) as dispatch, patch.object(module, '_poll_bulk_items'):
        module._run_single_tistory_publish('tistory_ktrip365', '한국여행정보')
    inputs = dispatch.call_args.args[3]
    assert stored['review_job_id'] == 'tistory_ktrip365:' + inputs['run_key']
    assert stored['status'] == 'done'


def test_sns_buttons_use_known_destinations_without_claiming_automation():
    accounts = module.get_sns_data()
    topik = next(row for row in accounts if row['platform_key'] == 'instagram' and row['brand'] == 'TOPIK')
    assert topik['url'] == 'https://www.instagram.com/sis_topik1/'
    assert all(row['url'].startswith('https://www.threads.com/@') for row in accounts if row['platform_key'] == 'threads')
    assert not any(row['publish_connected'] for row in accounts)
    assert not next(row for row in accounts if row['platform_key'] == 'tiktok' and row['brand'] == 'ENGLISH')['url']
