"""Remove duplicate hero/inline images from existing posts; keep IDs and text."""
import json,os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from editorial_image_guard import recent_posts,photo_url,image_fingerprint,same_photo
site=os.environ.get("REPAIR_SITE_URL","https://korea365.org").rstrip('/')
registry=json.loads(Path('config/automation_hub_sites.json').read_text(encoding='utf-8'))['sites']
entry=next(s for s in registry if s.get('url','').rstrip('/')==site)
auth=("huh0303@gmail.com",os.environ[entry['secret_name']])
posts=recent_posts(site,auth)
out=Path('artifacts/duplicate-image-repair');out.mkdir(parents=True,exist_ok=True)
known=[];results=[]
# Keep the oldest original; remove subsequent copies even if uploaded under new names.
for post in reversed(posts):
    url=photo_url(post)
    if not url:continue
    fp=image_fingerprint(url)
    duplicate=next((p for old,p in known if same_photo(fp,old)),None)
    if not duplicate:known.append((fp,post));continue
    record={'id':post['id'],'url':post['link'],'duplicates_post':duplicate['id'],'status':'identified'}
    results.append(record)
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    if os.getenv('APPLY_CHANGES')!='true':continue
    target=site+'/wp-json/wp/v2/posts/'+str(post['id'])
    r=requests.get(target,auth=auth,params={'context':'edit'},timeout=30);r.raise_for_status();current=r.json()
    if current['modified_gmt']!=post['modified_gmt']:raise RuntimeError('Concurrent edit; skipped')
    (out/(str(post['id'])+'-backup.json')).write_text(json.dumps(current,ensure_ascii=False),encoding='utf-8')
    soup=BeautifulSoup(current['content']['raw'],'html.parser')
    for img in list(soup.find_all('img')):
        src=img.get('src','')
        if src and same_photo(image_fingerprint(src),fp):
            parent=img.find_parent('figure')
            if parent:parent.decompose()
            else:img.decompose()
    payload={'featured_media':0,'content':str(soup)}
    r=requests.post(target,auth=auth,json=payload,timeout=30);r.raise_for_status()
    verify=requests.get(target,params={'context':'edit'},auth=auth,timeout=30);verify.raise_for_status()
    if verify.json().get('featured_media')!=0:raise RuntimeError('Hero removal not confirmed')
    if verify.json()['content']['raw']!=payload['content']:raise RuntimeError('Body save mismatch')
    record['status']='removed_verified'
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False))
