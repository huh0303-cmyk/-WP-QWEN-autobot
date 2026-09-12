"""Refresh only k-health sitemap settings when recent public URLs are missing."""
import os,json,requests,xml.etree.ElementTree as ET
from urllib.parse import unquote
SITE='https://k-health365.com'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
s=requests.Session();s.auth=('huh0303@gmail.com',os.environ['KHEALTH365COM'])
def get(url):
 r=s.get(url,timeout=30);r.raise_for_status();return r
def inventory():
 root=ET.fromstring(get(SITE+'/sitemap_index.xml').content)
 urls=[]
 for n in root.findall('s:sitemap/s:loc',NS):
  if not n.text.startswith(SITE+'/'):raise RuntimeError('foreign sitemap')
  if '/post-sitemap' not in n.text:continue
  tree=ET.fromstring(get(n.text).content)
  urls.extend(unquote(x.text).rstrip('/') for x in tree.findall('s:url/s:loc',NS))
 return set(urls)
posts=get(SITE+'/wp-json/wp/v2/posts?per_page=5&_fields=id,link').json()
expected={unquote(x['link']).rstrip('/') for x in posts}
before=inventory();print(json.dumps({'sitemap_urls_before':len(before),'recent_missing_before':sorted(expected-before)}))
if expected-before:
 endpoint=SITE+'/wp-json/rankmath/v1/updateSettings'
 # Empty field set returns current settings without changing any option.
 def save(settings):
  r=s.post(endpoint,json={'type':'sitemap','settings':settings,'fieldTypes':{'items_per_page':'text'},'updated':list(settings),'isReset':False},timeout=30)
  r.raise_for_status();data=r.json()
  if not isinstance(data,dict) or 'settings' not in data:raise RuntimeError('Unexpected Rank Math response')
  return data['settings']
 current=save({})
 if 'items_per_page' not in current:raise RuntimeError('Unknown sitemap page-size setting')
 original=current['items_per_page'];changed=int(original)+1
 try:
  updated=save({'items_per_page':str(changed)})
  if int(updated.get('items_per_page',0))!=changed:raise RuntimeError('Sitemap refresh setting not applied')
 finally:
  restored=save({'items_per_page':original})
  if str(restored.get('items_per_page'))!=str(original):raise RuntimeError('Sitemap setting restore failed')
after=inventory()
print(json.dumps({'sitemap_urls_after':len(after),'recent_missing_after':sorted(expected-after)}))
if expected-after:raise SystemExit('Recent posts still missing; sitemap refresh NOT verified')
