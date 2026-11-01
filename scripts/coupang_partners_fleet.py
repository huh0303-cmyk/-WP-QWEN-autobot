#!/usr/bin/env python3
"""London Project: verified personal-account Coupang Partners fleet insertion.
Only consumes portal-captured personal affiliate URLs and official blog HTML.
"""
import os, json, re, html, hashlib, argparse, time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

WP_USER = os.getenv('WP_USER', 'huh0303@gmail.com')
START = '<!-- LONDON_COUPANG_PARTNERS_FLEET_START -->'
END = '<!-- LONDON_COUPANG_PARTNERS_FLEET_END -->'
DISCLOSURE = '이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.'
SITES = [
 ('korea365.org','KOREA365ORG'),('kstudy365.com','KSTUDY365COM'),('oliveyoungkorea.com','OLIVEYOUNGKOREACOM'),
 ('jobkorea365.com','JOBKOREA365COM'),('k-health365.com','KHEALTH365COM'),('kskin365.com','KSKIN365COM'),
 ('k-trip365.com','KTRIP365COM'),('kfinance365.com','KFINANCE365COM'),('koreainsurance365.com','KOREAINSURANCE365COM'),
 ('koreataxnlaw.com','KOREATAXNLAWCOM'),('koreamedicaltour.com','KOREAMEDICALTOURCOM'),('studyinkorea365.com','STUDYINKOREA365COM'),
 ('jobinkorea365.com','JOBINKOREA365COM'),('kworld365.com','KWORLD365COM'),('koreawedding365.com','KOREAWEDDING365COM'),
 ('jobkoreaglobal.com','JOBKOREAGLOBALCOM'),('koreainvest365.com','KOREAINVEST365COM'),('krealestate365.com','KREALESTATE365COM'),
 ('koreacrypto365.com','KOREACRYPTO365COM'),('ktech365.com','KTECH365COM'),('kieca-korea.org','KIECAKOREAORG'),('koreanews365.com','KOREANEWS365COM')]
CATS = {'topic':2,'korean_life':2,'health':2,'kbeauty':2}

def sess(secret):
 s=requests.Session(); s.auth=(WP_USER,secret); s.headers['User-Agent']='LondonProject-CoupangPartners/2.0'
 retry=Retry(total=3,connect=3,read=3,backoff_factor=1,status_forcelist=[429,500,502,503,504],allowed_methods=['GET','POST'])
 s.mount('https://',HTTPAdapter(max_retries=retry)); return s

def valid_product(p):
 url=p.get('affiliate_url',''); tag=p.get('official_blog_html_tag',''); img=p.get('official_image_url','')
 if p.get('category') not in CATS: raise ValueError('invalid/missing category')
 if not p.get('verified_account_owned') or p.get('capture_source') != 'coupang_partners_portal':
  raise ValueError('personal-account ownership provenance missing')
 if not re.fullmatch(r'https://link\.coupang\.com/a/[A-Za-z0-9]+',url): raise ValueError('not a verified Coupang Partners short URL')
 if not tag or url not in tag or img not in tag or '<a ' not in tag.lower() or '<img ' not in tag.lower():
  raise ValueError('official blog HTML does not match affiliate URL/image')
 if not img.startswith('https://') or 'coupangcdn.com/' not in img: raise ValueError('unverified image host')

def section(post):
 products=post.get('products',[])
 if len(products)!=8: raise ValueError('exactly 8 products required')
 counts={k:0 for k in CATS}
 for p in products: valid_product(p); counts[p['category']]+=1
 if counts!=CATS: raise ValueError('category mix mismatch: '+str(counts))
 cards=[]
 for p in products:
  u=html.escape(p['affiliate_url'],quote=True); title=html.escape(p.get('product_title') or p.get('display_title_en') or '추천 상품')
  tag=p['official_blog_html_tag']
  # Preserve account-generated destination and image creative exactly; add sponsored rel only.
  tag=tag.replace('<a ', '<a rel="sponsored nofollow noopener" ', 1)
  cards.append('<article class="lp-coupang-card"><a class="lp-coupang-image" href="'+u+'" target="_blank" rel="sponsored nofollow noopener">'+tag+'</a><h3>'+title+'</h3><a class="lp-coupang-cta" href="'+u+'" target="_blank" rel="sponsored nofollow noopener">쇼핑하기</a></article>')
 return START+'\n<!-- wp:html -->\n<style>.lp-coupang-wrap{margin:32px 0;padding:22px 16px;border:1px solid #e5e7eb;border-radius:12px}.lp-coupang-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.lp-coupang-card{min-width:0;border:1px solid #e5e7eb;border-radius:12px;padding:12px;text-align:center;display:flex;flex-direction:column;align-items:center}.lp-coupang-image img{display:block;max-width:100%;height:auto;object-fit:contain}.lp-coupang-card h3{font-size:14px;line-height:1.5;margin:12px 0;overflow-wrap:anywhere}.lp-coupang-cta{display:inline-block;margin-top:auto;background:#356dff;color:#fff!important;padding:9px 18px;border-radius:24px;text-decoration:none;font-weight:700}@media(max-width:760px){.lp-coupang-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.lp-coupang-wrap{padding:16px 10px}}@media(max-width:360px){.lp-coupang-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.lp-coupang-card{padding:8px}}</style>\n<section class="lp-coupang-wrap"><p>'+DISCLOSURE+'</p><h2>함께 살펴볼 만한 추천 상품</h2><div class="lp-coupang-grid">'+'\n'.join(cards)+'</div></section>\n<!-- /wp:html -->\n'+END

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--apply',action='store_true'); ap.add_argument('--sites',default='all'); ap.add_argument('--limit',type=int,default=0); ap.add_argument('--map',default='data/affiliate/fleet-placements.json'); ap.add_argument('--out',default='reports/coupang-partners-fleet-report.json'); args=ap.parse_args()
 mapping=json.loads(Path(args.map).read_text(encoding='utf-8-sig')); report={'mode':'apply' if args.apply else 'dry_run','per_post':8,'sites':{}}
 selected=[x for x in SITES if args.sites=='all' or x[0] in args.sites.split(',')]
 for domain,secret_name in selected:
  secret=os.getenv(secret_name); entries=mapping.get('sites',{}).get(domain,[]); out=[]
  if not entries: report['sites'][domain]={'status':'BLOCKED_NO_SITE_PLACEMENT_MAP','posts':0}; continue
  if args.apply and not secret: report['sites'][domain]={'status':'BLOCKED_NO_WP_CREDENTIAL','posts':0}; continue
  s=sess(secret) if secret else requests.Session(); base='https://'+domain
  for item in entries[:args.limit or None]:
   pid=item['post_id']
   try:
    r=s.get(f'{base}/wp-json/wp/v2/posts/{pid}',params={'context':'edit'},timeout=60); r.raise_for_status(); p=r.json()
    if p.get('status')!='publish': raise ValueError('not published')
    raw=p.get('content',{}).get('raw')
    if raw is None: raise ValueError('raw content unavailable; no write')
    block=section(item); new=(raw[:raw.index(START)]+block+raw[raw.index(END)+len(END):]) if START in raw and END in raw else raw.rstrip()+'\n\n'+block+'\n'
    rec={'post_id':pid,'link':item.get('link'),'category_counts':CATS,'unique_affiliate_links':len({x['affiliate_url'] for x in item['products']}),'status':'DRY_RUN_VALIDATED'}
    if rec['unique_affiliate_links']!=8: raise ValueError('duplicate affiliate URLs')
    if args.apply and new!=raw:
     w=s.post(f'{base}/wp-json/wp/v2/posts/{pid}',json={'content':new},timeout=90); w.raise_for_status()
     q=s.get(f'{base}/wp-json/wp/v2/posts/{pid}',params={'context':'edit'},timeout=60); q.raise_for_status(); chk=q.json().get('content',{}).get('raw') or ''
     if START not in chk or sum(chk.count(x['affiliate_url']) for x in item['products'])<16: raise ValueError('REST read-back verification failed')
     pub=requests.get(f'{base}/wp-json/wp/v2/posts/{pid}',timeout=45); pub.raise_for_status(); rendered=pub.json().get('content',{}).get('rendered','')
     if any(x['affiliate_url'] not in rendered for x in item['products']): raise ValueError('public rendered affiliate URL missing')
     rec['status']='UPDATED_VERIFIED'
    out.append(rec)
   except Exception as e: out.append({'post_id':pid,'status':'ERROR','error':str(e)[:400]})
  report['sites'][domain]={'posts':len(out),'updated':sum(x['status']=='UPDATED_VERIFIED' for x in out),'dry_run_validated':sum(x['status']=='DRY_RUN_VALIDATED' for x in out),'errors':sum(x['status']=='ERROR' for x in out),'results':out}
 Path(args.out).parent.mkdir(parents=True,exist_ok=True); Path(args.out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({k:{a:v.get(a) for a in ('posts','updated','dry_run_validated','errors','status')} for k,v in report['sites'].items()},ensure_ascii=False))
if __name__=='__main__': main()
