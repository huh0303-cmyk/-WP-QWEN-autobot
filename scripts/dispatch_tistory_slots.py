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
from automation_hub.tistory_schedule import random_daily_selection

def main():
    now=datetime.now(ZoneInfo('Asia/Seoul'));day=now.date().isoformat();minute=now.hour*60+now.minute
    repo=os.environ['GITHUB_REPOSITORY']
    session=requests.Session();session.headers.update({'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'})
    base='https://api.github.com/repos/'+repo
    cfg=json.loads(Path('config/tistory_portfolio.json').read_text(encoding='utf-8'))
    eligible=[site for site in cfg['sites'] if site.get('launch_enabled')]
    selection_path=f'data/tistory-slots/{day}/selection.json'
    selection_endpoint=base+'/contents/'+selection_path
    existing_selection=session.get(selection_endpoint,timeout=20)
    if existing_selection.status_code==200:
        selection=json.loads(base64.b64decode(existing_selection.json()['content']).decode())
    else:
        if existing_selection.status_code!=404: existing_selection.raise_for_status()
        selection={
            'date':day,
            'timezone':'Asia/Seoul',
            'network_daily_posts':int(cfg.get('network_daily_posts',3)),
            'created_at':now.isoformat(),
            'jobs':random_daily_selection(
                [site['site_id'] for site in eligible],
                int(cfg.get('network_daily_posts',3)),
            ),
        }
        create=session.put(selection_endpoint,json={
            'message':f'Tistory {day} random three-site selection [skip ci]',
            'content':base64.b64encode(json.dumps(selection,ensure_ascii=False).encode()).decode(),
            'branch':'main',
        },timeout=30)
        if create.status_code in (409,422):
            reread=session.get(selection_endpoint,timeout=20);reread.raise_for_status()
            selection=json.loads(base64.b64decode(reread.json()['content']).decode())
        else:
            create.raise_for_status()
    report=[]
    for selected in selection['jobs']:
            site=next(site for site in eligible if site['site_id']==selected['site_id'])
            target=int(selected['scheduled_minute_kst'])
            if minute<target:continue
            key=f'{day}-random3-{site["site_id"]}'
            path=f'data/tistory-slots/{day}/{site["site_id"]}-random3.json'
            endpoint=base+'/contents/'+path
            existing=session.get(endpoint,timeout=20)
            if existing.status_code==200:continue
            if existing.status_code!=404:existing.raise_for_status()
            receipt={'site_id':site['site_id'],'run_key':key,'scheduled_minute_kst':target,'scheduled_local_time':selected['scheduled_local_time'],'reserved_at':now.isoformat(),'status':'reserved'}
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
                result=session.post(base+'/actions/workflows/tistory-daily-plan.yml/dispatches',json={'ref':'main','inputs':{'site_ids':site['site_id'],'run_key':key,'slot':'daily','scheduled_local_time':selected['scheduled_local_time']}},timeout=30)
                result.raise_for_status()
                write('dispatched',sha).raise_for_status()
                report.append(receipt)
            except Exception:
                write('dispatch_attention_required',sha)
                raise
    print(json.dumps(report))
if __name__=='__main__':main()
