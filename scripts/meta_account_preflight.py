from __future__ import annotations
import json, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'config' / 'meta_five_account_daily_policy.json'
def load_policy():
    data = json.loads(POLICY.read_text(encoding='utf-8-sig'))
    if len(data.get('accounts', [])) != 5: raise ValueError('Policy must contain exactly five accounts')
    handles = [a['handle'] for a in data['accounts']]
    keys = [a['key'] for a in data['accounts']]
    if len(set(handles)) != 5 or len(set(keys)) != 5: raise ValueError('Account handles and keys must be unique')
    if data['platforms'] != ['instagram', 'threads']: raise ValueError('Unexpected platform scope')
    return data
def readiness(data):
    rows, missing = [], []
    for platform in data['platforms']:
        for account in data['accounts']:
            prefix = f"META_{platform.upper()}_{account['key'].upper()}"
            tn, un = prefix + '_ACCESS_TOKEN', prefix + '_USER_ID'
            token, uid = os.getenv(tn, '').strip(), os.getenv(un, '').strip()
            ok = bool(token) and uid.isdigit()
            if not token: missing.append(tn)
            if not uid.isdigit(): missing.append(un)
            rows.append({'platform':platform,'handle':account['handle'],'status':'READY' if ok else 'MISSING_CREDENTIALS','token_present':bool(token),'numeric_user_id_present':uid.isdigit()})
    return {'account_count':5,'platform_count':2,'expected_connections':10,'ready_connections':sum(x['status']=='READY' for x in rows),'publish_enabled':False,'publication_performed':False,'missing_secret_names':missing,'connections':rows}
def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    d=load_policy(); r=readiness(d)
    if a.self_test:
        assert [x['handle'] for x in d['accounts']] == ['seoul_topik','seoul_jisoo','seoul_chris','english_pick1','japanese_pick']
        assert r['expected_connections']==10 and d['authentication']['publish_enabled'] is False
        print('SELF_TEST=PASS; five exact handles mapped to Instagram and Threads'); return
    print(json.dumps(r,ensure_ascii=False,indent=2))
    print('STATUS=BLOCKED_AUTH; no publishing attempted' if r['ready_connections'] != 10 else 'STATUS=AUTH_READY_CONTENT_QUEUE_AND_PUBLISHER_STILL_REQUIRED')
if __name__=='__main__': main()

