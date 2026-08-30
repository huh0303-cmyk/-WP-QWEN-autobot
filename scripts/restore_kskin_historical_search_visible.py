#!/usr/bin/env python3
"""Restore KSkin private posts that had Google Search Console search visibility before the 2026-08-26 forced reset.
Evidence rule: page URL had impressions or clicks in Search Analytics through 2026-08-25.
"""
import json, os, sys
from datetime import datetime, timezone
from urllib.parse import urlsplit
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from restore_indexed_private_posts import fetch_private_posts, publish
from daily_site_traffic import get_gsc_token, gsc_post

SITE='https://kskin365.com'; PROP='sc-domain:kskin365.com'; SECRET='KSKIN365COM'; OUT='restore_kskin_historical_search_visible_result.json'

def norm(u):
    try:
        p=urlsplit(u or '')
        host=(p.hostname or '').lower().removeprefix('www.')
        path=p.path or '/'
        if not path.endswith('/'): path += '/'
        return f'https://{host}{path}'
    except Exception: return (u or '').strip()

def save(x):
    x['updated_at']=datetime.now(timezone.utc).isoformat()
    with open(OUT,'w',encoding='utf-8') as f: json.dump(x,f,ensure_ascii=False,indent=2)

def main():
    pw=os.getenv(SECRET,'').strip()
    if not pw: raise SystemExit(f'{SECRET} missing')
    tok=get_gsc_token()
    body={
      'startDate':'2025-04-01','endDate':'2026-08-25','dimensions':['page'],
      'rowLimit':25000,'dataState':'final'
    }
    ep=f"/sites/{requests.utils.quote(PROP,safe='')}/searchAnalytics/query"
    r=gsc_post(tok,ep,body)
    if r.status_code!=200: raise SystemExit(f'GSC searchAnalytics HTTP {r.status_code}: {r.text[:300]}')
    rows=r.json().get('rows',[])
    visible={}
    for row in rows:
        keys=row.get('keys') or []
        if not keys: continue
        url=norm(keys[0]); imp=float(row.get('impressions',0) or 0); clk=float(row.get('clicks',0) or 0)
        if imp>0 or clk>0:
            visible[url]={'url':keys[0],'impressions':imp,'clicks':clk,'ctr':row.get('ctr'),'position':row.get('position')}
    priv=fetch_private_posts(SITE,pw)
    result={'started_at':datetime.now(timezone.utc).isoformat(),'gsc_property':PROP,'evidence_window':['2025-04-01','2026-08-25'],
            'gsc_visible_pages':len(visible),'private_before':len(priv),'matched_private':0,'restored':0,'failed':0,'items':[]}
    save(result)
    for p in priv:
        key=norm(p.get('link')); ev=visible.get(key)
        if not ev: continue
        result['matched_private']+=1
        ok,code,detail=publish(SITE,pw,p['id'])
        item={'id':p['id'],'url':p.get('link'),'title':(p.get('title') or {}).get('rendered','') if isinstance(p.get('title'),dict) else str(p.get('title') or ''),'evidence':ev}
        if ok:
            item['decision']='RESTORED_PUBLISH_HISTORICAL_GSC_VISIBLE'; result['restored']+=1
            print(f"RESTORED #{p['id']} impressions={ev['impressions']} clicks={ev['clicks']} {item['title'][:80]}",flush=True)
        else:
            item['decision']='RESTORE_FAILED'; item['http']=code; item['error']=detail; result['failed']+=1
        result['items'].append(item); save(result)
    result['private_after_expected']=result['private_before']-result['restored']; result['finished_at']=datetime.now(timezone.utc).isoformat(); save(result)
    print(json.dumps({k:result[k] for k in ['gsc_visible_pages','private_before','matched_private','restored','failed','private_after_expected']},ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__': main()
