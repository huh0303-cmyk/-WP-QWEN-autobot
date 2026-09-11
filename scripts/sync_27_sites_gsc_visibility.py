#!/usr/bin/env python3
"""Audit every publish/private WP post across all 27 sites and sync visibility to GSC.
PASS => publish; confirmed non-PASS => private; API/quota/permission uncertainty => NO CHANGE.
"""
import json, os, socket, sys, time
from pathlib import Path
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_registry import ACTIVE_SITES

WP_USER=os.getenv('WP_USER','').strip() or 'huh0303@gmail.com'
SITE_FILTER=os.getenv('SITE_FILTER','').strip().lower()
OUT=Path(f'sync_gsc_27_{SITE_FILTER}.json' if SITE_FILTER else 'sync_gsc_27_result.json')
_getaddrinfo=socket.getaddrinfo
socket.getaddrinfo=lambda host,port,family=0,type=0,proto=0,flags=0:_getaddrinfo(host,port,socket.AF_INET,type,proto,flags)

def token():
 r=requests.post('https://oauth2.googleapis.com/token',data={'client_id':os.environ['GOOGLE_METRICS_CLIENT_ID'],'client_secret':os.environ['GOOGLE_METRICS_CLIENT_SECRET'],'refresh_token':os.environ['GOOGLE_METRICS_REFRESH_TOKEN'],'grant_type':'refresh_token'},timeout=30); r.raise_for_status(); return r.json()['access_token']
def props(t):
 r=requests.get('https://www.googleapis.com/webmasters/v3/sites',headers={'Authorization':f'Bearer {t}'},timeout=30); r.raise_for_status(); return {x['siteUrl'] for x in r.json().get('siteEntry',[])}
def prop_for(site,ps):
 d=site.removeprefix('https://').rstrip('/')
 for c in (f'sc-domain:{d}',site.rstrip('/')+'/',site.rstrip('/')):
  if c in ps:return c
def posts(site,pw):
 out=[]; page=1
 while True:
  r=requests.get(f'{site}/wp-json/wp/v2/posts',auth=(WP_USER,pw),params={'context':'edit','status':'publish,private','per_page':100,'page':page,'orderby':'id','order':'asc','_fields':'id,link,status,title'},timeout=40)
  if r.status_code==400 and 'rest_post_invalid_page_number' in r.text:break
  r.raise_for_status(); b=r.json(); out+=b
  if len(b)<100:break
  page+=1
 return out
def inspect(t,p,url):
 for a in range(4):
  r=requests.post('https://searchconsole.googleapis.com/v1/urlInspection/index:inspect',headers={'Authorization':f'Bearer {t}','Content-Type':'application/json'},json={'inspectionUrl':url,'siteUrl':p},timeout=35)
  if r.status_code==200:
   x=r.json().get('inspectionResult',{}).get('indexStatusResult',{}); return {'ok':True,'verdict':x.get('verdict'),'coverageState':x.get('coverageState'),'googleCanonical':x.get('googleCanonical'),'userCanonical':x.get('userCanonical'),'lastCrawlTime':x.get('lastCrawlTime')}
  if r.status_code==429: time.sleep(10*(a+1)); continue
  return {'ok':False,'error':f'HTTP {r.status_code}: {r.text[:180]}'}
 return {'ok':False,'error':'quota retries exhausted'}
def set_status(site,pw,pid,status):
 r=requests.post(f'{site}/wp-json/wp/v2/posts/{pid}',auth=(WP_USER,pw),json={'status':status},timeout=40); return r.status_code in (200,201),r.status_code,r.text[:180]
def save(x): OUT.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 if os.getenv('CONFIRM')!='SYNC-27-GSC-VISIBILITY': raise SystemExit('exact confirmation required')
 targets=list(ACTIVE_SITES)
 if len(targets)!=27: raise SystemExit(f'scope guard: expected 27, got {len(targets)}')
 if SITE_FILTER:
  targets=[x for x in targets if x[0].removeprefix('https://').rstrip('/')==SITE_FILTER]
  if len(targets)!=1: raise SystemExit(f'bad site filter: {SITE_FILTER}')
 t=token(); ps=props(t); result={'policy':'GSC PASS=>publish; confirmed non-PASS=>private; uncertainty=>unchanged','sites':{}}
 for site,secret,_ in targets:
  site=site.rstrip('/'); d=site.removeprefix('https://'); pw=os.getenv(secret,'').strip(); p=prop_for(site,ps)
  s={'property':p,'posts_checked':0,'published':0,'privated':0,'kept':0,'uncertain':0,'failed':0,'items':[]}; result['sites'][d]=s; save(result)
  if not pw or not p: s['error']='missing WordPress secret' if not pw else 'missing GSC property'; save(result); continue
  try: pp=posts(site,pw)
  except Exception as e: s['error']=f'inventory failed: {e}'; save(result); continue
  s['posts_checked']=len(pp)
  for post in pp:
   ev=inspect(t,p,post['link']); desired=('publish' if ev.get('ok') and ev.get('verdict')=='PASS' else ('private' if ev.get('ok') else None))
   item={'id':post['id'],'url':post['link'],'before':post['status'],'desired':desired,'inspection':ev}
   if desired is None:s['uncertain']+=1
   elif desired==post['status']:s['kept']+=1
   else:
    ok,code,detail=set_status(site,pw,post['id'],desired)
    if ok:s['published' if desired=='publish' else 'privated']+=1
    else:s['failed']+=1; item.update({'http':code,'error':detail})
   s['items'].append(item); save(result); time.sleep(1.1)
 result['totals']={k:sum(s.get(k,0) for s in result['sites'].values()) for k in ('posts_checked','published','privated','kept','uncertain','failed')}; save(result); print(json.dumps(result['totals'],ensure_ascii=False))
if __name__=='__main__':main()
