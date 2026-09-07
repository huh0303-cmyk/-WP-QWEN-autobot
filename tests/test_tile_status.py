import importlib.util
from pathlib import Path


def module(path):
    spec = importlib.util.spec_from_file_location('tested_' + Path(path).stem, Path(__file__).resolve().parents[1] / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_verified_publication_survives_later_local_workflow_state():
    m = module('control_center/tile_status.py')
    public = dict(site_id='a', run_id=1, at='2026-09-07T01:00:00Z', status='published')
    local = dict(public, at='2026-09-07T02:00:00Z', status='workflow_success')
    failed = dict(public, run_id=2, at='2026-09-07T03:00:00Z', status='failed')
    result = m.summarize([public, local, failed])
    assert result['latest'] == failed
    assert result['success'] == public
    assert result['failure'] == failed
    assert len(result['events']) == 2


def test_group_history_filters_site_and_does_not_claim_draft_is_public():
    m = module('control_center/tile_status.py')
    state = {'items': [dict(site_id='a', status='done', conclusion='success'), dict(site_id='b', status='done', conclusion='failure')]}
    rows = m.local_events(state, 'a')
    assert len(rows) == 1
    assert rows[0]['status'] == 'workflow_success'
    assert m.summarize(rows)['success'] is None


def test_receipt_requires_matching_destination_and_public_evidence():
    m = module('scripts/collect_tile_publications.py')
    run = dict(id=1, conclusion='success', created_at='2026-09-07T01:00:00Z', html_url='https://github.com/run/1')
    sites = [dict(site_id='a', url='https://a.com'), dict(site_id='b', url='https://b.com')]
    rows = m.extract(run, '🌐 https://a.com\n✅ 공개 발행: https://a.com/article/', sites)
    assert len(rows) == 1 and rows[0]['status'] == 'published'
    assert m.extract(run, '🌐 https://a.com\n초안 생성: https://a.com/?p=2', sites)[0]['status'] == 'workflow_success'


def test_failed_measurement_is_unknown(monkeypatch):
    m = module('control_center/tile_status.py')
    def fail(*args, **kwargs):
        raise m.requests.RequestException('offline')
    monkeypatch.setattr(m.requests, 'get', fail)
    assert m.new_content('https://a.com', 'wordpress', 1) == {'new_posts': None, 'new_posts_delta': None}


def test_gsc_renews_expired_token_and_keeps_unspecified_unknown(monkeypatch):
    import sys
    import types
    monkeypatch.setitem(sys.modules, 'site_registry', types.SimpleNamespace(SITES=[]))
    m = module('scripts/audit_gsc_post_index.py')
    class Reply:
        def __init__(self, code, verdict=None):
            self.status_code = code
            self.text = 'expired'
            self.verdict = verdict
        def json(self):
            return {'inspectionResult': {'indexStatusResult': {'verdict': self.verdict}}}
    replies = iter([Reply(401), Reply(200, 'PASS'), Reply(200, 'VERDICT_UNSPECIFIED')])
    calls = []
    def post(*args, **kwargs):
        calls.append(kwargs['headers']['Authorization'])
        return next(replies)
    monkeypatch.setattr(m.requests, 'post', post)
    monkeypatch.setattr(m, 'token', lambda force=False: 'renewed' if force else 'cached')
    assert m.inspect('expired', 'sc-domain:a.com', 'https://a.com/')['state'] == 'indexed'
    assert calls == ['Bearer expired', 'Bearer renewed']
    assert m.inspect('renewed', 'sc-domain:a.com', 'https://a.com/b')['state'] == 'unknown'
