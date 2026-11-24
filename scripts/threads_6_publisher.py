"""Threads-only randomized publisher for the six brand accounts.

Independent of the Instagram readiness gate. Per-account guards instead:
credentials present, /me identity equals the expected handle + user id,
reviewed source for source-required accounts, one reserved slot per receipt.
Every reservation and every result is committed to GitHub (receipts file).
"""
import hashlib, json, os, sys, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meta_12_publisher as m  # noqa: E402
from meta_12_daily_schedule import plan  # noqa: E402

ROOT = m.ROOT
STATE = ROOT / 'data/threads_6_publishing_receipts.json'
BASE = 'https://graph.threads.net/v1.0'


def load_state():
    return json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def creds_for(key):
    prefix = f"META_THREADS_{key.upper()}"
    token = os.environ.get(prefix + '_ACCESS_TOKEN', '').strip()
    uid = os.environ.get(prefix + '_USER_ID', '').strip()
    # USER_ID variable is optional: identity is enforced by the /me handle match.
    return (token, uid) if token else (None, None)


def select_slots(now, force):
    day = now.date().isoformat()
    slots = [s for s in plan(day) if s['platform'] == 'threads']
    if force:
        seen, out = set(), []
        for s in slots:
            if s['account_key'] in seen:
                continue
            seen.add(s['account_key'])
            out.append(dict(s, slot_id=f"{day}:threads:{s['account_key']}:manual", time_kst=now.strftime('%H:%M')))
        return out
    catchup = m.POLICY['daily_cadence']['catchup_minutes'] * 60
    due = []
    for s in slots:
        hh, mm = map(int, s['time_kst'].split(':'))
        delay = (now - now.replace(hour=hh, minute=mm, second=0, microsecond=0)).total_seconds()
        if 0 <= delay <= catchup:
            due.append(s)
    return due


def main():
    if os.environ.get('THREADS_6_LIVE', 'true').lower() == 'false':
        print('RESULT=BLOCKED_KILL_SWITCH_THREADS_6_LIVE_FALSE'); return
    force = os.environ.get('FORCE_NOW', 'false').lower() == 'true'
    dry = os.environ.get('DRY_RUN', 'false').lower() == 'true'
    now = datetime.now(m.KST)
    state = load_state()
    todo = [s for s in select_slots(now, force) if s['slot_id'] not in state]
    prepared = []
    for slot in todo:
        sid, key = slot['slot_id'], slot['account_key']
        if dry:
            print(f"DRY slot={sid} handle={slot['expected_handle']} at={slot['time_kst']}"); continue
        token, uid = creds_for(key)
        if not token:
            print(f"SKIPPED_SLOT={sid} REASON=credentials missing"); continue
        try:
            me = m.api(BASE + '/me?fields=id,username', token)
            actual = str(me.get('id', ''))
            if not actual.isdigit() or (uid and uid != actual) or str(me.get('username', '')).lower().lstrip('@') != slot['expected_handle'].lower():
                raise RuntimeError('identity mismatch')
            uid = actual
            account = next(a for a in m.POLICY['accounts'] if a['key'] == key)
            post = m.generate(account, 'threads', slot, m.source_for(slot))
            state[sid] = {'status': 'ATTEMPT_RESERVED', 'platform': 'threads', 'account_key': key,
                          'expected_handle': slot['expected_handle'], 'at_kst': now.isoformat(),
                          'caption': post['caption'], 'content_sha256': hashlib.sha256(post['caption'].encode()).hexdigest()}
            prepared.append((slot, token, actual))
        except Exception as e:
            print(f"SKIPPED_SLOT={sid} REASON={str(e)[:100]}", flush=True)
    if prepared:
        save_state(state)
        m.commit([str(STATE.relative_to(ROOT))], 'threads6: reserve verified slots')
    ok = fail = 0
    for slot, token, uid in prepared:
        sid = slot['slot_id']
        try:
            c = m.api(f'{BASE}/{uid}/threads', token, 'POST', {'media_type': 'TEXT', 'text': state[sid]['caption']})
            cid = str(c.get('id', ''))
            if not cid:
                raise RuntimeError('container missing')
            time.sleep(5)
            pid = str(m.api(f'{BASE}/{uid}/threads_publish', token, 'POST', {'creation_id': cid}).get('id', ''))
            v = m.api(f'{BASE}/{pid}?fields=id,permalink', token)
            url = str(v.get('permalink', ''))
            if not pid or str(v.get('id', '')) != pid or not url.startswith('https://'):
                raise RuntimeError('permalink verification failed')
            state[sid].update({'status': 'PUBLISHED', 'id': pid, 'public_url': url, 'published_at_kst': datetime.now(m.KST).isoformat()})
            print(f"PUBLISHED threads:{slot['expected_handle']} url={url}", flush=True); ok += 1
        except Exception as e:
            state[sid].update({'status': 'NEEDS_RECONCILIATION', 'error': str(e)[:120]})
            print(f"NEEDS_RECONCILIATION threads:{slot['expected_handle']} error={str(e)[:100]}", flush=True); fail += 1
        save_state(state)
        m.commit([str(STATE.relative_to(ROOT))], f"threads6: record result {sid}")
    print(f"RESULT=FINISHED published={ok} failed={fail} candidates={len(todo)}")


if __name__ == '__main__':
    main()
