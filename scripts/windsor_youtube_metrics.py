import json,datetime,requests,sys,os
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,'/opt/korea365/scripts');import account_schedule_runner as q
root=Path('/opt/korea365/data');cfg=json.loads(Path('/etc/korea365/windsor-analytics.json').read_text(encoding='utf-8-sig'))
now=datetime.datetime.now(ZoneInfo('America/Los_Angeles'));day=(now.date()-datetime.timedelta(days=1)).isoformat();prev=(now.date()-datetime.timedelta(days=2)).isoformat();checked=datetime.datetime.now(q.KST).isoformat()
try:
 r=requests.get('https://connectors.windsor.ai/youtube',params={'date_preset':'last_7d','fields':'date,datasource,account_name,source,views,channel_id,channel_title','select_accounts':','.join(map(str,cfg['account_ids'])),'api_key':cfg['api_key']},timeout=90)
 if not r.ok:raise ValueError('HTTP_'+str(r.status_code))
 rows=r.json()['data'];assert isinstance(rows,list);group={}
 for x in rows:
  cid=x.get('channel_id');date=x.get('date');v=x.get('views')
  if not cid or not cid.startswith('UC') or not date or not isinstance(v,(int,float)):continue
  g=group.setdefault(cid,{'title':x.get('channel_title'),'days':{}})
  if date in g['days']:raise ValueError('Duplicate_channel_day')
  g['days'][date]=int(v)
 data=q.load(root/'account-audience-metrics.json',{'accounts':{}})
 for cid,g in group.items():
  dates=sorted(g['days']);latest=dates[-1];a=data['accounts'].setdefault(cid,{'identity':cid});a.update(analytics_connected=True,analytics_source='Windsor.ai',date=day,timezone='America/Los_Angeles',checked_at=checked,views=g['days'].get(day),delta=g['days'][day]-g['days'][prev] if day in g['days'] and prev in g['days'] else None,latest_available_date=latest,latest_available_views=g['days'][latest],verified_channel_title=g['title'],error='' if day in g['days'] else '연결 정상 · 전날 집계 대기 (최근 '+latest+': '+str(g['days'][latest])+'회)')
 data['checked_at']=checked;q.save(root/'account-audience-metrics.json',data)
 proof={'checked_at':checked,'http':200,'connected_accounts':len(cfg['account_ids']),'verified_channels':{k:v['title'] for k,v in group.items()},'rows':len(rows),'dates':sorted({x['date'] for x in rows}),'daily_available':sum(day in g['days'] for g in group.values())};q.save(root/'windsor-youtube-connection-proof.json',proof);print(json.dumps(proof,ensure_ascii=True))
except Exception as e:
 print('Windsor collection failed:',type(e).__name__);sys.exit(1)
