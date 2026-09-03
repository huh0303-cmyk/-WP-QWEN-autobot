#!/usr/bin/env python3
"""Audit Blogger image sources and replace broken ones with repository-hosted assets."""
from __future__ import annotations
import base64, hashlib, json, os, re, sys, time
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

def upload_asset(repo,gh_token,blog_id,post_id,data,content_type):
 ext='.png' if 'png' in content_type else '.jpg' if 'jpeg' in content_type else '.webp'
 path=f'assets/blogger_images/{blog_id}/{post_id}{ext}'; api=f'https://api.github.com/repos/{repo}/contents/{path}'
 payload={'message':f'fix: host Blogger image {post_id} [skip ci]','content':base64.b64encode(data).decode(),'branch':'main'}
 current=requests.get(api,headers={'Authorization':f'Bearer {gh_token}'},params={'ref':'main'},timeout=30)
 if current.status_code==200: payload['sha']=current.json()['sha']
 r=requests.put(api,headers={'Authorization':f'Bearer {gh_token}','Accept':'application/vnd.github+json'},json=payload,timeout=60); r.raise_for_status()
 return f'https://raw.githubusercontent.com/{repo}/main/{path}'

def main():
 profiles=json.loads((ROOT/'config/content_engine_profiles.json').read_text(encoding='utf-8'))['profiles']
 if len(profiles)!=33: raise SystemExit('scope guard requires 33 Blogger profiles')
 priority={'kwellness_lab':0,'kskin365':1}; profiles.sort(key=lambda p:(priority.get(p['site_key'],2),p['site_key']))
 auth={'Authorization':f'Bearer {token()}'}; repo=os.environ['GITHUB_REPOSITORY']; gh=os.environ['GH_ASSET_TOKEN']; rows=[]
 for p in profiles:
  bid=str(p['blogspot']['destination_id']); endpoint=f'https://www.googleapis.com/blogger/v3/blogs/{bid}/posts'
  listing=requests.get(endpoint,headers=auth,params={'status':'live','view':'ADMIN','fetchBodies':'true','maxResults':int(os.getenv('BLOGGER_RECENT_LIMIT','10'))},timeout=30); listing.raise_for_status()
  for post in listing.json().get('items',[]):
   content=post.get('content',''); found=IMG_RE.findall(content); broken=[]
   for _,src,_ in found:
    ok,evidence=image_check(src)
    if not ok: broken.append({'src':src,'evidence':evidence,'reason':'temporary_replicate_url' if 'replicate.delivery' in src else 'unreachable_or_non_image'})
   row={'site':p['site_key'],'blog_id':bid,'post_id':str(post['id']),'url':post.get('url',''),'images':len(found),'broken':broken,'status':'ok'}
   if broken:
    try:
     generated=generate_image_url(post.get('title',''),theme=p['wordpress']['theme']); ok,ev=image_check(generated or '')
     if not ok: raise RuntimeError(f'replacement generation invalid: {ev}')
     blob=requests.get(generated,timeout=30).content; stable=upload_asset(repo,gh,bid,str(post['id']),blob,ev['content_type']); ok,sev=image_check(stable)
     if not ok: raise RuntimeError(f'stable asset verification failed: {sev}')
     bad={b['src'] for b in broken}; new=IMG_RE.sub(lambda m:m.group(1)+stable+m.group(3) if m.group(2) in bad else m.group(0),content)
     patch=requests.patch(f'{endpoint}/{post["id"]}',headers=auth,params={'revert':'false'},json={'content':new},timeout=30); patch.raise_for_status()
     verify=requests.get(f'{endpoint}/{post["id"]}',headers=auth,params={'view':'ADMIN'},timeout=30); verify.raise_for_status()
     if stable not in verify.json().get('content',''): raise RuntimeError('Blogger patch re-read mismatch')
     row.update(status='repaired',stable_src=stable,stable_evidence=sev)
    except Exception as e: row.update(status='failed',error=str(e)[:500])
   rows.append(row); OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps({'records':rows},ensure_ascii=False,indent=2),encoding='utf-8')
   time.sleep(.3)
 print(json.dumps({'audited':len(rows),'broken':sum(bool(r['broken']) for r in rows),'repaired':sum(r['status']=='repaired' for r in rows),'failed':sum(r['status']=='failed' for r in rows)},ensure_ascii=False))
 return 1 if any(r['status']=='failed' for r in rows) else 0
if __name__=='__main__': raise SystemExit(main())
