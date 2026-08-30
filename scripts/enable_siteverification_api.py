#!/usr/bin/env python3
import json, os, time
import requests, jwt
KEY=json.loads(os.environ['GSC_SERVICE_ACCOUNT_JSON'])
now=int(time.time())
assertion=jwt.encode({'iss':KEY['client_email'],'scope':'https://www.googleapis.com/auth/cloud-platform','aud':'https://oauth2.googleapis.com/token','iat':now,'exp':now+3600},KEY['private_key'],algorithm='RS256')
r=requests.post('https://oauth2.googleapis.com/token',data={'grant_type':'urn:ietf:params:oauth:grant-type:jwt-bearer','assertion':assertion},timeout=20)
r.raise_for_status(); tok=r.json()['access_token']
project_id=KEY.get('project_id')
url=f'https://serviceusage.googleapis.com/v1/projects/{project_id}/services/siteverification.googleapis.com:enable'
x=requests.post(url,headers={'Authorization':f'Bearer {tok}','Content-Type':'application/json'},json={},timeout=30)
print('project_id=',project_id,flush=True)
print('enable_http=',x.status_code,flush=True)
print(x.text[:2000],flush=True)
if x.status_code not in (200,201): raise SystemExit(2)
# Poll long-running operation when returned.
name=x.json().get('name') if x.content else None
if name:
    for i in range(18):
        time.sleep(5)
        p=requests.get(f'https://serviceusage.googleapis.com/v1/{name}',headers={'Authorization':f'Bearer {tok}'},timeout=20)
        print('poll',i,p.status_code,p.text[:500],flush=True)
        if p.status_code==200 and p.json().get('done'): break
