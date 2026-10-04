from datetime import datetime
from pathlib import Path
import json
import sys
from unittest.mock import Mock

import requests
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import provider_key_check as pkc
import daily_publication_floor as floor


def resp(code, text=''):
    return Mock(status_code=code, text=text)


def session_returning(code, text=''):
    session = Mock()
    session.get.return_value = resp(code, text)
    return session


def test_the_exact_2026_09_29_failure_is_classified_as_invalid():
    body = '{"error": {"code": 400, "message": "API key not valid. Please pass a valid API key."}}'
    assert pkc.check_gemini('bad', session=session_returning(400, body)) == pkc.INVALID


@pytest.mark.parametrize('code,expected', [(200, pkc.OK), (429, pkc.QUOTA), (403, pkc.INVALID), (401, pkc.INVALID),
                                           (500, pkc.UNREACHABLE), (503, pkc.UNREACHABLE), (400, pkc.UNREACHABLE)])
def test_status_codes(code, expected):
    assert pkc.check_gemini('k', session=session_returning(code, '')) == expected


def test_missing_key_blocks_without_any_network_call():
    session = Mock()
    assert pkc.check_gemini('   ', session=session) == pkc.MISSING
    assert pkc.check_gemini(None, session=session) == pkc.MISSING
    session.get.assert_not_called()


def test_network_failure_is_not_treated_as_a_bad_key():
    session = Mock()
    session.get.side_effect = requests.ConnectionError('down')
    assert pkc.check_gemini('k', session=session) == pkc.UNREACHABLE
    assert pkc.UNREACHABLE not in pkc.BLOCKING and pkc.QUOTA not in pkc.BLOCKING


def test_key_is_sent_in_a_header_never_in_the_url():
    session = session_returning(200)
    pkc.check_gemini('secret-key-123', session=session)
    args, kwargs = session.get.call_args
    assert 'secret-key-123' not in args[0] and 'key' not in (kwargs.get('params') or {})
    assert kwargs['headers']['x-goog-api-key'] == 'secret-key-123'


def run_main(monkeypatch, tmp_path, provider_state, platform='blogger'):
    sites = [{'site_id': f's{i}', 'platform': platform, 'url': f'https://s{i}.example'} for i in range(3)]
    api = Mock()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(floor, 'sites_for', lambda p: sites)
    monkeypatch.setattr(floor, 'GitHub', lambda *a, **k: api)
    monkeypatch.setattr(floor, 'public_status', lambda site, now: {'status': 'DUE'})
    monkeypatch.setattr(floor, 'force_ipv4_dns', lambda: None)
    monkeypatch.setattr(floor, 'check_gemini', lambda key: provider_state)
    calls = []

    def fake_reconcile(site, public, api_, now, allow_dispatch, **kw):
        calls.append(allow_dispatch)
        return {'site_id': site['site_id'], 'url': site['url'], 'status': 'DISPATCHED' if allow_dispatch else 'DUE'}, allow_dispatch
    monkeypatch.setattr(floor, 'reconcile', fake_reconcile)
    monkeypatch.setenv('GITHUB_REPOSITORY', 'o/r')
    monkeypatch.setenv('GH_DISPATCH_TOKEN', 't')
    monkeypatch.setenv('GEMINI_API_KEY', 'x')
    monkeypatch.setattr(sys, 'argv', ['floor', '--platform', platform, '--max-dispatch', '4'])
    return calls


def test_rejected_key_dispatches_nothing_claims_nothing_and_fails_the_run(monkeypatch, tmp_path, capsys):
    calls = run_main(monkeypatch, tmp_path, pkc.INVALID)
    with pytest.raises(SystemExit) as exit_info:
        floor.main()
    assert exit_info.value.code == 1
    assert calls == [False, False, False]  # every site still verified publicly, none dispatched
    report = json.loads((tmp_path / 'artifacts/daily-publication-floor-blogger.json').read_text())
    assert report['dispatched'] == 0 and report['provider'] == {'gemini': 'INVALID', 'blocked': True}
    assert 'REJECTED' in capsys.readouterr().err


@pytest.mark.parametrize('state', [pkc.OK, pkc.QUOTA, pkc.UNREACHABLE])
def test_healthy_or_transient_provider_state_dispatches_as_before(monkeypatch, tmp_path, state):
    calls = run_main(monkeypatch, tmp_path, state)
    floor.main()
    assert calls == [True, True, True]
    report = json.loads((tmp_path / 'artifacts/daily-publication-floor-blogger.json').read_text())
    assert report['dispatched'] == 3 and report['provider']['blocked'] is False


def test_runs_without_the_key_env_behave_exactly_as_before(monkeypatch, tmp_path):
    calls = run_main(monkeypatch, tmp_path, pkc.INVALID)
    monkeypatch.delenv('GEMINI_API_KEY')
    floor.main()  # old callers that never pass the key are not blocked
    assert calls == [True, True, True]


def test_schedule_capacity_covers_every_site_with_a_retry_margin():
    import yaml
    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / '.github/workflows/daily-publication-floor.yml').read_text())
    cron = workflow[True]['schedule'][0]['cron']
    hours = cron.split()[1].split(',')
    assert len(hours) * 4 >= 33 + 3  # 4 dispatches/pass/platform must cover 33 Blogspot + retry margin
    assert cron.split()[0] not in {'0', '30'}  # never on the exact hour/half-hour
