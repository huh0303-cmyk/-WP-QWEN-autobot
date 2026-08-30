#!/usr/bin/env python3
"""Verify oliveyoungkorea.com for the GSC service account, then restore private posts with strong Google evidence.

Evidence for restoration:
1) current URL Inspection verdict == PASS, OR
2) Search Analytics page had impressions/clicks on or before 2026-08-25.
Never restores a post without Google evidence.
"""
import json, os, sys, time
from datetime import datetime, timezone
from urllib.parse import urlsplit
import requests, jwt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from restore_indexed_private_posts import fetch_private_posts, publish, inspect_url

SITE='https://oliveyoungkorea.com'
SITE_SLASH='https://oliveyoungkorea.com/'
DOMAIN='oliveyoungkorea.com'
SECRET='OLIVEYOUNGKOREACOM'
OUT='verify_and_restore_oliveyoung_result.json'
WP_USER=os.getenv('WP_USER','').strip() or 'huh0303@gmail.com'
GSC_JSON=os.getenv('GSC_SERVICE_ACCOUNT_JSON','')

def save(x):
    x['updated_at']=datetime.now(timezone.utc).isoformat()
    with open(OUT,'w',encoding='utf-8') as f: json.dump(x,f,ensure_ascii=False,indent=2)

def norm(u):
    p=urlsplit(u or '')
    host=(p.hostname or '').lower().removeprefix('www.')
    path=p.path or '/'
    if not path.endswith('/'): path+='/'
    return f'https://{host}{path}'

def google_token():
    key=json.loads(GSC_JSON); now=int(time.time())
    scopes='https://www.googleapis.com/auth/siteverification https://www.googleapis.com/auth/webmasters'
    assertion=jwt.encode({'iss':key['client_email'],'scope':scopes,'aud':'https://oauth2.googleapis.com/token','iat':now,'exp':now+3600},key['private_key'],algorithm='RS256')
    r=requests.post('https://oauth2.googleapis.com/token',data={'grant_type':'urn:ietf:params:oauth:grant-type:jwt-bearer','assertion':assertion},timeout=20)
    r.raise_for_status(); return r.json()['access_token'], key['client_email']

def deploy_file(pw, token_name):
    name='GSC service account verification file serve'
    php=f"""
add_action('init', function () {{
    if ($_SERVER['REQUEST_URI'] === '/{token_name}' || strpos($_SERVER['REQUEST_URI'], '/{token_name}?') === 0) {{
        header('Content-Type: text/html; charset=utf-8');
        echo 'google-site-verification: {token_name}';
        exit;
    }}
}}, 1);
"""
    base=f'{SITE}/wp-json/code-snippets/v1'
    auth=(WP_USER,pw)
    r=requests.get(f'{base}/snippets',auth=auth,params={'per_page':100},timeout=40)
    r.raise_for_status(); data=r.json()
    rows=data if isinstance(data,list) else data.get('data',data.get('items',[]))
    matches=[s for s in rows if s.get('name')==name]
    payload={'name':name,'desc':f'Serves /{token_name} for service-account GSC verification.','code':php,'scope':'global','active':True,'priority':1,'tags':['gsc','verification','service-account']}
    if matches:
        x=requests.post(f"{base}/snippets/{matches[0]['id']}",auth=auth,json=payload,timeout=40)
    else:
        x=requests.post(f'{base}/snippets',auth=auth,json=payload,timeout=40)
    x.raise_for_status()
    check=requests.get(f'{SITE}/{token_name}',timeout=25)
    return {'http':check.status_code,'body':check.text[:200]}

def main():
    result={'started_at':datetime.now(timezone.utc).isoformat(),'domain':DOMAIN,'verification':{},'restore':{}}
    save(result)
    if not GSC_JSON: raise SystemExit('GSC_SERVICE_ACCOUNT_JSON missing')
    pw=os.getenv(SECRET,'').strip()
    if not pw: raise SystemExit(f'{SECRET} missing')
    tok,email=google_token(); result['service_account']=email; save(result)
    headers={'Authorization':f'Bearer {tok}','Content-Type':'application/json'}

    # 1) Get service-account-specific FILE verification token.
    req={'verificationMethod':'FILE','site':{'identifier':SITE_SLASH,'type':'SITE'}}
    r=requests.post('https://www.googleapis.com/siteVerification/v1/token',headers=headers,json=req,timeout=30)
    result['verification']['get_token_http']=r.status_code; result['verification']['get_token_body']=r.text[:500]; save(result)
    if r.status_code!=200: raise SystemExit(f'siteVerification getToken HTTP {r.status_code}: {r.text[:500]}')
    token_name=r.json().get('token','').strip()
    if not token_name.endswith('.html'): raise SystemExit(f'unexpected FILE token: {token_name}')
    result['verification']['token_file']=token_name

    # 2) Put verification file at the site root through Code Snippets.
    result['verification']['file_check']=deploy_file(pw,token_name); save(result)
    if result['verification']['file_check']['http']!=200: raise SystemExit('verification file not reachable')

    # 3) Verify ownership for this service account.
    body={'site':{'identifier':SITE_SLASH,'type':'SITE'}}
    v=requests.post('https://www.googleapis.com/siteVerification/v1/webResource',headers=headers,params={'verificationMethod':'FILE'},json=body,timeout=30)
    result['verification']['insert_http']=v.status_code; result['verification']['insert_body']=v.text[:1000]; save(result)
    if v.status_code not in (200,201): raise SystemExit(f'siteVerification insert HTTP {v.status_code}: {v.text[:500]}')

    # 4) Add URL-prefix property to Search Console if needed.
    q=requests.utils.quote(SITE_SLASH,safe='')
    add=requests.put(f'https://www.googleapis.com/webmasters/v3/sites/{q}',headers={'Authorization':f'Bearer {tok}'},timeout=30)
    result['verification']['search_console_add_http']=add.status_code; result['verification']['search_console_add_body']=add.text[:500]
    sites=requests.get('https://www.googleapis.com/webmasters/v3/sites',headers={'Authorization':f'Bearer {tok}'},timeout=30)
    result['verification']['gsc_sites_http']=sites.status_code
    accessible={x.get('siteUrl') for x in sites.json().get('siteEntry',[])} if sites.status_code==200 else set()
    result['verification']['property_accessible']=SITE_SLASH in accessible or SITE in accessible or f'sc-domain:{DOMAIN}' in accessible
    save(result)
    if not result['verification']['property_accessible']: raise SystemExit('Search Console property still not accessible after verification')
    prop=SITE_SLASH if SITE_SLASH in accessible else (SITE if SITE in accessible else f'sc-domain:{DOMAIN}')
    result['verification']['gsc_property']=prop

    # 5) Historical Search Analytics evidence through the day before forced reset.
    ep=f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(prop,safe='')}/searchAnalytics/query"
    hist_body={'startDate':'2025-04-01','endDate':'2026-08-25','dimensions':['page'],'rowLimit':25000,'dataState':'final'}
    hr=requests.post(ep,headers=headers,json=hist_body,timeout=40)
    result['restore']['historical_query_http']=hr.status_code; save(result)
    visible={}
    if hr.status_code==200:
        for row in hr.json().get('rows',[]):
            keys=row.get('keys') or []
            if not keys: continue
            imp=float(row.get('impressions',0) or 0); clk=float(row.get('clicks',0) or 0)
            if imp>0 or clk>0:
                visible[norm(keys[0])]={'url':keys[0],'impressions':imp,'clicks':clk,'ctr':row.get('ctr'),'position':row.get('position')}
    result['restore']['historically_visible_pages']=len(visible)

    priv=fetch_private_posts(SITE,pw)
    result['restore'].update({'private_before':len(priv),'restored':0,'historical_matches':0,'current_pass_matches':0,'failed':0,'kept_private_no_google_evidence':0,'items':[]}); save(result)
    for p in priv:
        url=p.get('link'); key=norm(url); hist=visible.get(key)
        current=None; current_pass=False
        if not hist:
            current=inspect_url(tok,prop,url)
            current_pass=bool(current.get('ok') and current.get('verdict')=='PASS')
        if hist or current_pass:
            ok,code,detail=publish(SITE,pw,p['id'])
            item={'id':p['id'],'url':url,'title':(p.get('title') or {}).get('rendered','') if isinstance(p.get('title'),dict) else str(p.get('title') or ''),'historical_evidence':hist,'current_inspection':current}
            if hist: result['restore']['historical_matches']+=1
            if current_pass: result['restore']['current_pass_matches']+=1
            if ok:
                item['decision']='RESTORED_PUBLISH_GOOGLE_EVIDENCE'; result['restore']['restored']+=1
                print(f"RESTORED #{p['id']} {item['title'][:90]}",flush=True)
            else:
                item['decision']='RESTORE_FAILED'; item['http']=code; item['error']=detail; result['restore']['failed']+=1
            result['restore']['items'].append(item); save(result)
        else:
            result['restore']['kept_private_no_google_evidence']+=1
    result['restore']['private_after_expected']=result['restore']['private_before']-result['restore']['restored']
    result['finished_at']=datetime.now(timezone.utc).isoformat(); save(result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__': main()
