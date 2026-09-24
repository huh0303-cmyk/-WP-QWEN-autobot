#!/usr/bin/env python3
"""Schedule the locked ten YouTube channels for 2-3 private jobs per 7-day cycle."""
from __future__ import annotations
import hashlib,json,os,random,sys
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
ROOT=Path('/opt/korea365'); DATA=ROOT/'data'; KST=timezone(timedelta(hours=9)); EFFECTIVE=date(2026,9,26)
sys.path.insert(0,str(ROOT))
from automation_hub.youtube_vps_queue import enqueue
CHANNELS=[
 ('globalmusic','CAFE_ROMANTIC'),('healing','CAFE_HEALING'),('starbucks','CAFE_STARBUCKSVIBES'),
 ('mbb','CAFE_MOZART'),('kpop','CAFE_KPOP'),('nasa','NASA_XFILES'),('history','HISTORY_TV_TODAY'),
 ('invention','INVENTION_STORY1'),('silent_era','SILENT_ERA_FILM'),('retro_reels','RETRO_USA1')]

def atomic(path,payload):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)
def cycle_start(day):
 return EFFECTIVE+timedelta(days=max(0,(day-EFFECTIVE).days//7)*7)
def make_plan(start):
 rng=random.Random(int(hashlib.sha256(('youtube-private-10|'+start.isoformat()).encode()).hexdigest(),16)); rows=[]
 for key,name in CHANNELS:
  count=rng.choice((2,3));days=rng.sample(range(7),count)
  for d in days:
   minute=rng.randrange(0,1440);at=datetime.combine(start+timedelta(days=d),datetime.min.time(),tzinfo=KST)+timedelta(minutes=minute)
   rows.append({'channel_key':key,'name':name,'scheduled_at':at.isoformat(),'mode':'private_review_only','status':'planned','duplicate_key':f'{start}|{key}|{d}'})
 rows.sort(key=lambda x:x['scheduled_at']);return {'cycle_start':start.isoformat(),'cycle_end':(start+timedelta(days=6)).isoformat(),'publication':'private_only','slots':rows}
def main():
 now=datetime.now(KST)
 if now.date()<EFFECTIVE: print(json.dumps({'status':'waiting','effective':EFFECTIVE.isoformat()}));return 0
 start=cycle_start(now.date());path=DATA/'youtube-private-weekly'/f'{start}.json';plan=json.loads(path.read_text()) if path.exists() else make_plan(start)
 changed=not path.exists();dispatched=[]
 for row in plan['slots']:
  if row['status']!='planned':continue
  at=datetime.fromisoformat(row['scheduled_at'])
  if at<=now<at+timedelta(minutes=20):
   job=enqueue(row['channel_key'],row['name'],f"youtube_{row['channel_key']}",run_now=True)
   row.update(status='queued',job_id=job['job_id'],queued_at=now.isoformat());dispatched.append(row['channel_key']);changed=True
  elif now>=at+timedelta(minutes=20): row.update(status='missed',checked_at=now.isoformat());changed=True
 if changed: atomic(path,plan)
 print(json.dumps({'cycle':start.isoformat(),'slots':len(plan['slots']),'queued':dispatched,'private_only':True},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
