"""Read-only identity check for the current six Instagram + six Threads targets."""
import json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'config/meta_12_account_daily_policy.json').read_text(encoding='utf-8'))

def get_json(url, token):
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'LondonProject-Meta12-Preflight/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:return r.status,json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:return e.code,{}
    except Exception:return 0,{}

def main():
    report={'schema_version':1,'publication_attempted':False,'targets':[]}
    missing=[]
    for account in POLICY['accounts']:
        key=account['key'].upper()
        for platform in POLICY['platforms']:
            prefix=f'META_{platform.upper()}_{key}'
            token=os.environ.get(prefix+'_ACCESS_TOKEN','').strip()
            expected_id=os.environ.get(prefix+'_USER_ID','').strip()
            expected_handle=account[platform].lower().lstrip('@')
            row={'platform':platform,'account_key':account['key'],'expected_handle':expected_handle,'identity':'NOT_CHECKED','write_scope':'NOT_CHECKED'}
            if not token or not expected_id.isdigit():
                row['identity']='MISSING_CREDENTIALS'
                missing.append(prefix)
            else:
                graph='https://graph.instagram.com/v25.0/me' if platform=='instagram' else 'https://graph.threads.net/v1.0/me'
                fields='user_id,username' if platform=='instagram' else 'id,username'
                status,payload=get_json(graph+'?'+urllib.parse.urlencode({'fields':fields}),token)
                actual_id=str(payload.get('user_id' if platform=='instagram' else 'id',''))
                actual_handle=str(payload.get('username','')).lower().lstrip('@')
                row['identity']='VERIFIED' if status==200 and actual_id==expected_id and actual_handle==expected_handle else 'MISMATCH_OR_API_ERROR'
                row['http_status']=status
                row['account_id_match']=actual_id==expected_id
                row['handle_match']=actual_handle==expected_handle
                if row['identity']!='VERIFIED':missing.append(prefix)
            report['targets'].append(row)
    report['identity_verified_count']=sum(x['identity']=='VERIFIED' for x in report['targets'])
    report['identity_target_count']=len(report['targets'])
    report['missing_or_mismatched']=missing
    report['result']='ALL_12_IDENTITIES_VERIFIED' if report['identity_verified_count']==12 else 'INCOMPLETE'
    out=Path(os.environ.get('GITHUB_STEP_SUMMARY','/tmp/meta12-summary.md'))
    lines=['## Meta 12 destination preflight','',f"Identity verified: {report['identity_verified_count']}/12",'Publishing attempted: no','']
    lines += [f"- {x['platform']} @{x['expected_handle']}: {x['identity']}" for x in report['targets']]
    out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    path=Path(os.environ.get('REPORT_PATH','reports/meta_12_preflight.json'));path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f"RESULT={report['result']} VERIFIED={report['identity_verified_count']}/12 PUBLISHING=NOT_ATTEMPTED")
if __name__=='__main__':main()