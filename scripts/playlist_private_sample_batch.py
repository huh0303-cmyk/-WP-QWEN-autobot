"""Sequential sample batch with durable calendar identity; never publish publicly."""
import os, sys, time, random, json, datetime as dt
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from automation_hub.youtube_calendar import read_calendar, update_row, select_next_ready, KST
from youtube_calendar_dispatch import main as dispatch, youtube_worker_active
from gsheets_direct import get_sheets_service

ORDER=['healing','kpop','globalmusic','mbb','starbucks']

def main():
    service=get_sheets_service();sid=os.environ['SHEET_ID']
    batch=os.environ.get('SAMPLE_BATCH_ID','playlist-samples-20260907')
    results=[];deadline=time.monotonic()+5*60*60
    for channel in ORDER:
        marker=f'[sample-batch:{batch}:{channel}]'
        while time.monotonic()<deadline:
            rows=read_calendar(service,sid)
            row=next((r for r in rows if marker in r['notes']),None)
            if row and row['status']=='비공개 업로드' and row['url']:
                results.append({'channel':channel,'status':'private_verified','url':row['url']});break
            if row and row['status']=='실패':
                results.append({'channel':channel,'status':'failed','schedule_id':row['id'],'notes':row['notes']});break
            if not youtube_worker_active(os.environ['GITHUB_REPOSITORY'],os.environ['GH_DISPATCH_TOKEN'],['generate-youtube-playlist.yml','curio-longform-daily.yml']):
                if not row:
                    ready,_=select_next_ready(rows,dt.datetime.now(KST),{channel},1)
                    if not ready:
                        results.append({'channel':channel,'status':'no_ready_calendar_item'});break
                    row=ready[0]
                    update_row(service,sid,row,row['status'],row['url'],row['notes']+'\n'+marker)
                if row['status']=='기획확정·자료준비':
                    os.environ.update(TARGET_CHANNEL_KEY=channel,RUN_SELECTED_NOW='true',DRY_RUN='false',MAX_DISPATCH='1')
                    dispatch()
            time.sleep(45)
        else:
            results.append({'channel':channel,'status':'timeout_needs_reconciliation'})
        Path('artifacts').mkdir(exist_ok=True)
        Path('artifacts/playlist-private-samples.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(results[-1],ensure_ascii=False),flush=True)
        if channel!=ORDER[-1]: time.sleep(random.randint(11,23)*60)
    return int(any(r['status']!='private_verified' for r in results))
if __name__=='__main__':raise SystemExit(main())
