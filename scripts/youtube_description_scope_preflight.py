"""Read-only preflight for YouTube video-description metadata update scope."""
import os
import requests

profile=os.environ['PROFILE']
values={k:os.environ.get(k,'') for k in ('CLIENT_ID','CLIENT_SECRET','REFRESH_TOKEN','EXPECTED_CHANNEL_ID')}
if not all(values.values()):
    raise RuntimeError(f'{profile}: missing OAuth configuration')
r=requests.post('https://oauth2.googleapis.com/token',data={
    'client_id':values['CLIENT_ID'],'client_secret':values['CLIENT_SECRET'],
    'refresh_token':values['REFRESH_TOKEN'],'grant_type':'refresh_token'},timeout=30)
if not r.ok:
    raise RuntimeError(f'{profile}: refresh rejected HTTP {r.status_code}: {r.text[:300]}')
data=r.json(); scopes=set(data.get('scope','').split())
required={'https://www.googleapis.com/auth/youtube','https://www.googleapis.com/auth/youtube.force-ssl'}
if not scopes.intersection(required):
    raise RuntimeError(f'{profile}: upload credential works but lacks YouTube metadata-update scope; granted={sorted(scopes)}')
r=requests.get('https://www.googleapis.com/youtube/v3/channels',params={'part':'id','mine':'true'},headers={'Authorization':'Bearer '+data['access_token']},timeout=30)
if not r.ok:
    raise RuntimeError(f'{profile}: channel identity check rejected HTTP {r.status_code}')
ids={x['id'] for x in r.json().get('items',[])}
if values['EXPECTED_CHANNEL_ID'] not in ids:
    raise RuntimeError(f'{profile}: OAuth channel does not match expected channel ID')
print(f'{profile}: exact channel verified; YouTube metadata-update scope granted; no videos modified')
