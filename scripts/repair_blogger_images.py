#!/usr/bin/env python3
"""Audit Blogger image sources and replace broken ones with repository-hosted assets."""
from __future__ import annotations
import base64, hashlib, json, os, re, sys, time
from urllib.parse import urlparse
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'scripts'))
from replicate_image_provider import generate_image_url  # noqa:E402
OUT=ROOT/'artifacts/blogger-image-repair-results.json'
IMG_RE=re.compile(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'][^>]*>)',re.I)

def token():
 r=requests.post('https://oauth2.googleapis.com/token',data={'client_id':os.environ['BLOGGER_GOOGLE_CLIENT_ID'],'client_secret':os.environ['BLOGGER_GOOGLE_CLIENT_SECRET'],'refresh_token':os.environ['BLOGGER_GOOGLE_REFRESH_TOKEN'],'grant_type':'refresh_token'},timeout=30); r.raise_for_status(); return r.json()['access_token']

def image_check(url):
 try:
  r=requests.get(url,timeout=25,allow_redirects=True); ct=r.headers.get('content-type','').lower()
  return r.status_code==200 and ct.startswith('image/') and len(r.content)>500, {'http':r.status_code,'content_type':ct,'bytes':len(r.content),'final_url':r.url}
 except Exception as e: return False,{'error':str(e)[:300]}

def is_temporary(url):
 return urlparse(url).netloc.lower().endswith(('replicate.delivery','replicateusercontent.com'))

def upload_asset(repo,gh_token,blog_id,post_id,data,content_type):
 ext='.png' if 'png' in content_type else '.jpg' if 'jpeg' in content_type else '.webp'
 digest=hashlib.sha256(data).hexdigest()[:16]
 path=f'assets/blogger_images/{blog_id}/{post_id}-{digest}{ext}'; api=f'https://api.github.com/repos/{repo}/contents/{path}'
 payload={'message':f'fix: host Blogger image {post_id} [skip ci]','content':base64.b64encode(data).decode(),'branch':'main'}
 current=requests.get(api,headers={'Authorization':f'Bearer {gh_token}'},params={'ref':'main'},timeout=30)
 if current.status_code==200: return f'https://raw.githubusercontent.com/{repo}/main/{path}'
 r=requests.put(api,headers={'Authorization':f'Bearer {gh_token}','Accept':'application/vnd.github+json'},json=payload,timeout=60); r.raise_for_status()
 return f'https://raw.githubusercontent.com/{repo}/main/{path}'

def all_live_posts(endpoint,headers):
 token=None
 while True:
  params={'status':'live','view':'ADMIN','fetchBodies':'true','maxResults':500}
  if token: params['pageToken']=token
  response=requests.get(endpoint,headers=headers,params=params,timeout=30); response.raise_for_status()
  payload=response.json(); yield from payload.get('items',[])
  token=payload.get('nextPageToken')
  if not token: break

def stabilize_html_images(content,*,repo,gh_token,blog_id,asset_key):
 replacements={}; evidence=[]
 for _,src,_ in IMG_RE.findall(content):
  ok,ev=image_check(src); temporary=is_temporary(src)
  if ok and not temporary: evidence.append({'src':src,'status':'stable','evidence':ev}); continue
  data=b''; content_type=''
  if ok:
   download=requests.get(src,timeout=30); data=download.content; content_type=download.headers.get('content-type','')
  if not data:
   generated=generate_image_url(asset_key); valid,gev=image_check(generated or '')
   if not valid: raise RuntimeError(f'replacement generation invalid for {src}: {gev}')
   download=requests.get(generated,timeout=30); data=download.content; content_type=download.headers.get('content-type','')
  stable=upload_asset(repo,gh_token,blog_id,asset_key,data,content_type); valid,sev=False,{}
  for attempt in range(5):
   valid,sev=image_check(stable)
   if valid: break
   time.sleep(2**attempt)
  if not valid: raise RuntimeError(f'stable asset verification failed: {sev}')
  replacements[src]=stable; evidence.append({'src':src,'status':'temporary' if temporary else 'broken','evidence':ev,'stable_src':stable,'stable_evidence':sev})
 new=IMG_RE.sub(lambda m:m.group(1)+replacements.get(m.group(2),m.group(2))+m.group(3),content)
 return new,evidence

def main():
 profiles=json.loads((ROOT/'config/content_engine_profiles.json').read_text(encoding='utf-8'))['profiles']
 if len(profiles)!=33: raise SystemExit('scope guard requires 33 Blogger profiles')
 priority={'kwellness_lab':0,'kskin365':1}; profiles.sort(key=lambda p:(priority.get(p['site_key'],2),p['site_key']))
 auth={'Authorization':f'Bearer {token()}'}; repo=os.environ['GITHUB_REPOSITORY']; gh=os.environ['GH_ASSET_TOKEN']; rows=[]
 summary={'sites':33,'posts':0,'images':0,'normal_images':0,'temporary_images':0,'broken_images':0,'replaced_images':0,'normal_posts':0,'repaired_posts':0,'failed_posts':0}
 for p in profiles:
  bid=str(p['blogspot']['destination_id']); endpoint=f'https://www.googleapis.com/blogger/v3/blogs/{bid}/posts'
  site_rows=[]
  for post in all_live_posts(endpoint,auth):
   content=post.get('content',''); found=IMG_RE.findall(content)
   row={'site':p['site_key'],'blog_id':bid,'post_id':str(post['id']),'url':post.get('url',''),'images':len(found),'image_evidence':[],'issues':[],'status':'ok'}
   if found:
    try:
     new,evidence=stabilize_html_images(content,repo=repo,gh_token=gh,blog_id=bid,asset_key=str(post['id']))
     row['image_evidence']=evidence
     row['issues']=[e for e in evidence if e['status']!='stable']
     if new!=content:
      patch=requests.patch(f'{endpoint}/{post["id"]}',headers=auth,params={'revert':'false'},json={'content':new},timeout=30); patch.raise_for_status()
      verify=requests.get(f'{endpoint}/{post["id"]}',headers=auth,params={'view':'ADMIN'},timeout=30); verify.raise_for_status()
      verified_content=verify.json().get('content','')
      if any(e.get('stable_src') not in verified_content or e['src'] in verified_content for e in row['issues']):
       raise RuntimeError('Blogger patch re-read mismatch')
      row['status']='repaired'
    except Exception as e: row.update(status='failed',error=str(e)[:500])
   rows.append(row); site_rows.append(row); OUT.parent.mkdir(parents=True,exist_ok=True)
   evidence=[e for r in rows for e in r['image_evidence']]
   summary={'sites':33,'posts':len(rows),'images':sum(r['images'] for r in rows),'normal_images':sum(e['status']=='stable' for e in evidence),'temporary_images':sum(e['status']=='temporary' for e in evidence),'broken_images':sum(e['status']=='broken' for e in evidence),'replaced_images':sum(bool(e.get('stable_src')) for e in evidence),'normal_posts':sum(r['status']=='ok' for r in rows),'repaired_posts':sum(r['status']=='repaired' for r in rows),'failed_posts':sum(r['status']=='failed' for r in rows)}
   by_site={s:{'posts':sum(r['site']==s for r in rows),'images':sum(r['images'] for r in rows if r['site']==s),'normal_images':sum(e['status']=='stable' for r in rows if r['site']==s for e in r['image_evidence']),'replaced_images':sum(bool(e.get('stable_src')) for r in rows if r['site']==s for e in r['image_evidence']),'repaired_posts':sum(r['site']==s and r['status']=='repaired' for r in rows),'failed_posts':sum(r['site']==s and r['status']=='failed' for r in rows)} for s in {r['site'] for r in rows}}
   OUT.write_text(json.dumps({'summary':summary,'by_site':by_site,'records':rows},ensure_ascii=False,indent=2),encoding='utf-8')
   time.sleep(.3)
 print(json.dumps(summary,ensure_ascii=False))
 return 1 if any(r['status']=='failed' for r in rows) else 0
if __name__=='__main__': raise SystemExit(main())
