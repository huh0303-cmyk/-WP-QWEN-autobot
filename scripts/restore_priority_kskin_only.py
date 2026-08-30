#!/usr/bin/env python3
import json, os, sys, time
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from restore_indexed_private_posts import fetch_private_posts, inspect_url, publish, property_for, title_of, get_gsc_token, gsc_get
SITE="https://kskin365.com"; DOMAIN="kskin365.com"; SECRET="KSKIN365COM"; OUT="restore_priority_kskin_only_result.json"
def save(x):
    x['updated_at']=datetime.now(timezone.utc).isoformat()
    open(OUT,'w',encoding='utf-8').write(json.dumps(x,ensure_ascii=False,indent=2))
def main():
    res={"started_at":datetime.now(timezone.utc).isoformat(),"domain":DOMAIN,"private_before":0,"restored_indexed":0,"kept_private_unindexed":0,"kept_private_uncertain":0,"publish_failed":0,"items":[]}
    pw=os.getenv(SECRET,'').strip()
    if not pw: raise SystemExit(f'{SECRET} missing')
    tok=get_gsc_token(); r=gsc_get(tok,'/sites')
    if r.status_code!=200: raise SystemExit(f'GSC sites HTTP {r.status_code}')
    props={x.get('siteUrl') for x in r.json().get('siteEntry',[]) if x.get('siteUrl')}
    prop=property_for(DOMAIN,SITE,props); res['gsc_property']=prop
    if not prop: raise SystemExit('GSC property unavailable')
    posts=fetch_private_posts(SITE,pw); res['private_before']=len(posts); save(res)
    print(f'KSkin private={len(posts)}',flush=True)
    for p in posts:
        item={"id":p['id'],"url":p.get('link'),"title":title_of(p)}
        ins=inspect_url(tok,prop,p.get('link')); item['inspection']=ins
        if not ins.get('ok'):
            item['decision']='KEEP_PRIVATE_UNCERTAIN'; res['kept_private_uncertain']+=1
        elif ins.get('verdict')=='PASS':
            ok,code,detail=publish(SITE,pw,p['id'])
            if ok:
                item['decision']='RESTORED_PUBLISH_INDEXED'; res['restored_indexed']+=1
                print(f"RESTORED #{p['id']} {item['title'][:90]}",flush=True)
            else:
                item['decision']='RESTORE_FAILED'; item['http']=code; item['error']=detail; res['publish_failed']+=1
        else:
            item['decision']='KEEP_PRIVATE_UNINDEXED'; res['kept_private_unindexed']+=1
        res['items'].append(item); save(res); time.sleep(1.05)
    res['private_after_expected']=res['private_before']-res['restored_indexed']; res['finished_at']=datetime.now(timezone.utc).isoformat(); save(res)
    print(json.dumps({k:res[k] for k in ['private_before','restored_indexed','kept_private_unindexed','kept_private_uncertain','publish_failed','private_after_expected']},ensure_ascii=False),flush=True)
if __name__=='__main__': main()
