"""GitHub-hosted dispatcher; reserve each site/day/slot before dispatch."""
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from automation_hub.tistory_schedule import slot_minute, WINDOWS

def main():
    now=datetime.now(ZoneInfo('Asia/Seoul'));day=now.date().isoformat();minute=now.hour*60+now.minute
    repo=os.environ['GITHUB_REPOSITORY']
    session=requests.Session();session.headers.update({'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'})
    base='https://api.github.com/repos/'+repo
    cfg=json.loads(Path('config/tistory_portfolio.json').read_text(encoding='utf-8'))
    report=[]
    for site in cfg['sites']:
        if not site.get('launch_enabled'):continue
        for slot,(_,end) in WINDOWS.items():
            target=slot_minute(site['site_id'],day,slot)
            if not target<=minute<end:continue
            key=f'{day}-{slot}'
            path=f'data/tistory-slots/{day}/{site["site_id"]}-{slot}.json'
            endpoint=base+'/contents/'+path
            existing=session.get(endpoint,timeout=20)
            if existing.status_code==200:continue
            if existing.status_code!=404:existing.raise_for_status()
            receipt={'site_id':site['site_id'],'run_key':key,'scheduled_minute_kst':target,'reserved_at':now.isoformat(),'status':'reserved'}
            def write(status,sha=None):
                receipt['status']=status
                body={'message':f'Tistory {key} {site["site_id"]} {status} [skip ci]','content':base64.b64encode(json.dumps(receipt).encode()).decode(),'branch':'main'}
                if sha:body['sha']=sha
                return session.put(endpoint,json=body,timeout=30)
            reservation=write('reserved')
            if reservation.status_code in (409,422):continue
            reservation.raise_for_status();sha=reservation.json()['content']['sha']
            # An ambiguous dispatch is never blindly repeated (prevents duplicate paid generation).
            try:
                result=session.post(base+'/actions/workflows/tistory-daily-plan.yml/dispatches',json={'ref':'main','inputs':{'site_ids':site['site_id'],'run_key':key,'slot':slot}},timeout=30)
                result.raise_for_status()
                write('dispatched',sha).raise_for_status()
                report.append(receipt)
            except Exception:
                write('dispatch_attention_required',sha)
                raise
    print(json.dumps(report))
if __name__=='__main__':main()
