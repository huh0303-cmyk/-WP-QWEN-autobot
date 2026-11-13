"""Audit Blogger 33 posts since Nov 6 and remove repeated inline images only."""
import os, sys, json, re
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from publish_blogger_33_now import load_sites, access_token

SINCE=os.getenv('SINCE_DATE','2026-11-06')
DRY=os.getenv('DRY_RUN','true').lower()!='false'
OUT=ROOT/'artifacts'/'blogger-duplicate-image-cleanup.json'

def key(url):
    from urllib.parse import urlsplit,parse_qsl,urlunsplit,urlencode
    u=urlsplit(url.strip())
    # Strip CDN resize parameters, retaining identity-bearing paths.
    q=[(k,v) for k,v in parse_qsl(u.query) if k.lower() in ('id','photo','image')]
    return urlunsplit((u.scheme.lower(),u.netloc.lower(),u.path.rstrip('/'),urlencode(q),''))
def main():
    token=access_token()
    headers={'Authorization':'Bearer '+token}
    seen={}
    results=[]
    posts=[]
    for site in load_sites():
        endpoint=f"https://www.googleapis.com/blogger/v3/blogs/{site['id']}/posts"
        page=None
        while True:
            params={'maxResults':500,'fetchBodies':'true','status':'live'}
            if page:params['pageToken']=page
            try:
                response=requests.get(endpoint,params=params,headers=headers,timeout=45)
                response.raise_for_status()
                data=response.json()
            except Exception as exc:
                results.append({'site':site['key'],'status':'scan_error','error':str(exc)[:200]})
                break
            for post in data.get('items',[]):
                if post.get('published','')[:10]>=SINCE:
                    posts.append((site,endpoint,post))
            page=data.get('nextPageToken')
            if not page:break
    # Oldest eligible post keeps the image. Never delete text or entire articles.
    posts.sort(key=lambda row:row[2].get('published',''))
    for site,endpoint,post in posts:
        soup=BeautifulSoup(post.get('content',''),'html.parser')
        duplicates=[]
        for img in list(soup.find_all('img')):
            url=img.get('src','')
            if not url:continue
            identity=key(url)
            if identity in seen:
                duplicates.append({'image':url,'original':seen[identity]})
                if not DRY:
                    figure=img.find_parent('figure')
                    if figure:figure.decompose()
                    else:img.decompose()
            else:
                seen[identity]=post.get('url','')
        row={'site':site['key'],'post_id':post['id'],'url':post.get('url'),'duplicates':duplicates,'status':'clean' if not duplicates else 'identified'}
        if duplicates and not DRY:
            try:
                patch=requests.put(endpoint+'/'+post['id'],params={'revert':'false'},headers=headers,json={'content':str(soup)},timeout=45)
                patch.raise_for_status()
                verify=requests.get(endpoint+'/'+post['id'],headers=headers,timeout=30)
                verify.raise_for_status()
                current=BeautifulSoup(verify.json().get('content',''),'html.parser')
                if any(key(i.get('src',''))==key(d['image']) for d in duplicates for i in current.find_all('img')):
                    raise RuntimeError('duplicate remains after update')
                row['status']='removed_verified'
            except Exception as exc:
                row['status']='update_error';row['error']=str(exc)[:200]
        results.append(row)
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps({'since':SINCE,'dry_run':DRY,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'sites':len(set(x['site'] for x in results)),'posts':len(posts),'duplicates':sum(len(x.get('duplicates',[])) for x in results),'removed':sum(x['status']=='removed_verified' for x in results),'errors':sum(x['status'].endswith('error') for x in results)},ensure_ascii=False))
    if any(x['status'].endswith('error') for x in results):raise SystemExit(1)
if __name__=='__main__':main()
