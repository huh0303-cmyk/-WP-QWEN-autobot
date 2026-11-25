"""Publishing heartbeat — re-drives existing publishers when GitHub drops cron ticks.

Evidence (2026-11-25 KST): daily-publication-floor.yml has 34 cron ticks/day but
GitHub started only ~2 runs/day (0 after 2026-11-24 14:35Z); threads-6-publisher
*/10 got 0 scheduled runs in 7h; youtube-github-scheduler hourly got ~3/day.
workflow_dispatch is not dropped, so this loop dispatches the existing
publishers on a jittered ~15-minute cadence and then re-dispatches itself.

It never publishes anything by itself. Every target keeps its own gates,
idempotent receipts, kill switches and concurrency group.
"""
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

KST = timezone(timedelta(hours=9))
SELF_WORKFLOW = 'publishing-heartbeat.yml'

# (workflow file, KST start minute, KST end minute, minimum minutes between dispatches)
TARGETS = [
    # WordPress + Blogger + newsroom floor: per-site random slots 06:00-22:30, catch-up after.
    ('daily-publication-floor.yml', 6 * 60 + 5, 23 * 60 + 15, 14),
    # Threads 6: slots 08:10-22:50, script catch-up window is 20 minutes.
    ('threads-6-publisher.yml', 8 * 60 + 5, 23 * 60 + 15, 9),
    # YouTube calendar scheduler: designed for hourly ticks, at most one due row per run.
    ('youtube-github-scheduler.yml', 0, 24 * 60, 55),
]


def due_targets(now, last_sent):
    """Return workflow names to dispatch now. Pure, for tests.

    now: aware KST datetime. last_sent: {workflow: aware datetime}.
    """
    minute = now.hour * 60 + now.minute
    out = []
    for workflow, start, end, gap in TARGETS:
        if not (start <= minute < end):
            continue
        prev = last_sent.get(workflow)
        if prev is not None and now - prev < timedelta(minutes=gap):
            continue
        out.append(workflow)
    return out


def next_sleep_seconds(rng):
    """10-14 minutes, never aligned to a round second boundary."""
    return rng.randint(600, 840) + rng.random()


class Dispatcher:
    def __init__(self, repo, token, ref='main'):
        self.base = f'https://api.github.com/repos/{repo}/actions/workflows/'
        self.ref = ref
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
        })

    def dispatch(self, workflow, inputs=None):
        body = {'ref': self.ref}
        if inputs:
            body['inputs'] = inputs
        for attempt in range(3):
            try:
                r = self.session.post(self.base + workflow + '/dispatches', json=body, timeout=25)
                if r.status_code in (200, 204):
                    return True, r.status_code
                if r.status_code < 500:
                    return False, r.status_code
            except requests.RequestException as exc:
                print(f'DISPATCH_RETRY workflow={workflow} attempt={attempt + 1} error={type(exc).__name__}')
            time.sleep(5 * (attempt + 1))
        return False, 'network'


def main():
    if os.environ.get('PUBLISHING_HEARTBEAT', 'true').strip().lower() == 'false':
        print('RESULT=BLOCKED_KILL_SWITCH_PUBLISHING_HEARTBEAT_FALSE')
        return 0
    budget = int(os.environ.get('HEARTBEAT_BUDGET_SECONDS', str(5 * 3600 + 30 * 60)))
    chain = os.environ.get('HEARTBEAT_CHAIN', 'true').strip().lower() != 'false'
    api = Dispatcher(os.environ['GITHUB_REPOSITORY'], os.environ['GH_DISPATCH_TOKEN'],
                     os.environ.get('HEARTBEAT_REF', 'main'))
    rng = random.Random()
    started = time.monotonic()
    last_sent = {}
    cycles = sent = failed = 0
    while True:
        now = datetime.now(KST)
        for workflow in due_targets(now, last_sent):
            ok, code = api.dispatch(workflow)
            print(f'{now:%Y-%m-%d %H:%M:%S} KST DISPATCH workflow={workflow} ok={ok} status={code}')
            if ok:
                last_sent[workflow] = now
                sent += 1
            else:
                failed += 1
        cycles += 1
        sys.stdout.flush()
        wait = next_sleep_seconds(rng)
        if time.monotonic() - started + wait > budget:
            break
        time.sleep(wait)
    print(f'HEARTBEAT_SUMMARY cycles={cycles} dispatched={sent} failed={failed}')
    if chain:
        ok, code = api.dispatch(SELF_WORKFLOW)
        print(f'CHAIN_NEXT ok={ok} status={code}')
        if not ok:
            # Scheduled backup ticks in the workflow restart the chain.
            print('::warning::heartbeat self-dispatch failed; relying on backup cron')
    return 0


if __name__ == '__main__':
    sys.exit(main())
