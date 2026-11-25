from datetime import datetime, timedelta
from pathlib import Path
import random
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import publishing_heartbeat as hb


def at(h, m):
    return datetime(2026, 11, 25, h, m, tzinfo=hb.KST)


def test_floor_and_threads_and_youtube_due_in_daytime():
    assert set(hb.due_targets(at(9, 13), {})) == {
        'daily-publication-floor.yml', 'threads-6-publisher.yml', 'youtube-github-scheduler.yml'}


def test_night_only_youtube():
    assert hb.due_targets(at(3, 7), {}) == ['youtube-github-scheduler.yml']
    assert 'daily-publication-floor.yml' not in hb.due_targets(at(23, 20), {})


def test_floor_runs_through_catch_up_window():
    # Floor catch-up opens at 22:30 KST; heartbeat must still drive it then.
    assert 'daily-publication-floor.yml' in hb.due_targets(at(22, 41), {})


def test_min_gap_respected():
    now = at(10, 0)
    last = {w: now - timedelta(minutes=5) for w, *_ in hb.TARGETS}
    assert hb.due_targets(now, last) == []
    last = {w: now - timedelta(minutes=15) for w, *_ in hb.TARGETS}
    assert set(hb.due_targets(now, last)) == {'daily-publication-floor.yml', 'threads-6-publisher.yml'}


def test_threads_cadence_fits_twenty_minute_catchup():
    rng = random.Random(1)
    gap = dict((w, g) for w, _, _, g in hb.TARGETS)['threads-6-publisher.yml']
    worst_sleep = max(hb.next_sleep_seconds(rng) for _ in range(2000)) / 60
    # Worst case between two Threads dispatches is one sleep (gap < min sleep).
    assert gap < 10 and worst_sleep < 15


def test_sleep_bounds():
    rng = random.Random(7)
    values = [hb.next_sleep_seconds(rng) for _ in range(1000)]
    assert min(values) >= 600 and max(values) < 841


def test_targets_exist_and_are_dispatchable():
    for workflow, *_ in hb.TARGETS + [(hb.SELF_WORKFLOW,)]:
        doc = yaml.safe_load((ROOT / '.github/workflows' / workflow).read_text(encoding='utf-8'))
        triggers = doc.get('on', doc.get(True))
        assert 'workflow_dispatch' in triggers, workflow


def test_kill_switch(monkeypatch, capsys):
    monkeypatch.setenv('PUBLISHING_HEARTBEAT', 'false')
    assert hb.main() == 0
    assert 'BLOCKED_KILL_SWITCH' in capsys.readouterr().out


def test_main_dispatches_then_chains(monkeypatch):
    sent = []

    class FakeDispatcher:
        def __init__(self, *a, **k):
            pass

        def dispatch(self, workflow, inputs=None):
            sent.append(workflow)
            return True, 204

    monkeypatch.setattr(hb, 'Dispatcher', FakeDispatcher)
    monkeypatch.setattr(hb, 'datetime', type('D', (), {'now': staticmethod(lambda tz=None: at(9, 13))}))
    monkeypatch.setenv('GITHUB_REPOSITORY', 'o/r')
    monkeypatch.setenv('GH_DISPATCH_TOKEN', 'x')
    monkeypatch.setenv('HEARTBEAT_BUDGET_SECONDS', '1')
    monkeypatch.delenv('PUBLISHING_HEARTBEAT', raising=False)
    assert hb.main() == 0
    assert sent[-1] == hb.SELF_WORKFLOW
    assert set(sent[:-1]) == {'daily-publication-floor.yml', 'threads-6-publisher.yml', 'youtube-github-scheduler.yml'}
