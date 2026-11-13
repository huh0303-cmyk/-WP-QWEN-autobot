"""Read-only article length audit for WP and Blogger published posts."""
import os,sys,json,re,html
from pathlib import Path
from datetime import datetime,timezone
import requests
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from fix_duplicate_hero_images_v2 import SITES
from publish_blogger_33_now import load_sites,access_token
SINCE=os.getenv('SINCE_DATE','2026-11-06')
OUT=ROOT/'artifacts'/'article-length-audit.json'
def count(content):
    soup=BeautifulSoup(content or '', 'html.parser')
    for tag in soup(['script','style']):tag.decompose()
    return len(re.sub(r'\s+','',html.unescape(soup.get_text(' ',strip=True))))
def main():
    report={'since':SINCE,'policy':{'min':2500,'max':3500},'wordpress':[],'blogger':[],'errors':[]}
    for site in SITES:
        domain=site['url']
        secret=os.getenv(site['wp_pass_env'],'')
        if not secret:
            report['errors'].append({'platform':'wordpress','site':domain,'error':'missing credentials'})
            continue
        endpoint=domain.rstrip('/')+'/wp-json/wp/v2/posts'
        for page in range(1,101):
            try:
                response=requests.get(endpoint,auth=(os.getenv('WP_USER','huh0303@gmail.com'),secret),params={'page':page,'per_page':100,'status':'publish','orderby':'date','order':'desc','_fields':'id,date,link,content'},timeout=30)
                if response.status_code==400 and page>1:break
                response.raise_for_status()
                batch=response.json()
                for post in batch:
                    if post.get('date','')[:10]<SINCE:continue
                    n=count(post.get('content',{}).get('rendered',''))
                    report['wordpress'].append({'site':domain,'id':post['id'],'url':post.get('link'),'chars':n,'status':'pass' if 2500<=n<=3500 else 'out_of_range'})
                if len(batch)<100 or (batch and batch[-1].get('date','')[:10]<SINCE):break
            except Exception as exc:
                report['errors'].append({'platform':'wordpress','site':domain,'error':str(exc)[:180]})
                break
    try:
        token=access_token()
        headers={'Authorization':'Bearer '+token}
        for site in load_sites():
            endpoint=f"https://www.googleapis.com/blogger/v3/blogs/{site['id']}/posts"
            page=None
            while True:
                try:
                    params={'maxResults':500,'fetchBodies':'true','status':'live'}
                    if page:params['pageToken']=page
                    response=requests.get(endpoint,headers=headers,params=params,timeout=40)
                    response.raise_for_status()
                    data=response.json()
                    for post in data.get('items',[]):
                        if post.get('published','')[:10]<SINCE:continue
                        n=count(post.get('content',''))
                        report['blogger'].append({'site':site['url'],'id':post['id'],'url':post.get('url'),'chars':n,'status':'pass' if 2500<=n<=3500 else 'out_of_range'})
                    page=data.get('nextPageToken')
                    if not page:break
                except Exception as exc:
                    report['errors'].append({'platform':'blogger','site':site['url'],'error':str(exc)[:180]})
                    break
    except Exception as exc:
        report['errors'].append({'platform':'blogger','error':str(exc)[:180]})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for platform in ('wordpress','blogger'):
        rows=report[platform]
        print(f"{platform}: scanned={len(rows)} passed={sum(x['status']=='pass' for x in rows)} out_of_range={sum(x['status']!='pass' for x in rows)}")
    print('errors=',len(report['errors']))
if __name__=='__main__':main()
